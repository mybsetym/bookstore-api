# app/models/schemas.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr, ConfigDict


# --- 认证相关 ---
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[EmailStr] = None


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[int] = None


# --- 商品相关 ---
class BookBase(BaseModel):
    book_name: str
    author: str
    publisher: Optional[str] = None
    publish_date: Optional[str] = None
    category: str
    price: float
    condition: str  # 使用 'condition_' 避免与 SQL 关键字冲突，或者在 SQL 中用反引号包裹
    book_desc: Optional[str] = None
    stock: int = 1


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    price: Optional[float] = None
    condition: Optional[str] = None
    book_desc: Optional[str] = None
    stock: Optional[int] = None
    status: Optional[int] = None


class BookOut(BookBase):
    book_id: int
    seller_id: int
    cover_img: Optional[str] = None
    status: int
    view: int
    create_time: datetime
    update_time: datetime

    model_config = ConfigDict(from_attributes=True)