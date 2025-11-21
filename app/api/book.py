# app/api/book.py
from fastapi import APIRouter, HTTPException, Query, Body, Path
from app.utils.db import  execute_query_one, execute_update, execute_query_paginated

router = APIRouter(
    prefix="/books",
    tags=["图书模块"]
)


@router.get("/", summary="获取图书列表（支持学校筛选）")
def get_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    category: str = Query(None),
    seller_id: int = Query(None),
    school_id: int = Query(None, description="按学校筛选")  # 新增
):
    sql = "SELECT * FROM book WHERE 1=1"
    params = []
    if category:
        sql += " AND category = %s"
        params.append(category)
    if seller_id:
        sql += " AND seller_ID = %s"
        params.append(seller_id)
    if school_id:  # 新增学校筛选（关联卖家的学校）
        sql += " AND seller_ID IN (SELECT user_id FROM users WHERE school_id = %s)"
        params.append(school_id)
    sql += " ORDER BY create_time DESC"
    result = execute_query_paginated(sql, params, page, page_size)
    return {"code": 200, "message": "获取成功", "data": result}

@router.get("/{book_id}", summary="获取图书详情")
def get_book_detail(book_id: int = Path(..., description="图书ID")):
    sql = "SELECT * FROM book WHERE book_id = %s"
    book = execute_query_one(sql, (book_id,))
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")
    return {
        "code": 200,
        "message": "获取成功",
        "data": book
    }


@router.post("/", summary="添加图书")
def add_book(
        ISBN: str = Body(..., description="ISBN"),
        book_name: str = Body(..., description="图书名称"),
        author: str = Body(..., description="作者"),
        publisher: str = Body(..., description="出版社"),
        publish_date: str = Body(..., description="出版日期"),
        category: str = Body(..., description="分类"),
        book_desc: str = Body(..., description="图书描述"),
        cover_img: str = Body(..., description="封面图URL"),
        seller_ID: int = Body(..., description="卖家ID"),
        price: float = Body(..., description="价格"),
        condition: str = Body(..., description="图书状态（全新/二手等）"),
        status: int = Body(..., description="状态（0-下架，1-上架）"),
        status_desc: str = Body(None, description="状态描述"),
        stock: int = Body(..., description="库存"),
        view: int = Body(0, description="浏览量，默认0")
):
    sql = """
          INSERT INTO book (ISBN, book_name, author, publisher, publish_date, category, book_desc, cover_img, seller_ID, \
                            price, condition, status, status_desc, stock, view, create_time, update_time)
          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()) \
          """
    params = [ISBN, book_name, author, publisher, publish_date, category, book_desc, cover_img, seller_ID, price,
              condition, status, status_desc, stock, view]
    execute_update(sql, params)
    return {
        "code": 200,
        "message": "添加成功",
        "data": None
    }


@router.put("/{book_id}", summary="更新图书")
def update_book(
        book_id: int = Path(..., description="图书ID"),
        book_name: str = Body(None, description="图书名称"),
        price: float = Body(None, description="价格"),
        stock: int = Body(None, description="库存"),
        status: int = Body(None, description="状态")
):
    update_fields = []
    params = []
    if book_name:
        update_fields.append("book_name = %s")
        params.append(book_name)
    if price:
        update_fields.append("price = %s")
        params.append(price)
    if stock:
        update_fields.append("stock = %s")
        params.append(stock)
    if status:
        update_fields.append("status = %s")
        params.append(status)
    update_fields.append("update_time = NOW()")

    if not update_fields:
        raise HTTPException(status_code=400, detail="至少更新一个字段")

    sql = f"UPDATE book SET {', '.join(update_fields)} WHERE book_id = %s"
    params.append(book_id)
    execute_update(sql, params)
    return {
        "code": 200,
        "message": "更新成功",
        "data": None
    }