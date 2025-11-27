# app/api/message_settings.py
# 第三方库导入（FastAPI 相关）
from fastapi import APIRouter, Depends, HTTPException

# 本地应用导入（核心模型 → 核心安全 → 工具类）
from app.core.schemas import (
    AutoReplyUpdate,
    UserMessageSettingsOut,
    UserMessageSettingsUpdate,
)
from app.core.security import get_current_user  # 你的用户登录校验依赖
from app.utils.db import execute_query_one, execute_update

router = APIRouter(prefix="/message-settings", tags=["消息设置"])


# 初始化用户消息设置（用户注册时/首次获取时自动创建）
def init_user_message_settings(user_id: int):
    existing = execute_query_one(
        "SELECT * FROM user_message_settings WHERE user_id = %s",
        (user_id,)
    )
    if not existing:
        execute_update(
            sql="INSERT INTO user_message_settings (user_id) VALUES (%s)",
            params=(user_id,)
        )


# 1. 获取用户消息设置
@router.get("/", summary="获取用户消息设置", response_model=UserMessageSettingsOut)
def get_message_settings(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    # 自动初始化设置（首次访问时创建默认配置）
    init_user_message_settings(user_id)

    # 查询用户设置
    settings = execute_query_one(
        "SELECT * FROM user_message_settings WHERE user_id = %s",
        (user_id,)
    )
    if not settings:
        raise HTTPException(status_code=404, detail="消息设置不存在")

    # 转换数据库tinyint为bool
    return {
        "receive_book_notice": bool(settings["receive_book_notice"]),
        "interactive_msg_switch": bool(settings["interactive_msg_switch"]),
        "system_notice_switch": bool(settings["system_notice_switch"]),
        "follow_update_switch": bool(settings["follow_update_switch"]),
        "auto_reply_switch": bool(settings["auto_reply_switch"]),
        "auto_reply_content": settings["auto_reply_content"]
    }


# 2. 更新消息设置（通知开关）
@router.put("/", summary="更新消息通知开关")
def update_message_settings(
        update_data: UserMessageSettingsUpdate,
        current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]
    init_user_message_settings(user_id)

    # 构造更新字段
    update_fields = []
    params = []
    if update_data.receive_book_notice is not None:
        update_fields.append("receive_book_notice = %s")
        params.append(1 if update_data.receive_book_notice else 0)
    if update_data.interactive_msg_switch is not None:
        update_fields.append("interactive_msg_switch = %s")
        params.append(1 if update_data.interactive_msg_switch else 0)
    if update_data.system_notice_switch is not None:
        update_fields.append("system_notice_switch = %s")
        params.append(1 if update_data.system_notice_switch else 0)
    if update_data.follow_update_switch is not None:
        update_fields.append("follow_update_switch = %s")
        params.append(1 if update_data.follow_update_switch else 0)

    if not update_fields:
        raise HTTPException(status_code=400, detail="没有需要更新的开关")

    # 执行更新
    params.append(user_id)
    execute_update(
        sql=f"UPDATE user_message_settings SET {', '.join(update_fields)} WHERE user_id = %s",
        params=params
    )
    return {"code": 200, "message": "消息设置更新成功"}


# 3. 更新自动回复设置
@router.put("/auto-reply", summary="更新自动回复配置")
def update_auto_reply(
        update_data: AutoReplyUpdate,
        current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]
    init_user_message_settings(user_id)

    # 构造更新字段
    update_fields = []
    params = []
    if update_data.auto_reply_switch is not None:
        update_fields.append("auto_reply_switch = %s")
        params.append(1 if update_data.auto_reply_switch else 0)
    if update_data.auto_reply_content is not None:
        update_fields.append("auto_reply_content = %s")
        params.append(update_data.auto_reply_content)

    if not update_fields:
        raise HTTPException(status_code=400, detail="没有需要更新的自动回复配置")

    # 执行更新
    params.append(user_id)
    execute_update(
        sql=f"UPDATE user_message_settings SET {', '.join(update_fields)} WHERE user_id = %s",
        params=params
    )
    return {"code": 200, "message": "自动回复设置更新成功"}