#app/api/auth.py
# 第三方库导入
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

# 本地应用导入
from app.core.security import create_password_hash, verify_password
from app.utils.db import execute_query_one, execute_update

router = APIRouter(
    prefix="/auth",
    tags=["认证模块"]
)


# 注册请求模型
class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str
    nickname: str = None
    school_id: int = None


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


@router.post("/register", summary="用户注册")
def user_register(req: RegisterRequest):
    # 1. 校验用户名/邮箱是否已存在
    existing_user = execute_query_one(
        sql="SELECT user_id FROM users WHERE username = %s OR email = %s",
        params=(req.username, req.email)
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名或邮箱已被注册")

    # 2. 密码加密（使用安全模块的加密函数）
    hashed_pwd = create_password_hash(req.password)

    # 3. 插入用户到数据库
    execute_update(
        sql="""
            INSERT INTO users (username, password, email, nickname, school_id,
                               avg_rating, review_count, is_active, is_admin, create_time)
            VALUES (%s, %s, %s, %s, %s, 5.0, 0, 1, 0, NOW())
            """,
        params=(req.username, hashed_pwd, req.email, req.nickname, req.school_id)
    )
    user_id = execute_query_one("SELECT LAST_INSERT_ID() AS id")["id"]

    # 4. 初始化用户消息设置
    init_user_message_settings(user_id)

    # 5. 返回注册结果
    return {
        "code": 200,
        "message": "注册成功",
        "data": {
            "user_id": user_id,
            "username": req.username,
            "email": req.email,
            "nickname": req.nickname or req.username,
            "school_id": req.school_id
        }
    }


@router.post("/login", summary="用户登录")
def login(
        identifier: str = Body(..., description="用户名或邮箱"),
        password: str = Body(..., description="密码")
):
    # 1. 先通过用户名/邮箱查询用户（包含存储的哈希密码）
    user = execute_query_one(
        "SELECT user_id, username, email, nickname, password FROM users WHERE username = %s OR email = %s",
        (identifier, identifier)
    )
    if not user:
        raise HTTPException(status_code=401, detail="用户名/邮箱或密码错误")

    # 2. 验证密码（明文密码 vs 数据库存储的哈希密码）
    if not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="用户名/邮箱或密码错误")

    # 3. 返回用户信息（排除密码字段）
    user_data = {
        "user_id": user["user_id"],
        "username": user["username"],
        "email": user["email"],
        "nickname": user["nickname"]
    }
    return {
        "code": 200,
        "message": "登录成功",
        "data": user_data
    }