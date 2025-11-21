from fastapi import APIRouter, Body, Query, HTTPException, Path
from pydantic import BaseModel
from app.utils.db import execute_query, execute_query_one, execute_update
from datetime import datetime, timezone
from typing import Optional, List

# 路由配置（前缀/reviews，标签“评价模块”，统一归类）
router = APIRouter(
    prefix="/reviews",
    tags=["评价模块"],
    responses={404: {"description": "订单/评价不存在"}}
)


# --------------------------
# 数据模型：参数校验+格式定义
# --------------------------
class CreateReviewRequest(BaseModel):
    """创建评价的请求参数"""
    order_id: int  # 关联的订单ID（必须是已完成状态）
    rating: int = Body(..., ge=1, le=5, description="评分（1-5星）")
    content: Optional[str] = Body(None, description="评价文字（可选，最多500字）")
    img_urls: Optional[List[str]] = Body(None, description="评价图片URL列表（可选，最多3张）")
    reviewer_id: int  # 评价人ID（必须是该订单的买家）


# --------------------------
# 核心接口实现
# --------------------------
@router.post("/", summary="创建评价（买家对商品/卖家）")
def create_review(req: CreateReviewRequest):
    """
    核心约束：
    1. 仅订单状态为“completed”（已完成）可评价
    2. 一个订单仅能评价一次，不可重复提交
    3. 评价关联商品和卖家，影响卖家信誉分
    """
    # 步骤1：校验订单合法性（存在+已完成+评价人是买家）
    order = execute_query_one(
        "SELECT o.status, o.seller_id, o.product_id "
        "FROM orders o WHERE o.order_id = %s AND o.buyer_id = %s",
        (req.order_id, req.reviewer_id)
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在或非当前用户订单")
    if order["status"] != "completed":
        raise HTTPException(status_code=400, detail="仅已完成的订单可评价")

    # 步骤2：校验是否重复评价
    existing_review = execute_query_one(
        "SELECT id FROM reviews WHERE order_id = %s",
        (req.order_id,)
    )
    if existing_review:
        raise HTTPException(status_code=400, detail="该订单已评价，不可重复提交")

    # 步骤3：处理评价图片（列表转字符串存储，便于数据库存储，前端展示时再拆分）
    img_str = ",".join(req.img_urls) if req.img_urls else None
    # 限制图片数量（最多3张）
    if req.img_urls and len(req.img_urls) > 3:
        raise HTTPException(status_code=400, detail="评价图片最多支持3张")

    # 步骤4：插入评价数据
    now = datetime.now(timezone.utc)
    insert_sql = """
                 INSERT INTO reviews (order_id, reviewer_id, seller_id, product_id, rating, content, img_urls, \
                                      create_time, update_time) \
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) \
                 """
    insert_params = (
        req.order_id, req.reviewer_id, order["seller_id"], order["product_id"],
        req.rating, req.content[:500] if req.content else None,  # 限制文字长度个500字
        img_str, now, now
    )
    execute_update(insert_sql, insert_params)

    # 步骤5：更新卖家平均信誉分（可选，提升平台信任度）
    seller_stats = execute_query_one(
        "SELECT AVG(rating) AS avg_rating, COUNT(*) AS review_count "
        "FROM reviews WHERE seller_id = %s",
        (order["seller_id"],)
    )
    # 保留1位小数，无评价时默认5星
    avg_rating = round(seller_stats["avg_rating"], 1) if seller_stats["avg_rating"] else 5.0
    review_count = seller_stats["review_count"] or 0
    # 更新users表的卖家信誉分字段
    execute_update(
        "UPDATE users SET avg_rating = %s, review_count = %s, update_time = %s "
        "WHERE user_id = %s",
        (avg_rating, review_count, now, order["seller_id"])
    )

    return {
        "code": 201,
        "message": "评价提交成功",
        "data": {
            "review_id": execute_query_one("SELECT LAST_INSERT_ID() AS id")["id"],
            "avg_rating": avg_rating  # 返回卖家当前平均评分
        }
    }


@router.get("/product/{product_id}", summary="获取商品的评价列表")
def get_product_reviews(
        product_id: int = Path(..., ge=1, description="商品ID"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=50, description="每页条数")
):
    """商品详情页展示评价，按评价时间倒序排列，支持分页"""
    # 计算分页偏移量
    offset = (page - 1) * page_size

    # 查询评价列表（关联评价人昵称、头像，隐藏敏感信息）
    review_list = execute_query(
        """
        SELECT r.id,
               r.rating,
               r.content,
               r.img_urls,
               r.create_time,
               u.nickname AS reviewer_name,
               u.avatar   AS reviewer_avatar
        FROM reviews r
                 LEFT JOIN users u ON r.reviewer_id = u.user_id
        WHERE r.product_id = %s
        ORDER BY r.create_time DESC
            LIMIT %s
        OFFSET %s
        """,
        (product_id, page_size, offset)
    )

    # 处理评价图片（字符串转列表，方便前端展示）
    for review in review_list:
        if review["img_urls"]:
            review["img_urls"] = review["img_urls"].split(",")
        else:
            review["img_urls"] = []

    # 查询该商品的评价总数和平均评分（用于商品详情页展示）
    product_stats = execute_query_one(
        """
        SELECT AVG(rating) AS avg_rating, COUNT(*) AS total_review
        FROM reviews
        WHERE product_id = %s
        """,
        (product_id,)
    )
    avg_rating = round(product_stats["avg_rating"], 1) if product_stats["avg_rating"] else 0.0
    total_review = product_stats["total_review"] or 0

    return {
        "code": 200,
        "message": "获取评价列表成功",
        "data": {
            "product_id": product_id,
            "avg_rating": avg_rating,
            "total_review": total_review,
            "page": page,
            "page_size": page_size,
            "review_list": review_list
        }
    }


@router.get("/seller/{seller_id}", summary="获取卖家的评价列表")
def get_seller_reviews(
        seller_id: int = Path(..., ge=1, description="卖家ID"),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=50)
):
    """买家查看卖家主页时，展示该卖家的所有评价"""
    offset = (page - 1) * page_size

    review_list = execute_query(
        """
        SELECT r.id,
               r.rating,
               r.content,
               r.create_time,
               r.img_urls,
               u.nickname  AS reviewer_name,
               b.book_name AS product_name
        FROM reviews r
                 LEFT JOIN users u ON r.reviewer_id = u.user_id
                 LEFT JOIN book b ON r.product_id = b.book_id
        WHERE r.seller_id = %s
        ORDER BY r.create_time DESC
            LIMIT %s
        OFFSET %s
        """,
        (seller_id, page_size, offset)
    )

    # 处理图片列表
    for review in review_list:
        review["img_urls"] = review["img_urls"].split(",") if review["img_urls"] else []

    # 卖家整体信誉统计
    seller_stats = execute_query_one(
        "SELECT AVG(rating) AS avg_rating, COUNT(*) AS total_review FROM reviews WHERE seller_id = %s",
        (seller_id,)
    )
    avg_rating = round(seller_stats["avg_rating"], 1) if seller_stats["avg_rating"] else 0.0
    total_review = seller_stats["total_review"] or 0

    return {
        "code": 200,
        "message": "获取卖家评价列表成功",
        "data": {
            "seller_id": seller_id,
            "avg_rating": avg_rating,
            "total_review": total_review,
            "review_list": review_list
        }
    }