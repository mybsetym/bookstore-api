from fastapi import HTTPException
import time
import hmac
import hashlib
import base64
import httpx  # 替换requests为异步客户端
from app.config import settings
from app.utils.db import execute_query_one_async


class IMService:
    def __init__(self):
        self.secret_id = settings.TENCENT_IM_SECRET_ID
        self.secret_key = settings.TENCENT_IM_SECRET_KEY
        self.sdk_app_id = settings.TENCENT_IM_SDK_APP_ID
        self.api_host = "im.tencentcloudapi.com"
        self.api_version = "2020-12-29"
        # 初始化异步HTTP客户端
        self.client = httpx.AsyncClient(timeout=10)

    async def _check_user_exists(self, user_id: int) -> bool:
        user = await execute_query_one_async(
            "SELECT ID FROM logindata WHERE ID = %s",
            (user_id,)
        )
        return bool(user)

    def _generate_signature(self, action: str, params: dict) -> dict:
        # 签名生成逻辑保持不变
        public_params = {
            "SecretId": self.secret_id,
            "Timestamp": int(time.time()),
            "Nonce": int(time.time() * 1000),
            "Action": action,
            "Version": self.api_version
        }
        all_params = {**public_params, **params}

        sorted_params = sorted(all_params.items(), key=lambda x: x[0])
        query_string = "&".join([f"{k}={v}" for k, v in sorted_params if k != "Signature"])
        sign_str = f"GET{self.api_host}/?{query_string}"

        signature = hmac.new(
            self.secret_key.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).digest()
        all_params["Signature"] = base64.b64encode(signature).decode()
        return all_params

    async def _call_api(self, action: str, params: dict) -> dict:
        # 改为异步API调用
        try:
            params_with_sign = self._generate_signature(action, params)
            response = await self.client.get(  # 异步请求
                url=f"https://{self.api_host}",
                params=params_with_sign
            )
            result = response.json()

            if "Error" in result:
                raise Exception(f"IM接口错误: {result['Error']['Message']}")
            return result["Response"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            await self.client.aclose()  # 关闭客户端

    async def get_user_sig(self, user_id: int, expire: int = 86400) -> dict:
        if not await self._check_user_exists(user_id):
            raise HTTPException(status_code=404, detail="用户不存在")

        # 腾讯云IM获取签名的正确接口动作是"GenerateUserSig"（原代码用了"Signature"）
        response = await self._call_api(  # 异步调用
            action="GenerateUserSig",
            params={
                "SdkAppId": self.sdk_app_id,
                "UserId": str(user_id),
                "Expire": expire
            }
        )

        return {
            "user_id": user_id,
            "signature": response["UserSig"],  # 正确返回字段是UserSig（原代码用了Signature）
            "sdk_app_id": self.sdk_app_id,
            "expire": expire
        }