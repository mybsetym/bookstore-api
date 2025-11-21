# app/api/im.py
from fastapi import APIRouter, Query, HTTPException, Body
from app.utils.db import execute_query_one
from tencentcloud.im.v20201229 import im_client, models
from tencentcloud.common import credential
from app.config import settings  # 需在配置中添加腾讯云IM密钥（SECRET_ID/SECRET_KEY/SDK_APP_ID）

router = APIRouter(
    prefix="/im",
    tags=["即时通讯模块"]
)



# 初始化腾讯云IM客户端
def get_im_client():
    cred = credential.Credential(settings.TENCENT_IM_SECRET_ID, settings.TENCENT_IM_SECRET_KEY)
    return im_client.ImClient(cred, "ap-guangzhou")


@router.get("/user-sign", summary="获取IM用户签名（用于客户端登录）")
def get_im_user_sign(user_id: int = Query(..., description="用户ID")):
    """客户端需要先获取该签名，才能登录腾讯云IM"""
    client = get_im_client()
    req = models.SignatureRequest()
    req.SdkAppId = settings.TENCENT_IM_SDK_APP_ID
    req.UserId = str(user_id)  # IM的UserId需为字符串
    req.Expire = 86400  # 签名有效期1天
    resp = client.Signature(req)
    return {
        "code": 200,
        "message": "获取成功",
        "data": {
            "user_id": user_id,
            "im_user_id": str(user_id),
            "signature": resp.Signature,
            "sdk_app_id": settings.TENCENT_IM_SDK_APP_ID
        }
    }


@router.post("/create-conversation", summary="创建点对点会话")
def create_im_conversation(
        from_user_id: int = Body(..., description="发起方用户ID"),
        to_user_id: int = Body(..., description="接收方用户ID")
):
    """买家在商品页点击“联系卖家”时调用，创建IM会话"""
    # 1. 校验双方用户是否存在
    from_user = execute_query_one("SELECT ID FROM logindata WHERE ID = %s", (from_user_id,))
    to_user = execute_query_one("SELECT ID FROM logindata WHERE ID = %s", (to_user_id,))
    if not from_user or not to_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 2. 调用腾讯云IM接口创建会话（客户端也可直接创建，后端仅做校验）
    client = get_im_client()
    req = models.CreateP2PSessionRequest()
    req.SdkAppId = settings.TENCENT_IM_SDK_APP_ID
    req.FromUserId = str(from_user_id)
    req.ToUserId = str(to_user_id)
    client.CreateP2PSession(req)

    return {
        "code": 200,
        "message": "会话创建成功",
        "data": {
            "conversation_id": f"p2p_{min(from_user_id, to_user_id)}_{max(from_user_id, to_user_id)}",
            "from_user_id": from_user_id,
            "to_user_id": to_user_id
        }
    }