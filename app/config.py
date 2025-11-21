import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量。如果 .env 文件不存在，也不会报错。
# 在生产环境中，你可以直接在系统环境变量中设置这些值。
load_dotenv()

class Settings(BaseSettings):
    # API 相关配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Second-Hand Book Platform"

    # 数据库配置
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "your_strong_password")
    DB_NAME: str = os.getenv("DB_NAME", "second_hand_book_db")

    # JWT (JSON Web Tokens) 配置
    # 务必在生产环境中使用一个强随机密钥，并通过环境变量设置
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "a_very_weak_secret_key_for_development_only")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Token 有效期

    # 第三方 API 配置
    KUAIDI100_APP_KEY: str = os.getenv("KUAIDI100_APP_KEY", "")
    KUAIDI100_CUSTOMER: str = os.getenv("KUAIDI100_CUSTOMER", "")

    # 其他配置
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

    class Config:
        case_sensitive = True  # 使配置项区分大小写

# 创建一个配置实例，供其他模块导入使用
settings = Settings()