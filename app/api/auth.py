# app/api/auth.py
# 第三方库导入
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, model_validator, EmailStr

# 本地应用导入
from app.core.security import create_password_hash, verify_password
from app.utils.db import execute_query_one, execute_update
from app.core.exceptions import DuplicateDataError

router = APIRouter(
    prefix="/auth",
    tags=["认证模块"]
)


# 邮箱注册请求模型
class EmailRegisterRequest(BaseModel):
    password: str
    email: EmailStr  # 强制要求邮箱格式
    school_id: int = None

    @model_validator(mode="before")
    def check_email_format(cls, values):
        email = values.get('email')
        if '@' not in email:
            raise ValueError('邮箱格式不正确')
        return values


# 手机号注册请求模型
class PhoneRegisterRequest(BaseModel):
    password: str
    phone: str  # 手机号
    school_id: int = None

    @model_validator(mode="before")
    def check_phone_format(cls, values):
        phone = values.get('phone')
        if len(phone) != 11 or not phone.isdigit():
            raise ValueError('手机号格式不正确')
        return values


def init_user_message_settings(user_id: int):
    """初始化用户消息设置（默认开启易书通知，其他开关关闭）"""
    existing = execute_query_one(
        "SELECT id FROM user_message_settings WHERE user_id = %s",
        (user_id,)
    )
    if not existing:
        execute_update(
            sql="""
                INSERT INTO user_message_settings (user_id, receive_book_notice, interactive_msg_switch,
                                                   system_notice_switch, follow_update_switch, auto_reply_switch,
                                                   auto_reply_content, create_time)
                VALUES (%s, 1, 0, 0, 0, 0, '亲，我现在不在，喜欢可以拍下~', NOW())
                """,
            params=(user_id,)
        )


@router.post("/register/email", summary="邮箱注册（自动生成昵称）")
def email_register(req: EmailRegisterRequest):
    print(f"原始密码: {req.password}")
    print(f"字符长度: {len(req.password)}")
    print(f"UTF-8字节长度: {len(req.password.encode('utf-8'))}")
    # 1. 提取username（@之前的部分）
    username = req.email.split('@')[0]

    # 2. 校验邮箱是否已存在
    existing_user = execute_query_one(
        sql="""SELECT user_id FROM users 
               WHERE email = %s""",
        params=(req.email,)
    )
    if existing_user:
        raise DuplicateDataError(field="邮箱")

    # 3. 密码加密
    hashed_pwd = create_password_hash(req.password)

    # 4. 插入用户到数据库
    execute_update(
        sql="""
            INSERT INTO users (username, password, email, school_id,
                               avg_rating, review_count, is_active, is_admin, create_time)
            VALUES (%s, %s, %s, %s, 5.0, 0, 1, 0, NOW())
            """,
        params=(username, hashed_pwd, req.email, req.school_id)
    )

    # 5. 获取自增的user_id，生成昵称
    user_id = execute_query_one("SELECT LAST_INSERT_ID() AS id")["id"]
    nickname = f"用户{user_id}"

    # 6. 更新用户表的nickname字段
    execute_update(
        sql="UPDATE users SET nickname = %s WHERE user_id = %s",
        params=(nickname, user_id)
    )

    # 7. 初始化用户消息设置
    init_user_message_settings(user_id)

    # 8. 返回注册结果
    return {
        "code": 200,
        "message": "注册成功",
        "data": {
            "user_id": user_id,
            "username": username,  # 返回@之前的部分
            "email": req.email,
            "nickname": nickname,
            "school_id": req.school_id
        }
    }


@router.post("/register/phone", summary="手机号注册（自动生成昵称）")
def phone_register(req: PhoneRegisterRequest):
    # 1. 手机号直接作为username
    username = req.phone

    # 2. 校验手机号是否已存在
    existing_user = execute_query_one(
        sql="""SELECT user_id FROM users 
               WHERE phone = %s""",
        params=(req.phone,)
    )
    if existing_user:
        raise DuplicateDataError(field="手机号")

    # 3. 密码加密
    hashed_pwd = create_password_hash(req.password)

    # 4. 插入用户到数据库
    execute_update(
        sql="""
            INSERT INTO users (username, password, phone, school_id,
                               avg_rating, review_count, is_active, is_admin, create_time)
            VALUES (%s, %s, %s, %s, 5.0, 0, 1, 0, NOW())
            """,
        params=(username, hashed_pwd, req.phone, req.school_id)
    )

    # 5. 获取自增的user_id，生成昵称
    user_id = execute_query_one("SELECT LAST_INSERT_ID() AS id")["id"]
    nickname = f"用户{user_id}"

    # 6. 更新用户表的nickname字段
    execute_update(
        sql="UPDATE users SET nickname = %s WHERE user_id = %s",
        params=(nickname, user_id)
    )

    # 7. 初始化用户消息设置
    init_user_message_settings(user_id)

    # 8. 返回注册结果
    return {
        "code": 200,
        "message": "注册成功",
        "data": {
            "user_id": user_id,
            "username": username,  # 返回手机号
            "phone": req.phone,
            "nickname": nickname,
            "school_id": req.school_id
        }
    }


@router.post("/login", summary="用户登录（支持手机号/邮箱）")
def login(
        identifier: str = Body(..., description="手机号/邮箱"),
        password: str = Body(..., description="密码")
):
    # 保持登录接口不变，仍然支持两种登录方式
    user = execute_query_one(
        "SELECT user_id, username, phone, email, nickname, password FROM users WHERE phone = %s OR email = %s",
        (identifier, identifier)
    )
    if not user:
        raise HTTPException(status_code=401, detail="手机号/邮箱或密码错误")

    if not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="手机号/邮箱或密码错误")

    user_data = {
        "user_id": user["user_id"],
        "username": user["username"],
        "phone": user["phone"],
        "email": user["email"],
        "nickname": user["nickname"]
    }
    return {
        "code": 200,
        "message": "登录成功",
        "data": user_data
    }