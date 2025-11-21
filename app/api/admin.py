from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from app.utils.db import  execute_query_one, execute_update
from datetime import datetime, timezone
from typing import Optional

# 路由配置
router = APIRouter(
    prefix="/admin",
    tags=["Admin Module"],
    responses={
        403: {"description": "Insufficient permissions (admin required)"},
        404: {"description": "Audit target/log not found"},
        400: {"description": "Invalid parameters or illegal status"}
    }
)

# ... (省略 AuditRequest, AuditLogQueryRequest 等模型定义，与之前版本相同) ...
class AuditRequest(BaseModel):
    audit_type: str = Field(..., description="Type of audit: product/post")
    target_id: int = Field(..., ge=1, description="ID of target (product_id/post_id)")
    audit_result: str = Field(..., description="Audit result: pass/reject")
    audit_note: Optional[str] = Field(None, description="Audit note (required for rejection, 1-200 chars)")
    admin_id: int = Field(..., ge=1, description="ID of admin (must have admin role)")

    @field_validator("audit_note")
    def check_note_for_reject(cls, v, values):
        if values.get("audit_result") == "reject" and not v:
            raise ValueError("Audit note is required for rejection")
        if v and len(v) > 200:
            raise ValueError("Audit note cannot exceed 200 characters")
        return v

    @field_validator("audit_type")
    def check_audit_type(cls, v):
        if v not in ["product", "post"]:
            raise ValueError("Audit type must be 'product' or 'post'")
        return v

    @field_validator("audit_result")
    def check_audit_result(cls, v):
        if v not in ["pass", "reject"]:
            raise ValueError("Audit result must be 'pass' or 'reject'")
        return v

# --------------------------
# 辅助函数 (已优化命名)
# --------------------------
def verify_admin_permission(admin_id: int):
    """Verify if the user has admin permission (role = 'admin')"""
    admin = execute_query_one(
        "SELECT user_id FROM users WHERE user_id = %s AND role = 'admin'",
        (admin_id,)
    )
    if not admin:
        raise HTTPException(status_code=403, detail="Insufficient permissions: admin role required")

# --------------------------
# 核心接口 (使用优化后的函数名)
# --------------------------
@router.post("/audit", summary="Audit product/post (admin only)")
def audit_target(req: AuditRequest):
    # 步骤1：校验管理员权限
    verify_admin_permission(req.admin_id) # 使用优化后的函数名

    # ... (后续逻辑与之前版本完全相同) ...
    audit_config = {
        "product": {
            "table": "book", "status_field": "status", "pending_status": "pending_audit",
            "pass_status": "online", "reject_status": "rejected"
        },
        "post": {
            "table": "posts", "status_field": "status", "pending_status": "pending_audit",
            "pass_status": "visible", "reject_status": "hidden"
        }
    }
    config = audit_config.get(req.audit_type)
    if not config:
        raise HTTPException(status_code=400, detail="Invalid audit type")

    target = execute_query_one(
        f"SELECT id FROM {config['table']} WHERE id = %s AND {config['status_field']} = %s",
        (req.target_id, config['pending_status'])
    )
    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"{req.audit_type} not found, or already audited. Only 'pending_audit' status is allowed"
        )

    now = datetime.now(timezone.utc)
    new_status = config['pass_status'] if req.audit_result == 'pass' else config['reject_status']
    execute_update(
        f"UPDATE {config['table']} SET {config['status_field']} = %s, update_time = %s, audit_note = %s WHERE id = %s",
        (new_status, now, req.audit_note, req.target_id)
    )

    execute_update(
        "INSERT INTO audit_logs (audit_type, target_id, admin_id, audit_result, audit_note, create_time) VALUES (%s, %s, %s, %s, %s, %s)",
        (req.audit_type, req.target_id, req.admin_id, req.audit_result, req.audit_note, now)
    )

    return {
        "code": 200,
        "message": f"{req.audit_type} audited successfully. Status updated to {new_status}",
        "data": {"target_id": req.target_id, "new_status": new_status}
    }

# ... (省略其他接口，它们也需要将调用 `verify_admin权限` 的地方改为 `verify_admin_permission`) ...