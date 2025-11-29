# app/api/users.py
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, model_validator, EmailStr

# 本地模块导入（需和项目实际路径匹配）
from app.core.security import create_password_hash, verify_password
from app.utils.db import execute_query_one, execute_update
from app.core.exceptions import DuplicateDataError

# 初始化路由器（主路由已配置 prefix="/users"，所以最终接口路径是 /users/register/xxx）
router = APIRouter(tags=["users"])

# ------------------------------ 请求模型定义 ------------------------------
# 邮箱注册请求模型
class EmailRegisterRequest(BaseModel):
    password: str
    email: EmailStr  # 内置邮箱格式校验
    school_id: int = None

    @model_validator(mode="before")
    def validate_email(self, values):
        """二次校验邮箱格式（兜底）"""
        email = values.get("email")
        if not email or "@" not in email:
            raise ValueError("邮箱格式错误，必须包含@符号")
        return values

# 手机号注册请求模型
class PhoneRegisterRequest(BaseModel):
    password: str
    phone: str
    school_id: int = None

    @model_validator(mode="before")
    def validate_phone(self, values):
        """校验手机号格式（11位数字）"""
        phone = values.get("phone")
        if not (phone and len(phone) == 11 and phone.isdigit()):
            raise ValueError("手机号格式错误，必须是11位数字")
        return values

# ------------------------------ 工具函数 ------------------------------
def init_user_message_settings(user_id: int):
    """初始化用户消息设置（复用auth.py的逻辑）"""
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

# ------------------------------ 接口实现 ------------------------------
@router.post("/register/email", summary="【用户模块】邮箱注册")
def email_register(req: EmailRegisterRequest):
    """
    邮箱注册接口（用户模块）
    - username 取邮箱@前的部分
    - 自动生成昵称（用户+自增ID）
    - 初始化消息设置
    """
    # 1. 生成username（@前的部分）
    username = req.email.split("@")[0]

    # 2. 校验邮箱是否已注册
    existing_user = execute_query_one(
        sql="SELECT user_id FROM users WHERE email = %s",
        params=(req.email,)
    )
    if existing_user:
        raise DuplicateDataError(field="邮箱")

    # 3. 密码加密
    hashed_password = create_password_hash(req.password)

    # 4. 插入用户数据
    execute_update(
        sql="""
            INSERT INTO users (
                username, password, email, school_id,
                avg_rating, review_count, is_active, is_admin, create_time
            ) VALUES (%s, %s, %s, %s, 5.0, 0, 1, 0, NOW())
            """,
        params=(username, hashed_password, req.email, req.school_id)
    )

    # 5. 获取自增ID并生成昵称
    user_id = execute_query_one("SELECT LAST_INSERT_ID() AS id")["id"]
    nickname = f"用户{user_id}"

    # 6. 更新昵称字段
    execute_update(
        sql="UPDATE users SET nickname = %s WHERE user_id = %s",
        params=(nickname, user_id)
    )

    # 7. 初始化消息设置
    init_user_message_settings(user_id)

    # 8. 返回结果
    return {
        "code": 200,
        "message": "邮箱注册成功",
        "data": {
            "user_id": user_id,
            "username": username,  # 返回@前的部分
            "email": req.email,
            "nickname": nickname,
            "school_id": req.school_id
        }
    }

@router.post("/register/phone", summary="【用户模块】手机号注册")
def phone_register(req: PhoneRegisterRequest):
    """
    手机号注册接口（用户模块）
    - username 直接使用手机号
    - 自动生成昵称（用户+自增ID）
    - 初始化消息设置
    """
    # 1. 生成username（直接用手机号）
    username = req.phone

    # 2. 校验手机号是否已注册
    existing_user = execute_query_one(
        sql="SELECT user_id FROM users WHERE phone = %s",
        params=(req.phone,)
    )
    if existing_user:
        raise DuplicateDataError(field="手机号")

    # 3. 密码加密
    hashed_password = create_password_hash(req.password)

    # 4. 插入用户数据
    execute_update(
        sql="""
            INSERT INTO users (
                username, password, phone, school_id,
                avg_rating, review_count, is_active, is_admin, create_time
            ) VALUES (%s, %s, %s, %s, 5.0, 0, 1, 0, NOW())
            """,
        params=(username, hashed_password, req.phone, req.school_id)
    )

    # 5. 获取自增ID并生成昵称
    user_id = execute_query_one("SELECT LAST_INSERT_ID() AS id")["id"]
    nickname = f"用户{user_id}"

    # 6. 更新昵称字段
    execute_update(
        sql="UPDATE users SET nickname = %s WHERE user_id = %s",
        params=(nickname, user_id)
    )

    # 7. 初始化消息设置
    init_user_message_settings(user_id)

    # 8. 返回结果
    return {
        "code": 200,
        "message": "手机号注册成功",
        "data": {
            "user_id": user_id,
            "username": username,  # 返回手机号
            "phone": req.phone,
            "nickname": nickname,
            "school_id": req.school_id
        }
    }

# ------------------------------ 保留原有其他用户接口 ------------------------------
# 示例：用户信息查询、修改等接口（根据项目实际情况补充）
@router.get("/{user_id}", summary="查询用户信息")
def get_user_info(user_id: int):
    user = execute_query_one(
        sql="""
            SELECT user_id, username, nickname, email, phone, school_id, avg_rating, review_count 
            FROM users WHERE user_id = %s
            """,
        params=(user_id,)
    )
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "code": 200,
        "message": "查询成功",
        "data": user
    }