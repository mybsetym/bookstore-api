from fastapi import APIRouter, Query, Body, HTTPException
from fastapi import Path
from typing import Optional
import hashlib
from app.utils.db import (
    execute_query_one,
    execute_update,
    execute_query_paginated
)
from datetime import datetime

router = APIRouter(
    prefix="/users",
    tags=["用户模块"],
    responses={404: {"description": "用户不存在"}},
)


# --------------------------
#  1. 用户注册
# --------------------------
@router.post("/register", summary="用户注册")
def register(
        phone: str = Body(..., min_length=11, max_length=11, description="手机号"),
        email: str = Body(..., description="邮箱"),
        password: str = Body(..., min_length=6, description="密码"),
        school_id: Optional[int] = Body(None, description="学校ID（可选，从学校列表获取）")
):
    # 1. 校验手机号/邮箱是否已注册
    existing_phone = execute_query_one(
        "SELECT ID FROM logindata WHERE phone = %s",
        (phone,)
    )
    if existing_phone:
        raise HTTPException(status_code=400, detail="手机号已被注册")

    existing_email = execute_query_one(
        "SELECT ID FROM logindata WHERE email = %s",
        (email,)
    )
    if existing_email:
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    # 2. 密码 MD5 加密（生产环境建议替换为 bcrypt）
    hashed_password = hashlib.md5(password.encode()).hexdigest()

    # 3. 插入 logindata 表（认证核心信息）
    login_sql = """
                INSERT INTO logindata (phone, email, password)
                VALUES (%s, %s, %s) \
                """
    execute_update(login_sql, (phone, email, hashed_password))

    # 4. 获取新用户 ID
    new_user_id = execute_query_one(
        "SELECT LAST_INSERT_ID() AS ID"
    )["ID"]

    # 5. 初始化 users 表（个人信息表）
    user_sql = """
               INSERT INTO users (user_id, school_id, created_at, updated_at)
               VALUES (%s, %s, %s, %s) \
               """
    now = datetime.now()
    execute_update(user_sql, (new_user_id, school_id, now, now))

    return {
        "code": 201,
        "message": "注册成功",
        "data": {
            "user_id": new_user_id,
            "phone": phone,
            "email": email,
            "school_id": school_id
        }
    }


# --------------------------
#  2. 获取用户信息
# --------------------------
@router.get("/{user_id}", summary="获取用户信息")
def get_user_info(
        user_id: int = Path(..., ge=1, description="用户ID")
):
    # 关联查询 logindata、users、school 表的信息
    sql = """
          SELECT ld.ID as user_id, \
                 ld.phone, \
                 ld.email, \
                 u.nickname, \
                 u.avatar_url, \
                 u.gender, \
                 u.birth_date, \
                 u.bio, \
                 s.school_name
          FROM logindata ld
                   LEFT JOIN users u ON ld.ID = u.user_id
                   LEFT JOIN school s ON u.school_id = s.school_id
          WHERE ld.ID = %s \
          """
    user = execute_query_one(sql, (user_id,))

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {
        "code": 200,
        "message": "获取成功",
        "data": user
    }


# --------------------------
#  3. 更新用户信息
# --------------------------
@router.put("/{user_id}", summary="更新用户信息")
def update_user_info(
        user_id: int = Path(..., ge=1, description="用户ID"),
        nickname: Optional[str] = Body(None, min_length=1, max_length=50, description="昵称"),
        avatar_url: Optional[str] = Body(None, description="头像URL"),
        gender: Optional[int] = Body(None, ge=0, le=2, description="性别 0-未知 1-男 2-女"),
        birth_date: Optional[str] = Body(None, description="出生日期 格式: YYYY-MM-DD"),
        bio: Optional[str] = Body(None, description="个人简介"),
        school_id: Optional[int] = Body(None, description="学校ID（从学校列表获取）")
):
    # 1. 校验用户是否存在
    existing_user = execute_query_one(
        "SELECT ID FROM logindata WHERE ID = %s",
        (user_id,)
    )
    if not existing_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 2. 构建更新字段
    update_fields = []
    params = []

    if nickname is not None:
        update_fields.append("nickname = %s")
        params.append(nickname)
    if avatar_url is not None:
        update_fields.append("avatar_url = %s")
        params.append(avatar_url)
    if gender is not None:
        update_fields.append("gender = %s")
        params.append(gender)
    if birth_date is not None:
        update_fields.append("birth_date = %s")
        params.append(birth_date)
    if bio is not None:
        update_fields.append("bio = %s")
        params.append(bio)
    if school_id is not None:
        update_fields.append("school_id = %s")
        params.append(school_id)

    if not update_fields:
        raise HTTPException(status_code=400, detail="至少需要更新一个字段")

    # 3. 执行更新
    sql = f"UPDATE users SET {', '.join(update_fields)}, updated_at = %s WHERE user_id = %s"
    params.extend([datetime.now(), user_id])
    execute_update(sql, params)

    return {
        "code": 200,
        "message": "更新成功",
        "data": {"user_id": user_id}
    }


# --------------------------
#  4. 获取用户发布的商品
# --------------------------
@router.get("/{user_id}/products", summary="获取用户发布的商品")
def get_user_products(
        user_id: int = Path(..., ge=1, description="用户ID"),
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=50, description="每页数量")
):
    sql = """
          SELECT b.*, s.school_name
          FROM book b
                   LEFT JOIN users u ON b.seller_ID = u.user_id
                   LEFT JOIN school s ON u.school_id = s.school_id
          WHERE b.seller_ID = %s \
            AND b.status = 1
          ORDER BY b.create_time DESC \
          """
    result = execute_query_paginated(sql, (user_id,), page, page_size)

    return {
        "code": 200,
        "message": "获取成功",
        "data": result
    }