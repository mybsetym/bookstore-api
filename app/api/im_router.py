# app/api/im_router.py
# 标准库导入
from typing import Dict, List

# 第三方库导入
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

# 本地应用导入
from app.services.im_service import IMService

# 定义路由前缀和标签
router = APIRouter(
    prefix="/im",
    tags=["即时通讯"]
)

# 初始化IM服务
im_service = IMService()

# 用于存储WebSocket连接（用户ID -> WebSocket对象）
active_connections: Dict[int, WebSocket] = {}


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """建立WebSocket连接，用于实时推送通知"""
    await websocket.accept()
    active_connections[user_id] = websocket  # 存储连接
    try:
        while True:
            # 保持连接（可接收客户端消息，这里暂不处理）
            await websocket.receive_text()
    except WebSocketDisconnect:
        # 断开连接时移除
        active_connections.pop(user_id, None)


async def push_notification_to_user(user_id: int, message: str):
    """
    向指定用户推送通知
    :param user_id: 目标用户ID
    :param message: 通知内容
    """
    # 1. 检查用户是否有活跃的WebSocket连接
    if user_id in active_connections:
        websocket = active_connections[user_id]
        try:
            # 通过WebSocket实时推送
            await websocket.send_text(message)
            return True
        except Exception as e:
            # 连接异常时移除
            active_connections.pop(user_id, None)
            raise HTTPException(status_code=500, detail=f"推送通知失败: {str(e)}")

    # 2. 如果没有WebSocket连接，可 fallback 到IM服务推送（可选）
    # 例如调用腾讯云IM的发送消息接口
    # await im_service.send_single_message(user_id, message)
    return False

@router.get("/user-sign", summary="获取IM用户签名")
async def get_im_user_sign(
    user_id: int = Query(..., description="用户ID（对应logindata表的ID）"),
    expire: int = Query(86400, description="签名有效期（秒），默认1天")
):
    """生成用户登录IM所需的签名（UserSig）"""
    try:
        data = await im_service.get_user_sig(user_id, expire)
        return {
            "code": 200,
            "message": "获取成功",
            "data": data
        }
    except HTTPException as e:
        return {
            "code": e.status_code,
            "message": e.detail,
            "data": None
        }