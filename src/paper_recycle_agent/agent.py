"""对话引擎：把分类 / 估价能力包装成自然语言回复。"""

import re
from typing import Dict, Optional

from . import classifier, data, pricing, regions

_GREETING = {"你好", "您好", "hi", "hello", "在吗", "在么"}
_HELP = {"帮助", "help", "怎么用", "功能", "能做什么", "用法"}
_DATA = {"年鉴", "行业数据", "进口", "标准", "分类标准", "gb/t", "20811",
         "造纸", "废纸分几类", "废纸分类"}
_REGION = {"回收量", "利用率", "回收率", "统计", "企业数", "从业人员", "数据"}


def _extract_weight(text: str) -> Optional[float]:
    """从文本中提取重量，支持 kg / 公斤 / 千克 / 斤（斤自动折算为 kg）。"""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|公斤|千克|斤)", text, re.IGNORECASE)
    if not m:
        return None
    val = float(m.group(1))
    if m.group(2) == "斤":
        val = val / 2.0
    return val


def respond(user_input: str) -> str:
    """根据用户输入返回一句自然语言回复。"""
    text = (user_input or "").strip()
    if not text:
        return "请输入你想查询的废纸物品，例如「纸箱 2kg 能卖多少钱」。"

    low = text.lower()
    if low in _GREETING:
        return (
            "你好，我是废纸回收助手 🪨。告诉我废纸物品名称"
            "（如纸箱、报纸、纸巾），或加上重量估算回收价值。输入「帮助」查看用法。"
        )
    if any(k in text for k in _HELP):
        return _help_text()

    # 年鉴 / 行业数据 / 分类标准类查询
    if any(k in text for k in _DATA):
        return data.summary_text()

    # 区域分层统计查询（国家 / 省 / 市 / 县区）
    if any(k in text for k in _REGION):
        node = regions.find(text)
        return regions.summary(node["code"] if node else "CN")

    weight = _extract_weight(text)
    if weight is not None:
        return pricing.estimate(text, weight)["message"]

    # 默认走分类查询
    return classifier.classify(text)["message"]


def _help_text() -> str:
    return "\n".join(
        [
            "废纸回收助手使用说明：",
            "1) 查询是否可回收：直接说物品名，如「纸箱」「报纸」「纸巾」。",
            "2) 估算回收价值：物品名 + 重量，如「办公用纸 3kg」「纸箱 5 斤」。",
            "3) 查看全部类别：输入「类别」。",
            "4) 年鉴与行业数据：输入「年鉴」「行业数据」「废纸分类」。",
            "5) 区域分层统计：输入省/市/县名 + 「回收量」，如「广东省回收量」。",
        ]
    )
