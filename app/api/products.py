from fastapi import APIRouter, Query, Path, Body, HTTPException
from typing import Optional
from app.utils.db import (
    execute_query,
    execute_query_one,
    execute_query_paginated,
    execute_update,
)
from datetime import datetime, timezone

router = APIRouter(
    prefix="/products",  # 接口前缀统一为 /products
    tags=["商品模块"],  # 归类到“商品模块”，文档更清晰
    responses={404: {"description": "商品/分类不存在"}},
)


# --------------------------
#  分类核心接口：获取所有小类列表（给前端渲染分类菜单）
# --------------------------
@router.get("/categories", summary="获取所有商品小类")
def get_all_categories():
    """
    后端仅存储小类，前端可根据此列表自行分组为大类；
    返回数据格式：[{id: 1, name: "高校教材", description: "高等教育教材"}, ...]
    """
    sql = "SELECT id, name, description FROM categories ORDER BY name;"
    categories = execute_query(sql)
    return {
        "code": 200,
        "message": "获取分类成功",
        "data": categories
    }


# --------------------------
#  商品列表接口（支持按分类ID筛选）
# --------------------------
@router.get("/", summary="获取商品列表")
def get_products(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量"),
        category_id: Optional[int] = Query(None, description="按小类ID筛选（从 /products/categories 获取）"),
        min_price: Optional[float] = Query(None, ge=0, description="最低价格"),
        max_price: Optional[float] = Query(None, ge=0, description="最高价格"),
        condition: Optional[str] = Query(None, description="图书状态（全新/二手）"),
        school_id: Optional[int] = Query(None, description="按学校ID筛选"),
        search: Optional[str] = Query(None, description="搜索关键词（书名/作者/ISBN）"),
        status: Optional[int] = Query(1, description="商品状态（1-上架，0-下架）"),
):
    sql = """
          SELECT b.*, u.nickname as seller_name, s.school_name, c.name as category_name
          FROM book b
                   LEFT JOIN users u ON b.seller_ID = u.user_id
                   LEFT JOIN school s ON u.school_id = s.school_id
                   LEFT JOIN categories c ON b.category_id = c.id # 关联分类表，返回分类名称
          WHERE 1=1 \
          """
    params = []

    # 按分类ID筛选（核心联动逻辑）
    if category_id:
        sql += " AND b.category_id = %s"
        params.append(category_id)
    # 其他筛选条件（价格、状态等）
    if status is not None:
        sql += " AND b.status = %s"
        params.append(status)
    if min_price is not None:
        sql += " AND b.price >= %s"
        params.append(min_price)
    if max_price is not None:
        sql += " AND b.price <= %s"
        params.append(max_price)
    if condition:
        sql += " AND b.condition = %s"
        params.append(condition)
    if school_id:
        sql += " AND u.school_id = %s"
        params.append(school_id)
    if search:
        sql += " AND (b.book_name LIKE %s OR b.author LIKE %s OR b.ISBN LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    sql += " ORDER BY b.create_time DESC"
    result = execute_query_paginated(sql, params, page, page_size)
    return {
        "code": 200,
        "message": "获取商品成功",
        "data": result
    }


# --------------------------
#  商品创建接口（关联分类ID）
# --------------------------
@router.post("/", summary="创建商品")
def create_product(
        seller_id: int = Body(..., description="卖家ID（user_id）"),
        book_name: str = Body(..., min_length=1, max_length=100, description="书名"),
        author: str = Body(..., description="作者"),
        publisher: str = Body(..., description="出版社"),
        publish_date: str = Body(..., description="出版日期（格式：YYYY-MM-DD）"),
        ISBN: str = Body(..., description="ISBN编号"),
        category_id: int = Body(..., description="小类ID（从 /products/categories 获取，必填）"),
        price: float = Body(..., gt=0, description="售价（大于0）"),
        stock: int = Body(..., ge=0, description="库存（大于等于0）"),
        condition: str = Body(..., description="图书状态（全新/二手）"),
        cover_img: Optional[str] = Body(None, description="封面图片URL"),
        book_desc: Optional[str] = Body(None, description="图书描述"),
):
    # 1. 校验卖家是否存在
    if not execute_query_one("SELECT user_id FROM users WHERE user_id = %s", (seller_id,)):
        raise HTTPException(status_code=400, detail="卖家不存在")

    # 2. 校验分类ID是否有效（核心联动逻辑）
    if not execute_query_one("SELECT id FROM categories WHERE id = %s", (category_id,)):
        raise HTTPException(status_code=400, detail="无效的分类ID，请从 /products/categories 获取")

    # 3. 插入商品数据（关联 category_id）
    now = datetime.now(timezone.utc)
    sql = """
          INSERT INTO book (book_name, author, publisher, publish_date, ISBN, category_id, \
                            price, stock, condition, cover_img, book_desc, seller_ID, status, \
                            create_time, update_time) \
          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s) \
          """
    params = (
        book_name, author, publisher, publish_date, ISBN, category_id,
        price, stock, condition, cover_img, book_desc, seller_id, now, now
    )
    execute_update(sql, params)

    # 4. 返回新创建商品的ID
    new_book_id = execute_query_one("SELECT LAST_INSERT_ID() as book_id")["book_id"]
    return {
        "code": 201,
        "message": "商品创建成功",
        "data": {"book_id": new_book_id}
    }


# --------------------------
#  商品更新接口（支持修改分类ID）
# --------------------------
@router.put("/{book_id}", summary="更新商品信息")
def update_product(
        book_id: int = Path(..., ge=1, description="商品ID（book_id）"),
        seller_id: int = Body(..., description="卖家ID（用于权限校验）"),
        # 可选更新字段（分类ID可修改）
        category_id: Optional[int] = Body(None, description="新的小类ID（从 /products/categories 获取）"),
        book_name: Optional[str] = Body(None, min_length=1, max_length=100, description="书名"),
        price: Optional[float] = Body(None, gt=0, description="售价"),
        stock: Optional[int] = Body(None, ge=0, description="库存"),
        condition: Optional[str] = Body(None, description="图书状态"),
        cover_img: Optional[str] = Body(None, description="封面图片URL"),
        book_desc: Optional[str] = Body(None, description="图书描述"),
        status: Optional[int] = Body(None, description="商品状态（1-上架，0-下架）"),
):
    # 1. 校验商品是否存在
    product = execute_query_one("SELECT seller_ID FROM book WHERE book_id = %s", (book_id,))
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 2. 权限校验（仅卖家可修改）
    if product["seller_ID"] != seller_id:
        raise HTTPException(status_code=403, detail="无权限修改此商品")

    # 3. 构建更新字段（含分类ID校验）
    update_fields = []
    params = []

    if category_id is not None:
        # 校验新分类ID是否有效
        if not execute_query_one("SELECT id FROM categories WHERE id = %s", (category_id,)):
            raise HTTPException(status_code=400, detail="无效的分类ID")
        update_fields.append("category_id = %s")
        params.append(category_id)
    if book_name is not None:
        update_fields.append("book_name = %s")
        params.append(book_name)
    if price is not None:
        update_fields.append("price = %s")
        params.append(price)
    if stock is not None:
        update_fields.append("stock = %s")
        params.append(stock)
    if condition is not None:
        update_fields.append("condition = %s")
        params.append(condition)
    if cover_img is not None:
        update_fields.append("cover_img = %s")
        params.append(cover_img)
    if book_desc is not None:
        update_fields.append("book_desc = %s")
        params.append(book_desc)
    if status is not None:
        update_fields.append("status = %s")
        params.append(status)

    # 4. 执行更新（必须有更新字段才执行）
    if not update_fields:
        raise HTTPException(status_code=400, detail="至少需要更新一个字段")
    update_fields.append("update_time = %s")
    params.extend([datetime.now(timezone.utc), book_id])  # 拼接更新时间和商品ID

    sql = f"UPDATE book SET {', '.join(update_fields)} WHERE book_id = %s"
    execute_update(sql, params)

    return {
        "code": 200,
        "message": "商品更新成功",
        "data": {"book_id": book_id}
    }


# --------------------------
#  商品详情接口（返回分类名称）
# --------------------------
@router.get("/{book_id}", summary="获取商品详情")
def get_product_detail(book_id: int = Path(..., ge=1, description="商品ID")):
    sql = """
          SELECT b.*, u.nickname as seller_name, s.school_name, c.id as category_id, c.name as category_name
          FROM book b
                   LEFT JOIN users u ON b.seller_ID = u.user_id
                   LEFT JOIN school s ON u.school_id = s.school_id
                   LEFT JOIN categories c ON b.category_id = c.id # 关联分类表，返回分类ID和名称
          WHERE b.book_id = %s \
          """
    product = execute_query_one(sql, (book_id,))
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return {
        "code": 200,
        "message": "获取商品详情成功",
        "data": product
    }