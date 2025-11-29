# app/core/exceptions.py
from fastapi import status


class AppException(Exception):
    """系统基础异常类，所有自定义异常继承此类"""
    def __init__(self, message: str, code: int = 400, data: dict = None, biz_code: str = None):
        self.message = message
        self.code = code  # HTTP状态码
        self.data = data or {}
        if biz_code:
            self.data["biz_code"] = biz_code
        super().__init__(self.message)


# --------------------------
# 业务场景异常（按模块划分）
# --------------------------
class UserException(AppException):
    """用户模块异常（注册/登录/权限等）"""
    pass


class ProductException(AppException):
    """商品模块异常（创建/更新/库存等）"""
    pass


class OrderException(AppException):
    """订单模块异常（创建/支付/状态变更等）"""
    pass


class AdminException(AppException):
    """管理员模块异常（审核/权限等）"""
    pass


# --------------------------
# 通用具体异常
# --------------------------
class ResourceNotFoundError(AppException):
    """资源不存在（通用）"""
    def __init__(self, resource: str = "资源", biz_code: str = "RESOURCE_NOT_FOUND"):
        super().__init__(
            message=f"{resource}不存在",
            code=status.HTTP_404_NOT_FOUND,
            biz_code=biz_code,
            data={"resource": resource}
        )


class PermissionDeniedError(AppException):
    """权限不足（通用）"""
    def __init__(self, biz_code: str = "PERMISSION_DENIED"):
        super().__init__(
            message="权限不足，无法执行此操作",
            code=status.HTTP_403_FORBIDDEN,
            biz_code=biz_code
        )


class DuplicateDataError(AppException):
    """数据重复（如手机号已注册）"""
    def __init__(self, field: str = "数据", biz_code: str = "DUPLICATE_DATA"):
        message = f"{field}已被占用，请更换后重试" if field in ["手机号", "邮箱"] else f"{field}已存在，请勿重复提交"
        super().__init__(
            message=message,
            code=status.HTTP_400_BAD_REQUEST,
            biz_code=biz_code,
            data={"field": field}
        )


# --------------------------
# 用户模块具体异常
# --------------------------
class UserNotFoundError(UserException):
    """用户不存在"""
    def __init__(self):
        super().__init__(
            message="用户不存在，请检查用户ID",
            code=status.HTTP_404_NOT_FOUND,
            biz_code="USER_NOT_FOUND"
        )


class InvalidCredentialsError(UserException):
    """登录凭证无效（如密码错误）"""
    def __init__(self):
        super().__init__(
            message="手机号/邮箱或密码错误",
            code=status.HTTP_401_UNAUTHORIZED,
            biz_code="INVALID_CREDENTIALS"
        )