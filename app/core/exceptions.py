# app/core/exceptions.py
from fastapi import status


class AppException(Exception):
    """系统基础异常类，所有自定义异常继承此类"""
    def __init__(self, message: str, code: int = 400, data: dict = None):
        self.message = message
        self.code = code  # HTTP状态码
        self.data = data or {}
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

# 示例：常用具体异常
class ResourceNotFoundError(AppException):
    """资源不存在（通用）"""
    def __init__(self, resource: str = "资源"):
        super().__init__(message=f"{resource}不存在", code=status.HTTP_404_NOT_FOUND)

class PermissionDeniedError(AppException):
    """权限不足（通用）"""
    def __init__(self):
        super().__init__(message="权限不足，无法执行此操作", code=status.HTTP_403_FORBIDDEN)

class DuplicateDataError(AppException):
    """数据重复（如手机号已注册）"""
    def __init__(self, field: str = "数据"):
        super().__init__(message=f"{field}已存在，请勿重复提交", code=status.HTTP_400_BAD_REQUEST)