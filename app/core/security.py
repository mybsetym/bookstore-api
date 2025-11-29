#app\core\security.py
# 标准库导入（按模块名+导入项字母序排列）
from datetime import datetime, timezone, timedelta
from typing import Annotated, Any, Optional, Union  # 新增 Annotated 导入

# 第三方库导入
# Crypto 相关
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# FastAPI 相关依赖导入
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# jose 相关
from jose import JWTError, jwt

# passlib 相关
from passlib.context import CryptContext

# 本地应用导入
from app.config import settings
from app.utils.db import execute_query_one  # 导入数据库查询工具

# --- 密码哈希 ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_password_hash(password: str) -> str:
    # 关键：必须使用截断后的密码进行哈希
    truncated_pwd = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(truncated_pwd)  # 这里必须传入 truncated_pwd，而非原始 password

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# --- JWT Token ---
# 新增：定义 OAuth2 令牌提取方案（与你的登录接口路径匹配）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


# 新增：获取当前登录用户（放在 JWT 模块内，保持功能块统一）
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """从请求令牌中解析并验证当前用户（依赖 JWT 验证）"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解码 JWT 令牌，获取用户 ID（与 create_access_token 中 "sub" 字段对应）
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 查询数据库获取用户信息（与项目现有数据库操作方式一致）
    user = execute_query_one(
        "SELECT user_id, username, email, is_active, is_admin FROM users WHERE user_id = %s",
        (user_id,)
    )
    if user is None:
        raise credentials_exception
    return user


# --- AES 加密 (保持原有逻辑) ---
def aes_encrypt(data: str) -> str:
    cipher = AES.new(settings.AES_KEY, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))
    iv = cipher.iv
    return iv.hex() + ct_bytes.hex()


def aes_decrypt(encrypted_data: str) -> str:
    iv = bytes.fromhex(encrypted_data[:32])
    ct = bytes.fromhex(encrypted_data[32:])
    cipher = AES.new(settings.AES_KEY, AES.MODE_CBC, iv=iv)
    pt = unpad(cipher.decrypt(ct), AES.block_size)
    return pt.decode('utf-8')