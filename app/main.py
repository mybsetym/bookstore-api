from fastapi import FastAPI
from app.api import school
from app.api import search
from app.api import auth, book, order, profile, school, products # 导入 product
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="图书商城API",
    description="适配现有数据库表结构的后端接口",
    version="1.0.0"
)

# 解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(book.router)
app.include_router(order.router)
app.include_router(profile.router)
app.include_router(school.router)  # 注册学校模块路由
app.include_router(search.router)

app.include_router(products.router)
# 健康检查
@app.get("/", summary="健康检查")
def root():
    return {"message": "图书商城API运行中"}