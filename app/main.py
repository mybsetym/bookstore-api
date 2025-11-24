import os
from fastapi import FastAPI
from app.api import search
from app.api import auth, book, order, profile, school, products # 导入 product
from fastapi.middleware.cors import CORSMiddleware
from app.api.im_router import router as im_router  # 导入IM路由
from fastapi.staticfiles import StaticFiles
from app.api import posts
import logging
from app.core.exception_handlers import register_exception_handlers

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger("bookstore")
app = FastAPI(
    title="图书商城API",
    description="适配现有数据库表结构的后端接口",
    version="1.3.1"
)

# 解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
# 注册路由
app.include_router(auth.router)
app.include_router(book.router)
app.include_router(order.router)
app.include_router(profile.router)
app.include_router(school.router)  # 注册学校模块路由
app.include_router(search.router)
app.include_router(im_router)
app.include_router(products.router)
app.include_router(posts.router)
# app/main.py（确保已挂载static）

app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")
# 健康检查
@app.get("/health", tags=["系统"])
async def health_check():
    return {"status": "healthy", "message": "服务正常运行"}