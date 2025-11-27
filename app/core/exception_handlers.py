# app/core/exception_handlers.py
# 标准库导入
import logging
import uuid

# 第三方库导入
from fastapi import Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

# 本地应用导入
from app.core.exceptions import AppException
from app.core.schemas import ErrorResponse

# 初始化日志（独立配置，避免依赖 main.py）
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # 优化日志格式
)
logger = logging.getLogger("bookstore")

# --------------------------
# 1. 处理自定义业务异常
# --------------------------
async def app_exception_handler(request: Request, exc: AppException):
    request_id = str(uuid.uuid4())
    logger.error(
        f"Request ID: {request_id} | 业务异常: {exc.message} | 路径: {request.url.path} | 业务错误码: {exc.data.get('biz_code') if exc.data else '无'}",
        exc_info=True
    )
    return JSONResponse(
        status_code=exc.code,
        content=ErrorResponse(
            code=exc.code,
            message=exc.message,
            data=exc.data,
            request_id=request_id
        ).model_dump()
    )

# --------------------------
# 2. 处理FastAPI内置HTTP异常
# --------------------------
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = str(uuid.uuid4())
    logger.warning(
        f"Request ID: {request_id} | HTTP异常: {exc.detail} | 状态码: {exc.status_code} | 路径: {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.status_code,
            message=exc.detail,
            request_id=request_id
        ).model_dump()
    )

# --------------------------
# 3. 处理参数校验失败异常
# --------------------------
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = str(uuid.uuid4())
    errors = [
        {"field": ".".join(error["loc"]), "message": error["msg"]}
        for error in exc.errors()
    ]
    logger.warning(
        f"Request ID: {request_id} | 参数校验失败 | 路径: {request.url.path} | 错误详情: {errors}"
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="请求参数格式错误，请检查后重试",
            data={"errors": errors},
            request_id=request_id
        ).model_dump()
    )

# --------------------------
# 4. 处理未捕获通用异常
# --------------------------
async def general_exception_handler(request: Request, exc: Exception):
    request_id = str(uuid.uuid4())
    logger.critical(
        f"Request ID: {request_id} | 未捕获异常 | 路径: {request.url.path}",
        exc_info=True  # 强制打印堆栈，便于排查
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="系统内部错误，请稍后重试（如持续出现，请联系客服）",
            request_id=request_id
        ).model_dump()
    )

# --------------------------
# 异常处理器注册函数（供 main.py 调用）
# --------------------------
def register_exception_handlers(app):
    app.exception_handler(AppException)(app_exception_handler)
    app.exception_handler(HTTPException)(http_exception_handler)
    app.exception_handler(RequestValidationError)(validation_exception_handler)
    app.exception_handler(Exception)(general_exception_handler)