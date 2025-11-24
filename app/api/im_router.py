from fastapi import APIRouter, Query
#from app.services.im_service import IMService  # 导入服务类

# 定义路由前缀和标签
router = APIRouter(
    prefix="/im",
    tags=["即时通讯"]
)

# 初始化IM服务
#im_service = IMService()

@router.get("/user-sign", summary="获取IM用户签名")
async def get_im_user_sign(
    user_id: int = Query(..., description="用户ID（对应logindata表的ID）"),
    expire: int = Query(86400, description="签名有效期（秒），默认1天")
):
    """生成用户登录IM所需的签名（UserSig）"""
    return {
        "code": 200,
        "message": "获取成功",
        #"data": await im_service.get_user_sig(user_id, expire)
    }