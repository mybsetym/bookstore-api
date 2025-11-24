# app/api/posts.py
from fastapi import APIRouter, HTTPException, Query, Path
from app.core.schemas import CreatePostRequest, PostResponse
from app.utils.db import execute_query, execute_query_one, execute_update
from datetime import datetime, timezone

router = APIRouter(
    prefix="/posts",
    tags=["广场模块"],
    responses={404: {"description": "帖子不存在"}}
)


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