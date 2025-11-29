# app/utils/db_check.py
import logging
import pymysql
from pymysql.err import OperationalError, ProgrammingError, InterfaceError

# 配置日志（终端输出彩色/清晰格式）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]  # 输出到终端
)
logger = logging.getLogger("db_check")

# 数据库配置（建议抽离到配置文件，这里先硬编码方便测试）
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "MyB202853@",
    "database": "bookstore",  # 你的数据库名
    "charset": "utf8mb4",
    "port": 3306
}

def check_db_connection():
    """
    数据库连接全链路检测：
    1. 基础TCP连接（主机/端口是否可达）
    2. 数据库账号密码验证
    3. 目标数据库是否存在
    4. 核心表（users）是否存在
    返回：(是否成功, 检测信息)
    """
    conn = None
    try:
        # 1. 尝试建立TCP连接 + 账号密码验证
        logger.info("🔍 开始检测数据库连接...")
        conn = pymysql.connect(**DB_CONFIG)
        logger.info("✅ 步骤1：TCP连接/账号密码验证成功")

        # 2. 检测目标数据库是否存在
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()[0]
            if current_db != DB_CONFIG["database"]:
                raise ProgrammingError(f"目标数据库 {DB_CONFIG['database']} 不存在")
        logger.info("✅ 步骤2：目标数据库存在")

        # 3. 检测核心表（users）是否存在
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = 'users'
            """, (DB_CONFIG["database"],))
            table_exists = cursor.fetchone()[0] > 0
            if not table_exists:
                raise ProgrammingError("核心表 users 不存在")
        logger.info("✅ 步骤3：核心表 users 存在")

        # 4. 尝试执行简单查询（验证权限）
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
        logger.info("✅ 步骤4：数据库查询权限验证成功")

        logger.info("🎉 数据库连接全链路检测通过！")
        return (True, "数据库连接正常")

    except InterfaceError as e:
        msg = f"❌ 步骤1失败：TCP连接失败（主机/端口错误）- {str(e)}"
        logger.error(msg)
        return (False, msg)
    except OperationalError as e:
        if "Access denied" in str(e):
            msg = f"❌ 步骤1失败：账号/密码错误 - {str(e)}"
        elif "Unknown database" in str(e):
            msg = f"❌ 步骤2失败：数据库不存在 - {str(e)}"
        else:
            msg = f"❌ 数据库连接失败 - {str(e)}"
        logger.error(msg)
        return (False, msg)
    except ProgrammingError as e:
        msg = f"❌ 步骤3/4失败：表不存在或SQL语法错误 - {str(e)}"
        logger.error(msg)
        return (False, msg)
    except Exception as e:
        msg = f"❌ 未知错误：{str(e)}"
        logger.error(msg)
        return (False, msg)
    finally:
        if conn:
            conn.close()
            logger.info("🔌 数据库连接已关闭")

def check_db_before_request():
    """
    接口调用前的轻量检测（可选）：仅检测基础连接，不检测表
    可装饰在接口函数上，或在接口内调用
    """
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return True
    except Exception as e:
        logger.error(f"❌ 接口调用前检测到数据库连接失败：{str(e)}")
        return False
    finally:
        if conn:
            conn.close()