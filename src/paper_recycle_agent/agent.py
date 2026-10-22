"""对话引擎：把分类 / 估价 / 统计能力包装成自然语言回复。"""

import re
from typing import Optional

from . import classifier, data, enterprises, pricing, regions
from . import stats as stats_mod

_GREETING = {"你好", "您好", "hi", "hello", "在吗", "在么"}
_HELP = {"帮助", "help", "怎么用", "功能", "能做什么", "用法"}
# 历年趋势类
_HISTORY = {"历年", "年份", "以前", "过去", "趋势", "增长", "变化", "这几年", "近五年", "历史数据"}
# 按类别拆分回收量类
_CATEGORY_STATS = {"分类数据", "分类回收", "类别占比", "各类回收", "八大类", "按类别", "分类占比", "品种结构"}
# 年鉴 / 标准 / 分类定义类
_DATA = {"年鉴", "行业数据", "进口", "标准", "分类标准", "gb/t", "20811",
         "造纸", "废纸分几类", "废纸分类"}
# 企业维度类（放在区域之前匹配，避免「回收量」先命中）
_ENTERPRISE = {"企业", "公司", "回收站", "回收点", "打包厂", "分拣中心",
               "造纸厂", "贸易商", "名录", "哪家", "厂家", "老板"}
# 区域统计类（仅全国与省级）
_REGION = {"回收量", "利用率", "回收率", "统计", "企业数", "从业人员", "数据", "排名", "占比"}


def _extract_weight(text: str) -> Optional[float]:
    """从文本中提取重量，支持 kg / 公斤 / 千克 / 斤（斤自动折算为 kg）。"""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|公斤|千克|斤)", text, re.IGNORECASE)
    if not m:
        return None
    val = float(m.group(1))
    if m.group(2) == "斤":
        val = val / 2.0
    return val


def _extract_year(text: str) -> Optional[int]:
    """提取文本中的四位年份，如「2020 年分类数据」。"""
    m = re.search(r"(20\d{2})\s*年?", text)
    if not m:
        return None
    year = int(m.group(1))
    valid = {int(r["year"]) for r in stats_mod.get_history()}
    return year if year in valid else None


def respond(user_input: str) -> str:
    """根据用户输入返回一句自然语言回复。"""
    text = (user_input or "").strip()
    if not text:
        return "请输入你想查询的废纸物品，例如「纸箱 2kg 能卖多少钱」。"

    low = text.lower()
    if low in _GREETING:
        return (
            "你好，我是废纸回收助手 🪨。可以问我：废纸是否可回收、估算回收价值、"
            "全国/各省回收统计、历年趋势、八大类分类回收量。输入「帮助」查看用法。"
        )
    if any(k in text for k in _HELP):
        return _help_text()

    # 按类别拆分回收量
    if any(k in text for k in _CATEGORY_STATS):
        year = _extract_year(text) or stats_mod.LATEST_YEAR
        return stats_mod.category_summary(year)

    # 直接命中企业名（如「鲁清再生」）
    hit = enterprises.find(text)
    if hit:
        return _company_card(hit)

    # 企业维度：带「企业 / 公司 / 回收站」等词时，按省汇总
    if any(k in text for k in _ENTERPRISE):
        node = regions.find(text)
        code = str(node["code"]) if node and node["level"] == "province" else None
        return enterprises.summary(code)

    # 历年趋势
    if any(k in text for k in _HISTORY):
        return stats_mod.history_summary()

    # 年鉴 / 行业数据 / 分类标准定义
    if any(k in text for k in _DATA):
        return data.summary_text()

    # 区域统计（全国 / 省级）
    if any(k in text for k in _REGION):
        node = regions.find(text)
        return regions.summary(str(node["code"]) if node else "CN")

    # 只给了省份名
    node = regions.find(text)
    if node and node["level"] == "province":
        return regions.summary(str(node["code"]))

    weight = _extract_weight(text)
    if weight is not None:
        return pricing.estimate(text, weight)["message"]

    # 默认走分类查询
    return classifier.classify(text)["message"]


def _company_card(hit: dict) -> str:
    """单个企业的信息卡。"""
    lines = [
        f"【{hit['name']}】",
        f"- 位置：{hit['city']}（{hit['lat']}, {hit['lon']}）",
        f"- 类型：{hit['type']}",
        f"- 主营：{'、'.join(hit['category_names'])}",
        f"- 年回收量：{hit['volume']} 万吨",
        f"- 备注：{hit['note']}",
    ]
    if hit["is_demo"]:
        lines.append("（示例数据，可在 data/enterprises.csv 替换为真实名录）")
    return "\n".join(lines)


def _help_text() -> str:
    return "\n".join(
        [
            "废纸回收助手使用说明：",
            "1) 查询是否可回收：直接说物品名，如「纸箱」「报纸」「纸巾」。",
            "2) 估算回收价值：物品名 + 重量，如「办公用纸 3kg」「纸箱 5 斤」。",
            "3) 查看八大类分类标准：输入「废纸分类」。",
            "4) 按类别看回收量：输入「分类回收数据」「2020 年分类数据」。",
            "5) 看历年趋势：输入「历年数据」「近五年趋势」。",
            "6) 看区域统计（仅全国与省级）：输入「山东省回收量」「全国统计」「排名」。",
            "7) 看企业分布：输入「企业名录」「山东有哪些回收企业」「分拣中心」。",
            "8) 导出 Excel：右侧面板点「导出 Excel」，含省级、分类、历年、进口、企业、说明六张表。",
        ]
    )
