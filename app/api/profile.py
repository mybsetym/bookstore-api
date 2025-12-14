#app/api/profile.py
# 标准库导入
from typing import Optional

# 第三方库导入（FastAPI 相关）
from fastapi import APIRouter, Body, HTTPException, Query

# 本地应用导入（数据库工具函数）
from app.utils.db import (
    execute_query,
    execute_query_one,
    execute_query_paginated,
    execute_update,
)
router = APIRouter(
    prefix="/profile",
    tags=["个人中心模块"]
)


@router.get("/info", summary="获取个人信息")
def get_user_profile(user_id: int = Query(..., description="用户ID（users表中的user_id）")):
    """
    获取用户的综合信息，包括：
    - 从 users 表获取的登录信息（手机号、邮箱）和详细资料（昵称、头像等）。
    - 统计信息（发布的图书数量、订单数量）。
    """
    # 1. 检查用户是否存在于 users 表
    user_sql = "SELECT user_id, phone, email, create_time FROM users WHERE user_id = %s"
    user_info = execute_query_one(user_sql, (user_id,))
    if not user_info:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 2. 从 users 表获取详细资料（排除已获取的基本信息）
    detail_sql = "SELECT nickname, avatar, school_id, avg_rating, review_count FROM users WHERE user_id = %s"
    user_detail = execute_query_one(detail_sql, (user_id,))
    if not user_detail:
        # 如果 users 表中没有记录，返回一个默认结构
        user_detail = {
            "nickname": "",
            "avatar": None,
            "school_id": None,
            "avg_rating": 5.0,
            "review_count": 0
        }

    # 3. 统计用户发布的图书数量
    book_count_sql = "SELECT COUNT(*) AS count FROM book WHERE seller_id = %s"
    book_count = execute_query_one(book_count_sql, (user_id,))["count"]

    # 4. 统计用户的订单数量（作为买家）
    order_count_sql = "SELECT COUNT(*) AS count FROM orders WHERE buyer_id = %s"
    order_count = execute_query_one(order_count_sql, (user_id,))["count"]

    # 5. 合并所有信息并返回
    return {
        "code": 200,
        "message": "获取成功",
        "data": {
            "user_id": user_info["user_id"],
            "phone": user_info["phone"],
            "email": user_info["email"],
            "register_time": user_info["create_time"],
            "profile": user_detail,
            "stats": {
                "book_count": book_count,
                "order_count": order_count
            }
        }
    }


@router.put("/info", summary="更新个人信息")
def update_user_profile(
        user_id: int = Query(..., description="用户ID"),
        username: Optional[str] = Body(None, description="用户名"),
        nickname: Optional[str] = Body(None, description="昵称"),
        avatar: Optional[str] = Body(None, description="头像URL"),
        school_id: Optional[int] = Body(None, description="学校ID"),
        gender: Optional[int] = Body(None, description="性别 (0:未知, 1:男, 2:女)"),
        birth_date: Optional[str] = Body(None, description="出生日期 (格式: YYYY-MM-DD)"),
        bio: Optional[str] = Body(None, description="个人简介")
):
    """
    更新用户在 `users` 表中的个人资料。
    所有字段均为可选，仅更新提供的字段。
    """
    # 1. 检查用户是否存在
    check_sql = "SELECT user_id FROM users WHERE user_id = %s"
    if not execute_query_one(check_sql, (user_id,)):
        raise HTTPException(status_code=404, detail="用户不存在")

    # 2. 构造更新的字段和参数
    update_fields = []
    params = []

    if username is not None:
        update_fields.append("username = %s")
        params.append(username)
    if nickname is not None:
        update_fields.append("nickname = %s")
        params.append(nickname)
    if avatar is not None:
        update_fields.append("avatar = %s")
        params.append(avatar)
    if school_id is not None:
        update_fields.append("school_id = %s")
        params.append(school_id)
    if gender is not None:
        if gender not in [0, 1, 2]:
            raise HTTPException(status_code=400, detail="性别值必须是 0, 1, 或 2")
        update_fields.append("gender = %s")
        params.append(gender)
    if birth_date is not None:
        update_fields.append("birth_date = %s")
        params.append(birth_date)
    if bio is not None:
        update_fields.append("bio = %s")
        params.append(bio)

    if not update_fields:
        raise HTTPException(status_code=400, detail="至少需要提供一个要更新的字段")

    # 3. 执行更新
    # 先检查 users 表中是否已有该用户的记录
    user_exists_sql = "SELECT user_id FROM users WHERE user_id = %s"
    if execute_query_one(user_exists_sql, (user_id,)):
        # 记录存在，执行 UPDATE
        sql = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = %s"
        params.append(user_id)
        execute_update(sql, params)
    else:
        # 记录不存在，执行 INSERT
        # 确保 nickname 有一个默认值
        if not nickname:
            nickname = f"用户{user_id}"

        sql = """
              INSERT INTO users (user_id, username, nickname, avatar, school_id, gender, birth_date, bio)
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s) \
              """
        # 为 INSERT 构建参数，确保顺序正确
        insert_params = [user_id, username, nickname, avatar, school_id, gender, birth_date, bio]
        execute_update(sql, insert_params)

    return {
        "code": 200,
        "message": "个人信息更新成功"
    }


@router.get("/books", summary="获取用户发布的图书")
def get_user_books(
        user_id: int = Query(..., description="用户ID（作为卖家的ID）"),
        page: int = Query(1, description="页码", ge=1),
        page_size: int = Query(10, description="每页条数", ge=1, le=50)
):
    """分页查询当前用户发布的所有图书"""
    sql = "SELECT * FROM book WHERE seller_ID = %s ORDER BY create_time DESC"
    result = execute_query_paginated(sql, (user_id,), page, page_size)

    return {
        "code": 200,
        "message": "获取成功",
        "data": result
    }


@router.get("/orders", summary="获取用户的订单")
def get_user_orders(
        user_id: int = Query(..., description="用户ID（作为买家的ID）"),
        page: int = Query(1, description="页码", ge=1),
        page_size: int = Query(10, description="每页条数", ge=1, le=50)
):
    """分页查询当前用户作为买家的所有订单"""
    sql = "SELECT * FROM orders WHERE buyer_id = %s ORDER BY create_time DESC"
    result = execute_query_paginated(sql, (user_id,), page, page_size)

    # 项目订单模型为单表结构，订单详情已包含在orders表中，无需额外查询订单项

    return {
        "code": 200,
        "message": "获取成功",
        "data": result
    }