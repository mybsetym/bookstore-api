# app/core/constants.py
"""
项目全局常量定义
- 按业务模块分类，避免零散硬编码
- 枚举类型保证类型安全，注释说明业务含义和数据库映射关系
"""
from enum import IntEnum, StrEnum
from typing import Final

# ========================== 1. 图书相关常量 ==========================
class BookStatus(IntEnum):
    """图书状态（与数据库book.status字段一一映射，int类型）"""
    OFFLINE = 0  # 下架：不可推荐、不可下单
    ONLINE = 1   # 上架：可推荐、可下单（核心业务值）
    AUDITING = 2 # 审核中：暂不可推荐，待审核通过后改为ONLINE

class BookTargetType(StrEnum):
    """目标类型（与user_behavior.target_type字段映射）"""
    BOOK = "book"  # 行为目标为图书（推荐模块核心值）
    POST = "post"  # 行为目标为帖子（预留扩展）

# ========================== 2. 推荐系统专属常量 ==========================
class RecommendConfig:
    """推荐系统配置常量（可根据业务调整，避免硬编码）"""
    # 推荐数量限制
    DEFAULT_LIMIT: Final[int] = 10    # 默认推荐商品数量
    MIN_LIMIT: Final[int] = 5         # 最小推荐数量
    MAX_LIMIT: Final[int] = 30        # 最大推荐数量
    # 时间窗口（统计用户行为/热门商品的时间范围）
    HOT_BOOK_DAYS: Final[int] = 7     # 统计热门图书的时间窗口（最近7天）
    USER_PREFER_DAYS: Final[int] = 30 # 统计用户偏好的时间窗口（最近30天）
    # 推荐权重配置（浏览量/订单量权重）
    VIEW_WEIGHT: Final[float] = 0.3   # 浏览量权重
    ORDER_WEIGHT: Final[float] = 0.7  # 订单量权重（成交优先级更高）

# ========================== 3. 订单相关常量 ==========================
class OrderStatus(StrEnum):
    """订单状态（与数据库orders.status字段映射，str类型）"""
    PENDING = "pending"    # 待支付
    COMPLETED = "completed"# 已完成（推荐模块核心值，仅统计已成交订单）
    CANCELLED = "cancelled"# 已取消
    REFUNDED = "refunded"  # 已退款

# ========================== 4. 用户行为相关常量 ==========================
class UserBehaviorType(StrEnum):
    """用户行为类型（与user_behavior.behavior_type字段映射）"""
    VIEW = "view"      # 浏览（推荐模块核心值，统计浏览行为）
    COLLECT = "collect"# 收藏（预留：后续可加入偏好计算）
    BUY = "buy"        # 购买（预留：强化偏好权重）
    SHARE = "share"    # 分享（预留：扩展推荐维度）

# ========================== 5. 分类相关常量 ==========================
class CategoryConst:
    """分类模块常量"""
    MAX_CATEGORY_LIMIT: Final[int] = 50  # 分类查询最大返回数量
    DEFAULT_CATEGORY: Final[str] = "综合" # 无偏好时默认分类

# ========================== 6. 通用常量 ==========================
class CommonConst:
    """全局通用常量"""
    DATETIME_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"  # 数据库时间格式
    PAGE_SIZE: Final[int] = 20  # 通用分页大小（预留）