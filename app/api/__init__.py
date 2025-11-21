from fastapi import APIRouter

# 导入所有 API 模块
from app.api import auth, users, book, order, logistics, admin, nearby, recommend

# 创建主 API 路由器
api_router = APIRouter()

# 注册各个模块的路由
api_router.include_router(auth.router, tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(book.router, prefix="/books", tags=["books"])
api_router.include_router(order.router, prefix="/orders", tags=["orders"])
api_router.include_router(logistics.router, prefix="/logistics", tags=["logistics"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(nearby.router, tags=["nearby"])
api_router.include_router(recommend.router, prefix="/recommendations", tags=["recommendations"])

# 你可以在这里添加一个根路径的健康检查
@api_router.get("/", summary="Health Check")
def root():
    return {"message": "Welcome to the Second-Hand Book Platform API. See /docs for documentation."}