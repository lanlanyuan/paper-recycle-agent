"""FastAPI 服务：废纸回收 Agent 的图形界面与对话接口。

接口一览：
  GET  / 与 /index.html  -> 图形界面（对话 + 统计面板）
  GET  /api/info         -> {categories, quality, sources, years, national_year}
  GET  /api/regions      -> 区域树（全国 → 省）
  GET  /api/stats        -> 区域统计 + 历年序列 + 分类拆分（?code=CN&year=2024）
  GET  /export.xlsx      -> 多表 Excel 导出（?code=CN&year=2024）
  POST /chat             -> {"reply": "..."}
  GET  /health           -> {"status": "ok"}
"""

import io
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from paper_recycle_agent import data as yearbook
from paper_recycle_agent import exporter, regions, respond
from paper_recycle_agent import stats as stats_mod

app = FastAPI(title="废纸回收 Agent 对话助手")

_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

DEFAULT_YEAR = regions.NATIONAL_YEAR


class ChatReq(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html, headers={"Cache-Control": "no-store, max-age=0"})


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/info")
def info() -> dict:
    return {
        "categories": yearbook.get_categories(),
        "quality": yearbook.QUALITY_RULES,
        "sources": yearbook.SOURCES + stats_mod.SOURCES,
        "years": [int(r["year"]) for r in stats_mod.get_history()],
        "national_year": regions.NATIONAL_YEAR,
        "latest_year": stats_mod.LATEST_YEAR,
        "tiers": regions.TIER_LABEL,
    }


def _shallow(node: Dict[str, object]) -> Dict[str, object]:
    return {k: v for k, v in node.items() if k != "children"}


@app.get("/api/regions")
def regions_tree() -> dict:
    return regions.tree()


def _scoped_history(code: str) -> List[Dict[str, object]]:
    """按区域折算历年序列：省级 = 全国序列 × 该省占全国比重。"""
    share = regions.share_of_national(code)
    out: List[Dict[str, object]] = []
    for row in stats_mod.get_history():
        item = dict(row)
        if share != 1.0:
            if item["recovery"] is not None:
                item["recovery"] = round(float(item["recovery"]) * share, 1)
            if item["consumption"] is not None:
                item["consumption"] = round(float(item["consumption"]) * share, 1)
            if item["paper_output"] is not None:
                item["paper_output"] = round(float(item["paper_output"]) * share, 1)
        out.append(item)
    return out


@app.get("/api/stats")
def stats(code: str = "CN", year: Optional[int] = None) -> dict:
    node = regions.get_node(code) or regions.get_node("CN")
    node_code = str(node["code"])  # type: ignore[index]
    if year is None:
        year = DEFAULT_YEAR
    valid_years = {int(r["year"]) for r in stats_mod.get_history()}
    if year not in valid_years:
        year = max(valid_years)

    share = regions.share_of_national(node_code)
    base = (stats_mod.get_recovery(year) or 0.0) * share

    return {
        "node": _shallow(node),  # type: ignore[arg-type]
        "children": [_shallow(c) for c in regions.get_children(node_code)],
        "breadcrumb": regions.breadcrumb(node_code),
        "year": year,
        "years": sorted(valid_years),
        "national_year": regions.NATIONAL_YEAR,
        "scope": "national" if share == 1.0 else "province",
        "share_of_national": round(share * 100, 2),
        "base_tonnage": round(base, 1),
        "history": _scoped_history(node_code),
        "categories": stats_mod.category_breakdown(year, total=base),
        "import_series": stats_mod.get_import_series(),
    }


@app.get("/export.xlsx")
def export(code: str = "CN", year: Optional[int] = None) -> StreamingResponse:
    node = regions.get_node(code) or regions.get_node("CN")
    node_code = str(node["code"])  # type: ignore[index]
    if year is None:
        year = DEFAULT_YEAR
    content = exporter.build_workbook(node_code, year)
    fname = exporter.filename(node_code, year)
    from urllib.parse import quote

    return StreamingResponse(
        io.BytesIO(content),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(fname)}",
            "Cache-Control": "no-store",
        },
    )


@app.post("/chat")
def chat(req: ChatReq) -> dict:
    return {"reply": respond(req.message)}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
