# app/api/upload.py
from fastapi import APIRouter, UploadFile, File
import os
from datetime import datetime
# 导入全局配置的 UPLOAD_DIR
from app.config import UPLOAD_DIR


router = APIRouter(prefix="/upload", tags=["文件上传"])

@router.post("/img", summary="上传图片")
async def upload_img(file: UploadFile = File(...)):
    # 校验文件类型（只允许图片，避免恶意文件）
    allowed_types = ["image/jpeg", "image/png", "image/gif"]
    if file.content_type not in allowed_types:
        return {"code": 400, "message": "仅支持 JPG/PNG/GIF 图片格式"}

    # 生成唯一文件名（避免重复覆盖）
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{file.filename}"
    # 拼接文件完整路径
    file_path = os.path.join(UPLOAD_DIR, filename)

    # 保存图片到本地
    with open(file_path, "wb") as f:
        f.write(await file.read())

        # 返回URL：对应static/uploads/文件名
        img_url = f"http://127.0.0.1:9000/static/uploads/{filename}"
        return {
            "code": 200,
            "message": "图片上传成功",
            "data": {"img_url": img_url}
        }