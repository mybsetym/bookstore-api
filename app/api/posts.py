# app/api/posts.py
from fastapi import APIRouter, HTTPException, Query, Path, Body
from pydantic import BaseModel
from app.core.schemas import CreatePostRequest, PostResponse
from app.utils.db import execute_query, execute_query_one, execute_update
from app.utils.notification_utils import send_interactive_notification
from datetime import datetime, timezone

router = APIRouter(
    prefix="/posts",
    tags=["广场模块"],
    responses={404: {"description": "帖子不存在"}}
)


# 新增评论请求模型
class CreateCommentRequest(BaseModel):
    user_id: int
    content: str


# 评论响应模型
class CommentResponse(BaseModel):
    comment_id: int
    post_id: int
    user_id: int
    content: str
    create_time: datetime


# 发布帖子（确保响应模型匹配）
@router.post("/", summary="发布帖子", response_model=PostResponse)
def create_post(req: CreatePostRequest):
    # 1. 校验用户存在（users表主键是id，和之前posts表外键一致）
    user = execute_query_one(
        sql="SELECT id, username AS nickname, avatar FROM users WHERE id = %s",
        params=(req.user_id,)
    )
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 2. 处理图片URL（列表转字符串存储）
    img_str = ",".join(req.img_urls) if req.img_urls else None

    # 3. 插入posts表（确保表已创建成功）
    now = datetime.now(timezone.utc)
    execute_update(
        sql="""
            INSERT INTO posts (user_id, content, img_urls, status, create_time, update_time)
            VALUES (%s, %s, %s, 'pending_audit', %s, %s)
            """,
        params=(req.user_id, req.content, img_str, now, now)
    )

    # 4. 返回响应（严格匹配PostResponse字段）
    post_id = execute_query_one("SELECT LAST_INSERT_ID() AS id")["id"]
    return PostResponse(
        post_id=post_id,
        user_id=req.user_id,
        content=req.content,
        img_urls=req.img_urls,
        create_time=now,
        status="pending_audit",
        nickname=user["nickname"],
        avatar=user.get("avatar")  # 头像可选，不存在返回None
    )


# 获取帖子列表（测试接口，确保路由正常）
@router.get("/", summary="获取广场帖子列表")
def get_post_list(
        page: int = Query(1, ge=1),
        page_size: int = Query(10, ge=1, le=50)
):
    offset = (page - 1) * page_size
    # 只查询已审核通过的帖子
    posts = execute_query(
        sql="""
            SELECT p.post_id,
                   p.content,
                   p.img_urls,
                   p.create_time,
                   p.status,
                   u.username AS nickname,
                   u.avatar,
                   p.user_id
            FROM posts p
                     LEFT JOIN users u ON p.user_id = u.id
            WHERE p.status = 'visible'
            ORDER BY p.create_time DESC
                LIMIT %s
            OFFSET %s
            """,
        params=(page_size, offset)
    )
    # 处理图片URL（字符串转列表）
    for post in posts:
        post["img_urls"] = post["img_urls"].split(",") if post["img_urls"] else []
    # 统计总数
    total = execute_query_one(
        sql="SELECT COUNT(*) AS total FROM posts WHERE status = 'visible'"
    )["total"]
    return {
        "code": 200,
        "message": "success",
        "data": {"total": total, "page": page, "page_size": page_size, "posts": posts}
    }


# 获取帖子详情
@router.get("/{post_id}", summary="获取帖子详情")
def get_post_detail(post_id: int = Path(..., ge=1)):
    post = execute_query_one(
        sql="""
            SELECT p.post_id,
                   p.content,
                   p.img_urls,
                   p.create_time,
                   p.status,
                   u.username AS nickname,
                   u.avatar,
                   p.user_id
            FROM posts p
                     LEFT JOIN users u ON p.user_id = u.id
            WHERE p.post_id = %s
            """,
        params=(post_id,)
    )
    if not post:
        raise HTTPException(status_code=404, detail="帖子不存在")
    post["img_urls"] = post["img_urls"].split(",") if post["img_urls"] else []
    return {"code": 200, "message": "success", "data": post}


# 添加帖子评论接口
@router.post("/{post_id}/comments", summary="添加帖子评论", response_model=CommentResponse)
def add_post_comment(
        post_id: int = Path(..., ge=1, description="帖子ID"),
        req: CreateCommentRequest = Body(..., description="评论内容和用户信息")
):
    # 1. 校验评论用户存在
    user = execute_query_one(
        sql="SELECT id FROM users WHERE id = %s",
        params=(req.user_id,)
    )
    if not user:
        raise HTTPException(status_code=404, detail="评论用户不存在")

    # 2. 校验帖子存在并获取帖子作者信息
    post_info = execute_query_one(
        sql="SELECT user_id AS author_id, content FROM posts WHERE post_id = %s",
        params=(post_id,)
    )
    if not post_info:
        raise HTTPException(status_code=404, detail="帖子不存在")
    author_id = post_info["author_id"]
    post_content = post_info["content"][:20] + "..."  # 截取前个20字

    # 3. 插入评论到数据库
    now = datetime.now(timezone.utc)
    execute_update(
        sql="""
        INSERT INTO comments (post_id, user_id, content, create_time)
        VALUES (%s, %s, %s, %s)
        """,
        params=(post_id, req.user_id, req.content, now)
    )
    comment_id = execute_query_one("SELECT LAST_INSERT_ID() AS id")["id"]

    # 4. 发送互动通知
    send_interactive_notification(
        user_id=author_id,
        content=f"你的帖子「{post_content}」收到了新评论：{req.content[:15]}...",
        business_id=comment_id
    )

    # 5. 返回评论信息
    return CommentResponse(
        comment_id=comment_id,
        post_id=post_id,
        user_id=req.user_id,
        content=req.content,
        create_time=now
    )