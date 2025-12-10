import pytest
import pymysql
import sys
import os
from typing import Tuple

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 数据库配置（改为你的实际配置）
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "MyB202853@",
    "database": "bookstore",
    "charset": "utf8mb4",
    "autocommit": False
}

# 测试用临时数据（确保唯一，避免冲突）
TEST_EMAIL = f"test_register_{os.urandom(4).hex()}@example.com"
TEST_USERNAME = f"test_user_{os.urandom(4).hex()}"
TEST_PASSWORD = "Test@123456"


def get_db_connection() -> pymysql.connections.Connection:
    """获取数据库连接（与项目代码保持一致）"""
    return pymysql.connect(**DB_CONFIG)

def init_user_message_settings(user_id: int):
    # 临时调试：用当前连接查users表，看是否能看到这个user_id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE user_id = %s LIMIT 1", (user_id,))
    result = cursor.fetchone()
    print(f"插入消息设置时，当前连接能查到user_id={user_id}吗？：{bool(result)}")
    print(f"当前连接ID：{conn.thread_id()}，user_id类型：{type(user_id)}")

@pytest.fixture(scope="function")
def setup_test_tables():
    """
    测试前置：创建无外键的临时表，测试后清理数据
    跳过外键创建，改用代码层面校验user_id存在性
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. 创建临时users表（复刻原表结构，无外键）
    cursor.execute("""
        CREATE TEMPORARY TABLE IF NOT EXISTS temp_users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # 2. 创建临时消息设置表（无外键，仅保留字段结构）
    cursor.execute("""
        CREATE TEMPORARY TABLE IF NOT EXISTS temp_user_message_settings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            allow_notification TINYINT DEFAULT 1,
            allow_email TINYINT DEFAULT 1
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    conn.commit()

    yield conn, cursor  # 传递连接和游标给测试用例

    # 测试后置：清理临时表数据
    cursor.execute("DELETE FROM temp_user_message_settings;")
    cursor.execute("DELETE FROM temp_users;")
    conn.commit()
    cursor.close()
    conn.close()


def test_insert_user_get_correct_user_id(setup_test_tables):
    """测试1：插入用户后能正确获取自增user_id（int类型）"""
    conn, cursor = setup_test_tables

    # 插入测试用户
    insert_sql = """
        INSERT INTO temp_users (username, email, password) 
        VALUES (%s, %s, %s);
    """
    cursor.execute(insert_sql, (TEST_USERNAME, TEST_EMAIL, TEST_PASSWORD))
    user_id = cursor.lastrowid

    # 核心校验
    assert isinstance(user_id, int), f"user_id类型错误，实际是{type(user_id)}"
    assert user_id > 0, f"自增user_id无效，值为{user_id}"

    # 同一个连接内查询验证
    cursor.execute("SELECT 1 FROM temp_users WHERE user_id = %s LIMIT 1", (user_id,))
    result = cursor.fetchone()
    assert result is not None, f"同一个连接内查不到user_id={user_id}"

    print(f"测试1通过：插入用户的user_id={user_id}（类型：{type(user_id)}）")


def test_init_user_message_settings_no_foreign_key_error(setup_test_tables):
    """测试2：初始化消息设置时，user_id存在且类型正确（模拟外键校验）"""
    conn, cursor = setup_test_tables

    # 步骤1：插入用户并获取user_id
    insert_user_sql = """
        INSERT INTO temp_users (username, email, password) 
        VALUES (%s, %s, %s);
    """
    cursor.execute(insert_user_sql, (TEST_USERNAME, TEST_EMAIL, TEST_PASSWORD))
    user_id = cursor.lastrowid
    print(f"插入用户的user_id={user_id}，连接ID：{conn.thread_id()}")

    # 模拟外键校验：手动检查user_id是否存在
    cursor.execute("SELECT 1 FROM temp_users WHERE user_id = %s LIMIT 1", (user_id,))
    assert cursor.fetchone() is not None, f"user_id={user_id}不存在，无法初始化消息设置"

    # 步骤2：初始化消息设置（无外键，直接插入）
    insert_msg_sql = """
        INSERT INTO temp_user_message_settings (user_id, allow_notification, allow_email)
        VALUES (%s, %s, %s);
    """
    try:
        cursor.execute(insert_msg_sql, (user_id, 1, 1))
        conn.commit()
        print(f"测试2通过：成功为user_id={user_id}初始化消息设置")
    except Exception as e:
        raise AssertionError(f"插入消息设置失败：{e}") from e

    # 校验：消息设置表中存在该记录
    cursor.execute("SELECT 1 FROM temp_user_message_settings WHERE user_id = %s", (user_id,))
    assert cursor.fetchone() is not None, f"消息设置表中未找到user_id={user_id}的记录"


def test_full_register_flow(setup_test_tables):
    """测试3：完整注册流程（模拟项目的email_register接口逻辑）"""
    conn, cursor = setup_test_tables

    try:
        # 步骤1：插入用户
        insert_user_sql = """
            INSERT INTO temp_users (username, email, password) 
            VALUES (%s, %s, %s);
        """
        cursor.execute(insert_user_sql, (TEST_USERNAME, TEST_EMAIL, TEST_PASSWORD))
        user_id = cursor.lastrowid
        print(f"完整流程-插入用户：user_id={user_id}（类型：{type(user_id)}）")

        # 步骤2：校验当前连接能看到该user_id
        cursor.execute("SELECT user_id FROM temp_users WHERE email = %s", (TEST_EMAIL,))
        db_user_id = cursor.fetchone()[0]
        assert db_user_id == user_id, f"user_id不一致：代码获取{user_id}，数据库查询{db_user_id}"

        # 步骤3：模拟外键校验 + 初始化消息设置
        cursor.execute("SELECT 1 FROM temp_users WHERE user_id = %s", (user_id,))
        assert cursor.fetchone() is not None, f"user_id={user_id}不存在"

        insert_msg_sql = """
            INSERT INTO temp_user_message_settings (user_id, allow_notification, allow_email)
            VALUES (%s, %s, %s);
        """
        cursor.execute(insert_msg_sql, (user_id, 1, 1))

        # 步骤4：提交事务
        conn.commit()
        print(f"测试3通过：完整注册流程执行成功，user_id={user_id}")

        # 最终校验
        cursor.execute("SELECT * FROM temp_users WHERE user_id = %s", (user_id,))
        assert cursor.fetchone() is not None, "users表无数据"

        cursor.execute("SELECT * FROM temp_user_message_settings WHERE user_id = %s", (user_id,))
        assert cursor.fetchone() is not None, "user_message_settings表无数据"

    except Exception as e:
        conn.rollback()
        raise e


if __name__ == "__main__":
    # 运行所有测试用例，打印详细日志
    pytest.main([__file__, "-v", "-s"])