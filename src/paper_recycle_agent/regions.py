"""区域统计：全国 → 省级（仅两级）。

为什么只有两级
--------------
市级、县级废纸回收量没有公开的权威逐级统计，此前版本用权重分摊「造」出了
市县数据，容易让使用者误以为是真实统计。本版本**移除市县两级**，只保留
国家与省级，并把数据性质（官方 / 公开报道 / 梯队测算）显式标注到界面和导出表。

数据口径
--------
- 全国（2024 年）：中国造纸协会《中国造纸工业2024年度报告》官方值。
- 省级（2024 年）：
  * 山东 763 万吨、广东 733 万吨为公开报道值，`quality = "reported"`；
  * 其余 32 个省级行政区按行业分区梯队测算，`quality = "estimated"`，
    梯队内按确定性权重分配并归一化，使合计等于全国官方总量 6971 万吨。
- 省级的回收率 / 利用率 / 企业数 / 从业人员均为测算值，导出表中单独标注。

需要接入真实分省数据时，只需替换 `SEEDS` 中对应省份的 `reported` 值即可，
其余指标会自动重算。
"""

import zlib
from dataclasses import dataclass
from typing import Dict, List, Optional

NATIONAL_YEAR = 2024

# 官方口径（国家级，2024 年）
NATIONAL_STATS: Dict[str, float] = {
    "回收量(万吨)": 6971.0,
    "纸及纸板产量(万吨)": 13625.0,
    "回收率(%)": 51.1,
    "利用率(%)": 51.6,
    "回收企业数(家)": 4200,
    "从业人员(人)": 620000,
}

PROVENANCE_OFFICIAL = "官方（中国造纸协会《中国造纸工业2024年度报告》）"
PROVENANCE_REPORTED = "回收量为公开报道值，其余指标为测算值"
PROVENANCE_ESTIMATED = "梯队测算（按行业分区梯队归一化，非官方逐省统计）"

# 梯队说明
TIER_LABEL: Dict[str, str] = {
    "reported": "已公布",
    "B": "第一梯队（>500 万吨）",
    "C": "第二梯队（200–500 万吨）",
    "D": "第三梯队（100–200 万吨）",
    "E": "第四梯队（<100 万吨）",
}

# 梯队基准值（万吨），最终会归一化到全国总量
TIER_BASE: Dict[str, float] = {"B": 510.0, "C": 290.0, "D": 130.0, "E": 52.0}


@dataclass(frozen=True)
class ProvinceSeed:
    """一个省级行政区的种子数据。"""

    name: str
    code: str
    tier: str
    reported: Optional[float] = None


SEEDS: List[ProvinceSeed] = [
    # 已公布具体数值
    ProvinceSeed("山东省", "370000", "reported", 763.0),
    ProvinceSeed("广东省", "440000", "reported", 733.0),
    # 第一梯队：>500 万吨
    ProvinceSeed("河南省", "410000", "B"),
    ProvinceSeed("江西省", "360000", "B"),
    ProvinceSeed("浙江省", "330000", "B"),
    ProvinceSeed("江苏省", "320000", "B"),
    # 第二梯队：200–500 万吨
    ProvinceSeed("湖北省", "420000", "C"),
    ProvinceSeed("四川省", "510000", "C"),
    ProvinceSeed("福建省", "350000", "C"),
    ProvinceSeed("重庆市", "500000", "C"),
    ProvinceSeed("安徽省", "340000", "C"),
    ProvinceSeed("广西壮族自治区", "450000", "C"),
    ProvinceSeed("北京市", "110000", "C"),
    # 第三梯队：100–200 万吨
    ProvinceSeed("上海市", "310000", "D"),
    ProvinceSeed("贵州省", "520000", "D"),
    ProvinceSeed("湖南省", "430000", "D"),
    ProvinceSeed("山西省", "140000", "D"),
    # 第四梯队：<100 万吨
    ProvinceSeed("河北省", "130000", "E"),
    ProvinceSeed("天津市", "120000", "E"),
    ProvinceSeed("辽宁省", "210000", "E"),
    ProvinceSeed("吉林省", "220000", "E"),
    ProvinceSeed("黑龙江省", "230000", "E"),
    ProvinceSeed("内蒙古自治区", "150000", "E"),
    ProvinceSeed("陕西省", "610000", "E"),
    ProvinceSeed("甘肃省", "620000", "E"),
    ProvinceSeed("云南省", "530000", "E"),
    ProvinceSeed("新疆维吾尔自治区", "650000", "E"),
    ProvinceSeed("海南省", "460000", "E"),
    ProvinceSeed("宁夏回族自治区", "640000", "E"),
    ProvinceSeed("青海省", "630000", "E"),
    ProvinceSeed("西藏自治区", "540000", "E"),
    ProvinceSeed("中国香港", "810000", "E"),
    ProvinceSeed("中国澳门", "820000", "E"),
    ProvinceSeed("中国台湾", "710000", "E"),
]


def _jitter(seed: str, span: float = 4.0) -> float:
    """确定性抖动，范围约 [-span, span]，让同梯队省份不完全相同。"""
    return (zlib.crc32(seed.encode("utf-8")) % 1000 / 1000.0 - 0.5) * 2 * span


def _derived_stats(recovery: float, seed: str) -> Dict[str, object]:
    """由回收量推导其余指标（利用率 / 产量 / 企业数 / 从业人员）。"""
    utilization = round(51.6 + _jitter(seed + "u", 3.0), 1)
    utilization = min(72.0, max(35.0, utilization))
    rate = round(51.1 + _jitter(seed + "r", 4.0), 1)
    rate = min(65.0, max(38.0, rate))
    production = round(recovery / utilization * 100.0, 1)
    return {
        "回收量(万吨)": round(recovery, 1),
        "纸及纸板产量(万吨)": production,
        "回收率(%)": rate,
        "利用率(%)": utilization,
        "回收企业数(家)": max(1, int(round(recovery * 0.55))),
        "从业人员(人)": max(10, int(round(recovery * 85))),
    }


def _build() -> Dict[str, object]:
    total = float(NATIONAL_STATS["回收量(万吨)"])
    reported = [s for s in SEEDS if s.reported is not None]
    estimated = [s for s in SEEDS if s.reported is None]

    fixed = sum(float(s.reported) for s in reported)  # type: ignore[arg-type]
    remain = total - fixed

    raw = {
        s.code: TIER_BASE[s.tier] * (1.0 + _jitter(s.code, 0.06))
        for s in estimated
    }
    raw_sum = sum(raw.values()) or 1.0

    values: Dict[str, float] = {}
    for s in reported:
        values[s.code] = round(float(s.reported), 1)  # type: ignore[arg-type]
    for s in estimated:
        values[s.code] = round(remain * raw[s.code] / raw_sum, 1)

    # 归一化：把四舍五入误差补给最大的测算省份，保证合计严格等于全国总量
    diff = round(total - sum(values.values()), 1)
    if estimated and abs(diff) >= 0.1:
        biggest = max(estimated, key=lambda s: values[s.code])
        values[biggest.code] = round(values[biggest.code] + diff, 1)

    provinces: List[Dict[str, object]] = []
    for s in SEEDS:
        is_reported = s.reported is not None
        stats = _derived_stats(values[s.code], s.code + s.name)
        stats["回收量(万吨)"] = values[s.code]
        stats["占全国比重(%)"] = round(values[s.code] / total * 100.0, 2)
        provinces.append({
            "code": s.code,
            "name": s.name,
            "level": "province",
            "parent": "CN",
            "year": NATIONAL_YEAR,
            "tier": s.tier,
            "tier_label": TIER_LABEL[s.tier],
            "quality": "reported" if is_reported else "estimated",
            "reported_fields": ["回收量(万吨)"] if is_reported else [],
            "stats": stats,
            "provenance": PROVENANCE_REPORTED if is_reported else PROVENANCE_ESTIMATED,
        })

    provinces.sort(key=lambda p: float(p["stats"]["回收量(万吨)"]), reverse=True)  # type: ignore[index]
    for rank, p in enumerate(provinces, start=1):
        p["rank"] = rank

    return {
        "code": "CN",
        "name": "全国",
        "level": "national",
        "parent": None,
        "year": NATIONAL_YEAR,
        "stats": dict(NATIONAL_STATS),
        "provenance": PROVENANCE_OFFICIAL,
        "children": provinces,
    }


ROOT = _build()
_INDEX: Dict[str, Dict[str, object]] = {}


def _index(node: Dict[str, object]) -> None:
    _INDEX[str(node["code"])] = node
    for child in node.get("children", []):  # type: ignore[union-attr]
        _index(child)


_index(ROOT)

PROVINCE_TOTAL = float(NATIONAL_STATS["回收量(万吨)"])


def get_node(code: str) -> Optional[Dict[str, object]]:
    return _INDEX.get(code)


def get_children(code: str) -> List[Dict[str, object]]:
    node = _INDEX.get(code)
    return list(node.get("children", [])) if node else []  # type: ignore[union-attr]


def breadcrumb(code: str) -> List[Dict[str, str]]:
    path: List[Dict[str, str]] = []
    node = _INDEX.get(code)
    while node:
        path.append({"code": str(node["code"]), "name": str(node["name"])})
        parent = node.get("parent")
        node = _INDEX.get(str(parent)) if parent else None
    return list(reversed(path))


def find(name: str) -> Optional[Dict[str, object]]:
    """按名称查找区域：先精确匹配，再包含匹配（支持「山东」匹配「山东省」）。"""
    if not name:
        return None
    text = str(name).strip()
    if text in {"全国", "中国", "国家", "cn", "CN"}:
        return ROOT
    for node in _INDEX.values():
        if node["name"] == text:
            return node
    for node in _INDEX.values():
        n = str(node["name"])
        if len(text) >= 2 and n and (text in n or n in text):
            return node
    return None


def share_of_national(code: str) -> float:
    """某省回收量占全国的比重（0–1）；全国返回 1.0。"""
    node = get_node(code)
    if not node:
        return 0.0
    if node["level"] == "national":
        return 1.0
    return float(node["stats"]["回收量(万吨)"]) / PROVINCE_TOTAL  # type: ignore[index]


def summary(code: str = "CN") -> str:
    """对话助手使用的区域文字摘要。"""
    from . import stats as stats_mod

    node = get_node(code)
    if not node:
        return "未找到该区域，可查询的层级为：全国、各省（自治区、直辖市）。"
    s = node["stats"]
    lines = [f"【{node['name']}】废纸回收统计（{node['year']} 年，{node['provenance']}）"]
    lines.append(f"- 回收量：{s['回收量(万吨)']} 万吨")
    lines.append(f"- 纸及纸板产量：{s['纸及纸板产量(万吨)']} 万吨")
    lines.append(f"- 回收率：{s['回收率(%)']}%；利用率：{s['利用率(%)']}%")
    lines.append(f"- 回收企业数：{s['回收企业数(家)']} 家；从业人员：{s['从业人员(人)']} 人")

    children = get_children(str(node["code"]))
    if children:
        top = children[:5]
        lines.append("回收量前五：")
        for p in top:
            lines.append(
                f"  {p['rank']}. {p['name']} {p['stats']['回收量(万吨)']} 万吨"
                f"（占全国 {p['stats']['占全国比重(%)']}%）"
            )
        lines.append("")
        lines.append(stats_mod.history_summary())
        lines.append("")
        lines.append(stats_mod.category_summary(stats_mod.LATEST_YEAR))
    else:
        share = float(s.get("占全国比重(%)", 0.0))
        lines.append(f"- 占全国比重：{share}%，全国排名第 {node.get('rank', '—')} 位")
        lines.append(f"- 梯队：{node['tier_label']}")
    lines.append("")
    lines.append("注：本工具仅提供全国与省级两级统计，不再提供市县数据。")
    return "\n".join(lines)


def tree() -> Dict[str, object]:
    """轻量树结构（全国 + 省份，不含统计值）。"""
    return {
        "code": "CN",
        "name": "全国",
        "level": "national",
        "children": [
            {
                "code": p["code"],
                "name": p["name"],
                "level": "province",
                "tier": p["tier"],
                "children": [],
            }
            for p in get_children("CN")
        ],
    }
