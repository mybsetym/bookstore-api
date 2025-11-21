from fastapi import APIRouter, Body, Path, HTTPException, Query
from pydantic import BaseModel
from app.utils.db import execute_query, execute_query_one, execute_update
from datetime import datetime, timezone
from typing import Optional

# 创建路由实例（前缀统一为/orders，标签归类为“订单模块”，方便文档区分）
router = APIRouter(
    prefix="/orders",
    tags=["订单模块"],
    responses={404: {"description": "订单/商品不存在"}}
)


# --------------------------
# 1. 数据模型（Pydantic）：定义请求/响应格式，自动校验参数
# --------------------------
class CreateOrderRequest(BaseModel):
    """创建订单的请求参数"""
    product_id: int  # 商品ID（对应book表的book_id）
    buyer_id: int  # 买家ID（对应logindata表的ID）
    quantity: int = 1  # 购买数量，默认1本（二手书通常单本交易，可调整）
    fulfillment_type: str  # 履约方式：self_pickup（自提）/logistics（第三方物流）
    pickup_location_id: Optional[int] = None  # 自提地点ID（履约方式为self_pickup时必传）
    receiver_name: Optional[str] = None  # 收件人姓名（物流方式必传）
    receiver_phone: Optional[str] = None  # 收件人电话（物流方式必传）
    receiver_address: Optional[str] = None  # 收件地址（物流方式必传）
    remark: Optional[str] = None  # 订单备注（如“请尽快发货”）


class UpdateOrderStatusRequest(BaseModel):
    """更新订单状态的请求参数"""
    order_id: int  # 订单ID
    status: str  # 目标状态：pending_pay（待付款）/pending_ship（待发货）/pending_receive（待收货）/completed（已完成）/cancelled（已取消）
    operator_id: int  # 操作人ID（买家/卖家/管理员）
    logistics_no: Optional[str] = None  # 物流单号（卖家发货时传）


# --------------------------
# 2. 核心接口实现
# --------------------------
@router.post("/", summary="创建订单（买家下单）")
def create_order(req: CreateOrderRequest):
    """
    买家在商品详情页点击“下单”时调用，核心逻辑：
    1. 校验商品是否存在、在售且库存充足
    2. 校验履约方式对应的参数是否完整（如自提需选地点，物流需填收件信息）
    3. 生成唯一订单号，插入订单数据
    4. 扣减商品库存（乐观锁防超卖）
    """
    # 步骤1：校验商品状态与库存
    product = execute_query_one(
        "SELECT b.book_id, b.seller_ID, b.price, b.stock, b.status "
        "FROM book b WHERE b.book_id = %s",
        (req.product_id,)
    )
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    if product["status"] != 1:  # status=1表示“在售”
        raise HTTPException(status_code=400, detail="商品已下架，无法下单")
    if product["stock"] < req.quantity:
        raise HTTPException(status_code=400, detail="商品库存不足")

    # 步骤2：校验履约方式参数完整性
    if req.fulfillment_type == "self_pickup" and not req.pickup_location_id:
        raise HTTPException(status_code=400, detail="自提方式需选择自提地点")
    if req.fulfillment_type == "logistics":
        if not (req.receiver_name and req.receiver_phone and req.receiver_address):
            raise HTTPException(status_code=400, detail="物流方式需填写完整收件信息")

    # 步骤3：计算订单总金额（单价*数量，暂不考虑折扣）
    total_amount = product["price"] * req.quantity

    # 步骤4：插入订单数据（订单初始状态为“待付款”）
    now = datetime.now(timezone.utc)
    # 生成唯一订单号：格式YYYYMMDDHHMMSS+买家ID后4位（确保不重复）
    order_no = f"{now.strftime('%Y%m%d%H%M%S')}{str(req.buyer_id)[-4:].zfill(4)}"
    insert_sql = """
                 INSERT INTO orders (order_no, buyer_id, seller_id, product_id, quantity, total_amount, \
                                     fulfillment_type, pickup_location_id, receiver_name, receiver_phone, \
                                     receiver_address, \
                                     remark, status, create_time, update_time) \
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) \
                 """
    insert_params = (
        order_no, req.buyer_id, product["seller_ID"], req.product_id, req.quantity, total_amount,
        req.fulfillment_type, req.pickup_location_id, req.receiver_name, req.receiver_phone, req.receiver_address,
        req.remark, "pending_pay", now, now
    )
    execute_update(insert_sql, insert_params)

    # 步骤5：扣减商品库存（乐观锁：仅当库存>=购买数量时才扣减，防止超卖）
    update_stock_sql = """
                       UPDATE book \
                       SET stock       = stock - %s, \
                           update_time = %s
                       WHERE book_id = %s \
                         AND stock >= %s \
                       """
    update_stock_params = (req.quantity, now, req.product_id, req.quantity)
    affected_rows = execute_update(update_stock_sql, update_stock_params)

    # 若库存扣减失败（如并发下单导致库存不足），回滚订单
    if affected_rows == 0:
        delete_order_sql = "DELETE FROM orders WHERE order_no = %s"
        execute_update(delete_order_sql, (order_no,))
        raise HTTPException(status_code=400, detail="下单失败，商品库存已不足")

    # 步骤6：返回订单信息（含订单号，用于后续支付、查询）
    return {
        "code": 201,
        "message": "订单创建成功",
        "data": {
            "order_id": execute_query_one("SELECT LAST_INSERT_ID() AS order_id")["order_id"],
            "order_no": order_no,
            "total_amount": total_amount,
            "status": "pending_pay"
        }
    }


@router.get("/{order_id}", summary="获取订单详情")
def get_order_detail(order_id: int = Path(..., ge=1, description="订单ID")):
    """
    买家/卖家查看订单详情，返回订单基本信息、商品信息、收件/自提信息
    """
    order_detail = execute_query_one(
        "SELECT o.*, b.book_name, b.cover_img, b.author, b.price, "
        "u.nickname AS seller_name, s.school_name AS pickup_location_name "
        "FROM orders o "
        "LEFT JOIN book b ON o.product_id = b.book_id "
        "LEFT JOIN users u ON o.seller_id = u.user_id "
        "LEFT JOIN school s ON o.pickup_location_id = s.school_id "
        "WHERE o.order_id = %s",
        (order_id,)
    )
    if not order_detail:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 格式化返回数据（可选：隐藏敏感信息，如收件人电话中间4位打码）
    if order_detail["receiver_phone"]:
        phone = order_detail["receiver_phone"]
        order_detail["receiver_phone"] = f"{phone[:3]}****{phone[-4:]}"

    return {
        "code": 200,
        "message": "获取订单详情成功",
        "data": order_detail
    }


@router.get("/", summary="获取订单列表（买家/卖家视角）")
def get_order_list(
        user_id: int = Query(..., description="用户ID（买家/卖家）"),
        user_type: str = Query(..., description="用户类型：buyer（买家）/seller（卖家）"),
        status: Optional[str] = Query(None, description="订单状态筛选（留空查所有状态）"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页条数")
):
    """
    买家查看自己的所有订单，卖家查看自己收到的所有订单
    支持按状态筛选（如“待付款”“待发货”），分页返回
    """
    # 构建查询条件：区分买家/卖家
    base_sql = """
               SELECT o.order_id, \
                      o.order_no, \
                      o.total_amount, \
                      o.status, \
                      o.create_time,
                      b.book_name, \
                      b.cover_img, \
                      b.price, \
                      u.nickname AS other_party_name
               FROM orders o
                        LEFT JOIN book b ON o.product_id = b.book_id
                        LEFT JOIN users u ON
                   (CASE WHEN %s = 'buyer' THEN o.seller_id ELSE o.buyer_id END) = u.user_id
               WHERE 1 = 1 \
               """
    params = [user_type]

    # 筛选用户视角的订单
    if user_type == "buyer":
        base_sql += " AND o.buyer_id = %s"
    else:  # seller
        base_sql += " AND o.seller_id = %s"
    params.append(user_id)

    # 筛选订单状态
    if status:
        valid_status = ["pending_pay", "pending_ship", "pending_receive", "completed", "cancelled"]
        if status not in valid_status:
            raise HTTPException(status_code=400, detail=f"无效的状态值，可选：{valid_status}")
        base_sql += " AND o.status = %s"
        params.append(status)

    # 分页与排序（按创建时间倒序，最新订单在前）
    base_sql += " ORDER BY o.create_time DESC LIMIT %s OFFSET %s"
    offset = (page - 1) * page_size
    params.extend([page_size, offset])

    # 执行查询，获取订单列表
    order_list = execute_query(base_sql, params)

    # 获取总条数（用于分页显示）
    count_sql = """
                SELECT COUNT(*) AS total
                FROM orders o
                WHERE
                    (CASE WHEN %s = 'buyer' THEN o.buyer_id ELSE o.seller_id END) = %s \
                """ + (" AND o.status = %s" if status else "")
    count_params = [user_type, user_id]
    if status:
        count_params.append(status)
    total = execute_query_one(count_sql, count_params)["total"]

    return {
        "code": 200,
        "message": "获取订单列表成功",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "order_list": order_list
        }
    }


@router.put("/status", summary="更新订单状态（如发货、确认收货）")
def update_order_status(req: UpdateOrderStatusRequest):
    """
    订单状态流转核心接口，权限控制：
    - 买家：可取消待付款订单、确认收货（状态改为completed）
    - 卖家：可取消待付款订单、标记发货（状态改为pending_receive，需传物流单号）
    - 管理员：可强制修改所有状态（需额外校验角色，此处预留）
    """
    # 步骤1：校验订单存在性
    order = execute_query_one(
        "SELECT o.status, o.buyer_id, o.seller_id FROM orders o WHERE o.order_id = %s",
        (req.order_id,)
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 步骤2：校验操作人权限
    current_status = order["status"]
    operator_id = req.operator_id
    # 权限规则：操作人必须是买家/卖家，或管理员（此处暂未实现管理员角色，需补充）
    if operator_id != order["buyer_id"] and operator_id != order["seller_id"]:
        raise HTTPException(status_code=403, detail="无权限修改此订单")

    # 步骤3：校验状态流转合法性（防止非法状态变更，如待收货直接改为已取消）
    valid_transitions = {
        "pending_pay": ["cancelled", "pending_ship"],  # 待付款→取消/待发货（卖家发货前需买家付款，此处简化）
        "pending_ship": ["cancelled", "pending_receive"],  # 待发货→取消/待收货（卖家发货）
        "pending_receive": ["completed", "cancelled"],  # 待收货→完成（买家确认）/取消
        "completed": [],  # 已完成订单不可修改
        "cancelled": []  # 已取消订单不可修改
    }
    if req.status not in valid_transitions[current_status]:
        raise HTTPException(
            status_code=400,
            detail=f"当前状态[{current_status}]不支持转为[{req.status}]，允许的流转：{valid_transitions[current_status]}"
        )

    # 步骤4：处理特殊状态变更（如发货需传物流单号）
    update_sql = "UPDATE orders SET status = %s, update_time = %s"
    update_params = [req.status, datetime.now(timezone.utc)]
    if req.status == "pending_receive" and not req.logistics_no:
        raise HTTPException(status_code=400, detail="标记发货需填写物流单号")
    if req.status == "pending_receive":
        update_sql += ", logistics_no = %s"
        update_params.append(req.logistics_no)

    # 步骤5：执行状态更新
    update_sql += " WHERE order_id = %s"
    update_params.append(req.order_id)
    execute_update(update_sql, update_params)

    return {
        "code": 200,
        "message": f"订单状态已更新为[{req.status}]",
        "data": {"order_id": req.order_id, "status": req.status}
    }