# app/core/security.py
from datetime import datetime, timezone,timedelta
from typing import Any, Union, Optional

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from app.config import settings
from jose import jwt
from passlib.context import CryptContext

# --- 密码哈希 ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# --- JWT Token ---
def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta  # 修正此处
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)  # 修正此处

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

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
