from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from app.utils.db import execute_query, execute_query_one
from typing import Optional, List, Dict, Set
from datetime import datetime, timedelta

# 路由配置
router = APIRouter(
    prefix="/recommendations",
    tags=["推荐系统"],
    responses={404: {"description": "用户不存在"}}
)


# --------------------------
# 数据模型
# --------------------------
class RecommendationRequest(BaseModel):
    """获取推荐的请求参数"""
    user_id: int = Query(..., description="请求推荐的用户ID")
    limit: int = Query(10, ge=1, le=50, description="请求推荐的商品数量，默认10个")


# --------------------------
# 辅助函数
# --------------------------

def get_user_school_id(user_id: int) -> Optional[int]:
    """获取用户所在的学校ID"""
    result = execute_query_one(
        "SELECT school_id FROM users WHERE user_id = %s", (user_id,)
    )
    return result['school_id'] if result and result['school_id'] else None


def get_school_popular_products(school_id: int, limit: int) -> List[dict]:
    """获取指定学校的热门商品（按浏览量排序）"""
    sql = """
          SELECT b.book_id, b.book_name, b.cover_img, b.price, b.seller_ID, b.view
          FROM book b
                   JOIN users u ON b.seller_ID = u.user_id
          WHERE u.school_id = %s \
            AND b.status = 'online'
          ORDER BY b.view DESC
              LIMIT %s
          """
    return execute_query(sql, (school_id, limit))


def get_user_preferred_categories(user_id: int) -> List[int]:
    """分析用户偏好：获取用户历史行为中最常互动的图书分类ID列表"""
    six_months_ago = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d %H:%M:%S")
    preference_scores: Dict[int, int] = {}

    # 1. 购买行为 (权重: 3)
    purchased_categories_sql = """
                               SELECT b.category_id, COUNT(*) as count
                               FROM orders o JOIN book b \
                               ON o.product_id = b.book_id
                               WHERE o.buyer_id = %s \
                                 AND o.create_time \
                                   > %s \
                                 AND o.status = 'completed'
                               GROUP BY b.category_id \
                               ORDER BY count DESC \
                               """
    for cat in execute_query(purchased_categories_sql, (user_id, six_months_ago)):
        preference_scores[cat['category_id']] = preference_scores.get(cat['category_id'], 0) + cat['count'] * 3

    # 2. 评价行为 (权重: 2)
    reviewed_categories_sql = """
                              SELECT b.category_id, COUNT(*) as count
                              FROM reviews r JOIN book b \
                              ON r.product_id = b.book_id
                              WHERE r.reviewer_id = %s \
                                AND r.create_time \
                                  > %s
                              GROUP BY b.category_id \
                              ORDER BY count DESC \
                              """
    for cat in execute_query(reviewed_categories_sql, (user_id, six_months_ago)):
        preference_scores[cat['category_id']] = preference_scores.get(cat['category_id'], 0) + cat['count'] * 2

    # 按偏好度排序，返回Top N的分类ID
    sorted_preferences = sorted(preference_scores.items(), key=lambda item: item[1], reverse=True)
    return [cat_id for cat_id, _ in sorted_preferences]


def get_popular_products_in_categories(category_ids: List[int], limit: int, exclude_seller_id: Optional[int] = None) -> \
List[dict]:
    """根据分类ID列表，获取这些分类下最受欢迎的商品"""
    params = []
    category_conditions = "1=1"
    if category_ids:
        placeholders = ', '.join(['%s'] * len(category_ids))
        category_conditions = f"b.category_id IN ({placeholders})"
        params.extend(category_ids)

    seller_condition = "1=1"
    if exclude_seller_id:
        seller_condition = f"b.seller_ID != %s"
        params.append(exclude_seller_id)

    sql = f"""
    SELECT b.book_id, b.book_name, b.cover_img, b.price, b.seller_ID,
           COUNT(o.product_id) as sales_count
    FROM book b
    LEFT JOIN orders o ON b.book_id = o.product_id AND o.status = 'completed'
    WHERE b.status = 'online' AND {category_conditions} AND {seller_condition}
    GROUP BY b.book_id, b.book_name, b.cover_img, b.price, b.seller_ID
    ORDER BY sales_count DESC, b.view DESC
    LIMIT %s
    """
    params.append(limit)
    return execute_query(sql, tuple(params))


def get_collaborative_filtering_recommendations(user_id: int, limit: int) -> List[dict]:
    """(简化版) 协同过滤推荐"""
    # 1. 找到与该用户购买过至少一件相同商品的用户
    similar_users_sql = """
                        SELECT DISTINCT o2.buyer_id as similar_user_id
                        FROM orders o1 \
                                 JOIN orders o2 ON o1.product_id = o2.product_id
                        WHERE o1.buyer_id = %s \
                          AND o2.buyer_id != %s \
                          AND o1.status = 'completed' \
                          AND o2.status = 'completed'
                            LIMIT 10 \
                        """
    similar_users = execute_query(similar_users_sql, (user_id, user_id))
    if not similar_users:
        return []

    similar_user_ids = [user['similar_user_id'] for user in similar_users]

    # 2. 获取这些相似用户购买过的商品，但排除当前用户已经购买过的商品
    placeholders = ', '.join(['%s'] * len(similar_user_ids))
    cf_recommendations_sql = f"""
    SELECT DISTINCT b.book_id, b.book_name, b.cover_img, b.price, b.seller_ID
    FROM orders o JOIN book b ON o.product_id = b.book_id
    WHERE o.buyer_id IN ({placeholders}) AND o.status = 'completed'
    AND b.book_id NOT IN (SELECT product_id FROM orders WHERE buyer_id = %s AND status = 'completed')
    LIMIT %s
    """
    params = tuple(similar_user_ids) + (user_id, limit)
    return execute_query(cf_recommendations_sql, params)


def get_global_trending_products(limit: int) -> List[dict]:
    """获取平台全局热门商品"""
    sql = """
          SELECT b.book_id, b.book_name, b.cover_img, b.price, b.seller_ID
          FROM book b
                   LEFT JOIN orders o ON b.book_id = o.product_id AND o.status = 'completed'
          WHERE b.status = 'online'
          GROUP BY b.book_id, b.book_name, b.cover_img, b.price, b.seller_ID
          ORDER BY COUNT(o.order_id) DESC, b.view DESC
              LIMIT %s \
          """
    return execute_query(sql, (limit,))


def enrich_products_with_seller_info(products: List[dict]):
    """为商品列表添加卖家信息（昵称、头像）"""
    if not products:
        return products

    seller_ids = list({p['seller_ID'] for p in products})
    sellers_sql = f"SELECT user_id, nickname, avatar FROM users WHERE user_id IN ({','.join(map(str, seller_ids))})"
    sellers = execute_query(sellers_sql)
    seller_map = {seller['user_id']: seller for seller in sellers}

    for product in products:
        seller_info = seller_map.get(product['seller_ID'], {})
        product['seller_nickname'] = seller_info.get('nickname', '未知用户')
        product['seller_avatar'] = seller_info.get('avatar', '')
        product.pop('seller_ID', None)

    return products


# --------------------------
# 核心接口
# --------------------------
@router.get("/for-you", summary="获取为你推荐的商品")
def get_recommendations_for_user(req: RecommendationRequest = Depends()):
    """
    为指定用户生成个性化推荐列表 (结合版)。
    推荐策略 (按优先级排序)：
    1. 【同校热门】：推荐用户所在学校的高浏览量商品。
    2. 【基于内容】：分析用户历史行为，推荐相似分类下的热门商品。
    3. 【协同过滤】：推荐与该用户相似的其他用户喜欢的商品。
    4. 【平台热门】：如果以上推荐仍不足，则用平台整体热门商品填充。
    """
    user_id = req.user_id
    limit = req.limit

    # 步骤1: 验证用户是否存在
    if not execute_query_one("SELECT user_id FROM users WHERE user_id = %s", (user_id,)):
        raise HTTPException(status_code=404, detail="用户不存在")

    final_recommendations: List[dict] = []
    added_product_ids: Set[int] = set()

    # --- 步骤2: 【同校热门】推荐 ---
    school_id = get_user_school_id(user_id)
    if school_id:
        # 分配约40%的名额给同校热门
        school_recs_limit = min(int(limit * 0.4), limit - len(final_recommendations))
        if school_recs_limit > 0:
            school_recs = get_school_popular_products(school_id, school_recs_limit)
            for rec in school_recs:
                if rec['book_id'] not in added_product_ids:
                    final_recommendations.append(rec)
                    added_product_ids.add(rec['book_id'])

    # --- 步骤3: 【基于内容】推荐 ---
    remaining_slots = limit - len(final_recommendations)
    if remaining_slots > 0:
        preferred_categories = get_user_preferred_categories(user_id)
        if preferred_categories:
            content_recs = get_popular_products_in_categories(preferred_categories, remaining_slots,
                                                              exclude_seller_id=user_id)
            for rec in content_recs:
                if rec['book_id'] not in added_product_ids:
                    final_recommendations.append(rec)
                    added_product_ids.add(rec['book_id'])
                    remaining_slots -= 1
                    if remaining_slots <= 0:
                        break

    # --- 步骤4: 【协同过滤】推荐 ---
    if remaining_slots > 0:
        cf_recs = get_collaborative_filtering_recommendations(user_id, remaining_slots)
        for rec in cf_recs:
            if rec['book_id'] not in added_product_ids:
                final_recommendations.append(rec)
                added_product_ids.add(rec['book_id'])
                remaining_slots -= 1
                if remaining_slots <= 0:
                    break

    # --- 步骤5: 【平台热门】推荐 (兜底) ---
    if remaining_slots > 0:
        trending_recs = get_global_trending_products(remaining_slots)
        for rec in trending_recs:
            if rec['book_id'] not in added_product_ids:
                final_recommendations.append(rec)
                added_product_ids.add(rec['book_id'])
                remaining_slots -= 1
                if remaining_slots <= 0:
                    break

    # --- 步骤6: 整理和丰富结果 ---
    # 截取到指定数量
    final_recommendations = final_recommendations[:limit]
    # 添加卖家信息
    final_recommendations = enrich_products_with_seller_info(final_recommendations)

    return {
        "code": 200,
        "message": f"为用户 {user_id} 生成推荐成功",
        "data": {
            "recommendations": final_recommendations
        }
    }