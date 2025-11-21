# app/api/search.py
from fastapi import APIRouter, Query
from app.utils.db import execute_query, execute_query_paginated

router = APIRouter(
    prefix="/search",
    tags=["搜索与筛选模块"]
)


@router.get("/books", summary="图书综合搜索（支持多条件筛选）")
def search_books(
        keyword: str = Query(..., description="搜索关键词（匹配书名/作者/ISBN）"),
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=50),
        min_price: float = Query(None, description="最低价格"),
        max_price: float = Query(None, description="最高价格"),
        category: str = Query(None, description="图书分类"),
        condition: str = Query(None, description="图书状态（全新/二手等）"),
        school_id: int = Query(None, description="按学校筛选")
):
    # 构造搜索 SQL（支持模糊匹配+多条件筛选）
    sql = """
          SELECT b.*, u.nickname AS seller_nickname, s.school_name
          FROM book b
                   LEFT JOIN users u ON b.seller_ID = u.user_id
                   LEFT JOIN school s ON u.school_id = s.school_id
          WHERE (b.book_name LIKE %s OR b.author LIKE %s OR b.ISBN LIKE %s) \
          """
    params = [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]  # 关键词模糊匹配

    # 追加筛选条件
    if min_price is not None:
        sql += " AND b.price >= %s"
        # noinspection PyTypeChecker
        params.append(min_price)
    if max_price is not None:
        sql += " AND b.price <= %s"
        params.append(max_price)
    if category:
        sql += " AND b.category = %s"
        params.append(category)
    if condition:
        sql += " AND b.condition = %s"
        params.append(condition)
    if school_id:
        sql += " AND u.school_id = %s"
        params.append(school_id)

    # 按创建时间倒序（最新发布在前）
    sql += " ORDER BY b.create_time DESC"

    # 分页查询
    result = execute_query_paginated(sql, params, page, page_size)
    return {
        "code": 200,
        "message": "搜索成功",
        "data": result
    }


@router.get("/categories", summary="获取所有图书分类（用于筛选下拉框）")
def get_book_categories():
    """返回去重后的图书分类，供前端筛选组件使用"""
    sql = "SELECT DISTINCT category FROM book ORDER BY category"
    categories = execute_query(sql)
    return {
        "code": 200,
        "message": "获取成功",
        "data": [item["category"] for item in categories]
    }