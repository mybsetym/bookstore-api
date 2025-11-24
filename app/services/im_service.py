"""from fastapi import HTTPException
import time
import hmac
import hashlib
import base64
import requests
from app.config import settings  # 根目录的config.py
from app.utils.db import execute_query_one_async  # 你的数据库工具


class IMService:
    腾讯云IM服务封装（适配你的项目结构）

    def __init__(self):
        # 从根目录config.py读取配置
        self.secret_id = settings.TENCENT_IM_SECRET_ID
        self.secret_key = settings.TENCENT_IM_SECRET_KEY
        self.sdk_app_id = settings.TENCENT_IM_SDK_APP_ID
        self.api_host = "im.tencentcloudapi.com"
        self.api_version = "2020-12-29"

    async def _check_user_exists(self, user_id: int) -> bool:
        复用你的数据库校验逻辑（utils/db.py）
        user = await execute_query_one_async(
            "SELECT ID FROM logindata WHERE ID = %s",
            (user_id,)
        )
        return bool(user)

    def _generate_signature(self, action: str, params: dict) -> dict:
        生成腾讯云API签名（核心鉴权逻辑）
        public_params = {
            "SecretId": self.secret_id,
            "Timestamp": int(time.time()),
            "Nonce": int(time.time() * 1000),
            "Action": action,
            "Version": self.api_version
        }
        all_params = {**public_params, **params}

        # 按腾讯云规范生成签名
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

    def _call_api(self, action: str, params: dict) -> dict:
        调用IM API接口
        try:
            params_with_sign = self._generate_signature(action, params)
            response = requests.get(
                url=f"https://{self.api_host}",
                params=params_with_sign,
                timeout=10
            )
            result = response.json()

            if "Error" in result:
                raise Exception(f"IM接口错误: {result['Error']['Message']}")
            return result["Response"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_user_sig(self, user_id: int, expire: int = 86400) -> dict:
        获取用户签名（整合用户校验+API调用）
        if not await self._check_user_exists(user_id):
            raise HTTPException(status_code=404, detail="用户不存在")

        response = self._call_api(
            action="Signature",
            params={
                "SdkAppId": self.sdk_app_id,
                "UserId": str(user_id),
                "Expire": expire
            }
        )

        return {
            "user_id": user_id,
            "signature": response["Signature"],
            "sdk_app_id": self.sdk_app_id,
            "expire": expire
        }"""