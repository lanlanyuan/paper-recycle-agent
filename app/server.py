"""FastAPI 服务：提供废纸回收 Agent 的图形界面与对话接口。

运行：uvicorn app.server:app --reload
接口：
  GET  / 与 /index.html -> 图形界面（聊天 + 年鉴/行业数据面板）
  GET  /api/info        -> {categories, industry, quality, sources}
  POST /chat            -> {"reply": "..."}
  GET  /health          -> {"status": "ok"}
"""

from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from paper_recycle_agent import data as yearbook
from paper_recycle_agent import respond

app = FastAPI(title="废纸回收 Agent 对话助手")

_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


class ChatReq(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    # 避免浏览器请求 favicon 时产生 404 噪音
    return Response(status_code=204)


@app.get("/api/info")
def info() -> dict:
    return {
        "categories": yearbook.get_categories(),
        "industry": yearbook.get_industry_data(2024),
        "quality": yearbook.QUALITY_RULES,
        "sources": yearbook.SOURCES,
    }


@app.post("/chat")
def chat(req: ChatReq) -> dict:
    return {"reply": respond(req.message)}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
