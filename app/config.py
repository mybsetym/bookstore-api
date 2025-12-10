# C:\Users\myb13\Desktop\bookstore-api\app\config
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
# 加载 .env 文件（保持不变）
load_dotenv()

# --------------------------
# 模块级路径变量（移到类外部，确保能被其他模块识别）
# --------------------------
# 项目根目录（config.py 所在路径：app/config.py → 两次 dirname 得到 bookstore-api 根目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 图片上传目录（按你原有逻辑，放在项目根目录同级；若想放在根目录内，可去掉 ".."）
# 推荐调整为：os.path.join(BASE_DIR, "static", "uploads")（放在 static 内，更规范）
UPLOAD_DIR = os.path.join(BASE_DIR, "..", "bookstore_uploads")

# 自动创建上传目录（模块加载时执行，确保目录存在）
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --------------------------
# Pydantic Settings 类（仅保留「环境变量相关配置」，符合其设计用途）
# --------------------------
class Settings(BaseSettings):
    # API 相关配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Second-Hand Book Platform"

    # 数据库配置（保持不变）
    DATABASE_URL: str = "mysql+asyncmy://root:MyB202853@@localhost:3306/bookstore"
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "MyB202853@")
    DB_NAME: str = os.getenv("DB_NAME", "bookstore")

    # JWT 配置（保持不变）
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "a_very_weak_secret_key_for_development_only")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 第三方 API 配置（保持不变）
    KUAIDI100_APP_KEY: str = os.getenv("KUAIDI100_APP_KEY", "")
    KUAIDI100_CUSTOMER: str = os.getenv("KUAIDI100_CUSTOMER", "")

    # 其他配置（保持不变）
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    #腾讯云配置
    TENCENT_IM_SECRET_ID: str  # 之前已添加的
    TENCENT_IM_SECRET_KEY: str  # 补充这一行（关键）
    TENCENT_IM_SDK_APP_ID: str  # 确保也有这个

    class Config:
        case_sensitive = True  # 区分大小写
        env_file = ".env"
# 创建配置实例（保持不变）
settings = Settings()