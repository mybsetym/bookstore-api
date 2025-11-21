import requests
import hashlib
import json
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from app.config import settings  # 需配置快递100 API密钥
from typing import Optional

# 路由配置（前缀/logistics，标签“物流模块”，统一归类）
router = APIRouter(
    prefix="/logistics",
    tags=["物流模块"],
    responses={400: {"description": "参数错误"}, 500: {"description": "服务调用失败"}}
)


# --------------------------
# 数据模型：请求参数校验
# --------------------------
class LogisticsTrackRequest(BaseModel):
    """物流轨迹查询请求参数"""
    logistics_no: str = Query(..., description="物流单号（如SF1234567890）")
    logistics_code: Optional[str] = Query(None, description="快递公司编码（如SF=顺丰，可选，快递100可自动识别）")
    order_id: Optional[int] = Query(None, description="关联订单ID（可选，用于日志追溯）")


# --------------------------
# 辅助函数：生成快递100签名（第三方API安全校验）
# --------------------------
def generate_kuaidi100_sign(param_json: str) -> str:
    """
    快递100签名生成规则：param_json + customer + appkey → MD5加密（大写）
    :param param_json: 请求参数的JSON字符串
    :return: 签名字符串
    """
    if not settings.KUAIDI100_APP_KEY or not settings.KUAIDI100_CUSTOMER:
        raise HTTPException(status_code=500, detail="物流服务未配置（缺少快递100 API密钥）")
    # 拼接签名源字符串
    sign_source = f"{param_json}{settings.KUAIDI100_CUSTOMER}{settings.KUAIDI100_APP_KEY}"
    # MD5加密并转大写
    sign = hashlib.md5(sign_source.encode("utf-8")).hexdigest().upper()
    return sign


# --------------------------
# 核心接口：物流轨迹查询
# --------------------------
@router.get("/track", summary="查询物流轨迹（对接快递100）")
def get_logistics_track(
        logistics_no: str = Query(..., description="物流单号（如SF1234567890）"),
        logistics_code: Optional[str] = Query(None,
                                              description="快递公司编码（可选，如SF=顺丰、YT=圆通，参考快递100编码表）"),
        order_id: Optional[int] = Query(None, description="关联订单ID（可选，用于绑定订单查询）")
):
    """
    功能：输入物流单号，查询商品的实时物流轨迹（如“已揽收→运输中→派送中→已签收”）
    依赖：快递100 API（需在config.py配置KUAIDI100_APP_KEY和KUAIDI100_CUSTOMER）
    快递公司编码参考：https://www.kuaidi100.com/download/api_kuaidi100_com.html
    """
    # 步骤1：校验物流单号（简单校验长度，避免空值）
    if not logistics_no or len(logistics_no) < 6:
        raise HTTPException(status_code=400, detail="物流单号格式错误（长度至少6位）")

    # 步骤2：构造快递100请求参数
    kuaidi100_url = "https://poll.kuaidi100.com/poll/query.do"  # 快递100即时查询接口
    # 请求参数（需转JSON字符串，用于生成签名）
    param = {
        "com": logistics_code,  # 快递公司编码（可选，自动识别时传空）
        "num": logistics_no,  # 物流单号
        "from": "",  # 寄件地（可选，不影响查询结果）
        "to": "",  # 收件地（可选，不影响查询结果）
        "resultv2": "1"  # 返回完整轨迹（1=完整轨迹，0=简要轨迹）
    }
    param_json = json.dumps(param, ensure_ascii=False)  # 转JSON，保留中文
    sign = generate_kuaidi100_sign(param_json)  # 生成签名

    # 步骤3：调用快递100 API
    try:
        response = requests.post(
            url=kuaidi100_url,
            data={
                "customer": settings.KUAIDI100_CUSTOMER,
                "param": param_json,
                "sign": sign
            },
            timeout=10  # 超时时间10秒，避免长时间阻塞
        )
        response.raise_for_status()  # 若HTTP状态码不是200，抛异常
        resp_data = response.json()
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=500, detail="物流查询超时，请稍后重试")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"物流服务调用失败：{str(e)}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="物流服务响应格式错误")

    # 步骤4：处理快递100响应结果
    # 快递100状态码说明：200=成功，400=参数错误，500=服务器错误，其他=查询失败
    if resp_data.get("status") != "200":
        error_msg = resp_data.get("message", "物流查询失败（未知错误）")
        raise HTTPException(status_code=400, detail=f"物流查询失败：{error_msg}")

    # 步骤5：格式化物流轨迹（整理成前端易展示的时间线格式）
    track_list = resp_data.get("data", [])  # 原始轨迹列表（按时间升序）
    # 反转轨迹，按时间倒序排列（最新状态在前）
    formatted_track = [
        {
            "time": track.get("time", ""),  # 轨迹时间（如2024-05-20 14:30:00）
            "context": track.get("context", ""),  # 轨迹描述（如“【深圳市】已揽收”）
            "location": track.get("location", ""),  # 轨迹地点（可选，部分快递公司返回）
            "status": track.get("status", "")  # 轨迹状态（可选，如“在途”“签收”）
        } for track in reversed(track_list)
    ]

    # 步骤6：提取核心信息（快递公司名称、当前状态）
    logistics_info = {
        "logistics_no": logistics_no,
        "logistics_name": resp_data.get("com", "未知快递公司"),  # 快递公司名称（如顺丰速运）
        "current_status": resp_data.get("state", "未知状态"),  # 当前状态（0=待揽收，1=运输中，2=派送中，3=已签收）
        "status_desc": {
            "0": "待揽收",
            "1": "运输中",
            "2": "派送中",
            "3": "已签收",
            "4": "拒收",
            "5": "疑难件",
            "6": "退件中",
            "7": "已退件"
        }.get(resp_data.get("state", ""), "未知状态"),  # 状态中文描述
        "track_list": formatted_track,  # 格式化后的轨迹时间线
        "order_id": order_id  # 关联订单ID（可选）
    }

    return {
        "code": 200,
        "message": "物流轨迹查询成功",
        "data": logistics_info
    }


# --------------------------
# 辅助接口：获取快递公司编码列表（可选，方便前端选择）
# --------------------------
@router.get("/companies", summary="获取支持的快递公司编码列表")
def get_logistics_companies():
    """
    返回常用快递公司的编码映射（前端可用于下拉选择，避免用户手动输入编码）
    编码来源：快递100官方文档（https://www.kuaidi100.com/download/api_kuaidi100_com.html）
    """
    common_companies = {
        "顺丰速运": "SF",
        "圆通速递": "YT",
        "中通快递": "ZT",
        "申通快递": "ST",
        "韵达快递": "YD",
        "百世快递": "HTKY",
        "京东物流": "JD",
        "EMS": "EMS",
        "中国邮政": "YZPY",
        "极兔速递": "JT"
    }
    # 格式化为前端易处理的列表
    company_list = [{"name": name, "code": code} for name, code in common_companies.items()]
    return {
        "code": 200,
        "message": "获取快递公司列表成功",
        "data": company_list
    }