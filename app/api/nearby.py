from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from app.utils.db import execute_query, execute_query_paginated
from typing import Optional

# 路由配置
router = APIRouter(
    prefix="/nearby",
    tags=["附近的商品"],
    responses={400: {"description": "参数错误"}, 404: {"description": "未找到商品"}}
)


# --------------------------
# 数据模型
# --------------------------
class NearbyProductRequest(BaseModel):
    """获取附近商品的请求参数"""
    user_lat: float = Query(..., description="用户所在纬度（例如：39.908823）")
    user_lng: float = Query(..., description="用户所在经度（例如：116.397470）")
    radius: Optional[int] = Query(5, description="搜索半径，单位为公里（km），默认5公里")
    page: int = Query(1, ge=1, description="页码")
    page_size: int = Query(10, ge=1, le=50, description="每页条数")


# --------------------------
# 核心接口
# --------------------------
@router.get("/products", summary="获取附近的商品 (SQL优化版)")
def get_nearby_products(
        req: NearbyProductRequest = Depends()
):
    """
    根据用户当前地理位置，搜索附近在售的二手书商品。
    使用 MySQL 的 ST_Distance_Sphere 函数在数据库层完成距离计算和筛选，性能更优。
    """
    # 步骤1：参数合法性校验
    if not (-90 <= req.user_lat <= 90) or not (-180 <= req.user_lng <= 180):
        raise HTTPException(status_code=400, detail="无效的经纬度坐标")
    if req.radius <= 0 or req.radius > 50:
        raise HTTPException(status_code=400, detail="搜索半径必须在1到50公里之间")

    # 步骤2：构建分页查询 SQL
    sql = """
          SELECT b.book_id, \
                 b.book_name, \
                 b.cover_img, \
                 b.price, \
                 b.seller_ID, \
                 s.school_name, \
                 ROUND(ST_Distance_Sphere(POINT(%s, %s), POINT(s.longitude, s.latitude)) / 1000, 1) AS distance_km
          FROM book b \
                   LEFT JOIN \
               school s ON b.pickup_location_id = s.school_id
          WHERE b.status = 'online'
            AND s.latitude IS NOT NULL
            AND s.longitude IS NOT NULL
            AND ST_Distance_Sphere(POINT(%s, %s), POINT(s.longitude, s.latitude)) <= %s * 1000
          ORDER BY distance_km ASC \
          """

    # 使用优化后的分页查询函数
    result = execute_query_paginated(
        sql,
        params=(req.user_lng, req.user_lat, req.user_lng, req.user_lat, req.radius),
        page=req.page,
        page_size=req.page_size
    )

    # 步骤3：获取卖家信息，丰富返回结果
    products = result['data']
    if products:
        seller_ids = list({p['seller_ID'] for p in products})
        sellers_sql = f"SELECT user_id, nickname, avatar FROM users WHERE user_id IN ({','.join(map(str, seller_ids))})"
        sellers = execute_query(sellers_sql)
        seller_map = {seller['user_id']: seller for seller in sellers}

        for product in products:
            seller_info = seller_map.get(product['seller_ID'], {})
            product['seller_nickname'] = seller_info.get('nickname', '未知用户')
            product['seller_avatar'] = seller_info.get('avatar', '')
            product.pop('seller_ID', None)

    return {
        "code": 200,
        "message": "获取附近商品成功",
        "data": {
            "total": result['total'],
            "page": result['page'],
            "page_size": result['page_size'],
            "total_pages": result['total_pages'],
            "products": products
        }
    }