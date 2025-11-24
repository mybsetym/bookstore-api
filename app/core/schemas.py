# app/core/schemas.py（补充后完整版本）
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

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