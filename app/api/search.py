# app/api/search.py
from fastapi import APIRouter, Query, HTTPException
from app.utils.db import  execute_query_paginated,get_db_connection
import pymysql
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
    conn = None  # 提前初始化conn，避免finally中变量未定义
    cursor = None
    try:
        # 1. 建立数据库连接
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)  # 这里要确保pymysql已导入

        # 2. 关联查询分类名称（核心逻辑正确，保留）
        sql = """
        SELECT DISTINCT c.name AS category
        FROM book b
        LEFT JOIN categories c ON b.category_id = c.id
        WHERE c.name IS NOT NULL  # 过滤无分类的书籍
        ORDER BY c.name
        """
        cursor.execute(sql)
        result = cursor.fetchall()

        # 3. 提取分类列表
        categories = [item["category"] for item in result]
        return categories  # FastAPI会自动转为JSON响应

    except pymysql.MySQLError as e:
        # 数据库相关错误，返回500状态码+错误信息
        raise HTTPException(status_code=500, detail=f"数据库查询失败：{str(e)}")
    except Exception as e:
        # 其他未知错误
        raise HTTPException(status_code=500, detail=f"系统错误：{str(e)}")
    finally:
        # 安全关闭资源：判断cursor/conn是否存在再关闭
        if cursor:
            cursor.close()
        if conn:
            conn.close()