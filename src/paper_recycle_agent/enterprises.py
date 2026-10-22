"""企业维度：回收企业名录 + 地理位置 + 主营品类 + 年回收量。

为什么要有这一层
----------------
前三个模块（区域 / 历年 / 分类）回答的是「一个地方、一个年份、一个品类有多少量」。
但在真实业务里，统计口径最终要落到**企业**身上：某省的量是谁在做？分布在哪些城市？
各品类分别由哪类企业消化？这正是统计局核查、协会统计、回收企业找货源都要回答的问题。

数据性质（重要）
----------------
- 内置的 `ENTERPRISE_SEEDS` 是**示例名录**，企业名称为虚构，量级参考行业公开信息，
  仅用于演示「企业 × 地理位置 × 品类」这套数据结构与分析能力。
- 每条记录带 `is_demo = True`，界面与导出都会显示「示例」标记。
- 替换为真实名录：在项目根目录放 `data/enterprises.csv`（表头见 `CSV_FIELDS`），
  启动时会自动加载并覆盖示例数据，`is_demo` 变为 False。

CSV 字段
--------
id,name,province_code,city,type,categories,volume,lat,lon,note
categories 用分号或竖线分隔的大类代码，如 "1;8"
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional

import zlib

# 省级行政中心近似经纬度，用于把企业点落到地图示意坐标上
PROVINCE_CENTROID: Dict[str, tuple] = {
    "110000": (39.90, 116.41), "120000": (39.13, 117.20), "130000": (38.04, 114.51),
    "140000": (37.87, 112.55), "150000": (40.82, 111.75), "210000": (41.80, 123.43),
    "220000": (43.90, 125.32), "230000": (45.80, 126.53), "310000": (31.23, 121.47),
    "320000": (32.06, 118.80), "330000": (30.27, 120.15), "340000": (31.86, 117.28),
    "350000": (26.07, 119.30), "360000": (28.68, 115.89), "370000": (36.65, 117.00),
    "410000": (34.75, 113.62), "420000": (30.59, 114.30), "430000": (28.19, 112.98),
    "440000": (23.13, 113.26), "450000": (22.82, 108.32), "460000": (20.04, 110.32),
    "500000": (29.56, 106.55), "510000": (30.65, 104.07), "520000": (26.58, 106.71),
    "530000": (25.04, 102.71), "540000": (29.65, 91.13), "610000": (34.34, 108.94),
    "620000": (36.06, 103.83), "630000": (36.62, 101.78), "640000": (38.47, 106.27),
    "650000": (43.79, 87.62), "710000": (25.03, 121.57), "810000": (22.32, 114.17),
    "820000": (22.20, 113.54),
}

# 企业类型
TYPES: List[str] = ["回收站点", "分拣打包中心", "造纸企业", "贸易商"]

TYPE_DESC: Dict[str, str] = {
    "回收站点": "社区/街镇前端回收，量小面广，主要收废纸箱与混合废纸",
    "分拣打包中心": "区域集散与分拣打包，决定品类纯度与去向",
    "造纸企业": "自建回收网络，直接消化废纸制浆，量大且品类要求明确",
    "贸易商": "跨区域调货，价格敏感，承担库存与物流",
}

CSV_FIELDS = ["id", "name", "province_code", "city", "type",
              "categories", "volume", "lat", "lon", "note"]

# (id, 名称, 省代码, 城市, 类型, 主营大类, 年回收量万吨, 备注)
ENTERPRISE_SEEDS = [
    ("E001", "鲁清再生资源有限公司", "370000", "济南市", "分拣打包中心", ["1", "8"], 26.0, "辐射鲁中，纸箱为主"),
    ("E002", "青岛海岳废纸分拣中心", "370000", "青岛市", "分拣打包中心", ["1", "2"], 18.5, "港口周边，外贸包装来源多"),
    ("E003", "山东晨鸣纸业原料基地", "370000", "潍坊市", "造纸企业", ["1", "5"], 42.0, "自建回收网络，直接制浆"),
    ("E004", "临沂商城废纸回收站", "370000", "临沂市", "回收站点", ["1", "8"], 2.4, "批发市场前端回收"),
    ("E005", "粤丰再生资源集团", "440000", "广州市", "分拣打包中心", ["1", "6"], 31.0, "珠三角集散中心"),
    ("E006", "东莞纸源回收有限公司", "440000", "东莞市", "贸易商", ["1", "8"], 12.6, "跨市调货，价格敏感"),
    ("E007", "玖龙纸业（东莞）原料部", "440000", "东莞市", "造纸企业", ["1"], 55.0, "箱板纸原料，量大"),
    ("E008", "深圳南山办公废纸回收点", "440000", "深圳市", "回收站点", ["6", "5"], 1.8, "写字楼集中区，白度高"),
    ("E009", "豫中再生资源产业园", "410000", "郑州市", "分拣打包中心", ["1", "8"], 22.0, "园区化运营"),
    ("E010", "洛阳纸品回收站", "410000", "洛阳市", "回收站点", ["1", "8"], 1.5, "城区前端回收"),
    ("E011", "赣鑫废纸贸易有限公司", "360000", "南昌市", "贸易商", ["1", "3"], 14.2, "向浙闽调货"),
    ("E012", "江西理文造纸原料公司", "360000", "九江市", "造纸企业", ["1", "2"], 38.0, "沿江布局，水运成本低"),
    ("E013", "浙北废纸分拣中心", "330000", "湖州市", "分拣打包中心", ["1", "2", "3"], 19.8, "包装纸产业带配套"),
    ("E014", "宁波港废纸集散中心", "330000", "宁波市", "贸易商", ["1", "8"], 16.4, "进口替代后的内贸枢纽"),
    ("E015", "苏南再生资源有限公司", "320000", "苏州市", "分拣打包中心", ["1", "6"], 21.5, "电子制造业办公废纸多"),
    ("E016", "南京城北回收站点", "320000", "南京市", "回收站点", ["8", "5"], 1.2, "社区混合废纸"),
    ("E017", "鄂中废纸回收中心", "420000", "武汉市", "分拣打包中心", ["1", "8"], 13.7, "九省通衢，调货便利"),
    ("E018", "川渝纸业原料公司", "510000", "成都市", "造纸企业", ["1", "5"], 17.3, "西南区域龙头"),
    ("E019", "重庆两江回收站", "500000", "重庆市", "回收站点", ["1", "8"], 2.1, "城区前端"),
    ("E020", "闽南废纸贸易商行", "350000", "厦门市", "贸易商", ["1", "3"], 9.6, "对台贸易通道"),
    ("E021", "皖江再生资源中心", "340000", "芜湖市", "分拣打包中心", ["1", "2"], 11.2, "沿江造纸带配套"),
    ("E022", "桂南废纸回收站", "450000", "南宁市", "回收站点", ["1", "8"], 1.6, "县域覆盖"),
    ("E023", "京津冀再生资源集散中心", "110000", "北京市", "分拣打包中心", ["6", "5", "2"], 8.4, "办公与书刊废纸为主"),
    ("E024", "津沽废纸分拣厂", "120000", "天津市", "分拣打包中心", ["1", "8"], 7.9, "港口与制造业配套"),
    ("E025", "湘江纸品回收有限公司", "430000", "长沙市", "贸易商", ["1", "5"], 6.3, "向鄂赣调货"),
    ("E026", "黔中再生资源站点", "520000", "贵阳市", "回收站点", ["1", "8"], 1.1, "城区前端"),
    ("E027", "陕再生资源打包中心", "610000", "西安市", "分拣打包中心", ["1", "8"], 5.8, "西北集散"),
    ("E028", "沪上办公废纸回收中心", "310000", "上海市", "分拣打包中心", ["6", "5"], 9.1, "写字楼白领区，白度高"),
    ("E029", "辽沈废纸回收站", "210000", "沈阳市", "回收站点", ["1", "8"], 1.4, "老工业区"),
    ("E030", "滇中纸品贸易公司", "530000", "昆明市", "贸易商", ["1", "3"], 4.2, "面向东南亚边贸"),
]

CATEGORY_NAMES: Dict[str, str] = {
    "1": "废瓦楞纸箱类", "2": "废纸盒及废卡纸类", "3": "包装废纸类",
    "4": "废新闻纸类", "5": "废书刊杂志类", "6": "办公废纸类",
    "7": "特种废纸类", "8": "混合废纸类",
}

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "enterprises.csv"


def _jitter(seed: str, span: float) -> float:
    return (zlib.crc32(seed.encode("utf-8")) % 1000 / 1000.0 - 0.5) * 2 * span


def _make(seed: tuple, is_demo: bool = True) -> Dict[str, object]:
    eid, name, pcode, city, etype, cats, volume, note = seed
    lat0, lon0 = PROVINCE_CENTROID.get(pcode, (35.0, 110.0))
    return {
        "id": eid,
        "name": name,
        "province_code": pcode,
        "city": city,
        "type": etype,
        "categories": list(cats),
        "category_names": [CATEGORY_NAMES.get(c, c) for c in cats],
        "volume": float(volume),
        "lat": round(lat0 + _jitter(eid + "lat", 1.6), 3),
        "lon": round(lon0 + _jitter(eid + "lon", 2.2), 3),
        "note": note,
        "is_demo": is_demo,
    }


def _load_csv(path: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for raw in csv.DictReader(fh):
            cats = [c.strip() for c in str(raw.get("categories", "")).replace("|", ";").split(";") if c.strip()]
            try:
                volume = float(raw.get("volume") or 0)
            except ValueError:
                volume = 0.0
            rows.append({
                "id": raw.get("id") or f"CSV{len(rows) + 1}",
                "name": raw.get("name") or "",
                "province_code": raw.get("province_code") or "",
                "city": raw.get("city") or "",
                "type": raw.get("type") or "分拣打包中心",
                "categories": cats,
                "category_names": [CATEGORY_NAMES.get(c, c) for c in cats],
                "volume": volume,
                "lat": float(raw.get("lat") or 0) or None,
                "lon": float(raw.get("lon") or 0) or None,
                "note": raw.get("note") or "",
                "is_demo": False,
            })
    return rows


def _build() -> List[Dict[str, object]]:
    if DATA_FILE.exists():
        loaded = _load_csv(DATA_FILE)
        if loaded:
            return loaded
    return [_make(s) for s in ENTERPRISE_SEEDS]


ENTERPRISES: List[Dict[str, object]] = _build()
IS_DEMO = all(e["is_demo"] for e in ENTERPRISES) if ENTERPRISES else True


def list_enterprises(province: Optional[str] = None,
                     category: Optional[str] = None,
                     etype: Optional[str] = None) -> List[Dict[str, object]]:
    """按省 / 大类 / 类型筛选企业，按年回收量降序。"""
    rows = ENTERPRISES
    if province:
        rows = [e for e in rows if e["province_code"] == province]
    if category:
        rows = [e for e in rows if category in e["categories"]]  # type: ignore[operator]
    if etype:
        rows = [e for e in rows if e["type"] == etype]
    return sorted(rows, key=lambda e: float(e["volume"]), reverse=True)  # type: ignore[arg-type]


def by_province(province: Optional[str] = None) -> List[Dict[str, object]]:
    """按省汇总：企业数、年回收量、平均单企规模、主要品类。"""
    rows = list_enterprises(province)
    bucket: Dict[str, Dict[str, object]] = {}
    for e in rows:
        code = str(e["province_code"])
        item = bucket.setdefault(code, {
            "province_code": code,
            "count": 0,
            "volume": 0.0,
            "types": {},
            "categories": {},
        })
        item["count"] = int(item["count"]) + 1  # type: ignore[arg-type]
        item["volume"] = float(item["volume"]) + float(e["volume"])  # type: ignore[arg-type]
        item["types"][e["type"]] = int(item["types"].get(e["type"], 0)) + 1  # type: ignore[index]
        for c in e["categories"]:  # type: ignore[union-attr]
            item["categories"][c] = float(item["categories"].get(c, 0)) + float(e["volume"])  # type: ignore[index]

    out: List[Dict[str, object]] = []
    for code, item in bucket.items():
        top = max(item["categories"].items(), key=lambda kv: kv[1])[0] if item["categories"] else None  # type: ignore[union-attr]
        count = int(item["count"])  # type: ignore[arg-type]
        volume = round(float(item["volume"]), 1)  # type: ignore[arg-type]
        out.append({
            "province_code": code,
            "count": count,
            "volume": volume,
            "avg_volume": round(volume / count, 2) if count else 0.0,
            "top_category": top,
            "top_category_name": CATEGORY_NAMES.get(str(top), "—"),
        })
    return sorted(out, key=lambda r: float(r["volume"]), reverse=True)  # type: ignore[arg-type]


def by_category(province: Optional[str] = None) -> List[Dict[str, object]]:
    """按大类汇总企业数量与年回收量（同一企业涉及多类时分别计入）。"""
    bucket: Dict[str, Dict[str, float]] = {c: {"count": 0.0, "volume": 0.0} for c in CATEGORY_NAMES}
    for e in list_enterprises(province):
        for c in e["categories"]:  # type: ignore[union-attr]
            if c in bucket:
                bucket[c]["count"] += 1
                bucket[c]["volume"] += float(e["volume"])
    return [
        {
            "code": c,
            "name": CATEGORY_NAMES[c],
            "count": int(v["count"]),
            "volume": round(v["volume"], 1),
        }
        for c, v in sorted(bucket.items())
    ]


def by_type(province: Optional[str] = None) -> List[Dict[str, object]]:
    bucket: Dict[str, Dict[str, float]] = {t: {"count": 0.0, "volume": 0.0} for t in TYPES}
    for e in list_enterprises(province):
        t = str(e["type"])
        bucket.setdefault(t, {"count": 0.0, "volume": 0.0})
        bucket[t]["count"] += 1
        bucket[t]["volume"] += float(e["volume"])
    return [
        {"type": t, "desc": TYPE_DESC.get(t, ""), "count": int(v["count"]),
         "volume": round(v["volume"], 1)}
        for t, v in bucket.items()
    ]


def totals() -> Dict[str, object]:
    volume = sum(float(e["volume"]) for e in ENTERPRISES)
    return {
        "count": len(ENTERPRISES),
        "volume": round(volume, 1),
        "provinces": len({e["province_code"] for e in ENTERPRISES}),
        "is_demo": IS_DEMO,
    }


_GENERIC = {"废纸", "回收", "废纸回收", "回收站", "公司", "企业", "造纸",
            "纸厂", "中心", "站点", "分拣", "打包"}


def find(name: str) -> Optional[Dict[str, object]]:
    """按企业名查找，支持部分匹配。

    太短或太通用的词（「废纸」「回收」）不参与匹配，避免把普通提问误判成企业查询。
    """
    text = (name or "").strip()
    if len(text) < 3 or text in _GENERIC:
        return None
    for e in ENTERPRISES:
        if str(e["name"]) == text:
            return e
    for e in ENTERPRISES:
        n = str(e["name"])
        if text in n:
            return e
    return None


def summary(province: Optional[str] = None) -> str:
    """对话助手使用的企业维度摘要。"""
    from . import regions

    prov_name = "全国"
    if province:
        node = regions.get_node(province)
        prov_name = str(node["name"]) if node else province

    rows = by_province(province)
    if not rows:
        return f"【{prov_name}】暂无企业名录数据。"

    total_v = round(sum(float(r["volume"]) for r in rows), 1)
    total_c = sum(int(r["count"]) for r in rows)
    lines = [f"【{prov_name}回收企业概览】"]
    if IS_DEMO:
        lines.append("注：以下为示例企业名录（虚构名称），用于演示企业维度，可在 data/enterprises.csv 替换为真实名录。")
    lines.append(f"- 收录企业 {total_c} 家，年回收量合计 {total_v} 万吨")

    if province:
        node = regions.get_node(province)
        if node:
            prov_total = float(node["stats"]["回收量(万吨)"])  # type: ignore[index]
            lines.append(
                f"- 占该省官方回收量（{prov_total} 万吨）的 "
                f"{round(total_v / prov_total * 100, 1) if prov_total else 0}%（名录覆盖率）"
            )

    lines.append("")
    lines.append("按类型：")
    for t in by_type(province):
        if t["count"]:
            lines.append(f"- {t['type']}：{t['count']} 家，{t['volume']} 万吨 —— {t['desc']}")

    lines.append("")
    lines.append("按大类（同一企业涉及多类分别计入）：")
    for c in by_category(province):
        if c["count"]:
            lines.append(f"- {c['code']} {c['name']}：{c['count']} 家，{c['volume']} 万吨")

    top = list_enterprises(province)[:5]
    if top:
        lines.append("")
        lines.append("年回收量前五：")
        for e in top:
            lines.append(
                f"  {e['name']}（{e['city']}·{e['type']}）{e['volume']} 万吨，"
                f"主营 {'、'.join(e['category_names'])}"
            )
    return "\n".join(lines)
