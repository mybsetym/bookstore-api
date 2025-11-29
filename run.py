# C:\Users\myb13\Desktop\bookstore-api\run.py
import os
import sys
import uvicorn

# 项目根目录（bookstore-api）是代码的优先路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # 启动FastAPI：找 app包 → main.py
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=9000,
        reload=True

    )