# app/core/schemas.py（补充后完整版本）
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# 消息设置返回模型
class UserMessageSettingsOut(BaseModel):
    receive_book_notice: bool  # 是否接收易书通知
    interactive_msg_switch: bool  # 互动消息开关
    system_notice_switch: bool  # 通知消息开关
    follow_update_switch: bool  # 关注上新开关
    auto_reply_switch: bool  # 自动回复开关
    auto_reply_content: str  # 自动回复内容

    model_config = ConfigDict(from_attributes=True)


# 消息设置更新模型
class UserMessageSettingsUpdate(BaseModel):
    receive_book_notice: Optional[bool] = None
    interactive_msg_switch: Optional[bool] = None
    system_notice_switch: Optional[bool] = None
    follow_update_switch: Optional[bool] = None


# 自动回复更新模型
class AutoReplyUpdate(BaseModel):
    auto_reply_switch: Optional[bool] = None
    auto_reply_content: Optional[str] = None


# --------------------------
# 全局错误响应模型（原有，保留）
# --------------------------
class ErrorResponse(BaseModel):
    code: int
    message: str
    data: Optional[dict] = None
    request_id: Optional[str] = None

# --------------------------
# 广场发帖相关模型（新增，解决导入问题）
# --------------------------
class PostBase(BaseModel):
    content: str = Field(..., max_length=1000, description="帖子内容（最多1000字）")
    img_urls: Optional[List[str]] = Field(None, max_length=3, description="图片URL列表（最多3张）")

class CreatePostRequest(PostBase):
    user_id: int = Field(..., description="发布者用户ID（关联users表的id）")

class PostResponse(PostBase):
    post_id: int
    user_id: int
    create_time: datetime
    status: str = Field(..., pattern="^(pending_audit|visible|hidden)$", description="帖子状态")
    nickname: str = Field(..., description="发布者昵称")
    avatar: Optional[str] = Field(None, description="发布者头像URL")

    model_config = ConfigDict(from_attributes=True)  # Pydantic V2