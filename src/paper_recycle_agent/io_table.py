"""投入产出模型：把「废纸回收量」换算成「消耗金额」，并给出产业关联系数。

为什么需要这个模块
------------------
回收量（万吨）回答的是「有多少货」，但企业和地方政府真正关心的是「值多少钱、
谁在花钱买、这笔钱在产业链里怎么传导」。投入产出表正是回答这类问题的标准工具。

数据可得性（这是本模块最重要的部分，请务必连同界面上的标签一起阅读）
------------------------------------------------------------------
国家统计局在咨询公开中明确：

    「各省（自治区、直辖市）在开展投入产出调查的年份，也同步编制本地区
     投入产出表。**目前地级市暂不编制投入产出表。**」

因此本模块把口径分成四级，并在每个返回值里带 `provenance`：

    全国    官方    全国投入产出表（42 部门，最新为 2023 年表）+ 中国造纸协会年度报告
    省级    官方    各省投入产出表（《中国地区投入产出表》逐省出版，42 部门）
    地级市  估算    国家统计局不编制；按企业名录的城市分布分摊，仅供结构参考
    企业    示例    企业没有「投入产出表」，只有财务报表；用成本结构 × 经手量估算

企业层面特别说明：**不存在「企业投入产出表」这种东西**。企业有资产负债表、
利润表、现金流量表；投入产出表是国民经济核算工具，编制主体是国家/地区。
所以这里的企业金额是用「年经手量 × 市场均价」得到的采购金额估算，
不是从任何企业投入产出表里读出来的。

金额是怎么算出来的
------------------
    消耗金额(亿元) = Σ(分类消耗量(万吨) × 参考价(元/公斤) × 0.1)

参考价来自 `knowledge.py` 的回收价区间中值，属市场参考价。
全国消耗量取中国造纸协会年度报告的「废纸消费量」（2024 年为 7030 万吨），
未公布消费量的年份退回使用回收量，并在 `tonnage_basis` 里注明。

直接消耗系数
------------
    直接消耗系数 = 废纸采购金额 ÷ 造纸和纸制品业营业收入

这是本模块唯一能由公开数据直接推出、且量纲自洽的投入产出系数。
2024 年：营业收入 1.46 万亿元（中国造纸协会 2024 年度报告）。
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import enterprises, regions
from . import stats as stats_mod

# --------------------------------------------------------------------------
# 一、官方口径的聚合指标
# --------------------------------------------------------------------------
# 来源：中国造纸协会《中国造纸工业2024年度报告》（2025-05-07 发布）
#   全行业营业收入 1.46 万亿元，利润总额 520 亿元，
#   纸及纸板产量 13625 万吨，纸制品产量 6514 万吨。
#   废纸回收量 6971 万吨，回收率 51.1%，利用率 51.6%。
# 投入产出表：国家统计局 2023 年全国投入产出表（42 部门）。
NATIONAL_IO: Dict[str, object] = {
    "year": 2024,
    "paper_revenue": 14600.0,          # 亿元
    "paper_profit": 520.0,             # 亿元
    "paper_output": 13625.0,           # 万吨，纸及纸板
    "paper_products_output": 6514.0,   # 万吨，纸制品
    "wastepaper_recovery": 6971.0,     # 万吨
    "wastepaper_consumption": 7030.0,  # 万吨
    "recovery_rate": 51.1,             # %
    "utilization": 51.6,               # %
    "io_table_year": 2023,
    "io_sector_count": 42,
}

# 各年营业收入（亿元）。仅 2024 年有公开报道值，其余年份不推算，保持 None。
PAPER_REVENUE: Dict[int, Optional[float]] = {
    2024: 14600.0,
}

SOURCES: List[str] = [
    "国家统计局《2023年全国投入产出表》（42 部门）",
    "国家统计局《中国地区投入产出表》（分省，42 部门，逐省公开出版）",
    "国家统计局咨询公开（2024-08）：地级市暂不编制投入产出表",
    "中国造纸协会《中国造纸工业2024年度报告》：营业收入 1.46 万亿元、利润 520 亿元",
    "参考价取 knowledge.py 回收价区间中值，为市场参考价",
]

# 四级口径与数据可得性
LEVELS: List[Dict[str, object]] = [
    {
        "key": "national",
        "name": "全国",
        "io_available": True,
        "provenance": "官方",
        "note": "全国投入产出表（42 部门）+ 中国造纸协会年度报告",
    },
    {
        "key": "province",
        "name": "省级",
        "io_available": True,
        "provenance": "官方（表）+ 估算（分摊）",
        "note": "各省均编制本地区投入产出表；本工具的分省金额按回收量占比分摊，非实际采购分布",
    },
    {
        "key": "city",
        "name": "地级市",
        "io_available": False,
        "provenance": "估算",
        "note": "国家统计局：地级市暂不编制投入产出表。按企业名录城市分布分摊",
    },
    {
        "key": "enterprise",
        "name": "企业",
        "io_available": False,
        "provenance": "示例",
        "note": "企业无投入产出表（只有财务报表）。按年经手量 × 市场均价估算采购金额",
    },
]

PROVENANCE_OFFICIAL = "官方"
PROVENANCE_DERIVED = "测算（公开数据推导）"
PROVENANCE_ESTIMATED = "估算（分摊）"
PROVENANCE_DEMO = "示例"

# --------------------------------------------------------------------------
# 二、金额与系数
# --------------------------------------------------------------------------


def _history_row(year: int) -> Optional[Dict[str, object]]:
    for row in stats_mod.get_history():
        if int(row["year"]) == year:  # type: ignore[arg-type]
            return row
    return None


def tonnage(year: int) -> Tuple[float, str]:
    """返回 (消耗量万吨, 口径说明)。优先用废纸消费量，缺失时退回回收量。"""
    row = _history_row(year)
    if row is None:
        return 0.0, "无数据"
    consumption = row.get("consumption")
    if consumption is not None:
        return float(consumption), "废纸消费量（年度报告）"
    recovery = row.get("recovery")
    if recovery is not None:
        return float(recovery), "回收量（该年消费量未公布，以回收量代替）"
    return 0.0, "无数据"


def average_price(year: int) -> float:
    """加权平均参考价（元/吨）。按分类结构加权。"""
    amount, _ = tonnage(year)
    if amount <= 0:
        return 0.0
    value = sum(float(r["value"]) for r in stats_mod.category_breakdown(year, total=amount))
    # value 单位为亿元，amount 单位为万吨 → 亿元/万吨 × 10000 = 元/吨
    return round(value / amount * 10000, 1)


def spend(year: int = 2024) -> Dict[str, object]:
    """全国废纸货值（亿元），按回收参考价计价。

    注意：参考价是居民/回收站口径，纸厂「到厂价」还包含分拣、打包、运输，
    通常显著更高。本工具不额外乘一个加价系数——那会引入没有依据的假设，
    所以这里给出的是**纸厂废纸成本的下限**。
    """
    amount, basis = tonnage(year)
    rows = stats_mod.category_breakdown(year, total=amount)
    value = sum(float(r["value"]) for r in rows)
    return {
        "year": year,
        "tonnage": round(amount, 1),
        "tonnage_basis": basis,
        "avg_price": average_price(year),
        "amount": round(value, 1),
        "is_lower_bound": True,
        "provenance": PROVENANCE_DERIVED,
        "note": "金额 = Σ(分类消耗量 × 回收参考价)。参考价为居民/回收站口径，"
                "不含分拣、打包、运输，故该金额是纸厂废纸成本的下限，非到厂采购额。",
    }


def revenue(year: int = 2024) -> Optional[float]:
    """造纸和纸制品业营业收入（亿元）。仅有公开报道值的年份返回数字。"""
    return PAPER_REVENUE.get(year)


def direct_coefficient(year: int = 2024) -> Dict[str, object]:
    """造纸和纸制品业对废纸的直接消耗系数 = 采购金额 ÷ 营业收入。"""
    rev = revenue(year)
    if not rev:
        return {
            "year": year,
            "coefficient": None,
            "provenance": "无数据",
            "note": "%d 年造纸业营业收入无公开报道值，无法计算直接消耗系数" % year,
        }
    amount = float(spend(year)["amount"])
    return {
        "year": year,
        "spend": round(amount, 1),
        "revenue": rev,
        "coefficient": round(amount / rev, 4),
        "coefficient_pct": round(amount / rev * 100, 2),
        "is_lower_bound": True,
        "provenance": PROVENANCE_DERIVED,
        "note": "直接消耗系数 = 废纸货值 ÷ 造纸和纸制品业营业收入。"
                "因货值按回收参考价计，该系数是下限；到厂价口径下会更高。",
    }


def unit_consumption(year: int = 2024) -> Dict[str, object]:
    """单位产值废纸消耗（吨/万元）。"""
    amount, _ = tonnage(year)
    rev = revenue(year)
    if not rev:
        return {"year": year, "value": None, "provenance": "无数据"}
    return {
        "year": year,
        "tonnage": round(amount, 1),
        "revenue": rev,
        # 万吨 / 亿元 = 吨/万元（量纲相同，均为 10^4）
        "value": round(amount / rev, 3),
        "provenance": PROVENANCE_DERIVED,
        "note": "单位产值废纸消耗 = 废纸消耗量(万吨) ÷ 营业收入(亿元)，量纲为吨/万元",
    }


# --------------------------------------------------------------------------
# 三、分省 / 分市 / 分企业
# --------------------------------------------------------------------------


def province_spend(year: int = 2024, code: Optional[str] = None) -> Dict[str, object]:
    """分省消耗金额（亿元）。

    分摊口径：按该省废纸回收量占全国比重代理。
    这不是真实采购分布（废纸可能跨省流通），仅用于结构参考。
    """
    total = float(spend(year)["amount"])
    rows: List[Dict[str, object]] = []
    for node in regions.get_children("CN"):
        share = float(node["stats"]["占全国比重(%)"]) / 100.0  # type: ignore[index]
        rows.append({
            "code": node["code"],
            "name": node["name"],
            "tier_label": node["tier_label"],
            "quality": node["quality"],
            "share_pct": round(share * 100, 2),
            "recovery": node["stats"]["回收量(万吨)"],  # type: ignore[index]
            "amount": round(total * share, 1),
            "provenance": (
                PROVENANCE_OFFICIAL if node["quality"] == "reported"
                else PROVENANCE_ESTIMATED
            ),
        })
    rows.sort(key=lambda r: float(r["amount"]), reverse=True)  # type: ignore[arg-type]
    for i, row in enumerate(rows, start=1):
        row["rank"] = i

    if code:
        picked = [r for r in rows if r["code"] == code]
        return {
            "year": year,
            "basis": "按该省回收量占全国比重分摊，非实际采购分布",
            "total": round(total, 1),
            "rows": picked,
            "provenance": PROVENANCE_ESTIMATED,
        }
    return {
        "year": year,
        "basis": "按该省回收量占全国比重分摊，非实际采购分布",
        "total": round(total, 1),
        "rows": rows,
        "provenance": PROVENANCE_ESTIMATED,
    }


def city_spend(province_code: str, year: int = 2024) -> Dict[str, object]:
    """省内各城市的消耗金额（亿元）。

    地级市不编制投入产出表，这里按该省企业名录的年经手量在城市间的分布分摊。
    企业名录本身是示例数据，因此结果是「示例 × 估算」。
    """
    prov = regions.get_node(province_code)
    if prov is None or prov["level"] != "province":
        return {
            "year": year,
            "province": None,
            "cities": [],
            "provenance": "无数据",
            "note": "请传入省级行政区代码",
        }

    share = float(prov["stats"]["占全国比重(%)"]) / 100.0  # type: ignore[index]
    total = float(spend(year)["amount"]) * share
    rows = enterprises.list_enterprises(str(prov["code"]))
    by_city: Dict[str, float] = {}
    for e in rows:
        by_city[str(e["city"])] = by_city.get(str(e["city"]), 0.0) + float(e["volume"])

    vol_sum = sum(by_city.values())
    cities: List[Dict[str, object]] = []
    for city, vol in by_city.items():
        ratio = (vol / vol_sum) if vol_sum else 0.0
        cities.append({
            "city": city,
            "enterprise_volume": round(vol, 1),
            "amount": round(total * ratio, 2),
            "provenance": PROVENANCE_ESTIMATED,
        })
    cities.sort(key=lambda r: float(r["amount"]), reverse=True)  # type: ignore[arg-type]

    return {
        "year": year,
        "province": prov["name"],
        "province_amount": round(total, 1),
        "cities": cities,
        "provenance": PROVENANCE_ESTIMATED,
        "note": "地级市不编制投入产出表；此处按企业名录城市分布分摊，企业名录为示例数据",
    }


def enterprise_spend(year: int = 2024, etype: Optional[str] = None) -> Dict[str, object]:
    """企业采购金额（亿元）= 年经手量(万吨) × 均价(元/吨) ÷ 10000。"""
    price = average_price(year)
    rows: List[Dict[str, object]] = []
    for e in enterprises.list_enterprises(None, None, etype):
        volume = float(e["volume"])
        node = regions.get_node(str(e["province_code"]))
        rows.append({
            "name": e["name"],
            "province": node["name"] if node else "—",
            "city": e["city"],
            "type": e["type"],
            "volume": round(volume, 1),
            "avg_price": price,
            "amount": round(volume * price / 10000, 2),
            "is_demo": e["is_demo"],
            "provenance": PROVENANCE_DEMO if e["is_demo"] else PROVENANCE_ESTIMATED,
        })
    rows.sort(key=lambda r: float(r["amount"]), reverse=True)  # type: ignore[arg-type]
    return {
        "year": year,
        "avg_price": price,
        "total": round(sum(float(r["amount"]) for r in rows), 1),
        "rows": rows,
        "provenance": PROVENANCE_DEMO,
        "note": "企业不存在投入产出表；金额 = 年经手量 × 市场均价，属采购金额估算",
    }


# --------------------------------------------------------------------------
# 四、Leontief 逆矩阵与产业关联（需要用户导入真实投入产出表）
# --------------------------------------------------------------------------
# 本仓库不内置任何投入产出矩阵：编一张看起来权威的假矩阵，比不提供更糟。
# 算法在这里，数据请从国家统计局 42 部门表导出为 CSV 后导入。


def load_matrix_csv(path: str) -> Tuple[List[str], List[List[float]]]:
    """读取直接消耗系数矩阵 CSV。

    格式：第一行是部门名（列），第一列是部门名（行），其余为系数。
    """
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        names = header[1:]
        matrix: List[List[float]] = []
        for row in reader:
            if not row or not row[0].strip():
                continue
            matrix.append([float(x) for x in row[1:]])
    if not matrix:
        raise ValueError("矩阵为空：%s" % path)
    n = len(matrix)
    if any(len(r) != n for r in matrix):
        raise ValueError("矩阵不是方阵：行数 %d，列数不一致" % n)
    return names, matrix


def leontief_inverse(matrix: Sequence[Sequence[float]]) -> List[List[float]]:
    """计算 (I - A)^-1，即列昂惕夫逆矩阵（完全需求系数矩阵）。

    纯标准库实现：带部分主元的高斯-约当消元。A 为直接消耗系数矩阵。
    """
    n = len(matrix)
    if n == 0:
        raise ValueError("矩阵为空")
    # 构造 [I - A | I]
    aug: List[List[float]] = []
    for i in range(n):
        if len(matrix[i]) != n:
            raise ValueError("矩阵不是方阵")
        row = [-(float(matrix[i][j])) for j in range(n)]
        row[i] += 1.0
        row.extend(1.0 if k == i else 0.0 for k in range(n))
        aug.append(row)

    for col in range(n):
        # 部分主元
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError("矩阵奇异：第 %d 列无法消元（可能存在不合理的消耗系数）" % (col + 1))
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        factor = aug[col][col]
        aug[col] = [v / factor for v in aug[col]]
        for r in range(n):
            if r == col:
                continue
            ratio = aug[r][col]
            if ratio == 0.0:
                continue
            aug[r] = [a - ratio * b for a, b in zip(aug[r], aug[col])]

    return [row[n:] for row in aug]


def influence_coefficients(matrix: Sequence[Sequence[float]]) -> List[float]:
    """影响力系数 = 逆矩阵列和 ÷ 全部列和均值。>1 表示对上游拉动高于社会平均。"""
    inv = leontief_inverse(matrix)
    n = len(inv)
    col_sums = [sum(inv[i][j] for i in range(n)) for j in range(n)]
    mean = sum(col_sums) / n
    return [round(s / mean, 4) for s in col_sums]


def response_coefficients(matrix: Sequence[Sequence[float]]) -> List[float]:
    """感应度系数 = 逆矩阵行和 ÷ 全部行和均值。>1 表示受下游需求拉动高于社会平均。"""
    inv = leontief_inverse(matrix)
    n = len(inv)
    row_sums = [sum(inv[i]) for i in range(n)]
    mean = sum(row_sums) / n
    return [round(s / mean, 4) for s in row_sums]


# --------------------------------------------------------------------------
# 五、汇总
# --------------------------------------------------------------------------


def overview(year: int = 2024) -> Dict[str, object]:
    """投入产出总览：一次返回界面需要的全部口径。"""
    return {
        "national_io": dict(NATIONAL_IO),
        "levels": LEVELS,
        "sources": SOURCES,
        "spend": spend(year),
        "direct_coefficient": direct_coefficient(year),
        "unit_consumption": unit_consumption(year),
        "provinces": province_spend(year),
        "enterprises": enterprise_spend(year),
        "years": [int(r["year"]) for r in stats_mod.get_history()],
    }


def summary_text(year: int = 2024) -> str:
    """命令行输出。"""
    s = spend(year)
    d = direct_coefficient(year)
    u = unit_consumption(year)
    lines = [
        "【投入产出视角：废纸消耗金额（%d 年）】" % year,
        "消耗量　　%s 万吨（%s）" % (s["tonnage"], s["tonnage_basis"]),
        "平均参考价　%s 元/吨" % s["avg_price"],
        "消耗金额　%s 亿元　[%s]" % (s["amount"], s["provenance"]),
    ]
    if d["coefficient"] is not None:
        lines.append(
            "直接消耗系数　%s%%（采购 %s 亿元 ÷ 营业收入 %s 亿元，属下限）"
            % (d["coefficient_pct"], d["spend"], d["revenue"])
        )
    if u["value"] is not None:
        lines.append("单位产值消耗　%s 吨/万元" % u["value"])
    lines.append("")
    lines.append("口径分级：")
    for lv in LEVELS:
        flag = "有官方表" if lv["io_available"] else "无官方表"
        lines.append("  · %s（%s）%s —— %s" % (lv["name"], flag, lv["provenance"], lv["note"]))
    return "\n".join(lines)


def matrix_path() -> Path:
    """用户导入的真实投入产出表位置（不纳入版本库）。"""
    return Path(__file__).resolve().parents[2] / "data" / "io_matrix.csv"
