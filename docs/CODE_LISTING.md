# 代码清单

> 版本：v1.4.0　生成日期：2026-10-23　由 `tools/gen_code_listing.py` 自动生成，请勿手工编辑。

本文档把仓库全部源码按模块顺序嵌入，便于在不打开仓库的情况下通读实现。
- 生成时提交：`5b931e1`

## 目录
- 一、核心包（src/paper_recycle_agent）
- 二、Web 应用（app/）
- 三、测试（tests/）
- 四、启动入口与工程配置
- 五、工具脚本（tools/）

---

## 一、核心包（src/paper_recycle_agent）

### `src/paper_recycle_agent/__init__.py`（20 行）

```python
"""废纸回收 Agent 对话助手。"""

from . import (agent, classifier, data, enterprises, exporter, knowledge,
               pricing, regions, stats)
from .agent import respond

__version__ = "1.4.0"

__all__ = [
    "agent",
    "classifier",
    "data",
    "enterprises",
    "exporter",
    "knowledge",
    "pricing",
    "regions",
    "stats",
    "respond",
]
```

### `src/paper_recycle_agent/agent.py`（131 行）

```python
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
```

### `src/paper_recycle_agent/classifier.py`（86 行）

```python
"""废纸分类引擎：基于关键词与规则的轻量级分类。"""

from typing import Dict, List

from .knowledge import CATEGORIES, KEYWORD_INDEX, PaperCategory


def classify(text: str) -> Dict[str, object]:
    """根据用户输入文本判断废纸类别。

    返回字典包含：matched / category / key / recyclable / value_per_kg /
    tips / confidence / message。
    """
    if not text or not text.strip():
        return _empty()

    t = text.lower()
    hits: List[PaperCategory] = []
    for cat, kw in KEYWORD_INDEX:
        if kw.lower() in t:
            hits.append(cat)

    if not hits:
        # 关键词未命中时，尝试用类别主键兜底（如「cardboard」）。
        for cat in CATEGORIES:
            if cat.key in t:
                hits.append(cat)

    if not hits:
        return {
            "matched": False,
            "category": None,
            "recyclable": None,
            "confidence": 0.0,
            "message": "未能识别废纸类型，请描述更具体的物品（如：纸箱、报纸、纸巾、热敏小票）。",
        }

    cat = _prioritize(hits)
    confidence = 0.9 if len(hits) == 1 else 0.7
    return {
        "matched": True,
        "category": cat.name,
        "key": cat.key,
        "recyclable": cat.recyclable,
        "value_per_kg": cat.value_per_kg,
        "tips": cat.tips,
        "confidence": confidence,
        "message": _message(cat),
    }


def _prioritize(cats: List[PaperCategory]) -> PaperCategory:
    """多命中时，优先展示可回收且价值更高的类别。"""
    return sorted(cats, key=lambda c: (not c.recyclable, -c.value_per_kg))[0]


def _message(cat: PaperCategory) -> str:
    if cat.recyclable:
        return (
            f"识别为【{cat.name}】，可回收，参考回收价约 "
            f"{cat.value_per_kg} 元/kg。{cat.tips}"
        )
    return f"识别为【{cat.name}】，暂不可回收。{cat.tips}"


def _empty() -> Dict[str, object]:
    return {
        "matched": False,
        "category": None,
        "recyclable": None,
        "confidence": 0.0,
        "message": "请输入要查询的废纸物品。",
    }


def list_categories() -> List[Dict[str, object]]:
    """返回全部类别的概览，供 CLI / 文档使用。"""
    return [
        {
            "key": c.key,
            "name": c.name,
            "recyclable": c.recyclable,
            "value_per_kg": c.value_per_kg,
        }
        for c in CATEGORIES
    ]
```

### `src/paper_recycle_agent/cli.py`（99 行）

```python
"""命令行交互入口。"""

import argparse
import sys

from . import agent, classifier, data, pricing, regions
from . import stats as stats_mod


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="paper-recycle-agent", description="废纸回收 Agent 对话助手"
    )
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("chat", help="进入交互式对话")
    c = sub.add_parser("classify", help="分类查询")
    c.add_argument("text", help="物品描述")
    pr = sub.add_parser("price", help="估价")
    pr.add_argument("text", help="物品描述")
    pr.add_argument("weight", type=float, help="重量(kg)")
    sub.add_parser("categories", help="列出所有类别")
    sub.add_parser("info", help="废纸分类标准与行业数据")
    sub.add_parser("history", help="历年回收量 / 回收率 / 利用率")
    cs = sub.add_parser("catstats", help="按八大类拆分回收量")
    cs.add_argument("year", type=int, nargs="?", default=stats_mod.LATEST_YEAR)
    en = sub.add_parser("enterprises", help="企业名录（可按省 / 类型筛选）")
    en.add_argument("--province", default=None, help="省名，如 山东")
    en.add_argument("--type", dest="etype", default=None, help="企业类型")
    rg = sub.add_parser("region", help="区域统计（全国 / 省级）")
    rg.add_argument("name", nargs="?", default="全国")
    ex = sub.add_parser("export", help="导出 Excel")
    ex.add_argument("name", nargs="?", default="全国")
    ex.add_argument("--year", type=int, default=regions.NATIONAL_YEAR)
    ex.add_argument("--out", default="废纸回收统计.xlsx")
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "chat":
        _chat_loop()
    elif args.cmd == "classify":
        print(classifier.classify(args.text)["message"])
    elif args.cmd == "price":
        print(pricing.estimate(args.text, args.weight)["message"])
    elif args.cmd == "categories":
        for c in classifier.list_categories():
            tag = "可回收" if c["recyclable"] else "不可回收"
            print(f"- {c['name']} [{tag}]")
    elif args.cmd == "info":
        print(data.summary_text())
    elif args.cmd == "history":
        print(stats_mod.history_summary())
    elif args.cmd == "catstats":
        print(stats_mod.category_summary(args.year))
    elif args.cmd == "enterprises":
        from . import enterprises as ent_mod

        node = regions.find(args.province) if args.province else None
        code = str(node["code"]) if node and node["level"] == "province" else None
        if args.etype:
            rows = ent_mod.list_enterprises(code, None, args.etype)
            for e in rows:
                print(f"- {e['name']}（{e['city']}·{e['type']}）{e['volume']} 万吨")
            print(f"共 {len(rows)} 家")
        else:
            print(ent_mod.summary(code))
    elif args.cmd == "region":
        node = regions.find(args.name)
        print(regions.summary(str(node["code"]) if node else "CN"))
    elif args.cmd == "export":
        from . import exporter

        node = regions.find(args.name) or regions.ROOT
        content = exporter.build_workbook(str(node["code"]), args.year)
        with open(args.out, "wb") as fh:
            fh.write(content)
        print(f"已导出：{args.out}（{len(content)} 字节，6 张工作表）")
    else:
        _chat_loop()
    return 0


def _chat_loop() -> None:
    print("废纸回收助手（输入 exit 退出）")
    while True:
        try:
            line = input("你: ")
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break
        if line.strip().lower() in {"exit", "quit", "退出"}:
            print("再见。")
            break
        print("助手:", agent.respond(line))


if __name__ == "__main__":
    sys.exit(main())
```

### `src/paper_recycle_agent/data.py`（114 行）

```python
"""中国造纸年鉴 / 行业报告中的废纸分类与行业数据。

所有数据均标注来源，便于核验：
- GB/T 20811-2018《废纸分类技术要求》（国家市场监督管理总局、中国国家标准化管理委员会，
  2018-12-28 发布，2019-07-01 实施）：将废纸分为 8 大类 42 小类。
- 中国造纸协会《中国造纸工业2024年度报告》（2025-05-07 发布）：废纸回收利用核心指标。
- 生态环境部等《关于全面禁止进口固体废物有关事项的公告》（2021-01-01 施行）：废纸进口清零。
"""

from typing import Dict, List

# ---- 废纸分类（GB/T 20811-2018，共 8 大类 42 小类；此处列 8 大类及代表性小类）----
CATEGORIES_8: List[Dict[str, object]] = [
    {
        "code": "1",
        "name": "废瓦楞纸箱类",
        "examples": ["牛皮挂面旧瓦楞纸箱(101)", "新瓦楞纸箱(102)", "混合旧瓦楞纸箱(104)"],
        "note": "杂质≤1.0%、不可利用物≤3.0%；新箱更严。回收用于箱板纸/瓦楞原纸。",
    },
    {
        "code": "2",
        "name": "废纸盒及废卡纸类",
        "examples": ["工厂回收白色纸盒切边(201)"],
        "note": "白色纸盒切边杂质≤0.25%、不可利用物≤1.0%。",
    },
    {
        "code": "3",
        "name": "包装废纸类",
        "examples": ["白色包装纸(301)", "牛皮包装纸(302)"],
        "note": "不应有杂质，不可利用物≤0.5%。",
    },
    {
        "code": "4",
        "name": "废新闻纸类",
        "examples": ["新闻纸切边(401)", "未出售报纸(402)"],
        "note": "不应有杂质，不可利用物≤0.5%。",
    },
    {
        "code": "5",
        "name": "废书刊杂志类",
        "examples": ["白色未涂布纸切边(501)", "混合旧书刊杂志(505)"],
        "note": "混合旧书刊杂质≤0.5%、不可利用物≤2.5%。",
    },
    {
        "code": "6",
        "name": "办公废纸类",
        "examples": ["混合办公废纸(606)"],
        "note": "混合办公废纸杂质≤0.5%、不可利用物≤2.5%。",
    },
    {
        "code": "7",
        "name": "特种废纸类",
        "examples": ["白色湿强废纸(701)", "工厂使用过的特种废纸(709)"],
        "note": "部分品种不应有杂质；湿强废纸杂质≤0.5%、不可利用物≤2.0%。",
    },
    {
        "code": "8",
        "name": "混合废纸类",
        "examples": [
            "非纸箱纸盒类混合废纸(801)",
            "纸箱纸盒类混合废纸(802)",
            "混合废纸(803)",
        ],
        "note": "803 为不鼓励贸易类别；杂质≤1.0%~1.5%。",
    },
]

# 通用质量要求（GB/T 20811-2018）
QUALITY_RULES: Dict[str, str] = {
    "水分": "实测水分应 ≤ 12%（或按合同规定）",
    "质量差百分率": "应 ≥ -1.0%",
    "包装物质量": "应不大于对应实测质量的 1.0%",
}

# ---- 行业数据（中国造纸协会《中国造纸工业2024年度报告》）----
INDUSTRY_DATA: List[Dict[str, object]] = [
    {"year": 2024, "指标": "国内回收废纸总量", "数值": "6971 万吨", "同比": "+3.47%"},
    {"year": 2024, "指标": "废纸回收率", "数值": "51.1%", "同比": "—"},
    {"year": 2024, "指标": "废纸利用率", "数值": "51.6%", "同比": "—"},
    {"year": 2024, "指标": "纸及纸板产量", "数值": "13625 万吨", "同比": "+5.09%"},
    {"year": 2024, "指标": "全行业营业收入", "数值": "1.46 万亿元", "同比": "+3.88%"},
    {"year": 2024, "指标": "利润总额", "数值": "520 亿元", "同比": "+5.23%"},
    {"year": 2024, "指标": "废纸进口量", "数值": "基本清零（≈0）", "同比": "禁废令后维持低位"},
]

SOURCES: List[str] = [
    "GB/T 20811-2018《废纸分类技术要求》（国家市场监督管理总局、中国国家标准化管理委员会）",
    "中国造纸协会《中国造纸工业2024年度报告》（2025-05-07 发布）",
    "生态环境部等《关于全面禁止进口固体废物有关事项的公告》（2021-01-01 施行）",
]


def get_categories() -> List[Dict[str, object]]:
    """返回 GB/T 20811-2018 的 8 大类废纸分类。"""
    return CATEGORIES_8


def get_industry_data(year: int = 2024) -> List[Dict[str, object]]:
    """返回指定年份的行业数据。"""
    return [d for d in INDUSTRY_DATA if d["year"] == year]


def summary_text() -> str:
    """生成一段人类可读的「分类 + 行业数据」摘要。"""
    lines = ["【废纸分类（GB/T 20811-2018，共 8 大类 42 小类）】"]
    for c in CATEGORIES_8:
        lines.append(f"{c['code']}. {c['name']}：{', '.join(c['examples'])}")
    lines.append("")
    lines.append("【2024 年废纸回收利用（中国造纸协会年度报告）】")
    for d in get_industry_data(2024):
        lines.append(f"- {d['指标']}：{d['数值']}（{d['同比']}）")
    lines.append("")
    lines.append("数据来源：" + "；".join(SOURCES))
    return "\n".join(lines)
```

### `src/paper_recycle_agent/enterprises.py`（326 行）

```python
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
```

### `src/paper_recycle_agent/exporter.py`（250 行）

```python
"""Excel 导出：面向统计局/行业协会的多表工作簿。

工作表结构：
1. 省级统计   —— 34 个省级行政区的回收量、比重、回收率、利用率等（2024 年）
2. 分类回收   —— 按 GB/T 20811-2018 八大类拆分的回收量与估算货值（可选年份/区域）
3. 历年回收   —— 2014—2025 年回收量、消费量、回收率、利用率
4. 废纸进口   —— 2017—2025 年废纸进口量（体现禁废令效果）
5. 企业名录   —— 企业名称、城市、类型、主营大类、年回收量、经纬度
6. 数据说明   —— 数据来源、口径与「官方 / 测算 / 示例」区分，供复核
"""

from io import BytesIO
from typing import Dict, List, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from . import enterprises, regions
from . import stats as stats_mod

HEADER_FILL = PatternFill("solid", fgColor="2F7D4F")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
TITLE_FONT = Font(bold=True, size=13, color="1F2329")
NOTE_FONT = Font(size=10, color="6B7280")
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _style_header(ws, row: int, ncols: int) -> None:
    for col in range(1, ncols + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER


def _autofit(ws, widths: List[int]) -> None:
    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width


def _write_sheet(ws, title: str, headers: List[str], rows: List[List[object]],
                 widths: List[int], note: Optional[str] = None) -> None:
    """统一的「标题 + 表头 + 数据 + 备注」写入。"""
    ws.append([title])
    ws.cell(row=1, column=1).font = TITLE_FONT
    if note:
        ws.append([note])
        ws.cell(row=2, column=1).font = NOTE_FONT
        header_row = 3
    else:
        header_row = 2
    ws.append(headers)
    _style_header(ws, header_row, len(headers))
    for row in rows:
        ws.append(row)
    for r in range(header_row + 1, ws.max_row + 1):
        for c in range(1, len(headers) + 1):
            ws.cell(row=r, column=c).border = BORDER
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    _autofit(ws, widths)


def _province_rows() -> List[List[object]]:
    rows: List[List[object]] = []
    for p in regions.get_children("CN"):
        s = p["stats"]  # type: ignore[index]
        rows.append([
            p["rank"], p["name"], p["tier_label"],
            s["回收量(万吨)"], s["占全国比重(%)"],
            s["回收率(%)"], s["利用率(%)"], s["纸及纸板产量(万吨)"],
            s["回收企业数(家)"], s["从业人员(人)"],
            "公开报道" if p["quality"] == "reported" else "梯队测算",
        ])
    total = sum(float(p["stats"]["回收量(万吨)"]) for p in regions.get_children("CN"))  # type: ignore[index]
    rows.append(["合计", "全国", "—", round(total, 1), 100.0,
                 regions.NATIONAL_STATS["回收率(%)"], regions.NATIONAL_STATS["利用率(%)"],
                 regions.NATIONAL_STATS["纸及纸板产量(万吨)"],
                 regions.NATIONAL_STATS["回收企业数(家)"],
                 regions.NATIONAL_STATS["从业人员(人)"], "官方"])
    return rows


def build_workbook(code: str = "CN", year: int = regions.NATIONAL_YEAR) -> bytes:
    """生成多表工作簿，返回 .xlsx 字节流。"""
    node = regions.get_node(code) or regions.ROOT
    node_code = str(node["code"])
    is_national = node["level"] == "national"
    scope_name = str(node["name"])

    wb = Workbook()

    # ---- 1. 省级统计 ----
    ws1 = wb.active
    ws1.title = "省级统计"
    if is_national:
        rows1 = _province_rows()
        note1 = ("数据年度：2024 年。全国合计为中国造纸协会官方值；"
                 "山东、广东为公开报道值；其余省份为梯队测算，仅供结构参考。")
    else:
        s = node["stats"]  # type: ignore[index]
        rows1 = [[
            node.get("rank", "—"), node["name"], node["tier_label"],
            s["回收量(万吨)"], s["占全国比重(%)"],
            s["回收率(%)"], s["利用率(%)"], s["纸及纸板产量(万吨)"],
            s["回收企业数(家)"], s["从业人员(人)"],
            "公开报道" if node["quality"] == "reported" else "梯队测算",
        ]]
        note1 = f"仅导出「{scope_name}」。完整省级对照请选择「全国」后再导出。"
    _write_sheet(
        ws1, f"{scope_name} 废纸回收统计（2024 年）",
        ["排名", "区域", "梯队", "回收量(万吨)", "占全国比重(%)", "回收率(%)",
         "利用率(%)", "纸及纸板产量(万吨)", "回收企业数(家)", "从业人员(人)", "数据性质"],
        rows1,
        [8, 20, 22, 15, 14, 12, 12, 20, 16, 14, 12],
        note1,
    )

    # ---- 2. 分类回收 ----
    ws2 = wb.create_sheet("分类回收")
    share = regions.share_of_national(node_code)
    year_total = stats_mod.get_recovery(year)
    base = (year_total or 0.0) * share
    cat_rows = []
    for r in stats_mod.category_breakdown(year, total=base):
        cat_rows.append([
            r["code"], r["name"], r["share"], r["tonnage"],
            r["price"], r["value"], r["use"],
        ])
    cat_rows.append([
        "合计", "八大类", round(sum(float(r["share"]) for r in stats_mod.category_breakdown(year, total=base)), 2),
        round(sum(float(r["tonnage"]) for r in stats_mod.category_breakdown(year, total=base)), 1),
        "—",
        round(sum(float(r["value"]) for r in stats_mod.category_breakdown(year, total=base)), 1),
        "",
    ])
    _write_sheet(
        ws2, f"{scope_name} {year} 年废纸回收量分类拆分（GB/T 20811-2018）",
        ["类别代码", "类别名称", "占比(%)", "回收量(万吨)", "参考价(元/公斤)",
         "估算货值(亿元)", "主要去向"],
        cat_rows,
        [10, 20, 10, 14, 16, 16, 52],
        "占比为行业结构估算（2015/2020/2025 三锚点插值），回收量 = 占比 × 当年回收量；"
        "货值为「回收量 × 参考价」估算，非实际成交额。",
    )

    # ---- 3. 历年回收 ----
    ws3 = wb.create_sheet("历年回收")
    hist_rows = []
    for r in stats_mod.get_history():
        hist_rows.append([
            r["year"], r["recovery"],
            "—" if r["consumption"] is None else r["consumption"],
            "—" if r["yoy"] is None else r["yoy"],
            r["recovery_rate"],
            "—" if r["utilization"] is None else r["utilization"],
            "—" if r["paper_output"] is None else r["paper_output"],
            r["note"],
        ])
    _write_sheet(
        ws3, "历年废纸回收利用情况（全国）",
        ["年份", "回收量(万吨)", "废纸消费量(万吨)", "回收量同比(%)",
         "回收率(%)", "利用率(%)", "纸及纸板产量(万吨)", "数据性质"],
        hist_rows,
        [10, 15, 18, 14, 12, 12, 20, 14],
        "回收率 = 回收量 ÷ 纸及纸板消费量；利用率 = 废纸消费量 ÷ 纸及纸板产量。",
    )

    # ---- 4. 废纸进口 ----
    ws4 = wb.create_sheet("废纸进口")
    imp_rows = [[r["year"], r["value"]] for r in stats_mod.get_import_series()]
    _write_sheet(
        ws4, "废纸进口量（万吨）",
        ["年份", "进口量(万吨)"],
        imp_rows,
        [10, 16],
        "2021-01-01《关于全面禁止进口固体废物有关事项的公告》施行后，废纸进口清零。",
    )

    # ---- 5. 企业名录 ----
    ws5 = wb.create_sheet("企业名录")
    prov = None if is_national else node_code
    ent_rows = []
    for e in enterprises.list_enterprises(prov):
        ent_rows.append([
            e["name"], e["city"], e["type"],
            "、".join(e["category_names"]),
            e["volume"], e["lat"], e["lon"], e["note"],
            "示例" if e["is_demo"] else "真实",
        ])
    ent_rows.append([
        "合计", "", "", "",
        round(sum(float(e["volume"]) for e in enterprises.list_enterprises(prov)), 1),
        "", "", "", "",
    ])
    _write_sheet(
        ws5, f"{scope_name} 回收企业名录",
        ["企业名称", "城市", "类型", "主营大类", "年回收量(万吨)",
         "纬度", "经度", "备注", "数据性质"],
        ent_rows,
        [30, 12, 16, 34, 16, 10, 10, 34, 10],
        "企业维度用于回答「某个地方的量由谁在做、分布在哪些城市、各品类由哪类企业消化」。"
        "内置名录为示例数据（虚构名称），可在项目根目录放 data/enterprises.csv 覆盖。",
    )

    # ---- 6. 数据说明 ----
    ws6 = wb.create_sheet("数据说明")
    ws6.append(["数据来源与口径说明"])
    ws6.cell(row=1, column=1).font = TITLE_FONT
    lines = [
        "一、数据来源",
        *[f"  · {s}" for s in stats_mod.SOURCES],
        "",
        "二、口径区分",
        "  · 官方：中国造纸协会年度报告公布值，可直接引用。",
        "  · 公开报道：省级回收量来自行业研究机构公开报道。",
        "  · 梯队测算 / 估算：按行业分区梯队或结构占比推算，仅供结构参考，不可作为统计公报数据。",
        "  · 示例：企业名录为演示用虚构数据，需替换为真实名录后使用。",
        "",
        "三、已知口径差异",
        "  · 2024 年全国废纸回收量：中国造纸协会年度报告 6971 万吨；"
        "部分行业机构按 6797 万吨统计（同比 +9.1%）。本工具采用协会口径。",
        "  · 部分年份（2015、2017、2018）废纸消费量/利用率未在公开年报中单列，故留空。",
        "",
        "四、层级范围",
        "  · 本工具提供全国与省级两级统计；市级、县级无公开权威数据，故不提供，避免误导。",
        "  · 企业名录带城市与经纬度，可在省级以下提供更细的空间视角，但企业样本不代表全量。",
        "",
        "五、替换为真实数据",
        "  · 省级：修改 src/paper_recycle_agent/regions.py 的 SEEDS，为省份填入 reported 值。",
        "  · 历年：修改 src/paper_recycle_agent/stats.py 的 HISTORY。",
        "  · 分类占比：修改 CATEGORY_SHARES 的锚点年份数值。",
        "  · 企业名录：在项目根目录放 data/enterprises.csv（表头见 enterprises.CSV_FIELDS）。",
    ]
    for line in lines:
        ws6.append([line])
    ws6.column_dimensions["A"].width = 110
    for r in range(2, ws6.max_row + 1):
        ws6.cell(row=r, column=1).alignment = Alignment(wrap_text=False, vertical="center")

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def filename(code: str = "CN", year: int = regions.NATIONAL_YEAR) -> str:
    node = regions.get_node(code) or regions.ROOT
    return f"废纸回收统计_{node['name']}_{year}.xlsx"
```

### `src/paper_recycle_agent/knowledge.py`（99 行）

```python
"""废纸回收知识库：分类规则与回收指引数据。

所有分类规则集中在此，便于后续维护与扩展。
"""

from dataclasses import dataclass
from typing import List


@dataclass
class PaperCategory:
    """单个废纸类别的定义。"""

    key: str
    name: str
    aliases: List[str]
    recyclable: bool
    value_per_kg: float  # 参考回收价（元/kg），不可回收为 0.0
    tips: str


# 类别顺序：可回收在前、不可回收在后，便于阅读与优先级排序。
CATEGORIES: List[PaperCategory] = [
    PaperCategory(
        key="office",
        name="办公用纸",
        aliases=["打印纸", "复印纸", "a4", "文件", "办公纸", "办公用纸", "白纸", "资料"],
        recyclable=True,
        value_per_kg=1.1,
        tips="订书钉可保留，回形针建议取下；涉密文件请碎纸后交专业渠道。",
    ),
    PaperCategory(
        key="cardboard",
        name="纸箱/纸板",
        aliases=["纸箱", "纸板", "瓦楞纸", "快递箱", "纸盒", "包装盒"],
        recyclable=True,
        value_per_kg=0.9,
        tips="清空内容物、压平折叠，胶带尽量撕掉。",
    ),
    PaperCategory(
        key="newspaper",
        name="报纸",
        aliases=["报纸", "新闻纸", "旧报"],
        recyclable=True,
        value_per_kg=0.8,
        tips="去除塑料薄膜与装订后可整捆回收。",
    ),
    PaperCategory(
        key="magazine",
        name="书刊杂志",
        aliases=["杂志", "期刊", "书本", "书", "刊物"],
        recyclable=True,
        value_per_kg=0.7,
        tips="胶装书刊可整体回收；塑料封膜请分离。",
    ),
    PaperCategory(
        key="kraft",
        name="牛皮纸",
        aliases=["牛皮纸", "牛皮纸箱", "牛皮袋"],
        recyclable=True,
        value_per_kg=0.85,
        tips="干净干燥即可回收。",
    ),
    PaperCategory(
        key="tissue",
        name="纸巾/卫生纸",
        aliases=["纸巾", "卫生纸", "餐巾纸", "湿巾"],
        recyclable=False,
        value_per_kg=0.0,
        tips="已被污染且纤维过短，不可进入再生纸系统，请作为其他垃圾处理。",
    ),
    PaperCategory(
        key="thermal",
        name="热敏/涂布纸",
        aliases=["热敏纸", "小票", "收银条", "传真纸", "涂布纸"],
        recyclable=False,
        value_per_kg=0.0,
        tips="表面含显色涂层，不可回收，请作为其他垃圾。",
    ),
    PaperCategory(
        key="contaminated",
        name="污染/厨余纸",
        aliases=["油纸", "沾油", "披萨盒", "厨房纸巾", "被污染"],
        recyclable=False,
        value_per_kg=0.0,
        tips="油污、食物残渣会破坏纸浆，不可回收。",
    ),
    PaperCategory(
        key="composite",
        name="复合包装",
        aliases=["利乐包", "纸塑铝", "牛奶盒", "饮料纸盒"],
        recyclable=False,
        value_per_kg=0.0,
        tips="属纸塑铝复合材质，需专用回收线，请勿投入普通废纸。",
    ),
]

# 扁平化的「类别-关键词」索引，供分类引擎快速匹配。
KEYWORD_INDEX = [(cat, kw) for cat in CATEGORIES for kw in cat.aliases]
```

### `src/paper_recycle_agent/pricing.py`（47 行）

```python
"""回收估价：根据类别与重量估算回收价值。"""

from typing import Dict

from .classifier import classify


def estimate(text: str, weight_kg: float) -> Dict[str, object]:
    """估算指定废纸物品在给定重量下的回收价值。

    weight_kg 为负时按 0 处理。
    """
    result = classify(text)
    if not result["matched"]:
        return {
            **result,
            "weight_kg": weight_kg,
            "estimated_value": 0.0,
        }

    value_per_kg = float(result["value_per_kg"])  # type: ignore
    if not result["recyclable"]:
        return {
            "matched": True,
            "category": result["category"],
            "recyclable": False,
            "weight_kg": weight_kg,
            "estimated_value": 0.0,
            "message": (
                f"【{result['category']}】不可回收，无回收价值。"
                f"{result.get('tips', '')}"
            ),
        }

    value = round(value_per_kg * max(weight_kg, 0.0), 2)
    return {
        "matched": True,
        "category": result["category"],
        "recyclable": True,
        "weight_kg": weight_kg,
        "value_per_kg": value_per_kg,
        "estimated_value": value,
        "message": (
            f"【{result['category']}】{weight_kg} kg，"
            f"预计回收价值约 {value} 元。"
        ),
    }
```

### `src/paper_recycle_agent/regions.py`（326 行）

```python
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


_SUFFIXES = ("壮族自治区", "回族自治区", "维吾尔自治区", "特别行政区", "自治区", "省", "市")


def _short_name(name: str) -> str:
    """「山东省」→「山东」，「广西壮族自治区」→「广西」，「中国香港」→「香港」。"""
    text = name[2:] if name.startswith("中国") else name
    for suf in _SUFFIXES:
        if text.endswith(suf) and len(text) > len(suf):
            return text[: -len(suf)]
    return text


# 简称 -> 节点，供「山东有哪些企业」这类自然语言命中
_ALIAS: Dict[str, Dict[str, object]] = {}
for _node in _INDEX.values():
    _ALIAS.setdefault(str(_node["name"]), _node)
    _ALIAS.setdefault(_short_name(str(_node["name"])), _node)


def find(name: str) -> Optional[Dict[str, object]]:
    """按名称查找区域：支持全称、简称，以及嵌在自然语言里的省名。

    「山东」「山东省」「山东有哪些回收企业」都会命中山东省。
    """
    if not name:
        return None
    text = str(name).strip()
    if text in {"全国", "中国", "国家", "cn", "CN"}:
        return ROOT
    if text in _ALIAS:
        return _ALIAS[text]
    # 长别名优先，避免「海南」先被「海」之类的短串抢走
    for alias in sorted(_ALIAS, key=len, reverse=True):
        if len(alias) >= 2 and alias in text:
            return _ALIAS[alias]
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
```

### `src/paper_recycle_agent/stats.py`（239 行）

```python
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
```

## 二、Web 应用（app/）

### `app/server.py`（205 行）

```python
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
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from paper_recycle_agent import data as yearbook
from paper_recycle_agent import enterprises, exporter, regions, respond
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
```

### `app/static/index.html`（792 行）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>废纸回收 Agent 对话助手</title>
<style>
  :root {
    --bg: #f5f7fa; --panel: #ffffff; --ink: #1f2329; --muted: #6b7280;
    --brand: #2f7d4f; --brand-soft: #e8f3ec; --brand-line: #cfe6da;
    --border: #e5e7eb; --warn-bg: #fff8e6; --warn-line: #f2dfae; --warn-ink: #8a6d1f;
    --user-bubble: #2f7d4f; --bot-bubble: #eef1f5;
    --bar: #4a9d6b; --bar-2: #8fbfa3;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
         background: var(--bg); color: var(--ink); height: 100vh; display: flex; flex-direction: column; }
  header { background: var(--brand); color: #fff; padding: 11px 20px; font-size: 17px; font-weight: 600;
           display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  header .sub { font-size: 12px; font-weight: 400; opacity: .9; }
  .layout { flex: 1; display: flex; min-height: 0; }

  /* ---------- 左：对话 ---------- */
  .chat { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  .messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
  .msg { max-width: 82%; padding: 9px 13px; border-radius: 13px; line-height: 1.55;
         white-space: pre-wrap; word-break: break-word; font-size: 13.5px; }
  .msg.bot { background: var(--bot-bubble); align-self: flex-start; border-bottom-left-radius: 4px; }
  .msg.user { background: var(--user-bubble); color: #fff; align-self: flex-end; border-bottom-right-radius: 4px; }
  .chips { display: flex; gap: 8px; flex-wrap: wrap; padding: 0 16px 8px; }
  .chip { background: var(--brand-soft); color: var(--brand); border: 1px solid var(--brand-line);
          border-radius: 15px; padding: 5px 11px; font-size: 12px; cursor: pointer; }
  .chip:hover { background: #dcefe2; }
  .inputbar { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--border);
              background: var(--panel); align-items: center; }
  .inputbar input { flex: 1; padding: 10px 13px; border: 1px solid var(--border); border-radius: 9px;
                    font-size: 14px; outline: none; }
  .inputbar input:focus { border-color: var(--brand); }
  .inputbar button { background: var(--brand); color: #fff; border: none; border-radius: 9px;
                     padding: 0 18px; height: 38px; font-size: 14px; cursor: pointer; }
  .inputbar button:disabled { opacity: .5; cursor: default; }
  #micBtn { background: #fff; color: var(--brand); border: 1px solid var(--border); width: 40px; padding: 0; font-size: 17px; }
  #micBtn.listening { background: #fde8e8; border-color: #f5b5b5; animation: pulse 1s infinite; }
  #micBtn:disabled { opacity: .4; }
  @keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(220,80,80,.4);} 70%{box-shadow:0 0 0 10px rgba(220,80,80,0);} 100%{box-shadow:0 0 0 0 rgba(220,80,80,0);} }
  .voice-status { display: none; padding: 0 16px 10px; font-size: 11.5px; line-height: 1.5; color: var(--muted); }
  .voice-status.show { display: block; }
  .voice-status.info { color: var(--brand); }
  .voice-status.err { color: #b42318; background: #fef3f2; border-top: 1px solid #fecdca; padding: 8px 16px; }
  .voice-status.ok { color: var(--brand); }

  /* ---------- 右：统计面板 ---------- */
  .side { width: 500px; border-left: 1px solid var(--border); background: var(--panel);
          overflow-y: auto; padding: 12px 14px 24px; }
  .tabs { display: flex; gap: 4px; margin-bottom: 10px; border-bottom: 1px solid var(--border); }
  .tab { padding: 7px 12px; font-size: 13px; color: var(--muted); cursor: pointer;
         border-bottom: 2px solid transparent; margin-bottom: -1px; }
  .tab.active { color: var(--brand); font-weight: 600; border-bottom-color: var(--brand); }
  .pane { display: none; }
  .pane.active { display: block; }

  .crumb { font-size: 12.5px; margin-bottom: 8px; display: flex; flex-wrap: wrap; align-items: center; gap: 2px; }
  .crumb-item { color: var(--brand); cursor: pointer; }
  .crumb-item:hover { text-decoration: underline; }
  .crumb .sep { color: var(--muted); }

  .summary { border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; margin-bottom: 10px; background: #fbfcfd; }
  .sum-name { font-weight: 700; font-size: 15px; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .badge { font-size: 11px; font-weight: 400; color: var(--brand); background: var(--brand-soft); border-radius: 10px; padding: 2px 8px; }
  .badge.grey { color: var(--muted); background: #f1f2f4; }
  .sum-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 14px; }
  .sum-grid div { display: flex; justify-content: space-between; font-size: 12px; }
  .sum-grid span { color: var(--muted); }
  .sum-grid b { color: var(--ink); }
  .prov { font-size: 10.5px; color: var(--muted); margin-top: 8px; line-height: 1.45; }

  .sect-title { font-size: 13px; font-weight: 600; color: var(--ink); margin: 14px 0 6px;
                display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .sect-title .hintline { font-size: 10.5px; font-weight: 400; color: var(--muted); }
  .scroll { max-height: 268px; overflow-y: auto; border: 1px solid var(--border); border-radius: 8px; }

  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th, td { border-bottom: 1px solid var(--border); padding: 5px 6px; text-align: left; white-space: nowrap; }
  th { background: var(--brand-soft); color: var(--brand); font-weight: 600; position: sticky; top: 0; z-index: 1; }
  tbody tr.row { cursor: pointer; }
  tbody tr.row:hover { background: #f2f8f4; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  tr.hi { background: #f0f8f3; }
  td.empty { color: var(--muted); text-align: center; padding: 14px 0; }

  /* 条形图 */
  .barwrap { display: flex; align-items: center; gap: 6px; }
  .bartrack { flex: 1; height: 7px; background: #eef1f4; border-radius: 4px; overflow: hidden; min-width: 40px; }
  .barfill { height: 100%; background: var(--bar); border-radius: 4px; }
  .barfill.alt { background: var(--bar-2); }
  .barval { font-size: 11px; color: var(--muted); width: 46px; text-align: right; font-variant-numeric: tabular-nums; }

  .chart { border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; margin-bottom: 8px; }
  .chart .rowc { display: grid; grid-template-columns: 40px 1fr 56px; align-items: center; gap: 6px; margin: 3px 0; font-size: 11px; }
  .chart .lbl { color: var(--muted); }
  .chart .track { height: 12px; background: #eef1f4; border-radius: 3px; overflow: hidden; }
  .chart .fill { height: 100%; background: var(--bar); border-radius: 3px; transition: width .3s; }
  .chart .val { text-align: right; font-variant-numeric: tabular-nums; }

  .actions { display: flex; gap: 8px; margin: 10px 0 4px; }
  .actions button { flex: 1; height: 34px; border-radius: 8px; font-size: 13px; cursor: pointer;
                    border: 1px solid var(--border); background: #fff; color: var(--ink); }
  .actions #exportBtn { background: var(--brand); color: #fff; border-color: var(--brand); }
  .actions button:disabled { opacity: .6; cursor: default; }

  .yearbar { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 12px; color: var(--muted); }
  .yearbar select { padding: 4px 8px; border: 1px solid var(--border); border-radius: 6px; font-size: 12.5px; color: var(--ink); background: #fff; }

  .notice { background: var(--warn-bg); border: 1px solid var(--warn-line); color: var(--warn-ink);
            border-radius: 8px; padding: 7px 10px; font-size: 11px; line-height: 1.5; margin-bottom: 10px; }
  details.standards { margin-top: 14px; border-top: 1px dashed var(--border); padding-top: 8px; }
  details.standards summary { font-size: 12px; color: var(--muted); cursor: pointer; }
  .std-cat { border: 1px solid var(--border); border-radius: 8px; padding: 7px 9px; margin-top: 6px; font-size: 11px; }
  .std-cat .nm { font-weight: 600; font-size: 12px; }
  .std-cat .ex, .std-cat .nt { color: var(--muted); margin-top: 2px; }
  @media (max-width: 980px) { .side { display: none; } }
</style>
</head>
<body>
<header>🪨 废纸回收 Agent 对话助手
  <span class="sub">v1.4.0 · 全国+省级统计 · 历年 · 八大类 · 企业分布 · 语音输入 · 多表 Excel</span>
</header>
<div class="layout">
  <div class="chat">
    <div class="messages" id="messages"></div>
    <div class="chips" id="chips"></div>
    <div class="inputbar">
      <button id="micBtn" title="语音输入（Chrome / Edge，需 HTTPS 与麦克风权限）">🎤</button>
      <input id="input" placeholder="说或输入：纸箱 2kg / 山东省回收量 / 2020年分类数据 / 历年趋势"
             onkeydown="if(event.key==='Enter')send()" />
      <button id="sendBtn" onclick="send()">发送</button>
    </div>
    <div class="voice-status" id="voiceStatus"></div>
  </div>

  <aside class="side">
    <div class="tabs">
      <div class="tab active" data-pane="region" onclick="switchTab('region')">区域统计</div>
      <div class="tab" data-pane="history" onclick="switchTab('history')">历年数据</div>
      <div class="tab" data-pane="category" onclick="switchTab('category')">分类结构</div>
      <div class="tab" data-pane="enterprise" onclick="switchTab('enterprise')">企业分布</div>
    </div>

    <!-- 区域统计 -->
    <section class="pane active" id="pane-region">
      <div class="crumb" id="crumb"></div>
      <div class="summary" id="summary"></div>
      <div class="notice">
        本工具只提供<b>全国</b>与<b>省级</b>两级统计。市级、县级废纸回收量无公开权威数据，为避免误导已下线。
        全国值为中国造纸协会官方口径；山东、广东为公开报道值，其余省份为梯队测算（表中标注）。
      </div>
      <div class="sect-title">
        <span>省级回收量排名（2024 年）</span>
        <span class="hintline">点击行查看该省明细</span>
      </div>
      <div class="scroll">
        <table id="provTable">
          <thead>
            <tr>
              <th class="num">#</th><th>区域</th>
              <th class="num">回收量(万吨)</th><th class="num">占比(%)</th><th>数据</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div class="actions">
        <button id="backBtn" onclick="goBack()">返回全国</button>
        <button id="exportBtn" onclick="exportExcel()">导出 Excel</button>
      </div>
    </section>

    <!-- 历年数据 -->
    <section class="pane" id="pane-history">
      <div class="yearbar">
        <span>数据年份</span>
        <select id="yearSel" onchange="changeYear(this.value)"></select>
        <span id="yearHint"></span>
      </div>
      <div class="sect-title"><span>回收量走势（万吨）</span><span class="hintline" id="histScope"></span></div>
      <div class="chart" id="histChart"></div>
      <div class="sect-title"><span>历年明细</span><span class="hintline">来源：中国造纸协会年度报告</span></div>
      <div class="scroll">
        <table id="histTable">
          <thead>
            <tr>
              <th class="num">年份</th><th class="num">回收量</th><th class="num">同比</th>
              <th class="num">回收率</th><th class="num">利用率</th><th class="num">进口量</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div class="sect-title"><span>废纸进口量（万吨）</span><span class="hintline">2021 年禁废令后清零</span></div>
      <div class="chart" id="impChart"></div>
      <div class="actions">
        <button onclick="exportExcel()">导出 Excel（含历年表）</button>
      </div>
    </section>

    <!-- 分类结构 -->
    <section class="pane" id="pane-category">
      <div class="yearbar">
        <span>数据年份</span>
        <select id="yearSel2" onchange="changeYear(this.value)"></select>
        <span id="catScope"></span>
      </div>
      <div class="notice">
        官方<b>未逐类公布</b>回收量。下表为「行业结构占比 × 当年回收量」估算：
        占比按 2015 / 2020 / 2025 三个锚点线性插值，货值按参考价估算。可作结构参考，不宜作为统计公报数据。
      </div>
      <div class="sect-title"><span>八大类回收量（GB/T 20811-2018）</span><span class="hintline" id="catTotal"></span></div>
      <div class="chart" id="catChart"></div>
      <div class="scroll" style="max-height:320px">
        <table id="catTable">
          <thead>
            <tr>
              <th class="num">代码</th><th>类别</th>
              <th class="num">占比</th><th class="num">回收量(万吨)</th><th class="num">货值(亿元)</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div class="actions">
        <button onclick="exportExcel()">导出 Excel（含分类表）</button>
      </div>
      <details class="standards">
        <summary>内部参考：行业标准（GB/T 20811-2018 分类技术要求）</summary>
        <div id="standardsBody"></div>
      </details>
    </section>

    <!-- 企业分布 -->
    <section class="pane" id="pane-enterprise">
      <div class="yearbar" style="flex-wrap:wrap">
        <span>省份</span>
        <select id="entProv" onchange="loadEnterprises()"></select>
        <span>大类</span>
        <select id="entCat" onchange="loadEnterprises()"></select>
        <span>类型</span>
        <select id="entType" onchange="loadEnterprises()"></select>
      </div>
      <div class="notice" id="entNotice"></div>
      <div class="sect-title">
        <span>企业地理分布（示意图）</span>
        <span class="hintline" id="entTotal"></span>
      </div>
      <div class="chart" style="padding:4px">
        <svg id="entMap" viewBox="0 0 480 300" style="width:100%;height:300px;display:block"></svg>
      </div>
      <div class="sect-title"><span>按类型</span><span class="hintline">点数量与量级</span></div>
      <div class="chart" id="entTypeChart"></div>
      <div class="sect-title"><span>企业明细</span><span class="hintline">按年回收量降序</span></div>
      <div class="scroll" style="max-height:260px">
        <table id="entTable">
          <thead>
            <tr>
              <th>企业</th><th>城市</th><th>类型</th>
              <th class="num">年回收量(万吨)</th><th>主营</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div class="actions">
        <button onclick="exportExcel()">导出 Excel（含企业名录）</button>
      </div>
    </section>
  </aside>
</div>

<script>
  const SUGGESTIONS = [
    "纸箱能回收吗", "办公用纸 3kg", "山东省回收量",
    "全国统计", "历年数据", "分类回收数据"
  ];
  const messagesEl = document.getElementById("messages");
  const chipsEl = document.getElementById("chips");
  const inputEl = document.getElementById("input");
  const sendBtn = document.getElementById("sendBtn");
  const micBtn = document.getElementById("micBtn");

  const state = { code: "CN", year: 2024, data: null };

  /* ---------------- 对话 ---------------- */
  function addMsg(text, who) {
    const div = document.createElement("div");
    div.className = "msg " + who;
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  SUGGESTIONS.forEach(s => {
    const c = document.createElement("span");
    c.className = "chip"; c.textContent = s;
    c.onclick = () => { inputEl.value = s; send(); };
    chipsEl.appendChild(c);
  });

  async function send() {
    const text = inputEl.value.trim();
    if (!text) return;
    addMsg(text, "user");
    inputEl.value = "";
    sendBtn.disabled = true;
    try {
      const res = await fetch("/chat", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      addMsg(data.reply, "bot");
    } catch (e) {
      addMsg("服务暂时不可用：" + e, "bot");
    } finally {
      sendBtn.disabled = false;
    }
  }

  /* ---------------- 标签页 ---------------- */
  function switchTab(name) {
    document.querySelectorAll(".tab").forEach(t => {
      t.classList.toggle("active", t.dataset.pane === name);
    });
    document.querySelectorAll(".pane").forEach(p => {
      p.classList.toggle("active", p.id === "pane-" + name);
    });
    if (name === "enterprise") loadEnterprises();
  }

  /* ---------------- 区域 ---------------- */
  function renderCrumb(items) {
    const el = document.getElementById("crumb");
    el.innerHTML = "";
    items.forEach((it, i) => {
      const a = document.createElement("span");
      a.className = "crumb-item"; a.textContent = it.name;
      a.onclick = () => loadStats(it.code, state.year);
      el.appendChild(a);
      if (i < items.length - 1) {
        const s = document.createElement("span");
        s.className = "sep"; s.textContent = " / ";
        el.appendChild(s);
      }
    });
  }

  function renderSummary(node) {
    const s = node.stats;
    const isNational = node.level === "national";
    const badge = isNational
      ? `<span class="badge">国家</span>`
      : `<span class="badge">省</span><span class="badge grey">${node.tier_label || ""}</span>`;
    const extra = isNational
      ? `<div><span>纸及纸板产量</span><b>${s["纸及纸板产量(万吨)"]} 万吨</b></div>
         <div><span>从业人员</span><b>${s["从业人员(人)"]} 人</b></div>`
      : `<div><span>占全国比重</span><b>${s["占全国比重(%)"]}%</b></div>
         <div><span>全国排名</span><b>第 ${node.rank || "—"} 位</b></div>`;
    document.getElementById("summary").innerHTML =
      `<div class="sum-name">${node.name} ${badge}</div>
       <div class="sum-grid">
         <div><span>回收量</span><b>${s["回收量(万吨)"]} 万吨</b></div>
         <div><span>回收率</span><b>${s["回收率(%)"]}%</b></div>
         <div><span>利用率</span><b>${s["利用率(%)"]}%</b></div>
         <div><span>企业数</span><b>${s["回收企业数(家)"]} 家</b></div>
         ${extra}
       </div>
       <div class="prov">数据年度 ${node.year} 年 · ${node.provenance}</div>`;
  }

  function renderProvTable(children) {
    const tb = document.querySelector("#provTable tbody");
    tb.innerHTML = "";
    if (!children.length) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="5" class="empty">省级为最末级，无下级明细</td>`;
      tb.appendChild(tr);
      return;
    }
    const max = Math.max(...children.map(c => c.stats["回收量(万吨)"]));
    children.forEach(c => {
      const tr = document.createElement("tr");
      tr.className = "row" + (c.code === state.code ? " hi" : "");
      tr.onclick = () => loadStats(c.code, state.year);
      const pct = (c.stats["回收量(万吨)"] / max * 100).toFixed(1);
      tr.innerHTML =
        `<td class="num">${c.rank || ""}</td>
         <td>${c.name}</td>
         <td class="num">
           <div class="barwrap">
             <div class="bartrack"><div class="barfill" style="width:${pct}%"></div></div>
             <div class="barval">${c.stats["回收量(万吨)"]}</div>
           </div>
         </td>
         <td class="num">${c.stats["占全国比重(%)"]}</td>
         <td>${c.quality === "reported" ? "报道" : "测算"}</td>`;
      tb.appendChild(tr);
    });
  }

  /* ---------------- 历年 ---------------- */
  function renderHistory(history, scope) {
    const rows = history.filter(h => h.recovery !== null);
    const max = Math.max(...rows.map(h => h.recovery));
    document.getElementById("histScope").textContent = scope === "national" ? "全国" : "按该省占比折算";
    const chart = document.getElementById("histChart");
    chart.innerHTML = rows.map(h =>
      `<div class="rowc">
         <div class="lbl">${h.year}</div>
         <div class="track"><div class="fill" style="width:${(h.recovery / max * 100).toFixed(1)}%"></div></div>
         <div class="val">${h.recovery}</div>
       </div>`).join("");

    const tb = document.querySelector("#histTable tbody");
    tb.innerHTML = history.map(h => {
      const yoy = h.yoy === null ? "—" : (h.yoy > 0 ? "+" : "") + h.yoy + "%";
      const imp = h.import === null || h.import === undefined ? "—" : h.import;
      const util = h.utilization === null || h.utilization === undefined ? "—" : h.utilization + "%";
      return `<tr>
        <td class="num">${h.year}</td>
        <td class="num">${h.recovery === null ? "—" : h.recovery}</td>
        <td class="num">${yoy}</td>
        <td class="num">${h.recovery_rate}%</td>
        <td class="num">${util}</td>
        <td class="num">${imp}</td>
      </tr>`;
    }).join("");

    const imp = document.getElementById("impChart");
    const impRows = state.data.import_series;
    const impMax = Math.max(...impRows.map(r => r.value)) || 1;
    imp.innerHTML = impRows.map(r =>
      `<div class="rowc">
         <div class="lbl">${r.year}</div>
         <div class="track"><div class="fill alt" style="width:${(r.value / impMax * 100).toFixed(1)}%"></div></div>
         <div class="val">${r.value}</div>
       </div>`).join("");
  }

  /* ---------------- 分类 ---------------- */
  function renderCategory(categories, total, scopeName) {
    const maxShare = Math.max(...categories.map(c => c.share));
    document.getElementById("catScope").textContent = scopeName;
    document.getElementById("catTotal").textContent =
      `合计 ${total} 万吨`;
    document.getElementById("catChart").innerHTML = categories.map(c =>
      `<div class="rowc" style="grid-template-columns:118px 1fr 62px">
         <div class="lbl">${c.name}</div>
         <div class="track"><div class="fill" style="width:${(c.share / maxShare * 100).toFixed(1)}%"></div></div>
         <div class="val">${c.share}%</div>
       </div>`).join("");

    const tb = document.querySelector("#catTable tbody");
    tb.innerHTML = categories.map(c =>
      `<tr>
         <td class="num">${c.code}</td>
         <td title="${c.use}">${c.name}</td>
         <td class="num">${c.share}%</td>
         <td class="num">${c.tonnage}</td>
         <td class="num">${c.value}</td>
       </tr>`).join("");
  }

  /* ---------------- 数据加载 ---------------- */
  async function loadStats(code, year) {
    try {
      const q = new URLSearchParams({ code: code || "CN" });
      if (year) q.set("year", year);
      const res = await fetch("/api/stats?" + q.toString());
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      state.code = data.node.code;
      state.year = data.year;
      state.data = data;

      fillYearSelectors(data.years, data.year, data.national_year);
      renderCrumb(data.breadcrumb);
      renderSummary(data.node);
      renderProvTable(data.children);
      renderHistory(data.history, data.scope);
      renderCategory(data.categories, data.base_tonnage, data.node.name);
      initEntFilters();
      const back = document.getElementById("backBtn");
      back.textContent = data.scope === "national" ? "已在最上级" : "返回全国";
      back.disabled = data.scope === "national";
    } catch (e) {
      console.error(e);
    }
  }

  function fillYearSelectors(years, current, nationalYear) {
    const opts = years.map(y =>
      `<option value="${y}"${y === current ? " selected" : ""}>${y} 年${y === nationalYear ? "（省级同口径）" : ""}</option>`
    ).join("");
    ["yearSel", "yearSel2"].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = opts;
    });
    document.getElementById("yearHint").textContent = current === nationalYear ? "" : "（非省级口径年份）";
  }

  function changeYear(y) {
    loadStats(state.code, parseInt(y, 10));
  }

  function goBack() {
    loadStats("CN", state.year);
  }

  /* ---------------- 企业分布 ---------------- */
  const ENT_COLORS = {
    "回收站点": "#8fbfa3",
    "分拣打包中心": "#4a9d6b",
    "造纸企业": "#1f5c3a",
    "贸易商": "#b7a06a"
  };
  let entReady = false;

  function initEntFilters() {
    if (entReady || !state.data) return;
    entReady = true;
    const provSel = document.getElementById("entProv");
    provSel.innerHTML = `<option value="">全部省份</option>` +
      state.data.children.map(c => `<option value="${c.code}">${c.name}</option>`).join("");
    const catSel = document.getElementById("entCat");
    catSel.innerHTML = `<option value="">全部大类</option>` +
      state.data.categories.map(c => `<option value="${c.code}">${c.code} ${c.name}</option>`).join("");
    const typeSel = document.getElementById("entType");
    typeSel.innerHTML = `<option value="">全部类型</option>` +
      Object.keys(ENT_COLORS).map(t => `<option value="${t}">${t}</option>`).join("");
  }

  async function loadEnterprises() {
    initEntFilters();
    const prov = document.getElementById("entProv").value;
    const cat = document.getElementById("entCat").value;
    const typ = document.getElementById("entType").value;
    const q = new URLSearchParams();
    if (prov) q.set("province", prov);
    if (cat) q.set("category", cat);
    if (typ) q.set("type", typ);
    try {
      const res = await fetch("/api/enterprises?" + q.toString());
      const d = await res.json();
      renderEntNotice(d);
      renderEntMap(d.list);
      renderEntTypeChart(d.by_type);
      renderEntTable(d.list);
      const v = d.list.reduce((s, e) => s + e.volume, 0);
      document.getElementById("entTotal").textContent =
        `${d.list.length} 家 · 合计 ${v.toFixed(1)} 万吨`;
    } catch (e) {
      document.getElementById("entNotice").textContent = "企业数据加载失败：" + e;
    }
  }

  function renderEntNotice(d) {
    const el = document.getElementById("entNotice");
    if (d.is_demo) {
      el.innerHTML = `当前为<b>示例企业名录</b>（名称为虚构），用于演示「企业 × 地理位置 × 品类」分析。
        在项目根目录放 <code>data/enterprises.csv</code> 即可替换为真实名录，页面自动切换为真实数据。`;
    } else {
      el.innerHTML = `当前加载的是<b>自有企业名录</b>（data/enterprises.csv），共 ${d.totals.count} 家。`;
    }
  }

  function renderEntMap(list) {
    const svg = document.getElementById("entMap");
    if (!list.length) {
      svg.innerHTML = `<text x="240" y="150" text-anchor="middle" fill="#6b7280" font-size="12">当前筛选没有企业</text>`;
      return;
    }
    const X = lon => 22 + (lon - 73) / (135 - 73) * 436;
    const Y = lat => 14 + (54 - lat) / (54 - 18) * 272;
    const maxV = Math.max(...list.map(e => e.volume));
    let out = `<rect x="1" y="1" width="478" height="298" fill="#fbfcfd" stroke="#e5e7eb" rx="6"/>`;
    // 参考网格
    for (let lon = 80; lon <= 130; lon += 10) {
      out += `<line x1="${X(lon)}" y1="14" x2="${X(lon)}" y2="286" stroke="#eef1f4"/>`;
      out += `<text x="${X(lon)}" y="296" font-size="9" fill="#9aa3af" text-anchor="middle">${lon}°E</text>`;
    }
    for (let lat = 20; lat <= 50; lat += 10) {
      out += `<line x1="22" y1="${Y(lat)}" x2="458" y2="${Y(lat)}" stroke="#eef1f4"/>`;
      out += `<text x="2" y="${Y(lat) + 3}" font-size="9" fill="#9aa3af">${lat}°N</text>`;
    }
    list.forEach(e => {
      const r = 3 + Math.sqrt(e.volume / maxV) * 9;
      const color = ENT_COLORS[e.type] || "#4a9d6b";
      out += `<circle cx="${X(e.lon).toFixed(1)}" cy="${Y(e.lat).toFixed(1)}" r="${r.toFixed(1)}"
                fill="${color}" fill-opacity="0.72" stroke="#ffffff" stroke-width="1">
                <title>${e.name}\n${e.city} · ${e.type}\n年回收量 ${e.volume} 万吨\n主营 ${e.category_names.join("、")}</title>
              </circle>`;
    });
    // 图例
    let lx = 30;
    Object.keys(ENT_COLORS).forEach(t => {
      out += `<circle cx="${lx}" cy="10" r="3.5" fill="${ENT_COLORS[t]}"/>`;
      out += `<text x="${lx + 7}" y="13" font-size="9" fill="#6b7280">${t}</text>`;
      lx += 78;
    });
    svg.innerHTML = out;
  }

  function renderEntTypeChart(byType) {
    const rows = byType.filter(t => t.count > 0);
    const max = Math.max(...rows.map(t => t.volume), 1);
    document.getElementById("entTypeChart").innerHTML = rows.map(t =>
      `<div class="rowc" style="grid-template-columns:96px 1fr 74px">
         <div class="lbl">${t.type}</div>
         <div class="track"><div class="fill" style="width:${(t.volume / max * 100).toFixed(1)}%;background:${ENT_COLORS[t.type] || "#4a9d6b"}"></div></div>
         <div class="val">${t.count}家 / ${t.volume}</div>
       </div>`).join("");
  }

  function renderEntTable(list) {
    const tb = document.querySelector("#entTable tbody");
    if (!list.length) {
      tb.innerHTML = `<tr><td colspan="5" class="empty">当前筛选没有企业</td></tr>`;
      return;
    }
    tb.innerHTML = list.map(e =>
      `<tr title="${e.note}">
         <td>${e.name}</td>
         <td>${e.city}</td>
         <td>${e.type}</td>
         <td class="num">${e.volume}</td>
         <td>${e.category_names.join("、")}</td>
       </tr>`).join("");
  }

  /* ---------------- Excel 导出 ---------------- */
  async function exportExcel() {
    const btns = [document.getElementById("exportBtn")].filter(Boolean);
    const label = btns.length ? btns[0].textContent : "";
    btns.forEach(b => { b.disabled = true; b.textContent = "导出中…"; });
    const url = `/export.xlsx?code=${encodeURIComponent(state.code)}&year=${state.year}`;
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const blob = await res.blob();
      const name = `废纸回收统计_${(state.data && state.data.node.name) || "全国"}_${state.year}.xlsx`;
      const obj = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = obj;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(obj), 4000);
      btns.forEach(b => { b.textContent = "已导出 ✓"; });
      setTimeout(() => {
        btns.forEach(b => { b.textContent = label || "导出 Excel"; b.disabled = false; });
      }, 1600);
    } catch (e) {
      window.open(url, "_blank");
      btns.forEach(b => { b.textContent = "已打开下载"; });
      setTimeout(() => {
        btns.forEach(b => { b.textContent = label || "导出 Excel"; b.disabled = false; });
      }, 1600);
    }
  }

  /* ---------------- 行业标准 ---------------- */
  async function loadInfo() {
    try {
      const res = await fetch("/api/info");
      const info = await res.json();
      const box = document.getElementById("standardsBody");
      info.categories.forEach(c => {
        const d = document.createElement("div");
        d.className = "std-cat";
        d.innerHTML = `<div class="nm">${c.code}. ${c.name}</div>
                       <div class="ex">${c.examples.join("、")}</div>
                       <div class="nt">${c.note}</div>`;
        box.appendChild(d);
      });
    } catch (e) { /* ignore */ }
  }

  /* ---------------- 语音输入 ----------------
     浏览器 Web Speech API 的失败点很多，而且 onerror 默认是静默的，
     用户只会看到「按了没反应」。这里把每个失败原因都翻译成人话并显示出来。
  */
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const voiceEl = document.getElementById("voiceStatus");
  let recog = null;
  let voiceDone = false;

  function voiceMsg(text, kind) {
    voiceEl.textContent = text || "";
    voiceEl.className = "voice-status" + (text ? " show " + (kind || "info") : "");
  }

  const VOICE_ERRORS = {
    "not-allowed": "麦克风权限被拒绝。点地址栏左侧的锁/摄像头图标 → 把「麦克风」改为允许，再刷新页面。",
    "service-not-allowed": "浏览器禁用了语音识别服务（可能被企业策略或安全软件拦截）。请改用文字输入。",
    "audio-capture": "没有检测到麦克风。请检查麦克风是否插好、系统里是否被静音。",
    "network": "语音识别服务连接失败。Chrome 的识别服务在部分网络环境下不可用，请改用文字输入。",
    "no-speech": "没有听到声音。请靠近麦克风，看到「正在听…」后再说话。",
    "aborted": "语音输入已取消。",
    "language-not-supported": "当前浏览器不支持中文语音识别。",
    "bad-grammar": "识别语法错误，请重试。"
  };

  // 启动前先体检，把「注定失败」的情况直接说清楚，而不是让用户按了没反应
  function voicePreflight() {
    if (window.self !== window.top) {
      return "当前页面嵌在预览框里，浏览器一般会屏蔽麦克风。请点右上角「在浏览器中打开」后重试，或直接用文字输入。";
    }
    if (!window.isSecureContext) {
      return "语音输入要求 HTTPS 或 localhost 环境，当前地址不满足，浏览器会直接拒绝麦克风。";
    }
    if (!SR) {
      return "当前浏览器不支持语音识别。请用 Chrome 或 Edge（Firefox / 部分 Safari 不支持）。";
    }
    return null;
  }

  if (SR) {
    recog = new SR();
    recog.lang = "zh-CN";
    recog.continuous = false;
    recog.interimResults = true;   // 先出临时结果，让用户看到「确实在识别」
    recog.maxAlternatives = 1;

    recog.onstart = () => {
      voiceDone = false;
      voiceMsg("正在听…请说话（说完会自动结束）", "info");
    };
    recog.onresult = (e) => {
      let interim = "", final = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) final += t; else interim += t;
      }
      if (interim) inputEl.value = interim;          // 实时回显，证明麦克风在工作
      if (final) {
        voiceDone = true;
        inputEl.value = final;
        voiceMsg("识别完成：" + final, "ok");
        send();
      }
    };
    recog.onerror = (ev) => {
      const code = ev.error || "unknown";
      voiceMsg("语音输入失败（" + code + "）：" + (VOICE_ERRORS[code] || "未知错误，请改用文字输入。"), "err");
      micBtn.classList.remove("listening");
    };
    recog.onend = () => {
      micBtn.classList.remove("listening");
      micBtn.disabled = false;
      if (!voiceDone && voiceEl.className.indexOf("err") === -1) {
        voiceMsg("没有识别到内容，可以再说一次，或直接打字。", "info");
      }
    };
  }

  micBtn.onclick = () => {
    const block = voicePreflight();
    if (block) { voiceMsg(block, "err"); return; }
    if (micBtn.classList.contains("listening")) {   // 再点一次 = 停止
      try { recog.stop(); } catch (e) {}
      return;
    }
    micBtn.classList.add("listening");
    micBtn.disabled = true;
    setTimeout(() => { micBtn.disabled = false; }, 600);
    try {
      recog.start();
    } catch (e) {
      // 上一次还没结束就再次 start() 会抛 InvalidStateError
      micBtn.classList.remove("listening");
      voiceMsg("识别会话还没结束，请稍等一秒再按一次。", "err");
    }
  };

  addMsg("你好，我是废纸回收助手 🪨\n" +
         "可以问我：某个废纸能不能回收、估算值多少钱、全国/某省回收量、历年趋势、八大类分类回收量、某省有哪些回收企业。\n" +
         "右侧四个标签页：区域统计 / 历年数据 / 分类结构 / 企业分布，都可导出 Excel。\n" +
         "语音输入若不可用，页面输入框下方会直接告诉你原因。", "bot");
  loadStats("CN", 2024);
  loadInfo();
</script>
</body>
</html>
```

## 三、测试（tests/）

### `tests/test_agent.py`（100 行）

```python
from paper_recycle_agent import agent


def test_respond_greeting():
    out = agent.respond("你好")
    assert "废纸回收助手" in out


def test_respond_help():
    out = agent.respond("帮助")
    assert "使用说明" in out


def test_respond_classify():
    out = agent.respond("纸箱")
    assert "纸箱" in out


def test_respond_price_with_weight():
    out = agent.respond("办公用纸 3kg")
    assert "回收价值" in out


def test_respond_jin_conversion():
    out = agent.respond("纸箱 2斤")
    assert "回收价值" in out


def test_respond_yearbook_query():
    out = agent.respond("废纸分类标准")
    assert "GB/T 20811" in out
    assert "6971" in out


def test_respond_industry_data():
    out = agent.respond("回收量多少")
    assert "回收量" in out or "6971" in out


def test_respond_history_intent():
    out = agent.respond("历年数据")
    assert "历年" in out
    assert "2014" in out


def test_respond_history_trend_intent():
    out = agent.respond("近五年趋势")
    assert "历年" in out


def test_respond_category_stats_intent():
    out = agent.respond("分类回收数据")
    assert "废瓦楞纸箱类" in out
    assert "八大类" in out


def test_respond_category_stats_with_year():
    out = agent.respond("2020 年分类数据")
    assert "2020" in out
    assert "废瓦楞纸箱类" in out


def test_respond_province_only():
    out = agent.respond("山东省")
    assert "山东省" in out
    assert "763" in out


def test_no_city_data_claim():
    """市级数据已下线，助手不应再声称能查市县。"""
    out = agent.respond("帮助")
    assert "仅全国与省级" in out


def test_respond_enterprise_national():
    out = agent.respond("企业名录")
    assert "回收企业概览" in out
    assert "示例" in out


def test_respond_enterprise_by_province():
    out = agent.respond("山东有哪些回收企业")
    assert "山东" in out
    assert "名录覆盖率" in out


def test_respond_enterprise_by_name():
    out = agent.respond("鲁清再生")
    assert "鲁清再生资源有限公司" in out
    assert "济南市" in out


def test_respond_enterprise_type():
    out = agent.respond("分拣中心")
    assert "分拣打包中心" in out


def test_help_mentions_enterprise():
    out = agent.respond("帮助")
    assert "企业名录" in out
```

### `tests/test_classifier.py`（29 行）

```python
from paper_recycle_agent import classifier


def test_classify_cardboard():
    r = classifier.classify("我有一个快递纸箱")
    assert r["matched"] is True
    assert r["category"] == "纸箱/纸板"
    assert r["recyclable"] is True


def test_classify_tissue_not_recyclable():
    r = classifier.classify("用过的纸巾")
    assert r["recyclable"] is False


def test_classify_empty():
    r = classifier.classify("")
    assert r["matched"] is False


def test_classify_unknown():
    r = classifier.classify("塑料瓶")
    assert r["matched"] is False


def test_list_categories_nonempty():
    cats = classifier.list_categories()
    assert len(cats) >= 5
    assert any(c["recyclable"] for c in cats)
```

### `tests/test_data.py`（24 行）

```python
from paper_recycle_agent import data


def test_eight_categories():
    cats = data.get_categories()
    assert len(cats) == 8
    assert all("name" in c and "examples" in c for c in cats)


def test_industry_2024_has_volume():
    rows = data.get_industry_data(2024)
    volume = [r for r in rows if r["指标"] == "国内回收废纸总量"]
    assert volume, "应存在废纸回收总量记录"
    assert "6971" in volume[0]["数值"]


def test_summary_text_mentions_standard():
    txt = data.summary_text()
    assert "GB/T 20811" in txt
    assert "6971" in txt


def test_quality_rules_present():
    assert "水分" in data.QUALITY_RULES
```

### `tests/test_enterprises.py`（99 行）

```python
"""企业维度测试：名录、按省/按类/按类型汇总、覆盖率与对话摘要。"""

from paper_recycle_agent import enterprises, regions


def test_enterprises_loaded():
    assert len(enterprises.ENTERPRISES) >= 20
    assert enterprises.IS_DEMO is True  # 未放 data/enterprises.csv 时为示例数据


def test_fields_complete():
    for e in enterprises.ENTERPRISES:
        assert e["id"] and e["name"]
        assert e["province_code"] in regions._INDEX
        assert e["type"] in enterprises.TYPES
        assert e["categories"]
        assert float(e["volume"]) > 0
        assert -90 <= float(e["lat"]) <= 90
        assert 73 <= float(e["lon"]) <= 136


def test_list_sorted_desc():
    rows = enterprises.list_enterprises()
    vols = [float(r["volume"]) for r in rows]
    assert vols == sorted(vols, reverse=True)


def test_filter_by_province():
    rows = enterprises.list_enterprises("370000")
    assert rows
    assert all(r["province_code"] == "370000" for r in rows)


def test_filter_by_category():
    rows = enterprises.list_enterprises(category="6")  # 办公废纸
    assert rows
    assert all("6" in r["categories"] for r in rows)


def test_filter_by_type():
    rows = enterprises.list_enterprises(etype="造纸企业")
    assert rows
    assert all(r["type"] == "造纸企业" for r in rows)


def test_by_province_totals_match():
    rows = enterprises.by_province()
    total = sum(float(r["volume"]) for r in rows)
    assert round(total, 1) == enterprises.totals()["volume"]
    assert sum(int(r["count"]) for r in rows) == len(enterprises.ENTERPRISES)


def test_by_province_sorted():
    vols = [float(r["volume"]) for r in enterprises.by_province()]
    assert vols == sorted(vols, reverse=True)


def test_by_category_covers_all_eight():
    rows = enterprises.by_category()
    assert len(rows) == 8
    assert all(r["name"] for r in rows)


def test_by_type_totals():
    rows = enterprises.by_type()
    assert sum(int(r["count"]) for r in rows) == len(enterprises.ENTERPRISES)


def test_find_by_name():
    e = enterprises.find("鲁清再生")
    assert e is not None
    assert e["city"] == "济南市"


def test_find_short_name_returns_none():
    assert enterprises.find("废") is None


def test_summary_national():
    text = enterprises.summary()
    assert "回收企业概览" in text
    assert "示例" in text  # 必须声明是示例数据
    assert "按类型" in text


def test_summary_province_has_coverage():
    text = enterprises.summary("370000")
    assert "山东" in text
    assert "名录覆盖率" in text


def test_province_volume_not_exceed_official():
    """名录是样本，不应超过该省官方回收量（否则数据明显有问题）。"""
    for row in enterprises.by_province():
        node = regions.get_node(str(row["province_code"]))
        if not node:
            continue
        official = float(node["stats"]["回收量(万吨)"])  # type: ignore[index]
        assert float(row["volume"]) <= official, f"{node['name']} 企业量超过官方回收量"
```

### `tests/test_exporter.py`（96 行）

```python
import io

from openpyxl import load_workbook

from paper_recycle_agent import exporter, regions


def _load(code="CN", year=2024):
    data = exporter.build_workbook(code, year)
    assert data[:2] == b"PK"  # xlsx 是 zip 容器
    return load_workbook(io.BytesIO(data))


def test_sheets_present():
    wb = _load()
    assert wb.sheetnames == [
        "省级统计", "分类回收", "历年回收", "废纸进口", "企业名录", "数据说明"
    ]


def test_province_sheet_rows():
    ws = _load()["省级统计"]
    # 标题 + 备注 + 表头 = 3 行，之后 34 省 + 合计
    assert ws.max_row == 3 + 34 + 1
    values = [ws.cell(row=r, column=2).value for r in range(4, ws.max_row + 1)]
    assert "山东省" in values
    assert ws.cell(row=ws.max_row, column=1).value == "合计"


def test_province_sheet_total():
    ws = _load()["省级统计"]
    total_row = ws.max_row
    assert ws.cell(row=total_row, column=1).value == "合计"
    assert round(ws.cell(row=total_row, column=4).value, 1) == 6971.0


def test_category_sheet_eight_rows():
    ws = _load()["分类回收"]
    names = [ws.cell(row=r, column=2).value for r in range(4, 12)]
    assert len(names) == 8
    assert "废瓦楞纸箱类" in names
    assert ws.cell(row=12, column=1).value == "合计"


def test_history_sheet_years():
    ws = _load()["历年回收"]
    years = [ws.cell(row=r, column=1).value for r in range(4, ws.max_row + 1)]
    assert 2014 in years and 2025 in years
    assert years == sorted(years)


def test_import_sheet():
    ws = _load()["废纸进口"]
    pairs = {ws.cell(row=r, column=1).value: ws.cell(row=r, column=2).value
             for r in range(4, ws.max_row + 1)}
    assert pairs[2017] == 2572.0
    assert pairs[2024] == 0.0


def test_province_scoped_export():
    wb = _load("370000")
    ws = wb["省级统计"]
    # 只有 1 行数据
    assert ws.max_row == 3 + 1
    assert ws.cell(row=4, column=2).value == "山东省"


def test_notes_sheet_mentions_scope():
    ws = _load()["数据说明"]
    text = "\n".join(str(ws.cell(row=r, column=1).value or "") for r in range(1, ws.max_row + 1))
    assert "市级、县级" in text
    assert "6971" in text


def test_enterprise_sheet():
    ws = _load()["企业名录"]
    names = [ws.cell(row=r, column=1).value for r in range(4, ws.max_row + 1)]
    assert "鲁清再生资源有限公司" in names
    assert ws.cell(row=ws.max_row, column=1).value == "合计"


def test_enterprise_sheet_scoped_to_province():
    ws = _load("370000")["企业名录"]
    cities = [ws.cell(row=r, column=2).value for r in range(4, ws.max_row + 1)]
    assert "济南市" in cities
    assert "广州市" not in cities


def test_filename():
    assert exporter.filename("CN", 2024) == "废纸回收统计_全国_2024.xlsx"
    assert "山东省" in exporter.filename("370000", 2024)


def test_export_unknown_code_falls_back_to_national():
    wb = _load("NOT_A_CODE")
    assert wb["省级统计"].max_row == 3 + 34 + 1
```

### `tests/test_pricing.py`（23 行）

```python
from paper_recycle_agent import pricing


def test_estimate_value():
    r = pricing.estimate("办公用纸", 10)
    assert r["recyclable"] is True
    assert r["estimated_value"] == 11.0  # 1.1 * 10


def test_estimate_nonrecyclable():
    r = pricing.estimate("纸巾", 5)
    assert r["recyclable"] is False
    assert r["estimated_value"] == 0.0


def test_estimate_unknown():
    r = pricing.estimate("玻璃", 1)
    assert r["matched"] is False


def test_estimate_negative_weight():
    r = pricing.estimate("纸箱", -3)
    assert r["estimated_value"] == 0.0
```

### `tests/test_regions.py`（86 行）

```python
from paper_recycle_agent import regions


def test_national_node_official():
    node = regions.get_node("CN")
    assert node is not None
    assert node["name"] == "全国"
    assert node["level"] == "national"
    assert node["stats"]["回收量(万吨)"] == 6971.0
    assert "官方" in node["provenance"]


def test_only_two_levels():
    """v1.3.0 起只保留全国 + 省级，不再有市 / 县区。"""
    provinces = regions.get_children("CN")
    assert len(provinces) == 34
    assert all(p["level"] == "province" for p in provinces)
    for p in provinces:
        assert regions.get_children(p["code"]) == []


def test_no_city_or_county_level():
    levels = {node["level"] for node in regions._INDEX.values()}
    assert levels == {"national", "province"}


def test_province_sum_equals_national_total():
    total = sum(p["stats"]["回收量(万吨)"] for p in regions.get_children("CN"))
    assert round(total, 1) == regions.NATIONAL_STATS["回收量(万吨)"]


def test_reported_provinces_flagged():
    sd = regions.find("山东省")
    gd = regions.find("广东省")
    assert sd is not None and gd is not None
    assert sd["quality"] == "reported"
    assert sd["stats"]["回收量(万吨)"] == 763.0
    assert gd["stats"]["回收量(万吨)"] == 733.0


def test_find_short_name():
    node = regions.find("山东")
    assert node is not None
    assert node["name"] == "山东省"


def test_find_national_alias():
    for alias in ["全国", "中国", "国家", "CN"]:
        node = regions.find(alias)
        assert node is not None and node["code"] == "CN"


def test_breadcrumb_two_levels():
    sd = regions.find("山东省")
    crumb = regions.breadcrumb(sd["code"])
    assert len(crumb) == 2
    assert crumb[0]["code"] == "CN"
    assert crumb[-1]["code"] == sd["code"]


def test_share_of_national():
    assert regions.share_of_national("CN") == 1.0
    share = regions.share_of_national("370000")
    assert 0.10 < share < 0.12


def test_summary_contains_history_and_category():
    text = regions.summary("CN")
    assert "全国" in text
    assert "6971" in text
    assert "历年" in text
    assert "废瓦楞纸箱类" in text


def test_summary_province():
    text = regions.summary("370000")
    assert "山东省" in text
    assert "梯队" in text
    assert "占全国比重" in text


def test_tree_structure():
    tree = regions.tree()
    assert tree["code"] == "CN"
    assert len(tree["children"]) == 34
    assert all(c["children"] == [] for c in tree["children"])
```

### `tests/test_server.py`（113 行）

```python
"""Web 层路由测试：锁死「打开就是 Not Found」这类回归。

历史上踩过两次：
1. 只注册了 `/`，预览面板请求 `/index.html` → 404；
2. 托管环境用 HEAD 探测 / 或带路径前缀访问 → 405 / 404。

因此这里对每个入口路径都断言状态码，并检查首页确实带版本号。
"""

import re

import pytest

pytest.importorskip("httpx", reason="TestClient 依赖 httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.server import app  # noqa: E402

client = TestClient(app)


def test_root_ok():
    r = client.get("/")
    assert r.status_code == 200
    assert "废纸回收 Agent" in r.text
    # 版本号格式固定，具体数字随发布变化，不做硬编码
    assert re.search(r"v\d+\.\d+\.\d+", r.text)


def test_index_html_ok():
    r = client.get("/index.html")
    assert r.status_code == 200
    assert "<!DOCTYPE html>" in r.text


def test_head_root_ok():
    """托管平台会用 HEAD 探测，405 会被显示成页面不可用。"""
    assert client.head("/").status_code == 200
    assert client.head("/index.html").status_code == 200


@pytest.mark.parametrize("path", ["/index", "/home", "/app/", "/some/prefix/"])
def test_unknown_page_falls_back_to_index(path):
    r = client.get(path)
    assert r.status_code == 200
    assert "<!DOCTYPE html>" in r.text


@pytest.mark.parametrize("path", ["/api/nope", "/logo.png", "/export.csv"])
def test_api_and_assets_still_404(path):
    r = client.get(path)
    assert r.status_code == 404


def test_favicon_no_content():
    assert client.get("/favicon.ico").status_code == 204


def test_stats_api():
    r = client.get("/api/stats", params={"code": "CN", "year": 2024})
    assert r.status_code == 200
    data = r.json()
    assert data["node"]["code"] == "CN"
    assert len(data["children"]) == 34
    assert len(data["categories"]) == 8
    assert len(data["history"]) >= 8


def test_stats_province_keeps_full_list():
    r = client.get("/api/stats", params={"code": "370000"})
    data = r.json()
    assert data["node"]["name"] == "山东省"
    # 选中省份后仍要返回全部省份，否则排名表会变空
    assert len(data["children"]) == 34


def test_info_api():
    data = client.get("/api/info").json()
    assert len(data["categories"]) == 8
    assert 2024 in data["years"]
    assert data["enterprise_types"]


def test_enterprises_api():
    data = client.get("/api/enterprises").json()
    assert data["totals"]["count"] >= 20
    assert data["list"]
    assert data["is_demo"] is True
    assert len(data["by_category"]) == 8


def test_enterprises_api_filtered():
    data = client.get("/api/enterprises", params={"province": "370000"}).json()
    assert data["list"]
    assert all(e["province_code"] == "370000" for e in data["list"])


def test_export_xlsx():
    r = client.get("/export.xlsx", params={"code": "CN", "year": 2024})
    assert r.status_code == 200
    assert r.content[:2] == b"PK"
    assert "spreadsheetml" in r.headers["content-type"]


def test_chat():
    r = client.post("/chat", json={"message": "纸箱 2kg"})
    assert r.status_code == 200
    assert "reply" in r.json()


def test_health():
    assert client.get("/health").json() == {"status": "ok"}
```

### `tests/test_stats.py`（84 行）

```python
from paper_recycle_agent import stats


def test_history_sorted_and_sourced():
    rows = stats.get_history()
    years = [r["year"] for r in rows]
    assert years == sorted(years)
    assert years[0] == 2014
    assert years[-1] == 2025
    assert len(rows) >= 8


def test_history_latest_matches_national():
    rows = {r["year"]: r for r in stats.get_history()}
    assert rows[2024]["recovery"] == 6971.0
    assert rows[2024]["recovery_rate"] == 51.1
    assert rows[2025]["recovery"] == 7195.0
    assert rows[2025]["recovery_rate"] == 51.8


def test_yoy_computed():
    rows = {r["year"]: r for r in stats.get_history()}
    assert rows[2014]["yoy"] is None
    assert rows[2021]["yoy"] is not None
    assert round(rows[2021]["yoy"], 2) == 18.17


def test_import_series_cleared():
    series = {r["year"]: r["value"] for r in stats.get_import_series()}
    assert series[2017] == 2572.0
    assert series[2021] == 54.0
    assert series[2024] == 0.0


def test_category_shares_sum_to_100():
    for year in (2015, 2020, 2024, 2025):
        rows = stats.category_breakdown(year)
        assert len(rows) == 8
        assert abs(sum(r["share"] for r in rows) - 100.0) < 0.05


def test_category_tonnage_sums_to_recovery():
    rows = stats.category_breakdown(2024)
    total = sum(r["tonnage"] for r in rows)
    assert abs(total - 6971.0) < 1.0


def test_category_scaled_by_region_total():
    rows = stats.category_breakdown(2024, total=763.0)
    total = sum(r["tonnage"] for r in rows)
    assert abs(total - 763.0) < 0.5


def test_category_interpolation_between_anchors():
    """2018 年应落在 2015 与 2020 两个锚点之间。"""
    rows = {r["code"]: r for r in stats.category_breakdown(2018)}
    assert 52.0 < rows["1"]["share"] < 56.0
    assert 7.0 < rows["4"]["share"] < 13.0


def test_category_newsprint_declining():
    s2015 = {r["code"]: r["share"] for r in stats.category_breakdown(2015)}
    s2025 = {r["code"]: r["share"] for r in stats.category_breakdown(2025)}
    assert s2025["4"] < s2015["4"]          # 废新闻纸类下滑
    assert s2025["1"] > s2015["1"]          # 废瓦楞纸箱类上升


def test_category_has_provenance():
    for r in stats.category_breakdown(2024):
        assert "估算" in r["provenance"]


def test_category_summary_text():
    text = stats.category_summary(2024)
    assert "八大类" in text
    assert "废瓦楞纸箱类" in text
    assert "估算" in text


def test_history_summary_text():
    text = stats.history_summary()
    assert "历年" in text
    assert "2024" in text
    assert "6971" in text
```

## 四、启动入口与工程配置

### `run.py`（21 行）

```python
"""统一启动入口：读取 PORT 环境变量并启动 FastAPI 服务。

本地：python run.py            （默认 8000）
部署：平台注入 PORT，python run.py
"""

import os
import sys
from pathlib import Path

# 让 src/ 下的核心包可被导入
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import uvicorn  # noqa: E402

from app.server import app as fastapi_app  # noqa: E402


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port)
```

### `conftest.py`（15 行）

```python
"""pytest 全局配置：让 `src/` 与仓库根目录都可直接 import。

- `src/`：核心包 paper_recycle_agent
- 仓库根：Web 应用 app.server（测试需要导入 FastAPI 实例）
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

for path in (ROOT, ROOT / "src"):
    entry = str(path)
    if entry not in sys.path:
        sys.path.insert(0, entry)
```

### `pyproject.toml`（19 行）

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "paper-recycle-agent"
version = "1.4.0"
description = "废纸回收 Agent 对话助手：分类、估价、区域/历年/分类/企业统计（核心逻辑纯标准库）"
readme = "README.md"
requires-python = ">=3.9"
license = { text = "MIT" }
authors = [{ name = "梁湘瑶 / 阿岩" }]
keywords = ["recycling", "paper", "agent", "cli"]

[project.scripts]
paper-recycle-agent = "paper_recycle_agent.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

### `requirements.txt`（7 行）

```text
# 运行时依赖：无（核心包仅使用 Python 标准库）
# 开发 / 测试 / 图形界面依赖见下方注释
pytest>=7.0          # 单元测试（CI 使用）
fastapi>=0.110       # 图形界面 / HTTP 对话服务（app/server.py）
uvicorn>=0.29        # 运行 FastAPI 服务：uvicorn app.server:app --reload
openpyxl>=3.1        # 导出 Excel（/export.xlsx）
httpx>=0.27          # Web 路由测试（fastapi.testclient 依赖）
```

### `data/enterprises.csv.example`（3 行）

```csv
id,name,province_code,city,type,categories,volume,lat,lon,note
E001,某某再生资源有限公司,370000,济南市,分拣打包中心,1;8,26.0,36.65,117.00,示例：请替换为真实企业
E002,某某纸业原料部,440000,东莞市,造纸企业,1,55.0,23.02,113.75,示例：请替换为真实企业
```

### `.github/workflows/ci.yml`（29 行）

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.11"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        env:
          PYTHONPATH: src
        run: pytest -q
```

## 五、工具脚本（tools/）

### `tools/build_offline.py`（671 行）

```python
"""生成离线单文件版：dist/paper-recycle-offline.html

为什么要有这个
--------------
线上版依赖 HTTP 服务（FastAPI + 网络）。当浏览器无法访问托管域名、
或现场没有网络时，用户看到的就是"打不开"。
离线版把**全部数据内联进一个 HTML**，双击即可打开，不联网、不起服务。

能力差异（如实说明）：
- 保留：对话问答、区域统计、历年数据、分类结构、企业分布、CSV 导出
- 不含：xlsx 多表导出（需要 openpyxl）、语音输入（浏览器 API 与网络相关）
"""

import json
from pathlib import Path

from paper_recycle_agent import data as yearbook
from paper_recycle_agent import enterprises, knowledge, regions
from paper_recycle_agent import stats as stats_mod

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "paper-recycle-offline.html"


def build_payload() -> dict:
    years = [int(r["year"]) for r in stats_mod.get_history()]
    shares = {y: stats_mod._interp_shares(y) for y in years}

    provinces = []
    for p in regions.get_children("CN"):
        provinces.append({
            "code": p["code"],
            "name": p["name"],
            "rank": p["rank"],
            "tier": p["tier_label"],
            "quality": p["quality"],
            "stats": p["stats"],
        })

    return {
        "version": "1.4.0",
        "national": {
            "name": "全国",
            "year": regions.NATIONAL_YEAR,
            "stats": regions.NATIONAL_STATS,
            "provenance": regions.PROVENANCE_OFFICIAL,
        },
        "provinces": provinces,
        "history": stats_mod.get_history(),
        "imports": stats_mod.get_import_series(),
        "shares": shares,
        "catmeta": stats_mod.CATEGORY_META,
        "years": years,
        "national_year": regions.NATIONAL_YEAR,
        "latest_year": stats_mod.LATEST_YEAR,
        "enterprises": enterprises.ENTERPRISES,
        "ent_is_demo": enterprises.IS_DEMO,
        "ent_types": enterprises.TYPES,
        "knowledge": [
            {
                "name": c.name,
                "aliases": c.aliases,
                "recyclable": c.recyclable,
                "price": c.value_per_kg,
                "tips": c.tips,
            }
            for c in knowledge.CATEGORIES
        ],
        "gbt": yearbook.CATEGORIES_8,
        "quality_rules": yearbook.QUALITY_RULES,
        "sources": yearbook.SOURCES + stats_mod.SOURCES,
    }


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>废纸回收 Agent 对话助手（离线版）</title>
<style>
  :root {
    --bg:#f5f7fa; --panel:#fff; --ink:#1f2329; --muted:#6b7280;
    --brand:#2f7d4f; --brand-soft:#e8f3ec; --brand-line:#cfe6da; --border:#e5e7eb;
    --warn-bg:#fff8e6; --warn-line:#f2dfae; --warn-ink:#8a6d1f;
    --bot:#eef1f5; --bar:#4a9d6b; --bar2:#8fbfa3;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
       background:var(--bg);color:var(--ink);height:100vh;display:flex;flex-direction:column}
  header{background:var(--brand);color:#fff;padding:11px 20px;font-size:17px;font-weight:600;
         display:flex;align-items:center;gap:10px;flex-wrap:wrap}
  header .sub{font-size:12px;font-weight:400;opacity:.9}
  header .off{background:rgba(255,255,255,.2);border-radius:10px;padding:2px 8px;font-size:11px;font-weight:400}
  .layout{flex:1;display:flex;min-height:0}
  .chat{flex:1;display:flex;flex-direction:column;min-width:0}
  .messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}
  .msg{max-width:82%;padding:9px 13px;border-radius:13px;line-height:1.55;white-space:pre-wrap;
       word-break:break-word;font-size:13.5px}
  .msg.bot{background:var(--bot);align-self:flex-start;border-bottom-left-radius:4px}
  .msg.user{background:var(--brand);color:#fff;align-self:flex-end;border-bottom-right-radius:4px}
  .chips{display:flex;gap:8px;flex-wrap:wrap;padding:0 16px 8px}
  .chip{background:var(--brand-soft);color:var(--brand);border:1px solid var(--brand-line);
        border-radius:15px;padding:5px 11px;font-size:12px;cursor:pointer}
  .chip:hover{background:#dcefe2}
  .inputbar{display:flex;gap:8px;padding:12px 16px;border-top:1px solid var(--border);background:var(--panel)}
  .inputbar input{flex:1;padding:10px 13px;border:1px solid var(--border);border-radius:9px;font-size:14px;outline:none}
  .inputbar input:focus{border-color:var(--brand)}
  .inputbar button{background:var(--brand);color:#fff;border:none;border-radius:9px;padding:0 18px;height:38px;font-size:14px;cursor:pointer}
  .side{width:500px;border-left:1px solid var(--border);background:var(--panel);overflow-y:auto;padding:12px 14px 24px}
  .tabs{display:flex;gap:4px;margin-bottom:10px;border-bottom:1px solid var(--border)}
  .tab{padding:7px 12px;font-size:13px;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px}
  .tab.active{color:var(--brand);font-weight:600;border-bottom-color:var(--brand)}
  .pane{display:none}.pane.active{display:block}
  .summary{border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin-bottom:10px;background:#fbfcfd}
  .sum-name{font-weight:700;font-size:15px;margin-bottom:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .badge{font-size:11px;font-weight:400;color:var(--brand);background:var(--brand-soft);border-radius:10px;padding:2px 8px}
  .badge.grey{color:var(--muted);background:#f1f2f4}
  .sum-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px}
  .sum-grid div{display:flex;justify-content:space-between;font-size:12px}
  .sum-grid span{color:var(--muted)}.sum-grid b{color:var(--ink)}
  .prov{font-size:10.5px;color:var(--muted);margin-top:8px;line-height:1.45}
  .sect-title{font-size:13px;font-weight:600;margin:14px 0 6px;display:flex;justify-content:space-between;gap:8px}
  .sect-title .hintline{font-size:10.5px;font-weight:400;color:var(--muted)}
  .scroll{max-height:268px;overflow-y:auto;border:1px solid var(--border);border-radius:8px}
  table{width:100%;border-collapse:collapse;font-size:12px}
  th,td{border-bottom:1px solid var(--border);padding:5px 6px;text-align:left;white-space:nowrap}
  th{background:var(--brand-soft);color:var(--brand);font-weight:600;position:sticky;top:0;z-index:1}
  tbody tr.row{cursor:pointer}tbody tr.row:hover{background:#f2f8f4}
  td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
  tr.hi{background:#f0f8f3}
  td.empty{color:var(--muted);text-align:center;padding:14px 0}
  .barwrap{display:flex;align-items:center;gap:6px}
  .bartrack{flex:1;height:7px;background:#eef1f4;border-radius:4px;overflow:hidden;min-width:40px}
  .barfill{height:100%;background:var(--bar);border-radius:4px}
  .barval{font-size:11px;color:var(--muted);width:46px;text-align:right}
  .chart{border:1px solid var(--border);border-radius:8px;padding:8px 10px;margin-bottom:8px}
  .chart .rowc{display:grid;grid-template-columns:40px 1fr 56px;align-items:center;gap:6px;margin:3px 0;font-size:11px}
  .chart .lbl{color:var(--muted)}
  .chart .track{height:12px;background:#eef1f4;border-radius:3px;overflow:hidden}
  .chart .fill{height:100%;background:var(--bar);border-radius:3px}
  .chart .val{text-align:right}
  .yearbar{display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:12px;color:var(--muted);flex-wrap:wrap}
  .yearbar select{padding:4px 8px;border:1px solid var(--border);border-radius:6px;font-size:12.5px;color:var(--ink);background:#fff}
  .notice{background:var(--warn-bg);border:1px solid var(--warn-line);color:var(--warn-ink);
          border-radius:8px;padding:7px 10px;font-size:11px;line-height:1.5;margin-bottom:10px}
  .actions{display:flex;gap:8px;margin:10px 0 4px}
  .actions button{flex:1;height:34px;border-radius:8px;font-size:13px;cursor:pointer;
                  border:1px solid var(--border);background:#fff;color:var(--ink)}
  .actions #csvBtn{background:var(--brand);color:#fff;border-color:var(--brand)}
  details.standards{margin-top:14px;border-top:1px dashed var(--border);padding-top:8px}
  details.standards summary{font-size:12px;color:var(--muted);cursor:pointer}
  .std-cat{border:1px solid var(--border);border-radius:8px;padding:7px 9px;margin-top:6px;font-size:11px}
  .std-cat .nm{font-weight:600;font-size:12px}
  .std-cat .ex,.std-cat .nt{color:var(--muted);margin-top:2px}
  @media (max-width:980px){.side{display:none}}
</style>
</head>
<body>
<header>🪨 废纸回收 Agent 对话助手
  <span class="sub">v__VERSION__ · 全国+省级 · 历年 · 八大类 · 企业分布 · CSV 导出</span>
  <span class="off">离线单文件版 · 不需要联网</span>
</header>
<div class="layout">
  <div class="chat">
    <div class="messages" id="messages"></div>
    <div class="chips" id="chips"></div>
    <div class="inputbar">
      <input id="input" placeholder="输入：纸箱 2kg / 山东省回收量 / 2020年分类数据 / 企业名录"
             onkeydown="if(event.key==='Enter')send()" />
      <button onclick="send()">发送</button>
    </div>
  </div>
  <aside class="side">
    <div class="tabs">
      <div class="tab active" data-pane="region" onclick="switchTab('region')">区域统计</div>
      <div class="tab" data-pane="history" onclick="switchTab('history')">历年数据</div>
      <div class="tab" data-pane="category" onclick="switchTab('category')">分类结构</div>
      <div class="tab" data-pane="enterprise" onclick="switchTab('enterprise')">企业分布</div>
    </div>

    <section class="pane active" id="pane-region">
      <div class="crumb" id="crumb" style="font-size:12.5px;margin-bottom:8px;color:var(--brand);cursor:pointer"></div>
      <div class="summary" id="summary"></div>
      <div class="notice">只提供<b>全国</b>与<b>省级</b>两级统计。市级、县级无公开权威数据，故不提供。
        山东、广东为公开报道值，其余省份为梯队测算（表中标注）。</div>
      <div class="sect-title"><span>省级回收量排名（2024 年）</span><span class="hintline">点击行查看该省</span></div>
      <div class="scroll">
        <table id="provTable"><thead><tr>
          <th class="num">#</th><th>区域</th><th class="num">回收量(万吨)</th>
          <th class="num">占比(%)</th><th>数据</th></tr></thead><tbody></tbody></table>
      </div>
      <div class="actions">
        <button onclick="goNational()">返回全国</button>
        <button id="csvBtn" onclick="exportCSV()">导出 CSV</button>
      </div>
    </section>

    <section class="pane" id="pane-history">
      <div class="yearbar"><span>数据年份</span><select id="yearSel" onchange="changeYear(this.value)"></select></div>
      <div class="sect-title"><span>回收量走势（万吨）</span><span class="hintline" id="histScope"></span></div>
      <div class="chart" id="histChart"></div>
      <div class="sect-title"><span>历年明细</span><span class="hintline">中国造纸协会年度报告</span></div>
      <div class="scroll"><table id="histTable"><thead><tr>
        <th class="num">年份</th><th class="num">回收量</th><th class="num">同比</th>
        <th class="num">回收率</th><th class="num">利用率</th><th class="num">进口量</th>
        </tr></thead><tbody></tbody></table></div>
      <div class="sect-title"><span>废纸进口量（万吨）</span><span class="hintline">2021 年禁废令后清零</span></div>
      <div class="chart" id="impChart"></div>
    </section>

    <section class="pane" id="pane-category">
      <div class="yearbar"><span>数据年份</span><select id="yearSel2" onchange="changeYear(this.value)"></select>
        <span id="catScope"></span></div>
      <div class="notice">官方<b>未逐类公布</b>回收量。下表为「行业结构占比 × 当年回收量」估算，
        占比按 2015/2020/2025 三锚点插值，货值按参考价估算。</div>
      <div class="sect-title"><span>八大类回收量（GB/T 20811-2018）</span><span class="hintline" id="catTotal"></span></div>
      <div class="chart" id="catChart"></div>
      <div class="scroll" style="max-height:320px"><table id="catTable"><thead><tr>
        <th class="num">代码</th><th>类别</th><th class="num">占比</th>
        <th class="num">回收量(万吨)</th><th class="num">货值(亿元)</th>
        </tr></thead><tbody></tbody></table></div>
      <details class="standards"><summary>内部参考：GB/T 20811-2018 分类技术要求</summary>
        <div id="standardsBody"></div></details>
    </section>

    <section class="pane" id="pane-enterprise">
      <div class="yearbar"><span>省份</span><select id="entProv" onchange="renderEnt()"></select>
        <span>大类</span><select id="entCat" onchange="renderEnt()"></select>
        <span>类型</span><select id="entType" onchange="renderEnt()"></select></div>
      <div class="notice" id="entNotice"></div>
      <div class="sect-title"><span>企业地理分布（示意图）</span><span class="hintline" id="entTotal"></span></div>
      <div class="chart" style="padding:4px"><svg id="entMap" viewBox="0 0 480 300"
        style="width:100%;height:300px;display:block"></svg></div>
      <div class="sect-title"><span>按类型</span><span class="hintline">家数 / 万吨</span></div>
      <div class="chart" id="entTypeChart"></div>
      <div class="sect-title"><span>企业明细</span><span class="hintline">按年回收量降序</span></div>
      <div class="scroll" style="max-height:260px"><table id="entTable"><thead><tr>
        <th>企业</th><th>城市</th><th>类型</th><th class="num">年回收量(万吨)</th><th>主营</th>
        </tr></thead><tbody></tbody></table></div>
    </section>
  </aside>
</div>

<script>
const D = __DATA_JSON__;
const S = { code: "CN", year: D.national_year };

/* ---------- 通用 ---------- */
const $ = id => document.getElementById(id);
function addMsg(text, who) {
  const d = document.createElement("div");
  d.className = "msg " + who;
  d.textContent = text;
  $("messages").appendChild(d);
  $("messages").scrollTop = $("messages").scrollHeight;
}
["纸箱能回收吗","办公用纸 3kg","山东省回收量","历年数据","分类回收数据","企业名录"].forEach(s => {
  const c = document.createElement("span");
  c.className = "chip"; c.textContent = s;
  c.onclick = () => { $("input").value = s; send(); };
  $("chips").appendChild(c);
});
function switchTab(name) {
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.pane === name));
  document.querySelectorAll(".pane").forEach(p => p.classList.toggle("active", p.id === "pane-" + name));
  if (name === "enterprise") renderEnt();
}

/* ---------- 区域 ---------- */
function provByCode(code) { return D.provinces.find(p => p.code === code) || null; }
function share(code) { const p = provByCode(code); return p ? p.stats["回收量(万吨)"] / D.national.stats["回收量(万吨)"] : 1; }

function renderRegion(code) {
  S.code = code;
  const p = provByCode(code);
  const node = p || D.national;
  const s = node.stats;
  $("crumb").innerHTML = p
    ? `<span onclick="renderRegion('CN')">全国</span> / ${p.name}`
    : `全国`;
  const isN = !p;
  const badge = isN ? `<span class="badge">国家</span>`
                    : `<span class="badge">省</span><span class="badge grey">${p.tier}</span>`;
  const extra = isN
    ? `<div><span>纸及纸板产量</span><b>${s["纸及纸板产量(万吨)"]} 万吨</b></div>
       <div><span>从业人员</span><b>${s["从业人员(人)"]} 人</b></div>`
    : `<div><span>占全国比重</span><b>${s["占全国比重(%)"]}%</b></div>
       <div><span>全国排名</span><b>第 ${p.rank} 位</b></div>`;
  $("summary").innerHTML =
    `<div class="sum-name">${node.name} ${badge}</div>
     <div class="sum-grid">
       <div><span>回收量</span><b>${s["回收量(万吨)"]} 万吨</b></div>
       <div><span>回收率</span><b>${s["回收率(%)"]}%</b></div>
       <div><span>利用率</span><b>${s["利用率(%)"]}%</b></div>
       <div><span>企业数</span><b>${s["回收企业数(家)"]} 家</b></div>
       ${extra}
     </div>
     <div class="prov">数据年度 ${D.national.year} 年 · ${isN ? D.national.provenance : (p.quality === "reported" ? "回收量为公开报道值，其余测算" : "梯队测算，非官方逐省统计")}</div>`;

  const max = Math.max(...D.provinces.map(x => x.stats["回收量(万吨)"]));
  document.querySelector("#provTable tbody").innerHTML = D.provinces.map(x =>
    `<tr class="row${x.code === code ? " hi" : ""}" onclick="renderRegion('${x.code}')">
       <td class="num">${x.rank}</td><td>${x.name}</td>
       <td class="num"><div class="barwrap"><div class="bartrack">
         <div class="barfill" style="width:${(x.stats["回收量(万吨)"]/max*100).toFixed(1)}%"></div></div>
         <div class="barval">${x.stats["回收量(万吨)"]}</div></div></td>
       <td class="num">${x.stats["占全国比重(%)"]}</td>
       <td>${x.quality === "reported" ? "报道" : "测算"}</td></tr>`).join("");
  renderHistory(); renderCategory();
}
function goNational() { renderRegion("CN"); }

/* ---------- 历年 ---------- */
function renderHistory() {
  const k = share(S.code);
  const rows = D.history.filter(h => h.recovery !== null)
    .map(h => ({ ...h, recovery: +(h.recovery * k).toFixed(1) }));
  const max = Math.max(...rows.map(h => h.recovery));
  $("histScope").textContent = S.code === "CN" ? "全国" : "按该省占比折算";
  $("histChart").innerHTML = rows.map(h =>
    `<div class="rowc"><div class="lbl">${h.year}</div>
      <div class="track"><div class="fill" style="width:${(h.recovery/max*100).toFixed(1)}%"></div></div>
      <div class="val">${h.recovery}</div></div>`).join("");

  document.querySelector("#histTable tbody").innerHTML = D.history.map(h => {
    const yoy = h.yoy === null ? "—" : (h.yoy > 0 ? "+" : "") + h.yoy + "%";
    const rec = h.recovery === null ? "—" : +(h.recovery * k).toFixed(1);
    const util = h.utilization === null ? "—" : h.utilization + "%";
    const imp = h.import === null || h.import === undefined ? "—" : h.import;
    return `<tr><td class="num">${h.year}</td><td class="num">${rec}</td>
      <td class="num">${yoy}</td><td class="num">${h.recovery_rate}%</td>
      <td class="num">${util}</td><td class="num">${imp}</td></tr>`;
  }).join("");

  const imax = Math.max(...D.imports.map(r => r.value)) || 1;
  $("impChart").innerHTML = D.imports.map(r =>
    `<div class="rowc"><div class="lbl">${r.year}</div>
      <div class="track"><div class="fill" style="width:${(r.value/imax*100).toFixed(1)}%;background:var(--bar2)"></div></div>
      <div class="val">${r.value}</div></div>`).join("");
}

/* ---------- 分类 ---------- */
function catRows(year) {
  const k = share(S.code);
  const total = (D.history.find(h => h.year === year) || {}).recovery || 0;
  const base = total * k;
  const shares = D.shares[year] || D.shares[D.latest_year];
  return Object.keys(D.catmeta).sort().map(code => {
    const m = D.catmeta[code];
    const sh = shares[code];
    const t = +(base * sh / 100).toFixed(1);
    return { code, name: m.name, share: sh, tonnage: t, price: m.price,
             value: +(t * m.price * 0.1).toFixed(1), use: m.use };
  });
}
function renderCategory() {
  const rows = catRows(S.year);
  const total = rows.reduce((s, r) => s + r.tonnage, 0);
  const max = Math.max(...rows.map(r => r.share));
  $("catScope").textContent = S.code === "CN" ? "全国" : provByCode(S.code).name;
  $("catTotal").textContent = `合计 ${total.toFixed(1)} 万吨`;
  $("catChart").innerHTML = rows.map(r =>
    `<div class="rowc" style="grid-template-columns:118px 1fr 62px">
      <div class="lbl">${r.name}</div>
      <div class="track"><div class="fill" style="width:${(r.share/max*100).toFixed(1)}%"></div></div>
      <div class="val">${r.share}%</div></div>`).join("");
  document.querySelector("#catTable tbody").innerHTML = rows.map(r =>
    `<tr title="${r.use}"><td class="num">${r.code}</td><td>${r.name}</td>
      <td class="num">${r.share}%</td><td class="num">${r.tonnage}</td>
      <td class="num">${r.value}</td></tr>`).join("");
}
function changeYear(y) {
  S.year = parseInt(y, 10);
  $("yearSel").value = S.year; $("yearSel2").value = S.year;
  renderCategory();
}

/* ---------- 企业 ---------- */
const ENT_COLORS = {"回收站点":"#8fbfa3","分拣打包中心":"#4a9d6b","造纸企业":"#1f5c3a","贸易商":"#b7a06a"};
function initEnt() {
  $("entProv").innerHTML = `<option value="">全部省份</option>` +
    D.provinces.map(p => `<option value="${p.code}">${p.name}</option>`).join("");
  $("entCat").innerHTML = `<option value="">全部大类</option>` +
    Object.keys(D.catmeta).sort().map(c => `<option value="${c}">${c} ${D.catmeta[c].name}</option>`).join("");
  $("entType").innerHTML = `<option value="">全部类型</option>` +
    D.ent_types.map(t => `<option value="${t}">${t}</option>`).join("");
  $("entNotice").innerHTML = D.ent_is_demo
    ? `当前为<b>示例企业名录</b>（名称为虚构），用于演示「企业 × 地理位置 × 品类」分析。`
    : `当前为<b>自有企业名录</b>。`;
}
function entList() {
  const p = $("entProv").value, c = $("entCat").value, t = $("entType").value;
  return D.enterprises.filter(e =>
    (!p || e.province_code === p) && (!c || e.categories.includes(c)) && (!t || e.type === t)
  ).sort((a, b) => b.volume - a.volume);
}
function renderEnt() {
  const list = entList();
  const X = lon => 22 + (lon - 73) / (135 - 73) * 436;
  const Y = lat => 14 + (54 - lat) / (54 - 18) * 272;
  const svg = $("entMap");
  if (!list.length) {
    svg.innerHTML = `<text x="240" y="150" text-anchor="middle" fill="#6b7280" font-size="12">当前筛选没有企业</text>`;
  } else {
    const mv = Math.max(...list.map(e => e.volume));
    let out = `<rect x="1" y="1" width="478" height="298" fill="#fbfcfd" stroke="#e5e7eb" rx="6"/>`;
    for (let lon = 80; lon <= 130; lon += 10) {
      out += `<line x1="${X(lon)}" y1="14" x2="${X(lon)}" y2="286" stroke="#eef1f4"/>`
           + `<text x="${X(lon)}" y="296" font-size="9" fill="#9aa3af" text-anchor="middle">${lon}°E</text>`;
    }
    for (let lat = 20; lat <= 50; lat += 10) {
      out += `<line x1="22" y1="${Y(lat)}" x2="458" y2="${Y(lat)}" stroke="#eef1f4"/>`
           + `<text x="2" y="${Y(lat)+3}" font-size="9" fill="#9aa3af">${lat}°N</text>`;
    }
    list.forEach(e => {
      const r = (3 + Math.sqrt(e.volume / mv) * 9).toFixed(1);
      out += `<circle cx="${X(e.lon).toFixed(1)}" cy="${Y(e.lat).toFixed(1)}" r="${r}"
        fill="${ENT_COLORS[e.type] || "#4a9d6b"}" fill-opacity="0.72" stroke="#fff" stroke-width="1">
        <title>${e.name}\n${e.city} · ${e.type}\n年回收量 ${e.volume} 万吨\n主营 ${e.category_names.join("、")}</title></circle>`;
    });
    let lx = 30;
    Object.keys(ENT_COLORS).forEach(t => {
      out += `<circle cx="${lx}" cy="10" r="3.5" fill="${ENT_COLORS[t]}"/>`
           + `<text x="${lx+7}" y="13" font-size="9" fill="#6b7280">${t}</text>`;
      lx += 78;
    });
    svg.innerHTML = out;
  }

  const byType = {};
  D.ent_types.forEach(t => byType[t] = { count: 0, volume: 0 });
  list.forEach(e => { byType[e.type].count++; byType[e.type].volume += e.volume; });
  const tv = Math.max(...Object.values(byType).map(v => v.volume), 1);
  $("entTypeChart").innerHTML = Object.keys(byType).filter(t => byType[t].count).map(t =>
    `<div class="rowc" style="grid-template-columns:96px 1fr 74px">
      <div class="lbl">${t}</div>
      <div class="track"><div class="fill" style="width:${(byType[t].volume/tv*100).toFixed(1)}%;background:${ENT_COLORS[t]}"></div></div>
      <div class="val">${byType[t].count}家 / ${byType[t].volume.toFixed(1)}</div></div>`).join("");

  $("entTotal").textContent = `${list.length} 家 · 合计 ${list.reduce((s,e)=>s+e.volume,0).toFixed(1)} 万吨`;
  document.querySelector("#entTable tbody").innerHTML = list.length
    ? list.map(e => `<tr title="${e.note}"><td>${e.name}</td><td>${e.city}</td><td>${e.type}</td>
        <td class="num">${e.volume}</td><td>${e.category_names.join("、")}</td></tr>`).join("")
    : `<tr><td colspan="5" class="empty">当前筛选没有企业</td></tr>`;
}

/* ---------- 对话（离线规则引擎，与 Python 版同序） ---------- */
function findProv(text) {
  if (/全国|中国|国家/.test(text)) return "CN";
  const hits = D.provinces.filter(p => text.indexOf(p.name) >= 0);
  if (hits.length) return hits[0].code;
  const shorts = D.provinces.filter(p => {
    const s = p.name.replace(/^(中国)?/, "").replace(/(壮族|回族|维吾尔)?自治区$|特别行政区$|省$|市$/, "");
    return s.length >= 2 && text.indexOf(s) >= 0;
  });
  return shorts.length ? shorts[0].code : null;
}
function findEnt(text) {
  const generic = ["废纸","回收","废纸回收","回收站","公司","企业","造纸","纸厂","中心","站点","分拣","打包"];
  if (text.length < 3 || generic.indexOf(text) >= 0) return null;
  return D.enterprises.find(e => e.name.indexOf(text) >= 0) || null;
}
function catSummary(year) {
  const rows = catRows(year);
  const lines = [`【${year} 年废纸回收量按类别拆分（GB/T 20811-2018 八大类）】`,
                 "说明：官方未逐类公布回收量，下表为「行业结构占比 × 官方回收量」估算。"];
  rows.forEach(r => lines.push(`- ${r.code} ${r.name}：${r.share}%，约 ${r.tonnage} 万吨，参考价 ${r.price} 元/公斤`));
  return lines.join("\n");
}
function historySummary() {
  const lines = ["【历年废纸回收利用（中国造纸协会年度报告）】",
                 "年份　回收量(万吨)　回收率(%)　利用率(%)　废纸进口(万吨)"];
  D.history.forEach(h => lines.push(
    `${h.year}　${h.recovery}　${h.recovery_rate}　${h.utilization === null ? "—" : h.utilization}　${h.import === null || h.import === undefined ? "—" : h.import}`));
  const a = D.history[0], b = D.history[D.history.length - 1];
  lines.push(`趋势：${a.year}—${b.year} 回收量从 ${a.recovery} 万吨增至 ${b.recovery} 万吨；废纸进口自 2021 年禁废令后清零。`);
  return lines.join("\n");
}
function entSummary(code) {
  const list = code ? D.enterprises.filter(e => e.province_code === code) : D.enterprises;
  if (!list.length) return "暂无企业名录数据。";
  const name = code ? provByCode(code).name : "全国";
  const tv = list.reduce((s, e) => s + e.volume, 0);
  const lines = [`【${name}回收企业概览】`];
  if (D.ent_is_demo) lines.push("注：以下为示例企业名录（虚构名称），用于演示企业维度。");
  lines.push(`- 收录企业 ${list.length} 家，年回收量合计 ${tv.toFixed(1)} 万吨`);
  if (code) {
    const official = provByCode(code).stats["回收量(万吨)"];
    lines.push(`- 占该省官方回收量（${official} 万吨）的 ${(tv / official * 100).toFixed(1)}%（名录覆盖率）`);
  }
  lines.push("", "按类型：");
  const bt = {};
  list.forEach(e => { bt[e.type] = bt[e.type] || { c: 0, v: 0 }; bt[e.type].c++; bt[e.type].v += e.volume; });
  Object.keys(bt).forEach(t => lines.push(`- ${t}：${bt[t].c} 家，${bt[t].v.toFixed(1)} 万吨`));
  lines.push("", "年回收量前五：");
  list.slice().sort((a, b) => b.volume - a.volume).slice(0, 5).forEach(e =>
    lines.push(`  ${e.name}（${e.city}·${e.type}）${e.volume} 万吨，主营 ${e.category_names.join("、")}`));
  return lines.join("\n");
}
function classify(text) {
  const low = text.toLowerCase();
  let hit = null;
  D.knowledge.forEach(k => {
    if (hit) return;
    if (k.aliases.some(a => low.indexOf(a) >= 0) || low.indexOf(k.name) >= 0) hit = k;
  });
  if (!hit) return "未能识别废纸类型，请描述更具体的物品（如：纸箱、报纸、纸巾、热敏小票）。";
  return hit.recyclable
    ? `【${hit.name}】可回收，参考回收价 ${hit.price} 元/公斤。\n提示：${hit.tips}`
    : `【${hit.name}】不可回收。\n原因：${hit.tips}`;
}
function priceOf(text, kg) {
  const low = text.toLowerCase();
  const hit = D.knowledge.find(k => k.aliases.some(a => low.indexOf(a) >= 0) || low.indexOf(k.name) >= 0);
  if (!hit) return "未能识别废纸类型，请描述更具体的物品（如：纸箱、报纸）。";
  if (!hit.recyclable) return `【${hit.name}】不可回收，回收价值为 0。\n原因：${hit.tips}`;
  const val = (hit.price * Math.max(kg, 0)).toFixed(2);
  return `【${hit.name}】${kg} 公斤，参考回收价值约 ${val} 元（按 ${hit.price} 元/公斤估算）。\n提示：${hit.tips}`;
}
function respond(text) {
  if (!text) return "请输入你想查询的废纸物品，例如「纸箱 2kg 能卖多少钱」。";
  if (["你好","您好","hi","hello","在吗","在么"].indexOf(text.toLowerCase()) >= 0)
    return "你好，我是废纸回收助手 🪨。可以问我：能不能回收、值多少钱、全国/各省回收量、历年趋势、八大类分类、某省企业。";
  if (/帮助|help|怎么用|功能|能做什么|用法/.test(text)) {
    return ["废纸回收助手使用说明：",
      "1) 是否可回收：直接说物品名，如「纸箱」「纸巾」。",
      "2) 估算价值：物品名 + 重量，如「办公用纸 3kg」「纸箱 5 斤」。",
      "3) 分类标准：输入「废纸分类」。",
      "4) 按类别看回收量：输入「分类回收数据」「2020 年分类数据」。",
      "5) 历年趋势：输入「历年数据」。",
      "6) 区域统计（全国与省级）：输入「山东省回收量」。",
      "7) 企业分布：输入「企业名录」「山东有哪些回收企业」。",
      "8) 导出：右侧「导出 CSV」。离线版不支持 xlsx，在线版可导出六表 Excel。"].join("\n");
  }
  const ent = findEnt(text);
  if (ent) {
    return [`【${ent.name}】`, `- 位置：${ent.city}（${ent.lat}, ${ent.lon}）`,
      `- 类型：${ent.type}`, `- 主营：${ent.category_names.join("、")}`,
      `- 年回收量：${ent.volume} 万吨`, `- 备注：${ent.note}`,
      D.ent_is_demo ? "（示例数据）" : ""].filter(Boolean).join("\n");
  }
  if (/企业|公司|回收站|回收点|打包厂|分拣中心|造纸厂|贸易商|名录|哪家|厂家/.test(text)) {
    return entSummary(findProv(text));
  }
  if (/分类数据|分类回收|类别占比|各类回收|八大类|按类别|分类占比|品种结构/.test(text)) {
    const m = text.match(/(20\d{2})/);
    const y = m && D.years.indexOf(parseInt(m[1], 10)) >= 0 ? parseInt(m[1], 10) : D.latest_year;
    return catSummary(y);
  }
  if (/历年|年份|以前|过去|趋势|增长|变化|这几年|近五年|历史数据/.test(text)) return historySummary();
  if (/年鉴|行业数据|进口|标准|分类标准|gb\/t|20811|造纸|废纸分几类|废纸分类/.test(text)) {
    const lines = ["【废纸分类（GB/T 20811-2018，8 大类 42 小类）】"];
    D.gbt.forEach(c => lines.push(`${c.code}. ${c.name}：${c.examples.join("、")}`));
    lines.push("", "【2024 年废纸回收利用】", "回收量 6971 万吨、回收率 51.1%、利用率 51.6%。");
    return lines.join("\n");
  }
  if (/回收量|利用率|回收率|统计|企业数|从业人员|数据|排名|占比/.test(text)) {
    const code = findProv(text) || "CN";
    const p = provByCode(code);
    if (!p) return regionText("CN");
    return regionText(code);
  }
  const code = findProv(text);
  if (code && code !== "CN") return regionText(code);
  const m = text.match(/(\d+(?:\.\d+)?)\s*(kg|公斤|千克|斤)/i);
  if (m) {
    let kg = parseFloat(m[1]);
    if (m[2] === "斤") kg = kg / 2;
    return priceOf(text, kg);
  }
  return classify(text);
}
function regionText(code) {
  const p = provByCode(code);
  if (!p) {
    const n = D.national;
    const top = D.provinces.slice(0, 5).map(x => `  ${x.rank}. ${x.name} ${x.stats["回收量(万吨)"]} 万吨（占全国 ${x.stats["占全国比重(%)"]}%）`);
    return [`【全国】废纸回收统计（${n.year} 年，官方）`,
      `- 回收量：${n.stats["回收量(万吨)"]} 万吨`,
      `- 回收率：${n.stats["回收率(%)"]}%；利用率：${n.stats["利用率(%)"]}%`,
      `- 纸及纸板产量：${n.stats["纸及纸板产量(万吨)"]} 万吨`,
      "回收量前五：", ...top, "", "注：本工具仅提供全国与省级两级统计。"].join("\n");
  }
  const s = p.stats;
  return [`【${p.name}】废纸回收统计（${D.national.year} 年，${p.quality === "reported" ? "回收量为公开报道值" : "梯队测算"}）`,
    `- 回收量：${s["回收量(万吨)"]} 万吨（占全国 ${s["占全国比重(%)"]}%，第 ${p.rank} 位）`,
    `- 回收率：${s["回收率(%)"]}%；利用率：${s["利用率(%)"]}%`,
    `- 纸及纸板产量：${s["纸及纸板产量(万吨)"]} 万吨`,
    `- 回收企业数：${s["回收企业数(家)"]} 家；从业人员：${s["从业人员(人)"]} 人`,
    `- 梯队：${p.tier}`, "", "注：本工具仅提供全国与省级两级统计。"].join("\n");
}
function send() {
  const el = $("input");
  const text = el.value.trim();
  if (!text) return;
  addMsg(text, "user");
  el.value = "";
  addMsg(respond(text), "bot");
}

/* ---------- CSV 导出 ---------- */
function exportCSV() {
  const lines = [];
  const push = arr => lines.push(arr.map(v => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`).join(","));
  push(["废纸回收统计（离线版）"]);
  push(["全国", D.national.year, "回收量(万吨)", D.national.stats["回收量(万吨)"],
        "回收率(%)", D.national.stats["回收率(%)"], "利用率(%)", D.national.stats["利用率(%)"]]);
  push([]);
  push(["一、省级统计（2024 年）"]);
  push(["排名","区域","梯队","回收量(万吨)","占全国比重(%)","回收率(%)","利用率(%)","数据性质"]);
  D.provinces.forEach(p => push([p.rank, p.name, p.tier, p.stats["回收量(万吨)"],
    p.stats["占全国比重(%)"], p.stats["回收率(%)"], p.stats["利用率(%)"],
    p.quality === "reported" ? "公开报道" : "梯队测算"]));
  push([]);
  push([`二、分类回收（${S.year} 年，${S.code === "CN" ? "全国" : provByCode(S.code).name}）`]);
  push(["代码","类别","占比(%)","回收量(万吨)","参考价(元/公斤)","估算货值(亿元)"]);
  catRows(S.year).forEach(r => push([r.code, r.name, r.share, r.tonnage, r.price, r.value]));
  push([]);
  push(["三、历年回收"]);
  push(["年份","回收量(万吨)","回收率(%)","利用率(%)","废纸进口(万吨)"]);
  D.history.forEach(h => push([h.year, h.recovery, h.recovery_rate,
    h.utilization === null ? "—" : h.utilization,
    h.import === null || h.import === undefined ? "—" : h.import]));
  push([]);
  push(["四、企业名录" + (D.ent_is_demo ? "（示例数据）" : "")]);
  push(["企业名称","城市","类型","主营大类","年回收量(万吨)","纬度","经度","备注"]);
  entList().forEach(e => push([e.name, e.city, e.type, e.category_names.join("、"),
    e.volume, e.lat, e.lon, e.note]));

  const csv = "\uFEFF" + lines.join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `废纸回收统计_${S.code === "CN" ? "全国" : provByCode(S.code).name}_${S.year}.csv`;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 3000);
}

/* ---------- 初始化 ---------- */
(function init() {
  $("yearSel").innerHTML = D.years.map(y => `<option value="${y}"${y === D.national_year ? " selected" : ""}>${y} 年</option>`).join("");
  $("yearSel2").innerHTML = $("yearSel").innerHTML;
  $("standardsBody").innerHTML = D.gbt.map(c =>
    `<div class="std-cat"><div class="nm">${c.code}. ${c.name}</div>
     <div class="ex">${c.examples.join("、")}</div><div class="nt">${c.note}</div></div>`).join("");
  initEnt();
  renderRegion("CN");
  renderEnt();
  addMsg("你好，我是废纸回收助手 🪨（离线版，不联网）。\n"
    + "可以问我：能不能回收、值多少钱、各省回收量、历年趋势、八大类分类、某省有哪些企业。\n"
    + "右侧四个标签页：区域统计 / 历年数据 / 分类结构 / 企业分布。", "bot");
})();
</script>
</body>
</html>
"""


def main() -> int:
    payload = build_payload()
    html = TEMPLATE.replace("__VERSION__", payload["version"])
    html = html.replace("__DATA_JSON__", json.dumps(payload, ensure_ascii=False))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"已生成 {OUT.relative_to(ROOT)}（{OUT.stat().st_size} 字节）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### `tools/gen_code_listing.py`（127 行）

```python
"""生成 docs/CODE_LISTING.md：把全部源码嵌入一份独立的代码清单文档。

用法：
    python tools/gen_code_listing.py

清单按「包源码 → Web 应用 → 测试 → 工程配置」的顺序组织，
每段前带文件路径与行数，便于评审时逐段对照仓库。
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "CODE_LISTING.md"

LANG = {
    ".py": "python",
    ".html": "html",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".txt": "text",
    ".md": "markdown",
    ".sh": "bash",
    ".example": "csv",
}

# (标题, 目录或文件, 是否递归)
SECTIONS = [
    ("一、核心包（src/paper_recycle_agent）", ROOT / "src" / "paper_recycle_agent", True),
    ("二、Web 应用（app/）", ROOT / "app", True),
    ("三、测试（tests/）", ROOT / "tests", True),
    ("四、启动入口与工程配置", None, False),
    ("五、工具脚本（tools/）", ROOT / "tools", False),
]

ROOT_FILES = [
    "run.py",
    "conftest.py",
    "pyproject.toml",
    "requirements.txt",
    "data/enterprises.csv.example",
    ".github/workflows/ci.yml",
]


def _version() -> str:
    init = ROOT / "src" / "paper_recycle_agent" / "__init__.py"
    for line in init.read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "unknown"


def _files(path: Path, recursive: bool) -> list[Path]:
    if path.is_file():
        return [path]
    pattern = "**/*" if recursive else "*"
    return sorted(
        p for p in path.glob(pattern)
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix in LANG
    )


def _block(file: Path) -> str:
    rel = file.relative_to(ROOT).as_posix()
    text = file.read_text(encoding="utf-8")
    lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    lang = LANG.get(file.suffix, "")
    return f"### `{rel}`（{lines} 行）\n\n```{lang}\n{text.rstrip()}\n```\n"


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()
    except OSError:
        return ""


def main() -> int:
    parts: list[str] = []
    version = _version()
    parts.append(
        "# 代码清单\n\n"
        f"> 版本：v{version}　生成日期：{date.today().isoformat()}　"
        "由 `tools/gen_code_listing.py` 自动生成，请勿手工编辑。\n\n"
        "本文档把仓库全部源码按模块顺序嵌入，便于在不打开仓库的情况下通读实现。\n"
    )

    commit = _git("rev-parse", "--short", "HEAD")
    if commit:
        parts.append(f"- 生成时提交：`{commit}`\n")

    parts.append("\n## 目录\n")
    for title, _, _ in SECTIONS:
        parts.append(f"- {title}\n")
    parts.append("\n---\n")

    total = 0
    for title, path, recursive in SECTIONS:
        parts.append(f"\n## {title}\n")
        if path is None:
            files = [ROOT / f for f in ROOT_FILES if (ROOT / f).exists()]
        else:
            files = _files(path, recursive)
        for f in files:
            parts.append("\n" + _block(f))
            total += 1

    parts.append(f"\n---\n\n共收录 {total} 个文件。\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"已生成 {OUT.relative_to(ROOT)}（{total} 个文件，{OUT.stat().st_size} 字节）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

共收录 30 个文件。
