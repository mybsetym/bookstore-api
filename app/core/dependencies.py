# app/core/dependencies.py

from app.config import settings
from app.utils.db import execute_query_one  # 从你修改后的 db.py 中导入查询函数
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

# 定义 Token 的获取方式，这里假设你的登录接口在 /api/v1/auth/token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """
    从 JWT Token 中提取并验证当前用户的 ID。
    这是最基础的依赖，很多需要认证的接口都会用到它。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证，请重新登录。",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 尝试解码 Token
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        # 从 Token 的 payload 中获取用户 ID，这里假设你存储在 "sub" 字段
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return int(user_id)
    except JWTError:
        # 如果解码失败（如 Token 过期、签名错误等），抛出异常
        raise credentials_exception


def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    从 JWT Token 中获取当前用户的完整信息。
    它依赖于 get_current_user_id，并进一步从数据库中查询用户详情。
    """
    user_id = get_current_user_id(token)

    # 使用你在 db.py 中定义的 execute_query_one 函数来查询用户
    user = execute_query_one(
        "SELECT ld.ID, ld.phone, ld.email, u.nickname, u.avatar_url, u.school_id "
        "FROM logindata ld "
        "LEFT JOIN users u ON ld.ID = u.user_id "
        "WHERE ld.ID = %s",
        (user_id,)
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在。"
        )
    return user