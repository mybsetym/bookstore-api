# app/api/school.py
from fastapi import APIRouter, Query, HTTPException
from app.utils.db import execute_query, execute_query_one, execute_update

router = APIRouter(
    prefix="/schools",
    tags=["学校模块"]
)


@router.get("/list", summary="获取所有支持的学校列表")
def get_school_list():
    """供用户选择/切换学校时调用"""
    sql = "SELECT school_id, school_name, city FROM school WHERE status = 1 ORDER BY school_name"
    schools = execute_query(sql)
    return {
        "code": 200,
        "message": "获取成功",
        "data": schools
    }


@router.post("/bind", summary="绑定/切换学校")
def bind_school(
        user_id: int = Query(..., description="用户ID"),
        school_id: int = Query(..., description="学校ID（从学校列表获取）")
):
    # 1. 校验学校是否存在
    school = execute_query_one("SELECT school_id FROM school WHERE school_id = %s AND status = 1", (school_id,))
    if not school:
        raise HTTPException(status_code=404, detail="该学校暂不支持")

    # 2. 更新用户绑定的学校
    execute_update(
        "UPDATE users SET school_id = %s WHERE user_id = %s",
        (school_id, user_id)
    )

    # 3. 返回绑定结果（含学校信息）
    school_info = execute_query_one("SELECT school_name, city FROM school WHERE school_id = %s", (school_id,))
    return {
        "code": 200,
        "message": "学校绑定成功",
        "data": {
            "user_id": user_id,
            "school_id": school_id,
            "school_info": school_info
        }
    }


@router.get("/current", summary="获取用户当前绑定的学校")
def get_current_school(user_id: int = Query(..., description="用户ID")):
    sql = """
          SELECT s.school_id, s.school_name, s.city
          FROM users u
                   LEFT JOIN school s ON u.school_id = s.school_id
          WHERE u.user_id = %s \
          """
    school = execute_query_one(sql, (user_id,))
    return {
        "code": 200,
        "message": "获取成功",
        "data": school or {"school_id": None, "school_name": "未绑定", "city": ""}
    }