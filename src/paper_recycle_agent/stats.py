"""历年废纸回收利用数据 + 按 GB/T 20811-2018 大类拆分的回收结构。

数据口径（重要，请连同界面/导出中的「数据说明」一起阅读）：

1. 历年回收量、回收率、利用率、消费量
   来源：中国造纸协会历年《中国造纸工业年度报告》，以及《中国造纸》
   期刊「我国废纸回收利用及消费情况」历年统计表。
   - 2014、2016、2019—2024 为年度报告口径的正式值；
   - 2025 为初步核算值（回收率 51.8%，回收量 7195 万吨）。

2. 废纸进口量
   来源：海关总署 / 中国造纸协会历年进出口统计。
   2021-01-01《关于全面禁止进口固体废物有关事项的公告》施行后清零。

3. 分类回收结构（8 大类占比）
   **官方未逐类公布回收量**，本模块给出的是行业结构估算（以 2015 / 2020 / 2025
   三个锚点线性插值），再乘以当年官方回收量得到分类回收量。
   每个字段都带 `provenance`，界面上以「估算」标签显示，避免与官方值混淆。

4. 参考价（元/公斤）用于估算货值，取自 `knowledge.py` 的回收价区间中值，
   属市场参考价，随行情波动。
"""

from typing import Dict, List, Optional

# --------------------------------------------------------------------------
# 一、历年序列
# --------------------------------------------------------------------------
# 字段：year / recovery(回收量,万吨) / consumption(废纸消费量,万吨)
#       recovery_rate(回收率,%) / utilization(利用率,%) / note
HISTORY: List[Dict[str, object]] = [
    {"year": 2014, "recovery": 4841.0, "consumption": 7593.0,
     "recovery_rate": 48.1, "utilization": 72.5, "note": "年度报告"},
    {"year": 2016, "recovery": 4964.0, "consumption": None,
     "recovery_rate": 47.6, "utilization": None, "note": "年度报告"},
    {"year": 2019, "recovery": 5244.0, "consumption": 6280.0,
     "recovery_rate": 49.0, "utilization": 58.3, "note": "年度报告"},
    {"year": 2020, "recovery": 5493.0, "consumption": 6182.0,
     "recovery_rate": 46.4, "utilization": 54.9, "note": "年度报告"},
    {"year": 2021, "recovery": 6491.0, "consumption": 6545.0,
     "recovery_rate": 51.3, "utilization": 54.1, "note": "年度报告"},
    {"year": 2022, "recovery": 6585.0, "consumption": 6641.0,
     "recovery_rate": 53.1, "utilization": 53.5, "note": "年度报告"},
    {"year": 2023, "recovery": 6737.0, "consumption": 6795.0,
     "recovery_rate": 51.2, "utilization": 52.4, "note": "年度报告"},
    {"year": 2024, "recovery": 6971.0, "consumption": 7030.0,
     "recovery_rate": 51.1, "utilization": 51.6, "note": "年度报告"},
    {"year": 2025, "recovery": 7195.0, "consumption": None,
     "recovery_rate": 51.8, "utilization": None, "note": "初步核算"},
]

# 废纸进口量（万吨）。2017 年起固体废物进口管理制度改革，2021 年起清零。
IMPORT_SERIES: List[Dict[str, object]] = [
    {"year": 2017, "value": 2572.0},
    {"year": 2018, "value": 1703.0},
    {"year": 2019, "value": 1036.0},
    {"year": 2020, "value": 689.0},
    {"year": 2021, "value": 54.0},
    {"year": 2022, "value": 0.0},
    {"year": 2023, "value": 0.0},
    {"year": 2024, "value": 0.0},
    {"year": 2025, "value": 0.0},
]

# 纸及纸板产量（万吨），仅收录已确认年份
PAPER_OUTPUT: Dict[int, float] = {
    2024: 13625.0,
    2025: 14135.0,
}

LATEST_YEAR = 2025

PROVENANCE_OFFICIAL = "官方（中国造纸协会年度报告）"
PROVENANCE_PRELIMINARY = "初步核算（中国造纸协会 2025 年数据）"
PROVENANCE_ESTIMATED = "估算（行业结构占比 × 官方回收量）"

# --------------------------------------------------------------------------
# 二、分类结构：GB/T 20811-2018 八大类占比（%）
# --------------------------------------------------------------------------
# 三个锚点年份的结构占比，其余年份线性插值。
# 结构变化的行业逻辑：
#   - 电商快递拉动，废瓦楞纸箱类占比持续上升；
#   - 报纸发行量萎缩，废新闻纸类占比快速下滑；
#   - 垃圾分类推行后，混合废纸类占比反而上升（低值可回收物混入）。
CATEGORY_SHARES: Dict[int, Dict[str, float]] = {
    2015: {"1": 52.0, "2": 8.0, "3": 6.0, "4": 13.0, "5": 9.0, "6": 4.0, "7": 3.0, "8": 5.0},
    2020: {"1": 56.0, "2": 8.0, "3": 6.0, "4": 7.0, "5": 7.0, "6": 4.0, "7": 3.0, "8": 9.0},
    2025: {"1": 58.0, "2": 8.0, "3": 6.0, "4": 3.5, "5": 5.0, "6": 4.0, "7": 3.0, "8": 12.5},
}

# 大类代码 -> (名称, 参考回收价 元/公斤)
CATEGORY_META: Dict[str, Dict[str, object]] = {
    "1": {"name": "废瓦楞纸箱类", "price": 0.95,
          "use": "箱板纸、瓦楞原纸；回收体量最大、价格波动最敏感"},
    "2": {"name": "废纸盒及废卡纸类", "price": 0.85,
          "use": "白板纸、涂布白卡纸；工厂切边品质最稳定"},
    "3": {"name": "包装废纸类", "price": 0.90,
          "use": "包装用纸；杂质要求最严，价格较高"},
    "4": {"name": "废新闻纸类", "price": 0.80,
          "use": "新闻纸、低定量文化用纸；受报纸发行量下滑影响，体量持续萎缩"},
    "5": {"name": "废书刊杂志类", "price": 0.70,
          "use": "文化用纸、纸板芯层；混合旧书刊价格低于白切边"},
    "6": {"name": "办公废纸类", "price": 1.10,
          "use": "高档文化用纸、生活用纸；白度高、单价最高"},
    "7": {"name": "特种废纸类", "price": 1.30,
          "use": "特种纸；量小价高，需专用渠道"},
    "8": {"name": "混合废纸类", "price": 0.55,
          "use": "纸板芯层、低档包装纸；803 为不鼓励贸易类别"},
}


def _interp_shares(year: int) -> Dict[str, float]:
    """按锚点年份线性插值，返回该年 8 大类占比（%），合计归一到 100。"""
    anchors = sorted(CATEGORY_SHARES)
    if year <= anchors[0]:
        return dict(CATEGORY_SHARES[anchors[0]])
    if year >= anchors[-1]:
        return dict(CATEGORY_SHARES[anchors[-1]])
    lo = max(a for a in anchors if a <= year)
    hi = min(a for a in anchors if a >= year)
    if lo == hi:
        return dict(CATEGORY_SHARES[lo])
    ratio = (year - lo) / (hi - lo)
    a, b = CATEGORY_SHARES[lo], CATEGORY_SHARES[hi]
    out = {k: round(a[k] + (b[k] - a[k]) * ratio, 2) for k in a}
    total = sum(out.values())
    return {k: round(v * 100.0 / total, 2) for k, v in out.items()}


def get_history() -> List[Dict[str, object]]:
    """历年序列（含同比增速、进口量、纸及纸板产量）。"""
    rows: List[Dict[str, object]] = []
    prev: Optional[float] = None
    import_map = {int(r["year"]): r["value"] for r in IMPORT_SERIES}
    for item in HISTORY:
        year = int(item["year"])
        recovery = item["recovery"]
        yoy = None
        if prev and recovery:
            yoy = round((float(recovery) - prev) / prev * 100, 2)
        if recovery:
            prev = float(recovery)
        rows.append({
            "year": year,
            "recovery": recovery,
            "consumption": item["consumption"],
            "recovery_rate": item["recovery_rate"],
            "utilization": item["utilization"],
            "yoy": yoy,
            "import": import_map.get(year),
            "paper_output": PAPER_OUTPUT.get(year),
            "note": item["note"],
        })
    return rows


def get_import_series() -> List[Dict[str, object]]:
    return [dict(r) for r in IMPORT_SERIES]


def get_recovery(year: int) -> Optional[float]:
    """取某年官方回收量（万吨）；没有该年则返回 None。"""
    for item in HISTORY:
        if int(item["year"]) == year:
            return float(item["recovery"])  # type: ignore[arg-type]
    return None


def category_breakdown(year: int = LATEST_YEAR,
                       total: Optional[float] = None) -> List[Dict[str, object]]:
    """按 8 大类拆分回收量。

    `total` 可传入区域回收量（如某省），此时按同一结构占比折算，
    分类回收量即变为该区域的估算值。
    """
    base = float(total) if total is not None else (get_recovery(year) or 0.0)
    shares = _interp_shares(year)
    rows: List[Dict[str, object]] = []
    for code in sorted(CATEGORY_META):
        meta = CATEGORY_META[code]
        share = shares[code]
        tonnage = round(base * share / 100.0, 1)
        price = float(meta["price"])  # type: ignore[arg-type]
        # 1 万吨 = 1e7 公斤；货值(亿元) = 万吨 × 1e7 × 元/公斤 ÷ 1e8
        value = round(tonnage * price * 0.1, 1)
        rows.append({
            "code": code,
            "name": meta["name"],
            "share": share,
            "tonnage": tonnage,
            "price": price,
            "value": value,
            "use": meta["use"],
            "provenance": PROVENANCE_ESTIMATED,
        })
    return rows


def category_summary(year: int = LATEST_YEAR) -> str:
    """生成按类别划分的文字摘要，供对话助手使用。"""
    rows = category_breakdown(year)
    lines = [f"【{year} 年废纸回收量按类别拆分（GB/T 20811-2018 八大类）】"]
    lines.append("说明：官方未逐类公布回收量，下表为「行业结构占比 × 官方回收量」估算。")
    for r in rows:
        lines.append(
            f"- {r['code']} {r['name']}：{r['share']}%，约 {r['tonnage']} 万吨，"
            f"参考价 {r['price']} 元/公斤"
        )
    return "\n".join(lines)


def history_summary() -> str:
    """生成历年趋势的文字摘要。"""
    rows = get_history()
    lines = ["【历年废纸回收利用（中国造纸协会年度报告）】"]
    lines.append("年份　回收量(万吨)　回收率(%)　利用率(%)　废纸进口(万吨)")
    for r in rows:
        imp = "—" if r["import"] is None else r["import"]
        util = "—" if r["utilization"] is None else r["utilization"]
        lines.append(
            f"{r['year']}　{r['recovery']}　{r['recovery_rate']}　{util}　{imp}"
        )
    first, last = rows[0], rows[-1]
    growth = (float(last["recovery"]) - float(first["recovery"])) / float(first["recovery"]) * 100
    lines.append(
        f"趋势：{first['year']}—{last['year']} 回收量从 {first['recovery']} 万吨增至 "
        f"{last['recovery']} 万吨，累计增长 {growth:.1f}%；"
        f"废纸进口自 2021 年禁废令后清零。"
    )
    return "\n".join(lines)


SOURCES: List[str] = [
    "中国造纸协会《中国造纸工业年度报告》（历年）",
    "《中国造纸》期刊：我国废纸回收利用及消费情况统计表",
    "海关总署 / 中国造纸协会：废纸进出口统计",
    "GB/T 20811-2018《废纸分类技术要求》",
    "生态环境部等《关于全面禁止进口固体废物有关事项的公告》（2021-01-01 施行）",
]
