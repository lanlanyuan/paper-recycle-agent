"""FastAPI 服务：废纸回收 Agent 的图形界面与对话接口。

接口一览：
  GET  / 与 /index.html  -> 图形界面（对话 + 统计面板）
  GET  /api/info         -> {categories, quality, sources, years, national_year}
  GET  /api/regions      -> 区域树（全国 → 省）
  GET  /api/stats        -> 区域统计 + 历年序列 + 分类拆分（?code=CN&year=2024）
  GET  /api/enterprises  -> 企业名录与按省/类/型汇总
  GET  /api/io           -> 投入产出：消耗金额、直接消耗系数、分省/分市/分企业（?year=&code=）
  GET  /api/map/config   -> 地图接入配置（供应商、key 占位符、审图号说明）
  GET  /api/map/data     -> 省级消耗金额 + 中心点坐标（供地图打点）
  GET  /api/llm/config   -> 模型配置状态（密钥脱敏）
  POST /api/llm/config   -> 保存模型配置
  POST /api/llm/test     -> 连通性探测
  POST /api/llm/chat     -> 走大模型回答（未配置时回落规则引擎）
  GET  /export.xlsx      -> 多表 Excel 导出（?code=CN&year=2024）
  POST /chat             -> {"reply": "..."}（规则引擎）
  GET  /health           -> {"status": "ok"}
"""

import io
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from paper_recycle_agent import data as yearbook
from paper_recycle_agent import (enterprises, exporter, io_table, llm, regions,
                                 respond)
from paper_recycle_agent import stats as stats_mod

app = FastAPI(title="废纸回收 Agent 对话助手")

_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

DEFAULT_YEAR = regions.NATIONAL_YEAR

# 不能回落到首页的路径前缀（接口、静态资源、文档）
_API_PREFIXES = ("api/", "export", "static/", "docs", "redoc", "openapi.json", "health")


class ChatReq(BaseModel):
    message: str


def _index_html() -> HTMLResponse:
    html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html, headers={"Cache-Control": "no-store, max-age=0"})


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return _index_html()


@app.head("/", include_in_schema=False)
@app.head("/index.html", include_in_schema=False)
def index_head() -> Response:
    """部分托管环境/预览面板会先发 HEAD 探测，缺了会返回 405。"""
    return Response(
        status_code=200,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store, max-age=0"},
    )


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
        "enterprise_types": enterprises.TYPES,
        "enterprise_is_demo": enterprises.IS_DEMO,
        "excel_available": exporter.available(),
        "python_version": "{}.{}.{}".format(*sys.version_info[:3]),
    }


@app.get("/api/enterprises")
def enterprise_list(province: Optional[str] = None,
                    category: Optional[str] = None,
                    type: Optional[str] = None) -> dict:
    """企业维度：名录 + 按省 / 按大类 / 按类型汇总。"""
    code = province if province else None
    rows = enterprises.list_enterprises(code, category, type)
    return {
        "is_demo": enterprises.IS_DEMO,
        "totals": enterprises.totals(),
        "list": rows,
        "by_province": enterprises.by_province(code),
        "by_category": enterprises.by_category(code),
        "by_type": enterprises.by_type(code),
        "types": enterprises.TYPES,
        "type_desc": enterprises.TYPE_DESC,
        "filter": {"province": code, "category": category, "type": type},
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
        # 始终返回全部省份，便于在选中某省后仍能看到完整排名并切换
        "children": [_shallow(c) for c in regions.get_children("CN")],
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


@app.get("/api/io")
def io_overview(year: Optional[int] = None, code: Optional[str] = None) -> dict:
    """投入产出视角：消耗金额、直接消耗系数、分省 / 分市 / 分企业。"""
    if year is None:
        year = io_table.NATIONAL_IO["year"]  # type: ignore[assignment]
    year = int(year)
    valid = {int(r["year"]) for r in stats_mod.get_history()}
    if year not in valid:
        year = max(valid)

    data = io_table.overview(year)
    # 选中某省时，附带该省的城市分摊
    node = regions.get_node(code) if code else None
    if node is not None and node["level"] == "province":
        data["cities"] = io_table.city_spend(str(node["code"]), year)
        data["scope"] = node["name"]
    else:
        data["cities"] = None
        data["scope"] = "全国"
    return data


# 地图：合规要求只能用腾讯 / 高德 / 百度 / 天地图，且不得内置可用密钥。
# 这里只提供「接入说明 + 占位符」，真实 key 由用户在设置里填。
_MAP_PLACEHOLDER = (
    "Please apply for your own key at the Tencent Location Service Open Platform "
    "and replace this placeholder"
)
_MAP_ATTRIBUTION = (
    "底图由腾讯位置服务提供（已取得测绘资质与审图号），"
    "本工具仅在其上叠加统计数据，不自行绘制任何国界或行政区划界线。"
)


@app.get("/api/map/config")
def map_config() -> dict:
    """地图接入配置。密钥优先取环境变量，其次由前端在设置里填写。"""
    env_key = os.environ.get("TMAP_KEY", "").strip()
    return {
        "provider": "tencent",
        "sdk_url": "https://map.qq.com/api/gljs?v=1.exp",
        "key": env_key,
        "key_source": "env" if env_key else "none",
        "key_placeholder": _MAP_PLACEHOLDER,
        "apply_url": "https://lbs.qq.com/dev/console/application/mine",
        "attribution": _MAP_ATTRIBUTION,
        "fallback": "未配置密钥时，地图页降级为「省份消耗金额排行」，不绘制任何边界。",
    }


@app.get("/api/map/data")
def map_data(year: Optional[int] = None) -> dict:
    """省级消耗金额 + 中心点坐标（GCJ-02），供地图打点使用。"""
    if year is None:
        year = io_table.NATIONAL_IO["year"]  # type: ignore[assignment]
    year = int(year)
    rows = io_table.province_spend(year)["rows"]
    max_amount = max((float(r["amount"]) for r in rows), default=0.0)

    points = []
    for r in rows:
        centroid = enterprises.PROVINCE_CENTROID.get(str(r["code"]))
        if not centroid:
            continue
        amount = float(r["amount"])
        points.append({
            "code": r["code"],
            "name": r["name"],
            "amount": amount,
            "share_pct": r["share_pct"],
            "rank": r["rank"],
            # 归一化半径，供前端画圆
            "ratio": round(amount / max_amount, 4) if max_amount else 0.0,
            "lat": centroid[0],
            "lon": centroid[1],
            "provenance": r["provenance"],
        })

    return {
        "year": year,
        "unit": "亿元",
        "points": points,
        "max_amount": round(max_amount, 1),
        "coordinate_system": "GCJ-02",
        "attribution": _MAP_ATTRIBUTION,
        "note": "省份坐标取省会近似位置，仅用于打点示意，不代表实际厂址。",
    }


class LLMConfigReq(BaseModel):
    base_url: str = ""
    api_key: Optional[str] = None
    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 600
    timeout: float = 30.0
    system_prompt: Optional[str] = None


class LLMChatReq(BaseModel):
    message: str


@app.get("/api/llm/config")
def llm_config() -> dict:
    """模型配置状态。密钥只返回脱敏值。"""
    return llm.status()


@app.post("/api/llm/config")
def llm_config_save(req: LLMConfigReq) -> dict:
    cfg = llm.save_config(
        base_url=req.base_url,
        api_key=req.api_key,
        model=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        timeout=req.timeout,
        system_prompt=req.system_prompt,
    )
    return {"ok": True, "config": cfg.public()}


@app.post("/api/llm/config/clear")
def llm_config_clear() -> dict:
    removed = llm.clear_config()
    return {"ok": True, "removed": removed, "config": llm.load_config().public()}


@app.post("/api/llm/test")
def llm_test() -> dict:
    """连通性探测：能通返回 ok=True 与延迟。"""
    return llm.probe()


@app.post("/api/llm/chat")
def llm_chat(req: LLMChatReq) -> dict:
    """走大模型回答；未配置或调用失败时回落到规则引擎，并说明原因。"""
    message = (req.message or "").strip()
    if not message:
        return {"ok": False, "reply": "请输入内容。", "engine": "none"}

    # 把当前数据上下文喂给模型，减少胡编（数字全部取自模块，避免写死后过期）
    io_nat = io_table.NATIONAL_IO
    context = (
        "以下是本工具的数据口径，回答时以此为准，不要自行编造数字："
        "2024 年全国废纸回收量 {rec} 万吨，回收率 {rr}%，利用率 {ut}%；"
        "造纸和纸制品业营业收入 {rev} 亿元；"
        "废纸货值约 {amt} 亿元（按回收参考价计价，是纸厂废纸成本的下限，非到厂采购额）。"
        "省级回收量为「公开报道 + 梯队测算」，分类回收量为估算，企业名录为示例数据。"
    ).format(
        rec=io_nat["wastepaper_recovery"],
        rr=io_nat["recovery_rate"],
        ut=io_nat["utilization"],
        rev=io_nat["paper_revenue"],
        amt=io_table.spend(2024)["amount"],
    )
    result = llm.chat([
        {"role": "system", "content": context},
        {"role": "user", "content": message},
    ])
    if result["ok"]:
        return {
            "ok": True,
            "engine": "llm",
            "model": result["model"],
            "latency_ms": result["latency_ms"],
            "reply": result["reply"],
        }

    # 回落：规则引擎永远可用
    fallback = respond(message)
    return {
        "ok": True,
        "engine": "rule",
        "model": result.get("model", ""),
        "latency_ms": result.get("latency_ms", 0),
        "reply": fallback,
        "llm_error": result.get("error", ""),
    }


@app.get("/export.xlsx")
def export(code: str = "CN", year: Optional[int] = None) -> Response:
    node = regions.get_node(code) or regions.get_node("CN")
    node_code = str(node["code"])  # type: ignore[index]
    if year is None:
        year = DEFAULT_YEAR

    # openpyxl 是可选依赖：缺失时给出可读提示，而不是 500 堆栈
    if not exporter.available():
        return JSONResponse(
            {
                "detail": "当前服务未安装 openpyxl，无法生成 .xlsx。",
                "hint": "执行 pip install openpyxl 后重启服务；"
                        "或改用零依赖离线版 dist/paper-recycle-offline.html（自带 CSV 导出）。",
            },
            status_code=503,
        )

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


@app.head("/{full_path:path}", include_in_schema=False)
@app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
def spa_fallback(full_path: str) -> Response:
    """兜底路由：任何未匹配的页面路径都回落到首页。

    托管平台/预览面板可能带前缀或用 `/index`、`/home` 之类的路径访问，
    没有兜底时这些请求会拿到 FastAPI 的 `{"detail":"Not Found"}`。
    接口与静态资源路径仍保持 404，避免掩盖真实错误。
    """
    if full_path.startswith(_API_PREFIXES):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    if full_path and "." in full_path.rsplit("/", 1)[-1]:
        # 带扩展名的资源请求（如 /logo.png）应如实 404
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    return _index_html()
