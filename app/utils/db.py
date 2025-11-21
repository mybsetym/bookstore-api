import pymysql
import databases
from pymysql.cursors import DictCursor
from app.config import settings  # 假设你的配置文件在 app/config.py


def get_db_connection():
    """建立并返回一个数据库连接"""
    try:
        connection = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            cursorclass=DictCursor,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        return connection
    except pymysql.MySQLError as e:
        print(f"数据库连接失败: {e}")
        raise


def execute_query(sql, params=()):
    """
    执行查询并返回所有结果 (列表 of dicts)
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchall()
        return result
    finally:
        conn.close()


def execute_query_one(sql, params=()):
    """
    执行查询并返回单条记录 (dict)，如果没有结果则返回 None
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            result = cursor.fetchone()
        return result  # 当没有结果时，fetchone() 会返回 None
    finally:
        conn.close()


def execute_update(sql, params=()):
    """
    执行更新操作 (INSERT, UPDATE, DELETE)
    返回: 受影响的行数
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            affected_rows = cursor.execute(sql, params)
        conn.commit()
        return affected_rows
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
database = databases.Database(settings.DATABASE_URL)

async def execute_query_one_async(query, values):
    await database.connect()
    try:
        return await database.fetch_one(query, values)
    finally:
        await database.disconnect()

def execute_query_paginated(sql, params, page=1, page_size=10):
    """
    执行分页查询。
    注意: 此函数会修改原始 SQL，在末尾添加 LIMIT 和 OFFSET。
    请确保传入的 sql 字符串末尾没有分号，并且没有已经包含 LIMIT/OFFSET。
    """
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 10

    offset = (page - 1) * page_size

    # 拼接分页 SQL
    paginated_sql = f"{sql} LIMIT %s OFFSET %s"

    # 执行查询获取数据
    data_params = params + (page_size, offset)
    data = execute_query(paginated_sql, data_params)

    # 构建并执行 count SQL
    # 注意: 这种方式对于复杂 SQL (如包含 UNION, GROUP BY) 可能需要手动调整
    count_sql = f"SELECT COUNT(*) AS total FROM ({sql}) AS subquery"
    count_result = execute_query_one(count_sql, params)

    total = count_result['total'] if count_result else 0

    return {
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }