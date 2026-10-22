"""统一启动入口：读取 PORT 环境变量并启动 FastAPI 服务。

本地：python run.py            （默认 8000）
部署：平台注入 PORT，python run.py
"""

import os
import sys
from pathlib import Path

# 让 src/ 下的核心包可被导入
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import uvicorn  # noqa: E402

from app.server import app as fastapi_app  # noqa: E402


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port)
