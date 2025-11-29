# app/utils/notification_utils.py
import asyncio
from app.utils.db import execute_query_one, execute_update
from app.api.im_router import push_notification_to_user  # 复用WebSocket推送



def send_notification(
        user_id: int,
        notify_type: str,
        content: str,
        business_id: int = None
) -> None:
    """
    统一发送通知（自动校验用户开关状态）
    :param user_id: 接收通知的用户ID
    :param notify_type: 通知类型（对应开关字段）：interact(互动)/system(系统)/book(易书)/follow(关注上新)
    :param content: 通知内容
    :param business_id: 关联业务ID
    """
    # 1. 校验用户对应的通知开关（根据类型映射开关字段）
    switch_field_map = {
        "interact": "interactive_msg_switch",
        "system": "system_notice_switch",
        "book": "receive_book_notice",
        "follow": "follow_update_switch"
    }
    if notify_type not in switch_field_map:
        raise ValueError(f"不支持的通知类型：{notify_type}")

    # 2. 查询用户开关状态（未设置则默认关闭）
    settings = execute_query_one(
        sql=f"SELECT {switch_field_map[notify_type]} FROM user_message_settings WHERE user_id = %s",
        params=(user_id,)
    )
    if not settings or not settings[switch_field_map[notify_type]]:
        return  # 开关关闭，不发送通知

    # 3. 插入通知到数据库
    execute_update(
        sql="""
            INSERT INTO notifications (user_id, type, content, business_id, is_read, create_time)
            VALUES (%s, %s, %s, %s, 0, NOW())
            """,
        params=(user_id, notify_type, content, business_id)
    )
    notify_id = execute_query_one("SELECT LAST_INSERT_ID() AS id")["id"]

    # 4. 实时推送给用户（在线则推送）
    new_notification = {
        "id": notify_id,
        "type": notify_type,
        "content": content,
        "business_id": business_id,
        "is_read": 0,
        "create_time": execute_query_one("SELECT NOW() AS time")["time"].strftime("%Y-%m-%d %H:%M:%S")
    }
    # 异步推送（兼容同步代码）
    asyncio.run(push_notification_to_user(user_id, new_notification))


# --------------------------
# 各场景通知快捷函数（直接调用）
# --------------------------
def send_interactive_notification(user_id: int, content: str, business_id: int = None):
    """发送互动通知（留言/回复/点赞）"""
    send_notification(user_id, "interact", content, business_id)


def send_system_notification(user_id: int, content: str, business_id: int = None):
    """发送系统通知（平台公告/权益变更）"""
    send_notification(user_id, "system", content, business_id)


def send_book_notification(user_id: int, content: str, business_id: int = None):
    """发送易书通知（订单/商品相关）"""
    send_notification(user_id, "book", content, business_id)


def send_follow_notification(user_id: int, content: str, business_id: int = None):
    """发送关注上新通知（关注的用户上新商品）"""
    send_notification(user_id, "follow", content, business_id)