# app/core/schemas.py
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict, model_validator


# --------------------------
# 认证相关模型
# --------------------------
class UserCreate(BaseModel):
    """用户创建基础模型"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    email: Optional[EmailStr] = None


class UserOut(BaseModel):
    """用户信息返回模型"""
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool = True
    school_id: Optional[int] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """JWT令牌模型"""
    access_token: str
    token_type: str


class TokenPayload(BaseModel):
    """令牌负载模型"""
    sub: Optional[int] = None


class PhoneRegisterRequest(BaseModel):
    """手机号注册请求模型"""
    password: str
    phone: str  # 手机号
    school_id: Optional[int] = None

    @model_validator(mode="before")
    def check_phone_format(cls, values):
        phone = values.get('phone')
        if len(phone) != 11 or not phone.isdigit():
            raise ValueError('手机号格式不正确')
        return values


class EmailRegisterRequest(BaseModel):
    """邮箱注册请求模型"""
    password: str
    email: EmailStr  # 内置邮箱格式校验
    school_id: Optional[int] = None

    @model_validator(mode="before")
    def validate_email(self, values):
        """二次校验邮箱格式（兜底）"""
        email = values.get("email")
        if not email or "@" not in email:
            raise ValueError("邮箱格式错误，必须包含@符号")
        return values


# --------------------------
# 商品（图书）相关模型
# --------------------------
class BookBase(BaseModel):
    """图书基础模型"""
    book_name: str
    author: str
    publisher: Optional[str] = None
    publish_date: Optional[str] = None
    category_id: int = Field(..., description="分类ID（关联categories表）")
    price: float
    condition: str  # 图书状态（全新/二手等）
    book_desc: Optional[str] = None
    stock: int = 1


class BookCreate(BookBase):
    """创建图书请求模型"""
    ISBN: str = Field(..., description="ISBN编号")
    seller_id: int = Field(..., description="卖家ID")


class BookUpdate(BaseModel):
    """更新图书请求模型"""
    price: Optional[float] = None
    condition: Optional[str] = None
    book_desc: Optional[str] = None
    stock: Optional[int] = None
    status: Optional[int] = None  # 0-下架，1-上架，2-审核中
    category_id: Optional[int] = None


class BookOut(BookBase):
    """图书详情返回模型"""
    book_id: int
    seller_id: int
    cover_img: Optional[str] = None
    status: int
    view: int
    create_time: datetime
    update_time: datetime
    category_name: Optional[str] = Field(None, description="分类名称")
    seller_name: Optional[str] = Field(None, description="卖家昵称")

    model_config = ConfigDict(from_attributes=True)


# --------------------------
# 订单相关模型
# --------------------------
class CreateOrderRequest(BaseModel):
    """创建订单请求模型"""
    product_id: int  # 商品ID（对应book表的book_id）
    buyer_id: int  # 买家ID
    quantity: int = 1  # 购买数量，默认1本
    fulfillment_type: str = Field(..., pattern="^(self_pickup|logistics)$", description="履约方式：自提/物流")
    pickup_location_id: Optional[int] = Field(None, description="自提地点ID（自提时必传）")
    receiver_name: Optional[str] = Field(None, description="收件人姓名（物流时必传）")
    receiver_phone: Optional[str] = Field(None, description="收件人电话（物流时必传）")
    receiver_address: Optional[str] = Field(None, description="收件地址（物流时必传）")
    remark: Optional[str] = None  # 订单备注


class OrderOut(BaseModel):
    """订单返回模型"""
    order_id: int
    product_id: int
    buyer_id: int
    seller_id: int
    quantity: int
    total_price: float
    fulfillment_type: str
    status: str
    create_time: datetime
    update_time: datetime
    product_name: Optional[str] = None  # 商品名称
    buyer_name: Optional[str] = None  # 买家昵称
    seller_name: Optional[str] = None  # 卖家昵称

    model_config = ConfigDict(from_attributes=True)


# --------------------------
# 分类相关模型
# --------------------------
class CategoryOut(BaseModel):
    """分类返回模型"""
    id: int
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --------------------------
# 广场帖子相关模型
# --------------------------
class PostBase(BaseModel):
    """帖子基础模型"""
    content: str = Field(..., max_length=1000, description="帖子内容（最多1000字）")
    img_urls: Optional[List[str]] = Field(None, max_length=3, description="图片URL列表（最多3张）")


class CreatePostRequest(PostBase):
    """创建帖子请求模型"""
    user_id: int = Field(..., description="发布者用户ID（关联users表）")


class PostResponse(PostBase):
    """帖子返回模型"""
    post_id: int
    user_id: int
    create_time: datetime
    status: str = Field(..., pattern="^(pending_audit|visible|hidden)$", description="帖子状态")
    nickname: str = Field(..., description="发布者昵称")
    avatar: Optional[str] = Field(None, description="发布者头像URL")
    comment_count: int = 0  # 评论数

    model_config = ConfigDict(from_attributes=True)


# --------------------------
# 评论相关模型
# --------------------------
class CommentBase(BaseModel):
    """评论基础模型"""
    content: str = Field(..., max_length=500, description="评论内容（最多500字）")


class CreateCommentRequest(CommentBase):
    """创建评论请求模型"""
    post_id: int = Field(..., description="关联帖子ID")
    user_id: int = Field(..., description="评论者用户ID")


class CommentResponse(CommentBase):
    """评论返回模型"""
    comment_id: int
    post_id: int
    user_id: int
    create_time: datetime
    nickname: str  # 评论者昵称
    avatar: Optional[str] = None  # 评论者头像

    model_config = ConfigDict(from_attributes=True)


# --------------------------
# 学校相关模型
# --------------------------
class SchoolOut(BaseModel):
    """学校信息返回模型"""
    school_id: int
    school_name: str
    city: Optional[str] = None
    address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --------------------------
# 消息设置相关模型
# --------------------------
class UserMessageSettingsOut(BaseModel):
    """消息设置返回模型"""
    receive_book_notice: bool  # 是否接收易书通知
    interactive_msg_switch: bool  # 互动消息开关
    system_notice_switch: bool  # 系统通知开关
    follow_update_switch: bool  # 关注上新开关
    auto_reply_switch: bool  # 自动回复开关
    auto_reply_content: str  # 自动回复内容

    model_config = ConfigDict(from_attributes=True)


class UserMessageSettingsUpdate(BaseModel):
    """消息设置更新模型"""
    receive_book_notice: Optional[bool] = None
    interactive_msg_switch: Optional[bool] = None
    system_notice_switch: Optional[bool] = None
    follow_update_switch: Optional[bool] = None


class AutoReplyUpdate(BaseModel):
    """自动回复更新模型"""
    auto_reply_switch: Optional[bool] = None
    auto_reply_content: Optional[str] = None


# --------------------------
# 全局响应模型
# --------------------------
class SuccessResponse(BaseModel):
    """成功响应通用模型"""
    code: int = 200
    message: str = "操作成功"
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """错误响应通用模型"""
    code: int
    message: str
    data: Optional[dict] = None
    request_id: Optional[str] = None