from fastapi import APIRouter, Query, HTTPException, Body
# 假设你已经将数据库操作异步化
from app.utils.db import execute_query_one_async
from tencentcloud.im.v20201229 import im_client, models
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from app.config import settings

router = APIRouter(
    prefix="/im",
    tags=["即时通讯模块"]
)


def get_im_client():
    """初始化并返回腾讯云IM客户端"""
    try:
        cred = credential.Credential(settings.TENCENT_IM_SECRET_ID, settings.TENCENT_IM_SECRET_KEY)
        return im_client.ImClient(cred, "ap-guangzhou")
    except Exception as e:
        raise HTTPException(status_code=500, detail="IM服务配置错误")


@router.get("/user-sign", summary="获取IM用户签名（用于客户端登录）")
async def get_im_user_sign(user_id: int = Query(..., description="用户ID")):
    """客户端需要先获取该签名，才能登录腾讯云IM"""
    try:
        # 校验用户是否存在（可选，但建议保留）
        user = await execute_query_one_async("SELECT ID FROM logindata WHERE ID = %s", (user_id,))
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        client = get_im_client()
        req = models.SignatureRequest()
        req.SdkAppId = settings.TENCENT_IM_SDK_APP_ID
        req.UserId = str(user_id)
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
    except TencentCloudSDKException as e:
        raise HTTPException(status_code=502, detail=f"IM服务异常: {e.message}")
    except HTTPException:
        # 直接抛出已定义好的HTTP异常
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.post("/create-conversation", summary="创建点对点会话（后端校验）")
async def create_im_conversation(
        from_user_id: int = Body(..., description="发起方用户ID"),
        to_user_id: int = Body(..., description="接收方用户ID")
):
    """
    买家在商品页点击“联系卖家”时调用。
    主要做权限校验和业务记录，实际会话创建建议由客户端SDK完成。
    """
    if from_user_id == to_user_id:
        raise HTTPException(status_code=400, detail="不能与自己创建会话")

    try:
        # 1. 校验双方用户是否存在
        from_user = await execute_query_one_async("SELECT ID FROM logindata WHERE ID = %s", (from_user_id,))
        to_user = await execute_query_one_async("SELECT ID FROM logindata WHERE ID = %s", (to_user_id,))
        if not from_user or not to_user:
            raise HTTPException(status_code=404, detail="用户不存在")

        return {
            "code": 200,
            "message": "会话创建请求已受理",
            "data": {
                "conversation_id": f"p2p_{min(from_user_id, to_user_id)}_{max(from_user_id, to_user_id)}",
                "from_user_id": from_user_id,
                "to_user_id": to_user_id
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器内部错误")