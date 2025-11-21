# app/api/auth.py

from fastapi import APIRouter, HTTPException, Body
# 正确导入所需的函数
from app.utils.db import execute_query_one, execute_update
import hashlib

router = APIRouter(
    prefix="/auth",
    tags=["认证模块"]
)


@router.post("/register", summary="用户注册")
def register(
        phone: str = Body(..., description="手机号（必填）", min_length=11, max_length=11),
        email: str = Body(..., description="邮箱（必填）"),
        password: str = Body(..., description="密码（必填，至少6位）")
):
    # 检查手机号是否已注册
    existing_phone = execute_query_one("SELECT ID FROM logindata WHERE phone = %s", (phone,))
    if existing_phone:
        raise HTTPException(status_code=400, detail="手机号已被注册")

    # 检查邮箱是否已注册
    existing_email = execute_query_one("SELECT ID FROM logindata WHERE email = %s", (email,))
    if existing_email:
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    # 密码 MD5 加密（生产环境建议用 bcrypt）
    hashed_password = hashlib.md5(password.encode()).hexdigest()

    # 插入 logindata 表
    sql = """
          INSERT INTO logindata (phone, email, password)
          VALUES (%s, %s, %s) \
          """
    # 昵称默认和用户名一致
    execute_update(sql, (phone, email, hashed_password))

    # 获取新增用户的ID
    new_user = execute_query_one("SELECT ID FROM logindata WHERE phone = %s", (phone,))
    user_id = new_user["ID"]

    # 新增：在 users 表中创建对应的用户档案记录
    # 默认昵称可以设为手机号的后四位，或一个通用名称
    default_nickname = f"用户{phone[-4:]}"
    execute_update(
        "INSERT INTO users (user_id, nickname) VALUES (%s, %s)",
        (user_id, default_nickname)
    )

    return {
        "code": 200,
        "message": "注册成功",
        "data": {
            "user_id": user_id,
            "phone": phone,
            "email": email
        }
    }


@router.post("/login", summary="用户登录")
def login(
        identifier: str = Body(..., description="手机号或邮箱"),
        password: str = Body(..., description="密码")
):
    hashed_password = hashlib.md5(password.encode()).hexdigest()

    # 同时匹配手机号或邮箱
    user = execute_query_one(
        "SELECT ID, phone, email FROM logindata WHERE (phone = %s OR email = %s) AND password = %s",
        (identifier, identifier, hashed_password)
    )
    if not user:
        raise HTTPException(status_code=401, detail="手机号/邮箱或密码错误")

    return {
        "code": 200,
        "message": "登录成功",
        "data": user
    }