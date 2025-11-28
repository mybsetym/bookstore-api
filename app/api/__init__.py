from fastapi import APIRouter
from typing import Dict  # 导入必要的类型

# 导入所有 API 模块（按功能分组，添加注释说明）
from app.api import (
    auth,          # 认证模块（登录、注册、token校验）
    users,         # 用户管理模块（个人信息、权限）
    book,          # 图书管理模块（CRUD、筛选）
    order,         # 订单模块（创建、查询、状态）
    logistics,     # 物流模块（物流信息查询、更新）
    admin,         # 管理员模块（审核、权限管理）
    nearby,        # 附近模块（同城图书推荐）
    recommend,     # 推荐模块（个性化图书推荐）
    posts,         # 帖子模块（广场发帖、评论）
    reviews,       # 评价模块（图书评价、打分）
    im_router,     # 即时通讯模块（WebSocket、消息推送）
    message_settings,  # 消息设置模块（自动回复、通知开关）
    school,        # 学校模块（学校列表、绑定）
    search,        # 搜索模块（图书、帖子搜索）
    upload,        # 上传模块（图片、文件上传）
    profile        # 个人资料模块（资料修改、查询）
)

# 主 API 路由器（添加类型注解，明确实例类型）
api_router: APIRouter = APIRouter(
    prefix="/api/v1",  # 统一 API 前缀（可选，规范接口路径）
    tags=["核心接口集合"],  # 主路由标签（文档中分组显示）
    responses={404: {"description": "接口不存在"}},  # 全局响应模板
)

# 注册所有路由（仅保留 router/prefix/tags 合法参数）
api_router.include_router(auth.router, tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(book.router, prefix="/books", tags=["图书管理"])
api_router.include_router(order.router, prefix="/orders", tags=["订单管理"])
api_router.include_router(logistics.router, prefix="/logistics", tags=["物流管理"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理员接口"])
api_router.include_router(nearby.router, tags=["附近图书"])
api_router.include_router(recommend.router, prefix="/recommendations", tags=["个性化推荐"])
api_router.include_router(posts.router, prefix="/posts", tags=["帖子广场"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["图书评价"])
api_router.include_router(im_router.router, prefix="/im", tags=["即时通讯"])
api_router.include_router(message_settings.router, prefix="/message-settings", tags=["消息设置"])
api_router.include_router(school.router, prefix="/schools", tags=["学校管理"])
api_router.include_router(search.router, prefix="/search", tags=["搜索服务"])
api_router.include_router(upload.router, prefix="/upload", tags=["文件上传"])
api_router.include_router(profile.router, prefix="/profile", tags=["个人资料"])

# 健康检查接口
@api_router.get("/", tags=["基础功能"])
def root() -> Dict[str, str]:
    return {
        "status": "healthy",
        "message": "二手书平台API正常运行",
        "docs_url": "/docs"
    }