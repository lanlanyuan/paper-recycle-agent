"""可选：FastAPI 聊天服务（需 pip install fastapi uvicorn）。

运行：uvicorn app.server:app --reload
接口：
  POST /chat  body: {"message": "纸箱 2kg"}  -> {"reply": "..."}
  GET  /health -> {"status": "ok"}
"""

from fastapi import FastAPI
from pydantic import BaseModel

from paper_recycle_agent import respond

app = FastAPI(title="废纸回收 Agent")


class ChatReq(BaseModel):
    message: str


@app.post("/chat")
def chat(req: ChatReq):
    return {"reply": respond(req.message)}


@app.get("/health")
def health():
    return {"status": "ok"}
