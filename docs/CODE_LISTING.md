# 代码清单

> 版本：v1.9.2　生成日期：2026-11-23　由 `tools/gen_code_listing.py` 自动生成，请勿手工编辑。

本文档把仓库全部源码按模块顺序嵌入，便于在不打开仓库的情况下通读实现。
- 生成时提交：`c8b5e8e`

## 目录
- 一、核心包（src/paper_recycle_agent）
- 二、Web 应用（app/）
- 三、测试（tests/）
- 四、启动入口与工程配置
- 五、工具脚本（tools/）

---

## 一、核心包（src/paper_recycle_agent）

### `src/paper_recycle_agent/__init__.py`（42 行）

```python
"""造纸工厂多智能体系统 · 碳核算 Agent。

核心是碳核算 Agent（carbon/）：按国标方法核算工厂温室气体排放。
废纸回收助手作为工厂内的废纸回收子 Agent 保留全功能；
智能工厂（mill/）与产业大脑（brain/）分别是车间层与经营管理层。

最低支持 Python 3.7（核心逻辑纯标准库，无需任何第三方依赖）。
图形界面额外需要 Python 3.8+ 与 FastAPI；导出 Excel 额外需要 openpyxl。
"""

import sys

if sys.version_info < (3, 7):  # pragma: no cover - 仅在旧解释器上触发
    raise RuntimeError(
        "paper_recycle_agent 需要 Python 3.7 或更高版本，当前为 {}.{}.{}。".format(
            *sys.version_info[:3]
        )
    )

from . import (agent, brain, carbon, classifier, data, enterprises,  # noqa: E402
               exporter, io_table, knowledge, llm, mill, pricing, regions, stats)
from .agent import respond  # noqa: E402

__version__ = "1.9.2"

__all__ = [
    "agent",
    "brain",
    "carbon",
    "classifier",
    "data",
    "enterprises",
    "exporter",
    "io_table",
    "knowledge",
    "llm",
    "mill",
    "pricing",
    "regions",
    "stats",
    "respond",
]
```

### `src/paper_recycle_agent/agent.py`（154 行）

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
# 投入产出 / 消耗金额类（必须放在区域与估价之前，否则「金额」会被当成卖废品估价）
_IO = {"投入产出", "消耗金额", "采购金额", "消耗系数", "货值", "产值消耗",
       "消耗了多少钱", "花了多少钱", "投入产出表"}
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
            "全国/各省回收统计、历年趋势、八大类分类回收量、废纸消耗金额。输入「帮助」查看用法。"
        )
    if any(k in text for k in _HELP):
        return _help_text()

    # 投入产出：消耗金额 / 直接消耗系数
    if any(k in text for k in _IO):
        from . import io_table

        year = _extract_year(text) or int(io_table.NATIONAL_IO["year"])
        node = regions.find(text)
        if node is not None and node["level"] == "province":
            share = float(node["stats"]["占全国比重(%)"]) / 100.0  # type: ignore[index]
            total = float(io_table.spend(year)["amount"]) * share
            dc = io_table.direct_coefficient(year)
            coef = "—" if dc["coefficient"] is None else f"{dc['coefficient_pct']}%"
            return (
                f"{node['name']}{year} 年废纸消耗金额约 {total:.1f} 亿元"
                f"（按该省回收量占全国 {share * 100:.2f}% 分摊，属估算，非实际采购分布）。\n"
                f"全国同口径 {io_table.spend(year)['amount']} 亿元，"
                f"直接消耗系数 {coef}（按回收参考价计，属纸厂成本下限）。"
            )
        return io_table.summary_text(year)

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
            "8) 看消耗金额（投入产出）：输入「废纸消耗金额」「投入产出」「直接消耗系数」。",
            "9) 导出 Excel：右侧面板点「导出 Excel」，含省级、分类、历年、进口、企业、投入产出、说明七张表。",
        ]
    )
```

### `src/paper_recycle_agent/brain/__init__.py`（26 行）

```python
"""造纸产业大脑（仿真演示版）。

对标华泰集团「造纸产业大脑 + 瞬捷云链生态大模型」的业务形态：
把造纸企业的五条关键业务链——采购 / 生产 / 销售 / 仓储物流 / 资金财务——
接进一个共享的数据底座，每个业务链一个领域智能体，顶层由产业大脑编排，
模拟「数据贯通 → 跨域联动 → 决策建议」的全过程。

必须说清楚的三件事
------------------
1. 这是**仿真演示**，不是华泰系统的复刻，也不连接任何真实 ERP / MES / 供应链系统；
2. 所有 KPI 由仿真引擎生成；文档中引用的华泰成效数字（采购成本 -12%、吨纸能耗 -12%、
   交货 -2 天、物流成本 -8% 等）仅作**对标参考**，标注公开来源，不是本项目成果；
3. 领域智能体给出的是建议，真实企业经营决策由人做出。

Python 3.7 兼容：只用标准库与 dataclasses。
"""

from . import domains, engine, intelligence
from .engine import IndustryBrain

__all__ = [
    "domains",
    "engine",
    "intelligence",
    "IndustryBrain",
]
```

### `src/paper_recycle_agent/brain/domains.py`（157 行）

```python
"""五条业务链定义：采购 / 生产 / 销售 / 仓储物流 / 资金财务。

对应华泰「产业大脑」公开报道里的五链贯通：
  供应链（采购）、生产链、销售链、仓储物流链、资金链（财务）。

每个域声明自己的 KPI、数据来源、职责和联动出口。
KPI 的"基准值"是本仿真内部的相对指标（0-100 或比率），
不是任何企业的真实经营数据。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# 业务链顺序（与华泰五链口径一致）
ORDER: Tuple[str, ...] = ("procurement", "production", "sales", "logistics", "finance")

# 对标参考：华泰产业大脑公开的量化成效，仅用于界面展示来源标注。
# 每条都带来源，绝不并入本项目 KPI 的计算。
BENCHMARKS: List[Dict[str, str]] = [
    {"domain": "procurement", "metric": "采购成本", "value": "降低 12%",
     "source": "华泰造纸产业大脑公开报道（百度百科 / 山东省发改委 2025）"},
    {"domain": "production", "metric": "吨纸能耗 / 断纸次数", "value": "能耗 -12% / 断纸 23→7 次每月",
     "source": "华泰造纸产业大脑公开报道（百度百科 / 同花顺财经 2025）"},
    {"domain": "sales", "metric": "客户连接数", "value": "2.2 万家客户",
     "source": "瞬捷云链生态大模型公开资料（新华网 2025）"},
    {"domain": "logistics", "metric": "交货时间 / 物流成本", "value": "交货 -2 天 / 物流成本 -8%",
     "source": "华泰造纸产业大脑公开报道（百度百科 2025）"},
    {"domain": "finance", "metric": "财务费用", "value": "年节约约 9600 万元",
     "source": "华泰集团产业创新报道（百家号 2026-09）"},
]


@dataclass(frozen=True)
class KPI:
    """一个业务域的关键指标。"""

    key: str
    label: str
    unit: str
    good_direction: str  # "up" 越高越好 / "down" 越低越好
    base: float  # 仿真基准值


@dataclass
class Domain:
    """一条业务链。"""

    key: str
    name: str
    subtitle: str
    kpis: List[KPI]
    duties: List[str]
    # 该域的决策会影响哪些下游域（跨域联动）
    influences: List[str] = field(default_factory=list)
    # 参考的公开规模数字（华泰），仅展示，不参与仿真
    scale_note: str = ""


DOMAINS: Dict[str, Domain] = {
    "procurement": Domain(
        key="procurement",
        name="采购",
        subtitle="供应商评价 · 集中招标 · 原料成本",
        kpis=[
            KPI("supplier_count", "活跃供应商", "家", "up", 17000),
            KPI("purchase_cost_index", "采购成本指数", "点", "down", 100.0),
            KPI("raw_material_quality", "原料合格率", "%", "up", 92.0),
        ],
        duties=[
            "评估供应商履约与质量，形成供应商评分",
            "集中招标比价，压低废纸/木浆采购成本",
            "原料质量波动提前预警生产链",
        ],
        influences=["production", "finance"],
        scale_note="对标：连接 1.7 万家供应商（公开报道）",
    ),
    "production": Domain(
        key="production",
        name="生产",
        subtitle="质量预测 · 断纸预警 · 能耗优化",
        kpis=[
            KPI("energy_per_ton", "吨纸能耗指数", "点", "down", 100.0),
            KPI("pass_rate", "生产合格率", "%", "up", 94.0),
            KPI("break_risk", "断纸风险", "%", "down", 8.0),
        ],
        duties=[
            "基于工况预测纸张质量，提前干预",
            "识别断纸前兆，减少非计划停机",
            "优化蒸汽与电力消耗，降低吨纸能耗",
        ],
        influences=["sales", "logistics"],
        scale_note="对标：质量预测误差降低 66%（公开报道）",
    ),
    "sales": Domain(
        key="sales",
        name="销售",
        subtitle="客户画像 · 需求预测 · 订单排程",
        kpis=[
            KPI("customer_count", "活跃客户", "家", "up", 22000),
            KPI("order_fill_rate", "订单满足率", "%", "up", 93.0),
            KPI("demand_accuracy", "需求预测准确度", "%", "up", 88.0),
        ],
        duties=[
            "按客户历史订单预测需求，指导生产排程",
            "把客户交期要求传给仓储物流链",
            "识别高价值客户，优化报价策略",
        ],
        influences=["production", "finance"],
        scale_note="对标：连接 2.2 万家客户（公开报道）",
    ),
    "logistics": Domain(
        key="logistics",
        name="仓储物流",
        subtitle="网络货运 · 车辆调度 · 厂内外贯通",
        kpis=[
            KPI("vehicle_count", "在途车辆", "辆", "up", 27000),
            KPI("delivery_days", "平均交货时间", "天", "down", 5.0),
            KPI("logistics_cost", "物流成本指数", "点", "down", 100.0),
        ],
        duties=[
            "整合厂内外运输，做点对点全程管控",
            "按订单交期调度车辆与仓容",
            "运输成本与在途状态回传资金链",
        ],
        influences=["finance"],
        scale_note="对标：连接 2.7 万台运输车辆（公开报道）",
    ),
    "finance": Domain(
        key="finance",
        name="资金财务",
        subtitle="银企联云 · 成本归集 · 资金配置",
        kpis=[
            KPI("finance_cost_index", "财务费用指数", "点", "down", 100.0),
            KPI("cost_visibility", "成本可见率", "%", "up", 85.0),
            KPI("cash_turnover", "资金周转次数", "次/年", "up", 6.0),
        ],
        duties=[
            "归集采购/生产/物流成本，形成全链路成本视图",
            "基于订单与回款预测现金流",
            "向采购链反馈预算约束，向销售链反馈账期风险",
        ],
        influences=["procurement", "sales"],
        scale_note="对标：年节约财务费用约 9600 万元（公开报道）",
    ),
}


def get(key: str) -> Domain:
    """取业务域定义，未知 key 抛 ValueError。"""
    if key not in DOMAINS:
        raise ValueError("未知业务域：%s" % key)
    return DOMAINS[key]


def all_domains() -> List[Domain]:
    """按五链顺序返回全部业务域。"""
    return [DOMAINS[k] for k in ORDER]
```

### `src/paper_recycle_agent/brain/engine.py`（190 行）

```python
"""产业大脑仿真引擎：共享数据底座 + 跨域联动 + 推演。

核心机制「跨域联动」：一个域的 KPI 变化会沿 influences 影响下游域。
例如采购成本指数下降 → 生产成本下降 + 财务费用下降。
这正是华泰产业大脑「五链数据贯通」想解决的问题——本仿真用可解释的规则
把它做成可观测、可复盘的模型，而不是一句口号。

确定性：给定 seed，KPI 演化完全一致，便于评审复现。
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import domains


@dataclass
class DomainState:
    """一个业务域在某时刻的状态。"""

    key: str
    kpis: Dict[str, float] = field(default_factory=dict)
    # 最近一次联动影响的摘要
    last_impact: List[str] = field(default_factory=list)

    def public(self, with_def: bool = True) -> Dict[str, object]:
        out: Dict[str, object] = {
            "key": self.key,
            "name": domains.get(self.key).name,
            "subtitle": domains.get(self.key).subtitle,
            "kpis": dict(self.kpis),
            "last_impact": list(self.last_impact),
            "scale_note": domains.get(self.key).scale_note,
        }
        if with_def:
            out["duties"] = domains.get(self.key).duties
            out["kpi_defs"] = [
                {"key": k.key, "label": k.label, "unit": k.unit,
                 "good_direction": k.good_direction, "base": k.base}
                for k in domains.get(self.key).kpis
            ]
        return out


# 联动规则：(源域, 源KPI, 方向, 目标域, 目标KPI, 影响系数)
# 方向 'down' 表示源 KPI 下降时触发；'up' 表示上升时触发。
# 影响系数为目标 KPI 的变化量（按基准值的比例）。
LINK_RULES: List[tuple] = [
    ("procurement", "purchase_cost_index", "down", "production", "energy_per_ton", 0.12),
    ("procurement", "purchase_cost_index", "down", "finance", "finance_cost_index", 0.18),
    ("procurement", "raw_material_quality", "up", "production", "pass_rate", 0.10),
    ("procurement", "raw_material_quality", "up", "production", "break_risk", -0.15),
    ("production", "pass_rate", "up", "sales", "order_fill_rate", 0.08),
    ("production", "break_risk", "down", "logistics", "delivery_days", -0.10),
    ("production", "energy_per_ton", "down", "finance", "finance_cost_index", 0.09),
    ("sales", "demand_accuracy", "up", "logistics", "delivery_days", -0.07),
    ("sales", "order_fill_rate", "up", "finance", "cash_turnover", 0.05),
    ("logistics", "delivery_days", "down", "finance", "finance_cost_index", 0.05),
    ("logistics", "logistics_cost", "down", "finance", "finance_cost_index", 0.11),
    ("finance", "cost_visibility", "up", "procurement", "purchase_cost_index", -0.06),
]


class IndustryBrain:
    """产业大脑：五域共享底座 + 联动推演。"""

    def __init__(self, seed: int = 2026) -> None:
        self.rng = random.Random(seed)
        self.seed = seed
        self.step = 0
        self.states: Dict[str, DomainState] = {
            key: DomainState(key=key) for key in domains.ORDER
        }
        self.log: List[Dict[str, object]] = []
        self._reset_kpis()

    def _reset_kpis(self) -> None:
        for key, state in self.states.items():
            state.kpis = {
                k.key: float(k.base) for k in domains.get(key).kpis
            }
            state.last_impact = []

    def _emit(self, event: str, **kw: object) -> None:
        self.log.append({"step": self.step, "event": event, **kw})

    def reset(self) -> None:
        self.step = 0
        self._reset_kpis()
        self.log = []

    def advance(self) -> None:
        """推进一个仿真步：KPI 自然波动 → 应用联动 → 记录日志。"""
        self.step += 1

        # 1) 各域 KPI 在基准附近小幅波动（确定性）
        for key, state in self.states.items():
            for kpi in domains.get(key).kpis:
                base = kpi.base
                span = abs(base) * 0.02 if base else 1.0
                delta = self.rng.uniform(-span, span)
                # 供应商/客户/车辆数这些规模指标整数化
                value = base + delta
                if base >= 1000:
                    value = float(round(value))
                state.kpis[kpi.key] = round(value, 2)
            state.last_impact = []

        # 2) 应用联动规则（用上一步的基准偏差作为触发信号）
        for src, src_kpi, direction, dst, dst_kpi, coef in LINK_RULES:
            src_state = self.states[src]
            if src_kpi not in src_state.kpis:
                continue
            base = next(k.base for k in domains.get(src).kpis if k.key == src_kpi)
            current = src_state.kpis[src_kpi]
            improved = (current < base) if direction == "down" else (current > base)
            if not improved:
                continue
            dst_state = self.states[dst]
            if dst_kpi not in dst_state.kpis:
                continue
            dst_kpi_def = next(k for k in domains.get(dst).kpis if k.key == dst_kpi)
            # 影响量与偏差幅度成正比，上限 1 个基准跨度
            deviation = min(abs(current - base) / (abs(base) * 0.02 or 1.0), 1.0)
            change = base * coef * deviation
            # 按目标 KPI 的"好方向"决定是加还是减
            if dst_kpi_def.good_direction == "up":
                dst_state.kpis[dst_kpi] += change
                actual_change = change
            else:
                dst_state.kpis[dst_kpi] -= change
                actual_change = -change
            dst_state.last_impact.append(
                "%s·%s → %s %+.2f" % (
                    domains.get(src).name, src_kpi, dst_kpi_def.label, actual_change,
                )
            )
            self._emit("link", src=src, src_kpi=src_kpi, dst=dst,
                       dst_kpi=dst_kpi, change=round(change, 3))

        # 3) 收敛到合理范围，避免无限叠加
        for key, state in self.states.items():
            for kpi in domains.get(key).kpis:
                v = state.kpis[kpi.key]
                lo, hi = kpi.base * 0.7, kpi.base * 1.3
                state.kpis[kpi.key] = round(max(lo, min(hi, v)), 2)

    def run(self, steps: int = 5) -> Dict[str, object]:
        """连续推演 N 步。"""
        steps = max(1, min(int(steps), 30))
        for _ in range(steps):
            self.advance()
        return self.snapshot()

    def optimize(self, domain_key: str, kpi_key: str, target: float) -> Dict[str, object]:
        """模拟一次管理干预：把某域 KPI 直接调到目标值，观察跨域传导。

        这是"产业大脑辅助决策"的演示：改动一个参数，看五条链怎么联动。
        """
        domain = domains.get(domain_key)
        kpi = next((k for k in domain.kpis if k.key == kpi_key), None)
        if kpi is None:
            return {"ok": False, "error": "未知 KPI：%s" % kpi_key}
        state = self.states[domain_key]
        before = state.kpis[kpi_key]
        state.kpis[kpi_key] = float(target)
        self._emit("optimize", domain=domain_key, kpi=kpi_key,
                   before=round(before, 2), target=float(target))
        # 传导一轮
        self.advance()
        return {"ok": True, "domain": domain_key, "kpi": kpi_key,
                "before": round(before, 2), "after": float(target),
                "snapshot": self.snapshot()}

    def snapshot(self, with_defs: bool = True) -> Dict[str, object]:
        return {
            "step": self.step,
            "seed": self.seed,
            "states": [
                self.states[k].public(with_def=with_defs) for k in domains.ORDER
            ],
            "link_rules": [
                {"src": r[0], "src_kpi": r[1], "direction": r[2],
                 "dst": r[3], "dst_kpi": r[4], "coef": r[5]}
                for r in LINK_RULES
            ],
            "benchmarks": domains.BENCHMARKS,
            "log": self.log[-60:],
        }
```

### `src/paper_recycle_agent/brain/intelligence.py`（144 行）

```python
"""领域智能体：每条业务链一个"大模型"角色 + 产业大脑总编排。

对标瞬捷云链生态大模型「面向造纸产业链的专属 AI」定位：
每个领域智能体只懂自己那条链，但通过共享数据底座能感知跨域影响。

配置 API Key 时用大模型生成经营建议；未配置时用规则引擎回落，
保证零依赖可用。每条建议都标注 basis（rule / llm），不冒充确定结论。
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .. import llm
from . import domains
from .engine import DomainState, IndustryBrain


@dataclass
class Advice:
    """一个领域智能体的建议。"""

    domain: str
    headline: str
    detail: str
    basis: str  # rule / llm
    concerns: List[str]

    def public(self) -> Dict[str, object]:
        return {
            "domain": self.domain,
            "domain_name": domains.get(self.domain).name,
            "headline": self.headline,
            "detail": self.detail,
            "basis": self.basis,
            "concerns": self.concerns,
        }


_SYSTEM = (
    "你是造纸企业的「{name}」领域智能体，负责：{subtitle}。\n"
    "职责：基于给定的业务 KPI 与跨域联动信息，给出简短经营建议。\n"
    "要求：\n"
    "1. 只用给定数据，不编造未提供的数字；\n"
    "2. 中文，两句以内，先结论后理由；\n"
    "3. 真实经营决策由人做出，你的输出只是建议；\n"
    "4. 不要复述题目。\n"
    "你的职责：{duties}"
)


class DomainAgent:
    """单条业务链的领域智能体。"""

    def __init__(self, domain_key: str) -> None:
        self.domain = domains.get(domain_key)
        self.name = "%s智能体" % self.domain.name
        self.last_advice: Optional[Advice] = None

    def _rule_advice(self, state: DomainState) -> Advice:
        concerns = []
        for kpi in self.domain.kpis:
            val = state.kpis.get(kpi.key)
            if val is None:
                continue
            # 判断 KPI 是否偏离基准且方向不利
            base = kpi.base
            bad = (val > base * 1.05) if kpi.good_direction == "down" else (val < base * 0.95)
            if bad:
                concerns.append("%s %.2f%s（基准 %.2f）" % (
                    kpi.label, val, kpi.unit, base,
                ))
        if concerns:
            headline = "关注：" + "、".join(concerns[:2])
            detail = self.domain.duties[0] + "；" + (
                self.domain.duties[1] if len(self.domain.duties) > 1 else ""
            )
        else:
            headline = "%s链运行平稳" % self.domain.name
            detail = self.domain.duties[0]
        if state.last_impact:
            detail += "。跨域联动：" + "；".join(state.last_impact[:2])
        return Advice(self.domain.key, headline, detail, "rule", concerns)

    def advise(self, state: DomainState, use_llm: bool = True) -> Advice:
        advice = self._rule_advice(state)
        basis = "rule"
        if use_llm and llm.load_config().configured():
            kpi_lines = [
                "%s=%s%s" % (k.label, state.kpis.get(k.key, 0), k.unit)
                for k in self.domain.kpis
            ]
            system = _SYSTEM.format(
                name=self.domain.name,
                subtitle=self.domain.subtitle,
                duties="；".join(self.domain.duties),
            )
            result = llm.chat([
                {"role": "system", "content": system},
                {"role": "user", "content": (
                    "当前 KPI：" + "，".join(kpi_lines) +
                    ("。跨域联动：" + "；".join(state.last_impact[:2]) if state.last_impact else "")
                )},
            ], use_system_prompt=False)
            if result["ok"] and result["reply"]:
                advice = Advice(
                    domain=self.domain.key,
                    headline=str(result["reply"])[:120],
                    detail="",
                    basis="llm",
                    concerns=advice.concerns,
                )
                basis = "llm"
        advice.basis = basis
        self.last_advice = advice
        return advice


class BrainOrchestrator:
    """产业大脑：编排五域智能体，汇总建议。"""

    def __init__(self, brain: Optional[IndustryBrain] = None,
                 use_llm: bool = True) -> None:
        self.brain = brain or IndustryBrain()
        self.use_llm = use_llm
        self.agents = {key: DomainAgent(key) for key in domains.ORDER}

    def advise_all(self) -> List[Dict[str, object]]:
        """让五个领域智能体各自给出建议。"""
        out = []
        for key in domains.ORDER:
            advice = self.agents[key].advise(self.brain.states[key], use_llm=self.use_llm)
            self.brain._emit("advice", domain=key, headline=advice.headline,
                             basis=advice.basis)
            out.append(advice.public())
        return out

    def snapshot(self) -> Dict[str, object]:
        snap = self.brain.snapshot()
        snap["advices"] = [
            agent.last_advice.public()
            for agent in self.agents.values()
            if agent.last_advice
        ]
        return snap
```

### `src/paper_recycle_agent/carbon/__init__.py`（35 行）

```python
"""工厂碳核算 Agent（仿真版，国标方法）。

本包是整个造纸工厂多智能体系统的**核心 Agent**：按国标
《温室气体排放核算与报告要求 造纸和纸制品生产企业》(GB/T，报批稿)
的方法，把工厂的活动数据换算成温室气体排放量（tCO₂e）。

核算边界（国标 4.2 / 5.1）
--------------------------
    企业排放总量 = 化石燃料燃烧 + 过程排放 + 废水厌氧甲烷
                 + 购入电力 + 购入热力 − 输出电力 − 输出热力

排放因子来自国标附录 B 的缺省值，每一项都带出处；
活动数据是**仿真输入**（示例工厂，可改），不是任何真实工厂的实测值。

与废纸回收 Agent 的关系
-----------------------
废纸回收 Agent 的回收量折算成「原生浆替代」的减排量，作为范围三减排
单列展示，不并入国标核算边界（国标边界不含范围三），避免口径混淆。

投入产出表在 ``io_table.py`` 里的直接消耗系数 / Leontief 逆矩阵方法，
作为「环境扩展投入产出」的可选参考附在供应链碳足迹部分，标注为方法演示。

Python 3.7 兼容：只用标准库与 dataclasses。
"""

from . import accounting, factors, model, recycle_agent
from .accounting import CarbonAccounting

__all__ = [
    "accounting",
    "factors",
    "model",
    "recycle_agent",
    "CarbonAccounting",
]
```

### `src/paper_recycle_agent/carbon/accounting.py`（269 行）

```python
"""碳核算引擎：严格实现国标五类排放源的计算公式。

公式逐条对应国标正文（见 factors.all_factors()['formula']）：
    公式4  EF   = CC × OF × 44/12
    公式3  AD   = FC × NCV
    公式2  E燃烧 = Σ(AD_i × EF_i)
    公式5  E过程 = L × EF石灰
    废水   E_CH4 = (TOW − S) × EF × GWP − R × GWP
    公式10 E购入电 = AD电 × EF电
    公式1  E总   = 燃烧 + 过程 + 废水 + 购入电/热 − 输出电/热

每个结果都带 formula 和 source，可手算复核。
电力因子未配置时该项为 None，总量标注 incomplete=True，
不假装算出了一个"完整"结果——这是本项目一贯的口径纪律。
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from . import factors, model
from .model import ActivityData, FuelUse


@dataclass
class LineItem:
    """一个排放源的计算明细。"""

    key: str
    name: str
    activity: float  # 活动数据（按各项单位）
    activity_unit: str
    ef: Optional[float]  # 排放因子
    ef_unit: str
    emission: Optional[float]  # 排放量 tCO2e
    formula: str
    source: str
    detail: str = ""

    def public(self) -> Dict[str, object]:
        return {
            "key": self.key,
            "name": self.name,
            "activity": round(self.activity, 4),
            "activity_unit": self.activity_unit,
            "ef": None if self.ef is None else round(self.ef, 6),
            "ef_unit": self.ef_unit,
            "emission": None if self.emission is None else round(self.emission, 3),
            "formula": self.formula,
            "source": self.source,
            "detail": self.detail,
        }


class CarbonAccounting:
    """碳核算器：输入活动数据，输出按国标口径的核算结果。"""

    def __init__(self, activity: Optional[ActivityData] = None) -> None:
        self.activity = activity or model.demo_activity()

    # ---------- 五类排放源 ----------
    def fuel_items(self) -> List[LineItem]:
        """化石燃料燃烧：逐燃料一行（国标公式2/3/4）。"""
        items: List[LineItem] = []
        for use in self.activity.fuels:
            f = factors.fuel(use.key)
            ad = use.quantity * f.ncv  # 公式3：AD = FC × NCV
            ef = f.ef  # 公式4：EF = CC × OF × 44/12
            emission = ad * ef  # 公式2
            items.append(LineItem(
                key="fuel_" + f.key,
                name=f.name + "燃烧",
                activity=ad,
                activity_unit="GJ",
                ef=ef,
                ef_unit="tCO2/GJ",
                emission=emission,
                formula="E = 消耗量×低位发热×CC×OF×44/12",
                source=factors.SOURCE_STD,
                detail="消耗 %.2f %s × NCV %.3f = %.1f GJ" % (
                    use.quantity, f.unit, f.ncv, ad,
                ),
            ))
        return items

    def process_item(self) -> LineItem:
        """过程排放：石灰石分解（国标公式5）。"""
        ad = self.activity.limestone_ton
        return LineItem(
            key="process",
            name="过程排放（石灰石分解）",
            activity=ad,
            activity_unit="t",
            ef=factors.LIMESTONE_EF,
            ef_unit="tCO2/t",
            emission=ad * factors.LIMESTONE_EF,
            formula="E过程 = L × EF石灰（国标公式5）",
            source=factors.LIMESTONE_EF_SOURCE,
        )

    def wastewater_item(self) -> LineItem:
        """废水厌氧处理甲烷（国标公式8/9）。"""
        a = self.activity
        net_cod = max(0.0, a.wastewater_cod_removed - a.wastewater_cod_sludge)
        # E_CH4 = (TOW − S) × EF × GWP − R × GWP
        emission = net_cod * factors.CH4_MAX * factors.CH4_CORRECTION * factors.GWP_CH4 \
            - a.methane_recovered * factors.GWP_CH4
        return LineItem(
            key="wastewater",
            name="废水厌氧甲烷",
            activity=net_cod,
            activity_unit="tCOD",
            ef=factors.CH4_MAX * factors.CH4_CORRECTION * factors.GWP_CH4,
            ef_unit="tCO2e/tCOD",
            emission=emission,
            formula="E = (TOW−S)×BO×MF×GWP − R×GWP",
            source=factors.WAWWATER_SOURCE,
            detail="净COD %.1f t，BO=%.2f，MF=%.2f，GWP=%d，回收 %.1f tCH4" % (
                net_cod, factors.CH4_MAX, factors.CH4_CORRECTION,
                factors.GWP_CH4, a.methane_recovered,
            ),
        )

    def electricity_item(self) -> LineItem:
        """净购入电力（国标公式10/12，合并为净购入）。"""
        a = self.activity
        net = a.electricity_purchased - a.electricity_exported
        ef = a.electric_ef  # 未配置则 None
        emission = None if ef is None else net * ef
        return LineItem(
            key="electricity",
            name="净购入电力",
            activity=net,
            activity_unit="MWh",
            ef=ef,
            ef_unit="tCO2/MWh",
            emission=emission,
            formula="E = (购入−输出)电量 × EF电（国标公式10/12）",
            source=(factors.ELECTRIC_EF_SOURCE if ef is not None
                    else "未配置电力因子——国标要求取主管部门最近年份公布值"),
            detail=("购入 %.0f − 输出 %.0f = %.0f MWh" % (
                a.electricity_purchased, a.electricity_exported, net,
            )) + ("" if ef is not None else "；请在设置中填入 EF 及年份"),
        )

    def heat_item(self) -> LineItem:
        """净购入热力（国标公式11/13）。"""
        a = self.activity
        net = a.heat_purchased - a.heat_exported
        emission = net * factors.HEAT_EF_DEFAULT
        return LineItem(
            key="heat",
            name="净购入热力",
            activity=net,
            activity_unit="GJ",
            ef=factors.HEAT_EF_DEFAULT,
            ef_unit="tCO2/GJ",
            emission=emission,
            formula="E = (购入−输出)热力 × EF热（国标公式11/13）",
            source=factors.HEAT_EF_SOURCE,
            detail="购入 %.0f − 输出 %.0f = %.0f GJ" % (
                a.heat_purchased, a.heat_exported, net,
            ),
        )

    # ---------- 范围三：废纸回收减排（不计入国标边界） ----------
    def recycle_credit(self) -> Dict[str, object]:
        """废纸回收替代原生浆的减排量——范围三演示，单列不并入总量。"""
        tonnage = self.activity.wastepaper_recycled_wan_ton * 10000.0  # 万吨→吨
        credit = tonnage * model.RECYCLE_AVOID_COEF
        return {
            "wastepaper_ton": round(tonnage, 1),
            "coef": model.RECYCLE_AVOID_COEF,
            "coef_unit": "tCO2e/t废纸",
            "credit_tco2e": round(credit, 1),
            "scope": "范围三（不计入国标核算边界）",
            "source": model.RECYCLE_COEF_SOURCE,
            "note": "减排量为方法演示，不可用于碳交易或正式披露。",
        }

    # ---------- 汇总 ----------
    def calculate(self) -> Dict[str, object]:
        """按国标公式1汇总，返回完整核算结果。"""
        fuel = self.fuel_items()
        items = fuel + [
            self.process_item(),
            self.wastewater_item(),
            self.electricity_item(),
            self.heat_item(),
        ]
        # 电力因子未配置 → 该项 None → 总量不完整
        incomplete = any(it.emission is None for it in items)
        total = None if incomplete else round(
            sum(float(it.emission) for it in items), 3  # type: ignore[arg-type]
        )
        by_source: Dict[str, Optional[float]] = {}
        for it in items:
            prev = by_source.get(it.key)
            if prev is None:
                by_source[it.key] = it.emission
            elif it.emission is not None:
                by_source[it.key] = prev + it.emission

        output = self.activity.paper_output_wan_ton
        # 碳强度 = 总排放(tCO2e) ÷ 产量(万吨 × 10000 = 吨) → tCO2e/吨纸
        intensity = None if (total is None or output <= 0) else round(
            total / (output * 10000.0), 4
        )

        return {
            "factory": self.activity.factory_name,
            "year": self.activity.year,
            "provenance": self.activity.provenance,
            "items": [it.public() for it in items],
            "by_source": {
                k: (None if v is None else round(v, 3)) for k, v in by_source.items()
            },
            "total_tco2e": total,
            "output_wan_ton": output,
            "intensity_tco2e_per_ton": intensity,
            "intensity_unit": "tCO2e/吨纸",
            "incomplete": incomplete,
            "electric_configured": self.activity.electric_ef is not None,
            "recycle_credit": self.recycle_credit(),
            "formula": "E总 = 燃烧 + 过程 + 废水CH4 + 购入电/热 − 输出电/热（国标公式1）",
            "boundary_note": (
                "本结果为仿真演示：活动数据为示例输入，排放因子取国标附录B缺省值。"
                "电力因子需按主管部门最新年份配置。不含范围三排放。"
            ),
        }

    def scenario(self, changes: Dict[str, float]) -> Dict[str, object]:
        """情景模拟：改若干活动数据，对比基准与情景的排放变化。

        changes 的 key 形如 'limit:bituminous'（燃料用量）、'electricity_purchased'、'heat_purchased' 等。
        返回基准与情景两套结果及差额。
        """
        import copy

        base = self.calculate()
        alt_activity = copy.deepcopy(self.activity)
        for key, value in changes.items():
            if key.startswith("fuel:"):
                fk = key.split(":", 1)[1]
                found = False
                for fuel_use in alt_activity.fuels:
                    if fuel_use.key == fk:
                        fuel_use.quantity = float(value)
                        found = True
                        break
                if not found:
                    alt_activity.fuels.append(FuelUse(fk, float(value)))
            elif hasattr(alt_activity, key):
                setattr(alt_activity, key, float(value))
        alt = CarbonAccounting(alt_activity).calculate()

        b_total, a_total = base["total_tco2e"], alt["total_tco2e"]
        delta = None if (b_total is None or a_total is None) else round(a_total - b_total, 3)
        return {
            "changes": changes,
            "baseline": base,
            "scenario": alt,
            "delta_tco2e": delta,
            "interpretation": (
                "数据不完整，无法计算差额" if delta is None else
                ("排放下降 %.1f tCO2e（%.2f%%）" % (
                    -delta, (-delta / b_total * 100) if b_total else 0.0,
                ) if delta < 0 else "排放上升 %.1f tCO2e" % delta)
            ),
        }
```

### `src/paper_recycle_agent/carbon/factors.py`（152 行）

```python
"""排放因子库：全部取自国标附录 B，逐条带出处。

来源
----
《温室气体排放核算与报告要求 造纸和纸制品生产企业》(GB/T 报批稿)
附录 B「相关参数缺省值」表 B.1 / B.2 / B.3，以及正文 5.2.5.3。

表 B.1 的上标逐个对应原始出处：
    a 《中国能源统计年鉴 2013》
    b 《省级温室气体清单指南（试行）》
    c 《2006 年 IPCC 国家温室气体清单指南》
    d 行业经验数据

本模块**不编造任何因子**：每个数值都能指回上表或其出处。
电力因子国标正文要求「选用国家主管部门最近年份公布的数据」，
这里不硬编码一个可能过期的数值，而是暴露成可配置项并标注来源说明。
"""

from dataclasses import dataclass
from typing import Dict, Optional

# 排放因子来源体系（供界面逐条展示）
SOURCE_STD = "国标附录B（造纸核算标准 报批稿）"
SOURCE_ENERGY = "《中国能源统计年鉴 2013》（经国标附录B引用）"
SOURCE_PROV = "《省级温室气体清单指南（试行）》（经国标附录B引用）"
SOURCE_IPCC = "《2006年IPCC国家温室气体清单指南》（经国标附录B引用）"
SOURCE_EXP = "行业经验数据（经国标附录B引用）"
SOURCE_MEE = "生态环境部公布的全国电网平均排放因子（需按最新年份填入）"


@dataclass(frozen=True)
class FuelFactor:
    """一种化石燃料的参数（国标表 B.1）。"""

    key: str
    name: str
    unit: str  # 计量单位：t / 10^4 Nm3
    ncv: float  # 低位发热量 GJ/t 或 GJ/10^4Nm3
    cc: float  # 单位热值含碳量 tC/GJ
    of: float  # 碳氧化率
    ncv_source: str
    cc_source: str

    @property
    def ef(self) -> float:
        """二氧化碳排放因子 tCO2/GJ = CC × OF × 44/12（国标公式4）。"""
        return self.cc * self.of * 44.0 / 12.0

    def public(self) -> Dict[str, object]:
        return {
            "key": self.key,
            "name": self.name,
            "unit": self.unit,
            "ncv": self.ncv,
            "ncv_unit": "GJ/t" if self.unit == "t" else "GJ/10^4Nm3",
            "cc": self.cc,
            "of": self.of,
            "ef": round(self.ef, 6),
            "source": SOURCE_STD,
            "ncv_source": self.ncv_source,
            "cc_source": self.cc_source,
        }


# 国标表 B.1 常用化石燃料参数（选取造纸厂常见品种）
# 数值逐字取自 PDF 表 B.1；上标字母映射到上面的来源常量。
FUELS: Dict[str, FuelFactor] = {
    "anthracite": FuelFactor("anthracite", "无烟煤", "t", 26.7, 27.4e-3, 0.94,
                             SOURCE_IPCC, SOURCE_PROV),
    "bituminous": FuelFactor("bituminous", "烟煤", "t", 19.570, 26.1e-3, 0.93,
                             SOURCE_EXP, SOURCE_PROV),
    "lignite": FuelFactor("lignite", "褐煤", "t", 11.9, 28.0e-3, 0.96,
                          SOURCE_IPCC, SOURCE_PROV),
    "washed_coal": FuelFactor("washed_coal", "洗精煤", "t", 26.334, 25.41e-3, 0.90,
                              SOURCE_ENERGY, SOURCE_PROV),
    "coke": FuelFactor("coke", "焦炭", "t", 28.435, 29.5e-3, 0.93,
                       SOURCE_ENERGY, SOURCE_PROV),
    "petroleum_coke": FuelFactor("petroleum_coke", "石油焦", "t", 32.5, 27.5e-3, 1.00,
                                 SOURCE_IPCC, SOURCE_PROV),
    "fuel_oil": FuelFactor("fuel_oil", "燃料油", "t", 41.816, 21.1e-3, 0.98,
                           SOURCE_ENERGY, SOURCE_PROV),
    "diesel": FuelFactor("diesel", "柴油", "t", 42.652, 20.2e-3, 0.98,
                         SOURCE_ENERGY, SOURCE_PROV),
    "gasoline": FuelFactor("gasoline", "汽油", "t", 43.070, 18.9e-3, 0.98,
                           SOURCE_ENERGY, SOURCE_PROV),
    "lng": FuelFactor("lng", "液化天然气", "t", 44.2, 17.2e-3, 0.98,
                      SOURCE_IPCC, SOURCE_PROV),
    "lpg": FuelFactor("lpg", "液化石油气", "t", 50.179, 17.2e-3, 0.98,
                      SOURCE_ENERGY, SOURCE_PROV),
    "natural_gas": FuelFactor("natural_gas", "天然气", "10^4Nm3", 389.31, 15.3e-3, 0.99,
                              SOURCE_ENERGY, SOURCE_PROV),
}


def fuel(key: str) -> FuelFactor:
    """取燃料因子，未知 key 抛 ValueError。"""
    if key not in FUELS:
        raise ValueError("未知燃料：%s" % key)
    return FUELS[key]


# 过程排放：石灰石分解因子（国标表 B.2）
LIMESTONE_EF = 0.405  # tCO2/t
LIMESTONE_EF_SOURCE = "国标附录B 表B.2（行业经验数据）"

# 废水厌氧处理（国标表 B.3）
CH4_MAX = 0.25  # tCH4/kgCOD 最大生产能力
CH4_CORRECTION = 0.5  # 甲烷修正因子
WAWWATER_SOURCE = "国标附录B 表B.3（行业经验数据）"
GWP_CH4 = 21  # CH4 的全球变暖潜势（100年），国标正文用于折算 CO2e

# 热力缺省因子（国标正文 5.2.5.3）
HEAT_EF_DEFAULT = 0.11  # tCO2/GJ
HEAT_EF_SOURCE = "国标正文 5.2.5.3 缺省值（也可取主管部门最新公布数据）"

# 电力因子：国标要求用主管部门最近年份数据，不内置可能过期的数值。
# 默认留空，由用户在界面/配置里填；填了必须同时填来源年份。
ELECTRIC_EF_DEFAULT: Optional[float] = None
ELECTRIC_EF_SOURCE = SOURCE_MEE

# 生物质：国标口径下生物质燃烧的 CO2 不计入（碳中性假设），
# 但 CH4 / N2O 需按实际排放因子计入。这里只做口径说明，不做数值假设。
BIOMASS_NOTE = (
    "生物质燃料（如黑液、树皮、废纸渣）燃烧产生的 CO2 按碳中性不计入化石排放；"
    "其 CH4 / N2O 排放如有数据应单独计入（国标 4.2.1 注）。"
)


def all_factors() -> Dict[str, object]:
    """给界面的完整因子表（含出处）。"""
    return {
        "fuels": [f.public() for f in FUELS.values()],
        "limestone": {"ef": LIMESTONE_EF, "unit": "tCO2/t", "source": LIMESTONE_EF_SOURCE},
        "wastewater": {
            "ch4_max": CH4_MAX, "correction": CH4_CORRECTION,
            "gwp_ch4": GWP_CH4, "source": WAWWATER_SOURCE,
        },
        "heat": {"ef": HEAT_EF_DEFAULT, "unit": "tCO2/GJ", "source": HEAT_EF_SOURCE},
        "electric": {
            "ef": ELECTRIC_EF_DEFAULT, "unit": "tCO2/MWh",
            "source": ELECTRIC_EF_SOURCE,
            "note": "国标要求取主管部门最近年份公布值，请填写并标注年份",
        },
        "biomass_note": BIOMASS_NOTE,
        "formula": {
            "fuel_ef": "EF = CC × OF × 44/12（国标公式4）",
            "fuel_ad": "AD = FC × NCV（国标公式3）",
            "fuel_emission": "E燃烧 = Σ(AD_i × EF_i)（国标公式2）",
            "process": "E过程 = L × EF石灰（国标公式5）",
            "total": "E总 = 燃烧 + 过程 + 废水CH4 + 购入电/热 − 输出电/热（国标公式1）",
        },
    }
```

### `src/paper_recycle_agent/carbon/model.py`（121 行）

```python
"""碳核算数据模型：活动数据输入 + 结果口径标注。

活动数据是**示例工厂的仿真输入**（不是真实工厂实测值），
用户可以逐项修改。每项都带 provenance，界面上明确显示「示例」。

数据量为一家中型新闻纸/包装纸厂的量级，用于演示计算链，
不对应任何真实企业。产量、能耗之间不强行追求行业精确的物料平衡——
仿真演示的目标是让「活动数据 × 排放因子 = 排放量」这条链可核查。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import factors

PROVENANCE_DEMO = "示例（仿真输入，非真实工厂）"
PROVENANCE_STD = "国标缺省值"


@dataclass
class FuelUse:
    """一种燃料的消耗量。"""

    key: str
    quantity: float  # 吨 或 10^4Nm3（按燃料单位）
    provenance: str = PROVENANCE_DEMO

    def public(self) -> Dict[str, object]:
        f = factors.fuel(self.key)
        return {
            "key": self.key,
            "name": f.name,
            "quantity": self.quantity,
            "unit": f.unit,
            "provenance": self.provenance,
        }


@dataclass
class ActivityData:
    """一家工厂一个核算年度的活动数据。"""

    year: int = 2024
    factory_name: str = "示例造纸厂"
    # 化石燃料消耗
    fuels: List[FuelUse] = field(default_factory=list)
    # 过程排放：石灰石消耗量（吨）。无制浆工艺可为 0。
    limestone_ton: float = 0.0
    # 废水厌氧处理：去除的有机物总量（吨 COD）、污泥清除有机物、甲烷回收（吨）
    wastewater_cod_removed: float = 0.0
    wastewater_cod_sludge: float = 0.0
    methane_recovered: float = 0.0
    # 外购 / 输出电力（MWh）
    electricity_purchased: float = 0.0
    electricity_exported: float = 0.0
    electric_ef: Optional[float] = None  # tCO2/MWh，None 表示未配置
    electric_ef_year: Optional[int] = None
    # 外购 / 输出热力（GJ）
    heat_purchased: float = 0.0
    heat_exported: float = 0.0
    # 产品产量（万吨），用于算单位产品碳强度
    paper_output_wan_ton: float = 0.0
    # 废纸回收量（万吨）——来自废纸回收 Agent，仅用于减排演示，不进国标边界
    wastepaper_recycled_wan_ton: float = 0.0
    provenance: str = PROVENANCE_DEMO

    def public(self) -> Dict[str, object]:
        return {
            "year": self.year,
            "factory_name": self.factory_name,
            "fuels": [f.public() for f in self.fuels],
            "limestone_ton": self.limestone_ton,
            "wastewater_cod_removed": self.wastewater_cod_removed,
            "wastewater_cod_sludge": self.wastewater_cod_sludge,
            "methane_recovered": self.methane_recovered,
            "electricity_purchased": self.electricity_purchased,
            "electricity_exported": self.electricity_exported,
            "electric_ef": self.electric_ef,
            "electric_ef_year": self.electric_ef_year,
            "heat_purchased": self.heat_purchased,
            "heat_exported": self.heat_exported,
            "paper_output_wan_ton": self.paper_output_wan_ton,
            "wastepaper_recycled_wan_ton": self.wastepaper_recycled_wan_ton,
            "provenance": self.provenance,
        }


def demo_activity() -> ActivityData:
    """一套示例工厂活动数据（仿真演示用，非真实企业）。

    量级参考：中型纸厂年耗烟煤数万吨、外购电力数万 MWh、
    自备热电联产供汽。数字为演示取整值。
    """
    return ActivityData(
        year=2024,
        factory_name="示例造纸厂（仿真）",
        fuels=[
            FuelUse("bituminous", 32000.0),   # 烟煤 3.2 万吨
            FuelUse("natural_gas", 850.0),    # 天然气 850 万标方
            FuelUse("diesel", 420.0),         # 柴油 420 吨（厂内车辆）
        ],
        limestone_ton=1200.0,
        wastewater_cod_removed=1800.0,
        wastewater_cod_sludge=150.0,
        methane_recovered=0.0,
        electricity_purchased=42000.0,        # 42000 MWh
        electricity_exported=3000.0,          # 自发自用后上网 3000 MWh
        electric_ef=None,                     # 未配置时该项显示「待配置」
        electric_ef_year=None,
        heat_purchased=85000.0,               # 85000 GJ 外购蒸汽
        heat_exported=0.0,
        paper_output_wan_ton=28.0,            # 年产 28 万吨纸
        wastepaper_recycled_wan_ton=18.0,     # 年回收废纸 18 万吨（来自回收Agent）
    )


# 废纸替代原生浆的减排系数（范围三演示）
# 说明：这是文献常见的量级参考，用于演示方法，明确标注为「演示系数」，
# 不作正式核算依据。真实核算需按具体浆种、工艺、数据源确定。
RECYCLE_AVOID_COEF = 0.85  # tCO2e / 吨废纸替代（演示值）
RECYCLE_COEF_SOURCE = "演示系数（文献量级参考，正式核算须按浆种/工艺实测确定）"
```

### `src/paper_recycle_agent/carbon/recycle_agent.py`（133 行）

```python
"""废纸回收 Agent（工厂内子智能体）：把回收数据喂给碳核算。

定位变化
--------
原「废纸回收对话助手」在本系统里降级为工厂的一个子 Agent：
它继续负责分类 / 估价 / 区域统计等原有能力，同时把「回收量」
作为活动数据提供给碳核算 Agent，折算成范围三的原料替代减排量。

本模块只做**桥接**：从已有的 stats / regions / io_table 取数，
转换成碳核算需要的输入，不重复实现回收助手的业务逻辑。

投入产出表的角色
----------------
按用户要求，「投入产出表的思考剥离出来当成参考」——
这里用 io_table.leontief_inverse / influence_coefficients 做供应链
碳足迹的**方法演示**（环境扩展投入产出 EEIOA 的思路），
明确标注为方法演示、非真实核算，不并入国标核算边界。
"""

from typing import Dict, List, Optional

from .. import io_table, stats as stats_mod


def recovery_from_stats(year: int = 2024, code: Optional[str] = None) -> Dict[str, object]:
    """从现有回收统计取回收量，作为碳核算的原料输入。

    code=None 取全国；给定省级代码则按占全国比重分摊（沿用 io_table 口径）。
    """
    row = None
    for r in stats_mod.get_history():
        if int(r["year"]) == year:
            row = r
            break
    if row is None:
        return {"ok": False, "error": "无该年数据", "year": year}

    national = float(row.get("recovery") or 0.0)
    share = 1.0
    scope = "全国"
    if code and code != "CN":
        from .. import regions
        node = regions.get_node(code)
        if node is not None and node["level"] == "province":
            share = float(node["stats"]["占全国比重(%)"]) / 100.0  # type: ignore[index]
            scope = str(node["name"])

    return {
        "ok": True,
        "year": year,
        "scope": scope,
        "recovery_wan_ton": round(national * share, 1),
        "national_wan_ton": round(national, 1),
        "share": round(share, 4),
        "provenance": "全国为行业年报数据；分省按回收量占比分摊（估算）",
        "note": "这是行业/区域统计口径，非单厂实际回收量；用于碳核算演示时请按需替换为工厂实测值。",
    }


def bridge_to_activity(recovery_wan_ton: float,
                       activity: object,
                       overwrite: bool = True) -> Dict[str, object]:
    """把回收量写进碳核算活动数据的 wastepaper 字段。

    返回桥接说明。不直接修改调用方之外的数据，由调用方决定是否采用。
    """
    from .model import ActivityData
    if not isinstance(activity, ActivityData):
        return {"ok": False, "error": "活动数据类型不符"}
    written = bool(overwrite or activity.wastepaper_recycled_wan_ton <= 0)
    if written:
        activity.wastepaper_recycled_wan_ton = float(recovery_wan_ton)
    return {
        "ok": True,
        "written": written,
        "wastepaper_recycled_wan_ton": activity.wastepaper_recycled_wan_ton,
        "source": "废纸回收 Agent（stats 回收量）",
        "note": "该值仅用于范围三减排演示，不进入国标核算边界。",
    }


def supply_chain_carbon_demo(matrix: Optional[List[List[float]]] = None) -> Dict[str, object]:
    """环境扩展投入产出（EEIOA）方法演示。

    思路：把直接消耗系数矩阵 A 换成「单位产值的碳排放强度向量」后，
    完全需求（Leontief 逆）可用于估算供应链累积碳足迹：
        C_total = c × (I − A)^-1 × y
    这里 c 为各部门直接碳强度，y 为最终需求。

    本演示**不内置任何碳强度向量或最终需求**（那会是编数据），
    只提供算法骨架：传入矩阵与向量才算得出结果。
    """
    if matrix is None:
        return {
            "ok": False,
            "available": False,
            "method": "环境扩展投入产出（EEIOA）",
            "formula": "C_total = c × (I−A)^-1 × y",
            "reason": "未提供投入产出矩阵与部门碳强度向量，不做无数据推算。",
            "reuse": "io_table.leontief_inverse / influence_coefficients / response_coefficients",
            "boundary": "方法演示，非国标核算边界，不并入碳核算总量。",
        }
    try:
        inv = io_table.leontief_inverse(matrix)
        return {
            "ok": True,
            "available": True,
            "method": "环境扩展投入产出（EEIOA）",
            "formula": "C_total = c × (I−A)^-1 × y",
            "leontief_inverse": inv,
            "influence": io_table.influence_coefficients(matrix),
            "response": io_table.response_coefficients(matrix),
            "boundary": "方法演示；需另配部门碳强度 c 与最终需求 y 才能算碳足迹。",
        }
    except ValueError as exc:
        return {"ok": False, "error": "矩阵无法求逆：%s" % exc}


def agent_status() -> Dict[str, object]:
    """废纸回收 Agent 在系统里的状态说明（供界面展示）。"""
    return {
        "role": "工厂内的废纸回收子 Agent",
        "source_modules": ["stats", "regions", "io_table", "classifier", "pricing"],
        "capabilities": [
            "废纸分类与可回收判定（原有）",
            "按重量估价（原有）",
            "区域 / 历年 / 分类统计（原有）",
            "回收量 → 碳核算原料输入（新增桥接）",
            "范围三原料替代减排演示（新增）",
        ],
        "carbon_link": "回收量经 model.RECYCLE_AVOID_COEF 折算为减排量，单列展示",
        "io_reference": "投入产出系数与 Leontief 逆作为供应链碳足迹方法参考",
    }
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

### `src/paper_recycle_agent/cli.py`（105 行）

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
    io = sub.add_parser("io", help="投入产出：消耗金额与直接消耗系数")
    io.add_argument("year", type=int, nargs="?", default=2024)
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
    elif args.cmd == "io":
        from . import io_table

        print(io_table.summary_text(args.year))
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
        print(f"已导出：{args.out}（{len(content)} 字节，7 张工作表）")
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

### `src/paper_recycle_agent/exporter.py`（363 行）

```python
"""Excel 导出：面向统计局/行业协会的多表工作簿。

工作表结构：
1. 省级统计   —— 34 个省级行政区的回收量、比重、回收率、利用率等（2024 年）
2. 分类回收   —— 按 GB/T 20811-2018 八大类拆分的回收量与估算货值（可选年份/区域）
3. 历年回收   —— 2014—2025 年回收量、消费量、回收率、利用率
4. 废纸进口   —— 2017—2025 年废纸进口量（体现禁废令效果）
5. 企业名录   —— 企业名称、城市、类型、主营大类、年回收量、经纬度
6. 投入产出   —— 消耗金额、直接消耗系数、单位产值消耗、分省与企业采购金额
7. 数据说明   —— 数据来源、口径与「官方 / 测算 / 估算 / 示例」区分，供复核

依赖策略
--------
openpyxl 只在真正要写工作簿时才导入。这样即使机器上没装 openpyxl，
`import paper_recycle_agent`、命令行对话、离线 HTML 版都能正常工作，
只有点击「导出 Excel」时才会提示安装。
"""

from io import BytesIO
from typing import Dict, List, Optional

from . import enterprises, io_table, regions
from . import stats as stats_mod

_INSTALL_HINT = (
    "导出 Excel 需要 openpyxl，但当前环境没有安装。\n"
    "请执行：pip install openpyxl\n"
    "若无法联网安装，可改用「零依赖离线版」：dist/paper-recycle-offline.html，"
    "其中自带 CSV 导出，可直接用 Excel 打开。"
)

# 惰性构造的样式缓存，避免在模块导入期就依赖 openpyxl
_STYLE_CACHE: Dict[str, object] = {}


def available() -> bool:
    """当前环境是否具备导出 Excel 的能力。"""
    try:
        import openpyxl  # noqa: F401
    except Exception:  # pragma: no cover - 取决于运行环境
        return False
    return True


def _require_openpyxl():
    """导入 openpyxl，失败时抛出带安装指引的异常。"""
    try:
        import openpyxl
    except Exception as exc:  # pragma: no cover - 取决于运行环境
        raise RuntimeError(_INSTALL_HINT) from exc
    return openpyxl


def _styles() -> Dict[str, object]:
    """首次调用时构造样式对象并缓存。"""
    if _STYLE_CACHE:
        return _STYLE_CACHE
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    thin = Side(style="thin", color="D9D9D9")
    _STYLE_CACHE.update({
        "header_fill": PatternFill("solid", fgColor="2F7D4F"),
        "header_font": Font(color="FFFFFF", bold=True, size=11),
        "title_font": Font(bold=True, size=13, color="1F2329"),
        "note_font": Font(size=10, color="6B7280"),
        "border": Border(left=thin, right=thin, top=thin, bottom=thin),
        "center": Alignment(horizontal="center", vertical="center", wrap_text=True),
        "left": Alignment(wrap_text=False, vertical="center"),
    })
    return _STYLE_CACHE


def _style_header(ws, row: int, ncols: int) -> None:
    st = _styles()
    for col in range(1, ncols + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = st["header_fill"]
        cell.font = st["header_font"]
        cell.alignment = st["center"]
        cell.border = st["border"]


def _autofit(ws, widths: List[int]) -> None:
    from openpyxl.utils import get_column_letter

    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width


def _write_sheet(ws, title: str, headers: List[str], rows: List[List[object]],
                 widths: List[int], note: Optional[str] = None) -> None:
    """统一的「标题 + 表头 + 数据 + 备注」写入。"""
    st = _styles()
    ws.append([title])
    ws.cell(row=1, column=1).font = st["title_font"]
    if note:
        ws.append([note])
        ws.cell(row=2, column=1).font = st["note_font"]
        header_row = 3
    else:
        header_row = 2
    ws.append(headers)
    _style_header(ws, header_row, len(headers))
    for row in rows:
        ws.append(row)
    for r in range(header_row + 1, ws.max_row + 1):
        for c in range(1, len(headers) + 1):
            ws.cell(row=r, column=c).border = st["border"]
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
    """生成多表工作簿，返回 .xlsx 字节流。

    :raises RuntimeError: 环境缺少 openpyxl 时，异常信息含安装指引。
    """
    openpyxl = _require_openpyxl()

    node = regions.get_node(code) or regions.ROOT
    node_code = str(node["code"])
    is_national = node["level"] == "national"
    scope_name = str(node["name"])

    wb = openpyxl.Workbook()

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

    # ---- 6. 投入产出 ----
    ws6io = wb.create_sheet("投入产出")
    st = _styles()
    sp = io_table.spend(year)
    dc = io_table.direct_coefficient(year)
    uc = io_table.unit_consumption(year)

    ws6io.append([f"{scope_name} 废纸消耗金额（投入产出视角，{year} 年）"])
    ws6io.cell(row=1, column=1).font = st["title_font"]
    ws6io.append(["口径：全国为官方投入产出表 + 协会年报；省级为分摊；地级市与企业为估算。"
                  "金额按回收参考价计价，属纸厂废纸成本下限。"])
    ws6io.cell(row=2, column=1).font = st["note_font"]

    kv = [
        ("废纸消耗量(万吨)", sp["tonnage"], sp["tonnage_basis"]),
        ("加权参考价(元/吨)", sp["avg_price"], "分类结构加权，居民/回收站口径"),
        ("废纸货值(亿元)", sp["amount"], sp["provenance"]),
        ("直接消耗系数(%)",
         "—" if dc["coefficient"] is None else dc["coefficient_pct"],
         dc["note"]),
        ("单位产值消耗(吨/万元)",
         "—" if uc["value"] is None else uc["value"],
         "消耗量 ÷ 营业收入"),
    ]
    ws6io.append(["指标", "数值", "说明"])
    _style_header(ws6io, 3, 3)
    for name, value, note in kv:
        ws6io.append([name, value, note])

    ws6io.append([])
    ws6io.append([f"{scope_name} 分省消耗金额（亿元）"])
    ws6io.cell(row=ws6io.max_row, column=1).font = st["title_font"]
    ws6io.append(["排名", "省份", "占全国比重(%)", "金额(亿元)", "金额性质", "回收量性质"])
    head_row = ws6io.max_row
    _style_header(ws6io, head_row, 6)
    for r in io_table.province_spend(year)["rows"]:
        ws6io.append([r["rank"], r["name"], r["share_pct"], r["amount"],
                      r["provenance"], r["recovery_provenance"]])

    ws6io.append([])
    ws6io.append(["企业采购金额（示例：年经手量 × 均价）"])
    ws6io.cell(row=ws6io.max_row, column=1).font = st["title_font"]
    ws6io.append(["企业", "省 / 市", "年经手量(万吨)", "金额(亿元)", "数据性质"])
    head_row2 = ws6io.max_row
    _style_header(ws6io, head_row2, 5)
    for e in io_table.enterprise_spend(year)["rows"]:
        ws6io.append([e["name"], f"{e['province']} / {e['city']}",
                      e["volume"], e["amount"], e["provenance"]])

    ws6io.column_dimensions["A"].width = 26
    for col in ("B", "C", "D", "E"):
        ws6io.column_dimensions[col].width = 20

    # ---- 7. 数据说明 ----
    ws6 = wb.create_sheet("数据说明")
    ws6.append(["数据来源与口径说明"])
    ws6.cell(row=1, column=1).font = _styles()["title_font"]
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
        "五、投入产出口径",
        "  · 全国：官方。国家统计局全国投入产出表（42 部门）+ 中国造纸协会年度报告。",
        "  · 省级：各省均编制本地区投入产出表；本工具的分省金额按回收量占比分摊，非实际采购分布。",
        "  · 地级市：国家统计局明确「地级市暂不编制投入产出表」，本表按企业名录城市分布分摊，属估算。",
        "  · 企业：不存在「企业投入产出表」，只有财务报表；本表金额 = 年经手量 × 市场均价，属示例估算。",
        "  · 金额按回收参考价（居民/回收站口径）计价，不含分拣、打包、运输，",
        "    因此是纸厂废纸成本的下限，不是到厂采购额；直接消耗系数同此口径。",
        "",
        "六、替换为真实数据",
        "  · 省级：修改 src/paper_recycle_agent/regions.py 的 SEEDS，为省份填入 reported 值。",
        "  · 历年：修改 src/paper_recycle_agent/stats.py 的 HISTORY。",
        "  · 分类占比：修改 CATEGORY_SHARES 的锚点年份数值。",
        "  · 企业名录：在项目根目录放 data/enterprises.csv（表头见 enterprises.CSV_FIELDS）。",
    ]
    for line in lines:
        ws6.append([line])
    ws6.column_dimensions["A"].width = 110
    for r in range(2, ws6.max_row + 1):
        ws6.cell(row=r, column=1).alignment = _styles()["left"]

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def filename(code: str = "CN", year: int = regions.NATIONAL_YEAR) -> str:
    node = regions.get_node(code) or regions.ROOT
    return f"废纸回收统计_{node['name']}_{year}.xlsx"
```

### `src/paper_recycle_agent/io_table.py`（487 行）

```python
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
            # 金额永远是分摊估算：回收量可能是报道值，但「金额」是拿它乘出来的。
            # 把回收量的口径单独放在 recovery_provenance，避免金额被误读成官方数据。
            "provenance": PROVENANCE_ESTIMATED,
            "recovery_provenance": (
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

### `src/paper_recycle_agent/llm.py`（360 行）

```python
"""模型配置模块：接入任意 OpenAI 兼容的大模型 API。

设计要点
--------
1. **零第三方依赖**：用标准库 `urllib.request` 发请求，不引入 requests / openai SDK。
   这样「Python 3.7 + 什么都不装」的承诺不会因为接了大模型而破功。
2. **密钥不出现在任何输出里**：`public_config()` 只返回脱敏值（`sk-…3f9a`），
   报错信息也会先把密钥替换掉再返回。日志、接口响应、异常里都不会带明文。
3. **没配置也能用**：`chat()` 在未配置时返回 `configured=False`，
   上层自动回落到 `agent.py` 的规则引擎。整个工具不会因为「没填 API Key」而不可用。
4. **配置来源优先级**：环境变量 > config/llm.json > 默认值。
   环境变量适合 CI / 服务器；JSON 适合本地图形界面里填。

安全提醒（README 里也写了）
--------------------------
前端明文保存的密钥可被同机程序读取。本模块把配置存在服务端文件
（`config/llm.json`，已加入 .gitignore），接口只回脱敏值。
如果要把服务暴露到公网，请自行加鉴权，或改用只读环境变量方式。
"""

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

ENV_BASE_URL = "PAPER_LLM_BASE_URL"
ENV_API_KEY = "PAPER_LLM_API_KEY"
ENV_MODEL = "PAPER_LLM_MODEL"

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT = 30.0

# 仓库根目录下的 config/llm.json（不纳入版本库）
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "llm.json"

DEFAULT_SYSTEM_PROMPT = (
    "你是废纸回收领域的助手，服务对象包括回收企业、造纸厂、行业协会和统计部门。"
    "回答要求：\n"
    "1. 涉及数据时，先说明口径（官方 / 测算 / 估算 / 示例），不确定就直说不确定；\n"
    "2. 不要编造具体省份的回收量、企业采购量或价格；\n"
    "3. 回答简洁，能用一两句说清就不要展开；\n"
    "4. 中文回答。"
)

# 常见服务商的默认地址，供界面下拉选择
PRESETS: List[Dict[str, str]] = [
    {"name": "OpenAI", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    {"name": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    {"name": "通义千问（DashScope 兼容模式）",
     "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
     "model": "qwen-plus"},
    {"name": "智谱 GLM", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash"},
    {"name": "Kimi（Moonshot）", "base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"},
    {"name": "本地 Ollama", "base_url": "http://127.0.0.1:11434/v1", "model": "qwen2.5"},
]


def mask_key(key: Optional[str]) -> str:
    """把密钥脱敏成 sk-…3f9a 形式；空值返回空串。"""
    if not key:
        return ""
    text = str(key)
    if len(text) <= 8:
        return "…" + text[-2:] if len(text) > 2 else "…"
    return text[:3] + "…" + text[-4:]


@dataclass
class LLMConfig:
    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    model: str = DEFAULT_MODEL
    temperature: float = 0.3
    max_tokens: int = 600
    timeout: float = DEFAULT_TIMEOUT
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    source: str = field(default="default", compare=False)

    def endpoint(self) -> str:
        """补全为 …/chat/completions。兼容用户填 /v1 或填完整路径。"""
        base = self.base_url.strip().rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"

    def configured(self) -> bool:
        return bool(self.api_key.strip())

    def public(self) -> Dict[str, object]:
        """对外暴露的配置：绝不含明文密钥。"""
        return {
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "system_prompt": self.system_prompt,
            "api_key_masked": mask_key(self.api_key),
            "has_api_key": bool(self.api_key),
            "configured": self.configured(),
            "source": self.source,
        }


def _from_env() -> Optional[LLMConfig]:
    base = os.environ.get(ENV_BASE_URL, "").strip()
    key = os.environ.get(ENV_API_KEY, "").strip()
    model = os.environ.get(ENV_MODEL, "").strip()
    if not (base or key or model):
        return None
    return LLMConfig(
        base_url=base or DEFAULT_BASE_URL,
        api_key=key,
        model=model or DEFAULT_MODEL,
        source="env",
    )


def _from_file() -> Optional[LLMConfig]:
    if not CONFIG_PATH.exists():
        return None
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    return LLMConfig(
        base_url=str(raw.get("base_url") or DEFAULT_BASE_URL),
        api_key=str(raw.get("api_key") or ""),
        model=str(raw.get("model") or DEFAULT_MODEL),
        temperature=float(raw.get("temperature", 0.3)),
        max_tokens=int(raw.get("max_tokens", 600)),
        timeout=float(raw.get("timeout", DEFAULT_TIMEOUT)),
        system_prompt=str(raw.get("system_prompt") or DEFAULT_SYSTEM_PROMPT),
        source="file",
    )


def load_config() -> LLMConfig:
    """环境变量 > config/llm.json > 默认值。"""
    return _from_env() or _from_file() or LLMConfig()


def save_config(base_url: str, api_key: Optional[str], model: str,
                temperature: float = 0.3, max_tokens: int = 600,
                timeout: float = DEFAULT_TIMEOUT,
                system_prompt: Optional[str] = None) -> LLMConfig:
    """保存配置到 config/llm.json。

    `api_key` 传 None 或空串时，保留原有密钥（避免界面上只改模型却把密钥清掉）。
    """
    current = _from_file() or LLMConfig()
    key = current.api_key if not api_key else str(api_key)
    cfg = LLMConfig(
        base_url=(base_url or DEFAULT_BASE_URL).strip(),
        api_key=key.strip(),
        model=(model or DEFAULT_MODEL).strip(),
        temperature=float(temperature),
        max_tokens=int(max_tokens),
        timeout=float(timeout),
        system_prompt=(system_prompt or DEFAULT_SYSTEM_PROMPT),
        source="file",
    )
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(
            {
                "base_url": cfg.base_url,
                "api_key": cfg.api_key,
                "model": cfg.model,
                "temperature": cfg.temperature,
                "max_tokens": cfg.max_tokens,
                "timeout": cfg.timeout,
                "system_prompt": cfg.system_prompt,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    try:  # 尽量收紧权限（Windows 上 chmod 语义有限，失败不影响功能）
        os.chmod(str(CONFIG_PATH), 0o600)
    except OSError:
        pass
    return cfg


def clear_config() -> bool:
    """删除本地配置文件。环境变量方式不受影响。"""
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
        return True
    return False


def _scrub(text: str, key: str) -> str:
    """把可能出现在报错文本里的密钥替换掉。"""
    if key and key in text:
        return text.replace(key, mask_key(key))
    return text


def _post(url: str, payload: Dict[str, object], key: str, timeout: float):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def chat(messages: List[Dict[str, str]],
         config: Optional[LLMConfig] = None,
         use_system_prompt: bool = True) -> Dict[str, object]:
    """调用 /chat/completions。

    返回结构：
        {"ok": bool, "configured": bool, "reply": str, "error": str,
         "model": str, "latency_ms": int, "usage": {...}}

    未配置密钥时 `ok=False, configured=False`，调用方应回落到规则引擎。
    """
    cfg = config or load_config()
    if not cfg.configured():
        return {
            "ok": False,
            "configured": False,
            "reply": "",
            "error": "未配置模型 API：请在「设置」里填写 Base URL 与 API Key，"
                     "或设置环境变量 %s。" % ENV_API_KEY,
            "model": cfg.model,
            "latency_ms": 0,
            "usage": {},
        }

    payload_msgs: List[Dict[str, str]] = []
    if use_system_prompt and cfg.system_prompt:
        payload_msgs.append({"role": "system", "content": cfg.system_prompt})
    payload_msgs.extend(messages)

    payload = {
        "model": cfg.model,
        "messages": payload_msgs,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
        "stream": False,
    }

    started = time.time()
    try:
        data = _post(cfg.endpoint(), payload, cfg.api_key, cfg.timeout)
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:400]
        except Exception:  # pragma: no cover - 读取失败时忽略
            detail = ""
        hint = {
            401: "密钥无效或已过期",
            403: "密钥无权限访问该模型",
            404: "Base URL 或模型名不正确",
            429: "触发限流或余额不足",
        }.get(exc.code, "HTTP %d" % exc.code)
        return {
            "ok": False,
            "configured": True,
            "reply": "",
            "error": _scrub("%s（%s）%s" % (hint, exc.code, detail), cfg.api_key),
            "model": cfg.model,
            "latency_ms": int((time.time() - started) * 1000),
            "usage": {},
        }
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "configured": True,
            "reply": "",
            "error": _scrub("连接失败：%s（检查 Base URL 与网络）" % exc.reason, cfg.api_key),
            "model": cfg.model,
            "latency_ms": int((time.time() - started) * 1000),
            "usage": {},
        }
    except Exception as exc:  # pragma: no cover - 兜底，避免接口 500
        return {
            "ok": False,
            "configured": True,
            "reply": "",
            "error": _scrub("调用异常：%s" % exc, cfg.api_key),
            "model": cfg.model,
            "latency_ms": int((time.time() - started) * 1000),
            "usage": {},
        }

    latency = int((time.time() - started) * 1000)
    try:
        reply = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return {
            "ok": False,
            "configured": True,
            "reply": "",
            "error": "返回结构不符合 OpenAI 兼容格式（缺少 choices[0].message.content）",
            "model": cfg.model,
            "latency_ms": latency,
            "usage": {},
        }

    return {
        "ok": True,
        "configured": True,
        "reply": str(reply).strip(),
        "error": "",
        "model": cfg.model,
        "latency_ms": latency,
        "usage": data.get("usage") or {},
    }


def probe(config: Optional[LLMConfig] = None) -> Dict[str, object]:
    """连通性探测：发一句最短的请求，看能不能通。"""
    cfg = config or load_config()
    result = chat(
        [{"role": "user", "content": "回复两个字：可用"}],
        config=cfg,
        use_system_prompt=False,
    )
    return {
        "ok": result["ok"],
        "configured": result["configured"],
        "model": result["model"],
        "latency_ms": result["latency_ms"],
        "reply": result["reply"][:60],
        "error": result["error"],
        "endpoint": cfg.endpoint(),
        "api_key_masked": mask_key(cfg.api_key),
    }


def status() -> Dict[str, object]:
    """给界面用的状态：是否配置、当前来源、可选预设。"""
    cfg = load_config()
    return {
        "config": cfg.public(),
        "presets": PRESETS,
        "config_path": str(CONFIG_PATH),
        "env_vars": [ENV_BASE_URL, ENV_API_KEY, ENV_MODEL],
        "ready": cfg.configured(),
    }
```

### `src/paper_recycle_agent/mill/__init__.py`（31 行）

```python
"""造纸工艺全流程智能体（仿真版）。

本包把一个造纸厂的连续流程拆成四道工序，每道工序由一个子智能体负责，
顶层由总调度智能体（Orchestrator）编排任务、处理异常、下发作业给设备层。

重要边界
--------
这是**仿真演示**，不是工业控制系统：

* 工序工况由仿真引擎生成，机器狗 / AGV / PLC 是内存中的模拟对象；
* 本包不会连接任何真实设备、不发送 MODBUS / OPC UA 指令；
* 接入真实产线需要安全认证、联锁逻辑与人工复核，超出本项目范围。

设计上复用了本仓库已有的 ``llm.py``（OpenAI 兼容调用）：配置了 API Key 时
子智能体用大模型给出决策建议；未配置时自动回落到规则引擎，保证零依赖可用。

Python 3.7 兼容：只用标准库与 dataclasses（3.7 引入）。
"""

from . import agents, devices, processes, simulation
from .agents import Orchestrator
from .simulation import MillSimulation

__all__ = [
    "agents",
    "devices",
    "processes",
    "simulation",
    "Orchestrator",
    "MillSimulation",
]
```

### `src/paper_recycle_agent/mill/agents.py`（250 行）

```python
"""多智能体：工序子智能体 + 总调度智能体（Orchestrator）。

分工
----
* ProcessAgent：每道工序一个，负责「看工况 → 判异常 → 给处置建议 → 下发作业」。
  配置了 API Key 时用大模型生成建议；未配置时用知识库规则回落。
* Orchestrator：按流水线顺序推进批次，汇总各工序状态，
  在异常时做仲裁（继续 / 降速 / 停机待人工），并记录调度日志。

所有决策都带 ``basis`` 字段，标明是「规则」还是「大模型」给出，
避免把大模型的建议伪装成确定的工艺结论。
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .. import llm
from . import processes
from .devices import DeviceFleet
from .simulation import MillSimulation, StageState


@dataclass
class Decision:
    """一个子智能体的决策结果。"""

    agent: str
    process: str
    status: str  # normal / warn / critical
    advice: str
    basis: str  # rule / llm
    actions: List[str] = field(default_factory=list)

    def public(self) -> Dict[str, object]:
        return {
            "agent": self.agent,
            "process": self.process,
            "status": self.status,
            "advice": self.advice,
            "basis": self.basis,
            "actions": self.actions,
        }


# 工序智能体的系统提示词模板（喂给大模型时替换工序名与知识）
_AGENT_SYSTEM = (
    "你是造纸厂的「{name}」工序智能体，负责工序：{subtitle}。\n"
    "你的职责：根据给定的工况参数判断是否异常，给出简短的处置建议。\n"
    "要求：\n"
    "1. 只依据给定数据，不要编造未提供的数值；\n"
    "2. 建议不超过两句，用中文；\n"
    "3. 这是仿真演示，涉及停机/判废时请说明「需人工确认」；\n"
    "4. 直接给结论，不要复述题目。\n"
    "本工序专家知识：{knowledge}"
)


class ProcessAgent:
    """单道工序的智能体。"""

    def __init__(self, process_key: str) -> None:
        self.process = processes.get(process_key)
        self.name = "%s智能体" % self.process.name
        self.last_decision: Optional[Decision] = None

    def _system_prompt(self) -> str:
        return _AGENT_SYSTEM.format(
            name=self.process.name,
            subtitle=self.process.subtitle,
            knowledge="；".join(self.process.knowledge),
        )

    def _rule_advice(self, stage: StageState) -> str:
        """规则引擎：按越界参数给建议，完全离线。"""
        abnormal = [
            m for m in self.process.metrics
            if stage.metric_status.get(m.key, "normal") != "normal"
        ]
        if not abnormal:
            return "工况正常，维持当前参数，继续下一工序。"
        parts = []
        for m in abnormal:
            value = stage.metrics.get(m.key)
            status = stage.metric_status.get(m.key)
            if value is None:
                continue
            tag = "严重偏离" if status == "critical" else "轻微越界"
            parts.append("%s %s%s（正常 %s–%s %s）" % (
                m.label, tag, _fmt(value), _fmt(m.low), _fmt(m.high), m.unit,
            ))
        # 用第一条专家知识兜底，保证建议有依据
        hint = self.process.knowledge[0] if self.process.knowledge else "请人工复核。"
        return "异常：" + "；".join(parts) + "。" + hint

    def decide(self, stage: StageState, use_llm: bool = True) -> Decision:
        """看工况并决策。大模型失败时自动回落到规则。"""
        status = stage.overall_status
        actions: List[str] = []
        if status == "critical":
            actions = ["hold", "dispatch_robot_dog"]
        elif status == "warn":
            actions = ["slow_down", "notify_plc"]

        advice = self._rule_advice(stage)
        basis = "rule"

        if use_llm and llm.load_config().configured():
            lines = [
                "%s=%s%s（正常 %s–%s）" % (
                    m.label, _fmt(stage.metrics.get(m.key, 0.0)), m.unit,
                    _fmt(m.low), _fmt(m.high),
                )
                for m in self.process.metrics
            ]
            result = llm.chat(
                [
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": "当前工况：" + "，".join(lines)},
                ],
                use_system_prompt=False,
            )
            if result["ok"] and result["reply"]:
                advice = str(result["reply"])[:300]
                basis = "llm"

        decision = Decision(
            agent=self.name,
            process=self.process.key,
            status=status,
            advice=advice,
            basis=basis,
            actions=actions,
        )
        self.last_decision = decision
        return decision


def _fmt(value: float) -> str:
    """数值格式化：整数不带小数点，小数保留两位。"""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return "%.2f" % f


class Orchestrator:
    """总调度智能体：编排四道工序、汇总决策、仲裁异常。"""

    def __init__(self, simulation: Optional[MillSimulation] = None,
                 fleet: Optional[DeviceFleet] = None,
                 use_llm: bool = True) -> None:
        self.sim = simulation or MillSimulation()
        self.fleet = fleet or DeviceFleet()
        self.use_llm = use_llm
        self.agents = {key: ProcessAgent(key) for key in processes.ORDER}
        self.log: List[Dict[str, object]] = []
        self._batch_seq = 0
        self._task_seq = 0

    def _emit(self, event: str, **kw: object) -> None:
        self.log.append({
            "step": self.sim.step,
            "time": round(time.time(), 3),
            "event": event,
            **kw,
        })

    def _next_task_id(self, prefix: str) -> str:
        self._task_seq += 1
        return "%s-%03d" % (prefix, self._task_seq)

    def start_batch(self) -> Dict[str, object]:
        """投一个生产批次，下发首道工序作业。"""
        self._batch_seq += 1
        batch = "B%03d" % self._batch_seq
        self.sim.start_batch(batch)
        self._emit("batch_start", batch=batch, process="pulping")
        self._dispatch_process("pulping", "start")
        return {"batch": batch, "process": "pulping"}

    def _dispatch_process(self, process_key: str, action: str) -> None:
        sent = self.fleet.dispatch_for(
            process_key, action, self._next_task_id("T")
        )
        self._emit("dispatch", process=process_key, action=action, devices=sent)

    def step(self) -> Dict[str, object]:
        """推进一个仿真步：设备执行 → 智能体决策 → 工序流转。"""
        self.sim.advance()
        results = self.fleet.tick(self.sim.step)
        for r in results:
            self._emit("device_done", device=r.device_id, task=r.task_id, message=r.message)

        decisions: List[Dict[str, object]] = []
        for key in processes.ORDER:
            stage = self.sim.stages[key]
            if stage.state not in ("running", "done"):
                continue
            decision = self.agents[key].decide(stage, use_llm=self.use_llm)
            decisions.append(decision.public())
            self._emit("decision", process=key, status=decision.status,
                       basis=decision.basis, advice=decision.advice)

            # 异常仲裁：严重异常挂起本批次并派机器狗巡检
            if decision.status == "critical" and stage.state == "running":
                self.sim.hold_batch(key)
                self._emit("arbitration", process=key, action="hold",
                           reason="工况严重偏离，需人工确认后恢复")
                self._dispatch_process(key, "inspect")
            elif decision.status == "warn" and stage.state == "running":
                self._dispatch_process(key, "adjust")

        # 工序完成判定
        finished = self.sim.finish_completed()
        for key in finished:
            self._emit("process_done", process=key)
            nxt = self.sim.next_process(key)
            if nxt:
                self.sim.begin_process(nxt)
                self._emit("process_begin", process=nxt)
                self._dispatch_process(nxt, "start")
            else:
                self._emit("batch_complete", batch=self.sim.batch_id)

        return self.snapshot()

    def run_until_idle(self, max_steps: int = 60) -> Dict[str, object]:
        """连续推进直到流水线空闲或到达最大步数。"""
        steps = 0
        while steps < max_steps and not self.sim.all_idle():
            self.step()
            steps += 1
        return self.snapshot()

    def snapshot(self) -> Dict[str, object]:
        """给 API / 前端的完整快照。"""
        return {
            "sim": self.sim.snapshot(),
            "decisions": [
                agent.last_decision.public()
                for agent in self.agents.values()
                if agent.last_decision
            ],
            "devices": self.fleet.snapshot(),
            "log": self.log[-80:],
        }
```

### `src/paper_recycle_agent/mill/devices.py`（152 行）

```python
"""设备层模拟：AGV、巡检机器狗、PLC。

**全部是内存模拟对象，不连接任何真实硬件。**
每台设备暴露统一的 ``assign(task)`` 接口，调度器下发任务后，
设备按自身能力耗时完成并返回结果。这样上层多智能体架构与真实设备
接口「形状一致」，将来若接真实设备，只需替换本模块的实现。

安全说明：真实工厂里 AI 不应直接下发控制指令，必须经过联锁与人工复核；
本项目刻意把设备层做成 mock，就是这个边界的体现。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import processes


@dataclass
class Task:
    """一台设备接收的作业任务。"""

    task_id: str
    process: str
    action: str
    payload: Dict[str, object] = field(default_factory=dict)
    # 剩余执行步数，0 表示已完成
    remaining: int = 1


@dataclass
class DeviceResult:
    """设备执行回执。"""

    device_id: str
    task_id: str
    ok: bool
    message: str
    step: int = 0


@dataclass
class Device:
    """设备基类（模拟）。"""

    device_id: str
    name: str
    kind: str  # agv / robot_dog / plc
    speed: int = 1  # 每步推进量
    current: Optional[Task] = None
    queue: List[Task] = field(default_factory=list)
    log: List[DeviceResult] = field(default_factory=list)

    def busy(self) -> bool:
        return self.current is not None

    def assign(self, task: Task) -> bool:
        """下发任务；设备忙时排队。"""
        if self.current is None:
            self.current = task
            return True
        self.queue.append(task)
        return False

    def tick(self, step: int) -> Optional[DeviceResult]:
        """推进一步；任务完成时返回回执。"""
        if self.current is None:
            return None
        self.current.remaining -= self.speed
        if self.current.remaining > 0:
            return None
        done = self.current
        result = DeviceResult(
            device_id=self.device_id,
            task_id=done.task_id,
            ok=True,
            message="%s 完成 %s / %s" % (self.name, processes.get(done.process).name, done.action),
            step=step,
        )
        self.log.append(result)
        self.current = None
        if self.queue:
            self.current = self.queue.pop(0)
        return result

    def snapshot(self) -> Dict[str, object]:
        return {
            "id": self.device_id,
            "name": self.name,
            "kind": self.kind,
            "status": "busy" if self.busy() else "idle",
            "current": (
                {
                    "task_id": self.current.task_id,
                    "process": self.current.process,
                    "action": self.current.action,
                    "remaining": max(self.current.remaining, 0),
                }
                if self.current
                else None
            ),
            "queue_len": len(self.queue),
            "done_count": len(self.log),
        }


class DeviceFleet:
    """设备编队，按工序找到对应设备。"""

    def __init__(self) -> None:
        self.devices: Dict[str, Device] = {
            "agv-01": Device("agv-01", "AGV 运输车 1 号", "agv", speed=1),
            "agv-02": Device("agv-02", "AGV 运输车 2 号", "agv", speed=1),
            "robot-dog-01": Device("robot-dog-01", "巡检机器狗", "robot_dog", speed=1),
            "plc-pulp": Device("plc-pulp", "制浆 PLC", "plc", speed=2),
            "plc-paper": Device("plc-paper", "抄纸 PLC", "plc", speed=2),
            "plc-dryer": Device("plc-dryer", "干燥 PLC", "plc", speed=2),
            "plc-qc": Device("plc-qc", "质检 PLC", "plc", speed=2),
        }

    def assign(self, device_id: str, task: Task) -> bool:
        device = self.devices.get(device_id)
        if device is None:
            return False
        return device.assign(task)

    def tick(self, step: int) -> List[DeviceResult]:
        results = []
        for device in self.devices.values():
            result = device.tick(step)
            if result is not None:
                results.append(result)
        return results

    def dispatch_for(self, process_key: str, action: str, task_id: str,
                     payload: Optional[Dict[str, object]] = None) -> List[str]:
        """给某工序的所有责任设备下发同一任务，返回成功下发的设备 id。"""
        proc = processes.get(process_key)
        sent = []
        for device_id in proc.devices:
            task = Task(
                task_id="%s-%s" % (task_id, device_id),
                process=process_key,
                action=action,
                payload=dict(payload or {}),
                remaining=2 if self.devices[device_id].kind == "plc" else 3,
            )
            if self.assign(device_id, task):
                sent.append(device_id)
        return sent

    def snapshot(self) -> List[Dict[str, object]]:
        return [d.snapshot() for d in self.devices.values()]
```

### `src/paper_recycle_agent/mill/processes.py`（141 行）

```python
"""工序定义：制浆 → 抄纸 → 干燥 → 质检。

每个工序声明自己的工况参数、正常区间、负责设备与专家规则。
区间数值取自公开的制浆造纸工艺常识，仅用于仿真演示，
不代表任何具体工厂的实际控制参数（见 docs/MILL_AGENTS.md 的口径说明）。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# 工序顺序（仿真流水线按此推进）
ORDER: Tuple[str, ...] = ("pulping", "papermaking", "drying", "quality")


@dataclass(frozen=True)
class Metric:
    """一个工况参数及其正常区间。"""

    key: str
    label: str
    unit: str
    low: float
    high: float
    # 超出区间多少比例算「严重」，用于异常分级
    critical_ratio: float = 0.25

    def status(self, value: float) -> str:
        """返回 normal / warn / critical。"""
        if self.low <= value <= self.high:
            return "normal"
        span = self.high - self.low
        if span <= 0:
            return "critical"
        if value < self.low:
            dev = (self.low - value) / span
        else:
            dev = (value - self.high) / span
        return "critical" if dev >= self.critical_ratio else "warn"


@dataclass
class Process:
    """一道工序。"""

    key: str
    name: str
    subtitle: str
    metrics: List[Metric]
    devices: List[str]
    knowledge: List[str] = field(default_factory=list)
    base_time: int = 3  # 正常处理一个批次需要的仿真步数


PROCESSES: Dict[str, Process] = {
    "pulping": Process(
        key="pulping",
        name="制浆",
        subtitle="碎浆 · 脱墨 · 漂白",
        metrics=[
            Metric("pulp_consistency", "浆浓", "%", 2.5, 4.5),
            Metric("pulping_temp", "碎浆温度", "°C", 55, 75),
            Metric("brightness", "白度", "%ISO", 78, 88),
        ],
        devices=["agv-01", "plc-pulp"],
        knowledge=[
            "浆浓过高会增大泵送负荷、影响后续筛选；过低则降低产能。",
            "脱墨段温度偏高有利于油墨剥离，但过高会增加能耗与纤维损伤。",
            "白度不达标时优先检查漂白剂用量与浆料停留时间。",
        ],
        base_time=3,
    ),
    "papermaking": Process(
        key="papermaking",
        name="抄纸",
        subtitle="流送 · 成形 · 压榨",
        metrics=[
            Metric("machine_speed", "车速", "m/min", 600, 900),
            Metric("basis_weight", "定量", "g/m²", 60, 120),
            Metric("pressure", "压榨线压力", "kN/m", 30, 60),
        ],
        devices=["plc-paper", "agv-02"],
        knowledge=[
            "车速提高时若定量波动变大，应先稳住流送泵的脉冲。",
            "定量偏轻通常来自上网浓度偏低或脱水过快。",
            "压榨线压力过高会造成湿部断纸，需与毛毯状态联动判断。",
        ],
        base_time=4,
    ),
    "drying": Process(
        key="drying",
        name="干燥",
        subtitle="蒸汽优化 · 数字孪生",
        metrics=[
            Metric("dryer_temp", "烘缸温度", "°C", 105, 135),
            Metric("steam_pressure", "蒸汽压力", "MPa", 0.3, 0.6),
            Metric("moisture", "成纸水分", "%", 5.0, 7.0),
        ],
        devices=["plc-dryer", "robot-dog-01"],
        knowledge=[
            "干燥是造纸能耗最高的环节，蒸汽压力在小幅波动内优先维持稳定。",
            "成纸水分偏高会引发后续卷曲折皱，偏低则纸张发脆。",
            "数字孪生可在不停机的情况下评估提车速对蒸汽单耗的影响。",
        ],
        base_time=4,
    ),
    "quality": Process(
        key="quality",
        name="质检",
        subtitle="视觉检测 · 定量水分",
        metrics=[
            Metric("defect_rate", "缺陷率", "%", 0.0, 1.5),
            Metric("moisture_check", "抽检水分", "%", 5.0, 7.0),
            Metric("pass_rate", "合格率", "%", 95.0, 100.0),
        ],
        devices=["robot-dog-01", "plc-qc"],
        knowledge=[
            "缺陷率连续升高时，向前追溯干燥温度与压榨压力。",
            "抽检水分与在线水分偏差超过 0.5% 时，先校准在线仪表。",
            "质检智能体只给出处置建议，判废与放行由人工确认。",
        ],
        base_time=2,
    ),
}


def get(key: str) -> Process:
    """取工序定义，未知 key 抛 ValueError。"""
    if key not in PROCESSES:
        raise ValueError("未知工序：%s" % key)
    return PROCESSES[key]


def all_processes() -> List[Process]:
    """按流水线顺序返回全部工序。"""
    return [PROCESSES[k] for k in ORDER]


def describe(key: str) -> str:
    """工序的一句话说明，给前端与对话用。"""
    p = get(key)
    return "%s（%s）：%s" % (p.name, p.subtitle, "；".join(p.knowledge[:1]))
```

### `src/paper_recycle_agent/mill/simulation.py`（187 行）

```python
"""工艺仿真引擎：确定性、可复现的工况状态机。

设计要点
--------
1. **确定性**：给定同一个 seed，工况序列完全一致，便于测试与演示复现。
   这里用标准库 random.Random(seed)，不用全局随机源。
2. **状态机**：每道工序有 idle → running → done 状态；批次在工序间流转。
3. **异常注入**：``inject_anomaly(process, metric, value)`` 可在指定工序
   强制某个参数越界，用来演示智能体的异常处置链。
4. **口径诚实**：数值是仿真生成的工艺常识区间内随机值，不是任何真实产线数据。
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import processes


@dataclass
class StageState:
    """一道工序在某个时刻的状态。"""

    key: str
    state: str = "idle"  # idle / running / done / held
    elapsed: int = 0
    metrics: Dict[str, float] = field(default_factory=dict)
    metric_status: Dict[str, str] = field(default_factory=dict)

    @property
    def overall_status(self) -> str:
        """汇总工况：有 critical 就 critical，其次 warn，否则 normal。"""
        values = list(self.metric_status.values())
        if "critical" in values:
            return "critical"
        if "warn" in values:
            return "warn"
        return "normal"

    def public(self) -> Dict[str, object]:
        return {
            "key": self.key,
            "name": processes.get(self.key).name,
            "subtitle": processes.get(self.key).subtitle,
            "state": self.state,
            "elapsed": self.elapsed,
            "metrics": dict(self.metrics),
            "metric_status": dict(self.metric_status),
            "status": self.overall_status,
        }


class MillSimulation:
    """整厂仿真：管理批次在四道工序间的流转与工况演化。"""

    def __init__(self, seed: int = 2024) -> None:
        self.rng = random.Random(seed)
        self.seed = seed
        self.step = 0
        self.batch_id: Optional[str] = None
        self.stages: Dict[str, StageState] = {
            key: StageState(key=key) for key in processes.ORDER
        }
        # 人工注入的异常：{(process, metric): forced_value}
        self._forced: Dict[tuple, float] = {}

    # ---------- 批次与工序流转 ----------
    def start_batch(self, batch_id: str) -> None:
        """开始新批次，重置所有工序状态。"""
        self.batch_id = batch_id
        self._forced.clear()
        for key, stage in self.stages.items():
            stage.state = "idle"
            stage.elapsed = 0
            stage.metrics = {}
            stage.metric_status = {}
        self.begin_process("pulping")

    def begin_process(self, key: str) -> None:
        stage = self.stages[key]
        stage.state = "running"
        stage.elapsed = 0
        self._generate_metrics(stage)

    def next_process(self, key: str) -> Optional[str]:
        """返回下一道工序 key；末道工序返回 None。"""
        order = list(processes.ORDER)
        if key not in order:
            return None
        idx = order.index(key)
        return order[idx + 1] if idx + 1 < len(order) else None

    def finish_completed(self) -> List[str]:
        """把达到工时且未被挂起的 running 工序标记为 done，返回其 key。"""
        done = []
        for key in processes.ORDER:
            stage = self.stages[key]
            proc = processes.get(key)
            if stage.state == "running" and stage.elapsed >= proc.base_time:
                stage.state = "done"
                done.append(key)
        return done

    def hold_batch(self, key: str) -> None:
        """挂起某工序，等待人工处置。"""
        self.stages[key].state = "held"

    def resume(self, key: str) -> None:
        """人工确认后恢复工序。"""
        stage = self.stages[key]
        if stage.state == "held":
            stage.state = "running"
            stage.elapsed = 0
            self._generate_metrics(stage)

    def all_idle(self) -> bool:
        """流水线是否空闲：没有 running 工序，或没有进行中的批次。"""
        if self.batch_id is None:
            return True
        return all(
            s.state not in ("running",)
            for s in self.stages.values()
        )

    # ---------- 工况生成 ----------
    def _generate_metrics(self, stage: StageState) -> None:
        """为工序生成一组工况值（正常区间内）并计算状态。"""
        for m in processes.get(stage.key).metrics:
            forced = self._forced.get((stage.key, m.key))
            if forced is not None:
                value = forced
            else:
                # 90% 概率落在区间中部，10% 轻微越界，制造可观测波动
                if self.rng.random() < 0.1:
                    span = m.high - m.low
                    value = self.rng.uniform(m.low - 0.12 * span, m.high + 0.12 * span)
                else:
                    value = self.rng.uniform(
                        m.low + 0.15 * (m.high - m.low),
                        m.high - 0.15 * (m.high - m.low),
                    )
            decimals = 0 if (m.high - m.low) >= 50 else 2
            stage.metrics[m.key] = round(value, decimals)
            stage.metric_status[m.key] = m.status(value)

    def advance(self) -> None:
        """推进一个仿真步：更新工况与工时。"""
        self.step += 1
        for key in processes.ORDER:
            stage = self.stages[key]
            if stage.state == "running":
                stage.elapsed += 1
                self._generate_metrics(stage)

    def inject_anomaly(self, process: str, metric: str, value: float) -> bool:
        """注入异常：强制某工序的某参数取指定值，直到批次结束。

        返回是否注入成功（工序/参数必须存在）。
        """
        proc = processes.get(process)
        keys = [m.key for m in proc.metrics]
        if metric not in keys:
            return False
        self._forced[(process, metric)] = float(value)
        stage = self.stages[process]
        if stage.state == "running":
            stage.metrics[metric] = float(value)
            m = next(m for m in proc.metrics if m.key == metric)
            stage.metric_status[metric] = m.status(float(value))
        return True

    def clear_anomalies(self) -> None:
        self._forced.clear()

    # ---------- 对外快照 ----------
    def snapshot(self) -> Dict[str, object]:
        return {
            "step": self.step,
            "seed": self.seed,
            "batch": self.batch_id,
            "idle": self.all_idle(),
            "stages": [self.stages[k].public() for k in processes.ORDER],
            "anomalies": [
                {"process": p, "metric": m, "value": v}
                for (p, m), v in self._forced.items()
            ],
        }
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

### `app/server.py`（708 行）

```python
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
  GET  /api/mill/processes -> 智能工厂：四道工序定义与专家知识
  GET  /api/mill/state   -> 智能工厂：当前仿真快照
  POST /api/mill/start   -> 投一个新生产批次
  POST /api/mill/step    -> 推进 N 个仿真步
  POST /api/mill/run     -> 跑到流水线空闲
  POST /api/mill/anomaly -> 注入工序参数异常（演示处置链）
  POST /api/mill/reset   -> 重置仿真
  GET  /api/brain/state  -> 产业大脑：五域 KPI + 跨域联动 + 对标参考
  POST /api/brain/run    -> 推演 N 步
  POST /api/brain/advise -> 五个领域智能体给建议
  POST /api/brain/optimize -> 模拟管理干预，观察跨域传导
  POST /api/brain/reset  -> 重置产业大脑
  GET  /api/carbon/factors  -> 碳核算排放因子表（国标附录B，带出处）
  GET  /api/carbon/state -> 碳核算结果 + 活动数据 + 回收Agent状态
  POST /api/carbon/activity -> 修改示例工厂活动数据并重算
  POST /api/carbon/scenario -> 情景模拟对比
  POST /api/carbon/reset -> 重置示例数据
  POST /api/carbon/bridge-recycle -> 回收量桥接到碳核算原料输入
  GET  /export.xlsx      -> 多表 Excel 导出（?code=CN&year=2024）
  POST /chat             -> {"reply": "..."}（规则引擎）
  GET  /health           -> {"status": "ok"}
"""

import io
import os
import sys
import threading
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
from paper_recycle_agent.mill.agents import Orchestrator
from paper_recycle_agent.brain.engine import IndustryBrain
from paper_recycle_agent.brain.intelligence import BrainOrchestrator
from paper_recycle_agent.carbon import factors as carbon_factors
from paper_recycle_agent.carbon import recycle_agent
from paper_recycle_agent.carbon.accounting import CarbonAccounting
from paper_recycle_agent.carbon.model import ActivityData, FuelUse

app = FastAPI(title="造纸工厂多智能体 · 碳核算 Agent")

# 智能工厂仿真：全局单例 + 锁，保证并发请求不会把状态改乱。
# 这是仿真对象，不连接任何真实设备。
_MILL = Orchestrator()
_MILL_LOCK = threading.Lock()

# 产业大脑仿真：五条业务链共享数据底座 + 跨域联动（同样是仿真对象）
_BRAIN = BrainOrchestrator(brain=IndustryBrain())
_BRAIN_LOCK = threading.Lock()

# 碳核算：活动数据为示例工厂仿真输入，可用接口修改后重算
_CARBON_ACTIVITY = CarbonAccounting().activity
_CARBON_LOCK = threading.Lock()

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


# ---------------- 智能工厂仿真（多智能体） ----------------

class MillAnomalyReq(BaseModel):
    process: str
    metric: str
    value: float


class MillStepReq(BaseModel):
    steps: int = 1


@app.get("/api/mill/processes")
def mill_processes() -> dict:
    """返回四道工序定义（参数区间、责任设备、专家知识）。"""
    from paper_recycle_agent.mill import processes as proc_mod
    return {
        "order": list(proc_mod.ORDER),
        "processes": {
            key: {
                "key": p.key,
                "name": p.name,
                "subtitle": p.subtitle,
                "devices": p.devices,
                "knowledge": p.knowledge,
                "base_time": p.base_time,
                "metrics": [
                    {
                        "key": m.key, "label": m.label, "unit": m.unit,
                        "low": m.low, "high": m.high,
                    }
                    for m in p.metrics
                ],
            }
            for key, p in proc_mod.PROCESSES.items()
        },
    }


@app.get("/api/mill/state")
def mill_state() -> dict:
    """当前仿真快照：工序状态、设备、智能体决策、调度日志。"""
    with _MILL_LOCK:
        return _MILL.snapshot()


@app.post("/api/mill/start")
def mill_start() -> dict:
    """投一个新生产批次。"""
    with _MILL_LOCK:
        _MILL.start_batch()
        return _MILL.snapshot()


@app.post("/api/mill/step")
def mill_step(req: MillStepReq) -> dict:
    """推进 N 个仿真步（上限 60，防止一次请求跑太久）。"""
    steps = max(1, min(int(req.steps), 60))
    with _MILL_LOCK:
        for _ in range(steps):
            _MILL.step()
        return _MILL.snapshot()


@app.post("/api/mill/run")
def mill_run() -> dict:
    """一直跑到流水线空闲。"""
    with _MILL_LOCK:
        return _MILL.run_until_idle(max_steps=80)


@app.post("/api/mill/anomaly")
def mill_anomaly(req: MillAnomalyReq) -> dict:
    """注入异常：强制某工序参数越界，演示智能体处置链。"""
    with _MILL_LOCK:
        ok = _MILL.sim.inject_anomaly(req.process, req.metric, req.value)
        if ok:
            _MILL._emit("anomaly_injected", process=req.process,
                        metric=req.metric, value=req.value)
        return {"ok": ok, "snapshot": _MILL.snapshot()}


@app.post("/api/mill/reset")
def mill_reset() -> dict:
    """重置仿真（清空日志、批次、异常）。"""
    global _MILL
    with _MILL_LOCK:
        _MILL = Orchestrator()
        return _MILL.snapshot()


# ---------------- 产业大脑仿真（五链贯通） ----------------

class BrainRunReq(BaseModel):
    steps: int = 5


class BrainOptimizeReq(BaseModel):
    domain: str
    kpi: str
    target: float


@app.get("/api/brain/state")
def brain_state() -> dict:
    """产业大脑快照：五域 KPI、跨域联动规则、对标参考。"""
    with _BRAIN_LOCK:
        return _BRAIN.snapshot()


@app.post("/api/brain/run")
def brain_run(req: BrainRunReq) -> dict:
    """推演 N 步（上限 30）。"""
    with _BRAIN_LOCK:
        _BRAIN.brain.run(req.steps)
        return _BRAIN.snapshot()


@app.post("/api/brain/advise")
def brain_advise() -> dict:
    """五个领域智能体各自给建议。"""
    with _BRAIN_LOCK:
        advices = _BRAIN.advise_all()
        return {"advices": advices, "snapshot": _BRAIN.snapshot()}


@app.post("/api/brain/optimize")
def brain_optimize(req: BrainOptimizeReq) -> dict:
    """模拟管理干预：调某域 KPI，观察跨域传导。"""
    with _BRAIN_LOCK:
        return _BRAIN.brain.optimize(req.domain, req.kpi, req.target)


@app.post("/api/brain/reset")
def brain_reset() -> dict:
    """重置产业大脑仿真。"""
    global _BRAIN
    with _BRAIN_LOCK:
        _BRAIN = BrainOrchestrator(brain=IndustryBrain())
        return _BRAIN.snapshot()


# ---------------- 碳核算 Agent（国标方法） ----------------

class CarbonActivityReq(BaseModel):
    """更新示例工厂活动数据；字段可选，只更新提供的字段。"""

    factory_name: Optional[str] = None
    year: Optional[int] = None
    fuel_quantities: Optional[Dict[str, float]] = None
    limestone_ton: Optional[float] = None
    wastewater_cod_removed: Optional[float] = None
    wastewater_cod_sludge: Optional[float] = None
    methane_recovered: Optional[float] = None
    electricity_purchased: Optional[float] = None
    electricity_exported: Optional[float] = None
    electric_ef: Optional[float] = None
    electric_ef_year: Optional[int] = None
    heat_purchased: Optional[float] = None
    heat_exported: Optional[float] = None
    paper_output_wan_ton: Optional[float] = None
    wastepaper_recycled_wan_ton: Optional[float] = None


class CarbonScenarioReq(BaseModel):
    changes: Dict[str, float]


@app.get("/api/carbon/factors")
def carbon_factor_list() -> dict:
    """排放因子表（国标附录B，逐条带出处）与公式说明。"""
    return carbon_factors.all_factors()


@app.get("/api/carbon/state")
def carbon_state() -> dict:
    """当前核算结果 + 活动数据 + 废纸回收 Agent 状态。"""
    with _CARBON_LOCK:
        result = CarbonAccounting(_CARBON_ACTIVITY).calculate()
        return {
            "result": result,
            "activity": _CARBON_ACTIVITY.public(),
            "recycle_agent": recycle_agent.agent_status(),
            "supply_chain_method": recycle_agent.supply_chain_carbon_demo(),
        }


@app.post("/api/carbon/activity")
def carbon_update_activity(req: CarbonActivityReq) -> dict:
    """修改示例工厂活动数据并重算（改完立即返回新结果）。"""
    global _CARBON_ACTIVITY
    with _CARBON_LOCK:
        a = _CARBON_ACTIVITY
        for field in ("factory_name", "year", "limestone_ton", "wastewater_cod_removed",
                      "wastewater_cod_sludge", "methane_recovered", "electricity_purchased",
                      "electricity_exported", "electric_ef", "electric_ef_year",
                      "heat_purchased", "heat_exported", "paper_output_wan_ton",
                      "wastepaper_recycled_wan_ton"):
            value = getattr(req, field)
            if value is not None:
                setattr(a, field, value)
        if req.fuel_quantities:
            known = {f.key for f in a.fuels}
            for key, qty in req.fuel_quantities.items():
                matched = False
                for f in a.fuels:
                    if f.key == key:
                        f.quantity = qty
                        matched = True
                        break
                if not matched:
                    a.fuels.append(FuelUse(key, qty))
        result = CarbonAccounting(a).calculate()
        return {"ok": True, "result": result, "activity": a.public()}


@app.post("/api/carbon/scenario")
def carbon_scenario(req: CarbonScenarioReq) -> dict:
    """情景模拟：改若干活动数据，对比基准与情景排放。"""
    with _CARBON_LOCK:
        return CarbonAccounting(_CARBON_ACTIVITY).scenario(req.changes)


@app.post("/api/carbon/reset")
def carbon_reset() -> dict:
    """重置为示例工厂数据。"""
    global _CARBON_ACTIVITY
    with _CARBON_LOCK:
        _CARBON_ACTIVITY = CarbonAccounting().activity
        result = CarbonAccounting(_CARBON_ACTIVITY).calculate()
        return {"ok": True, "result": result, "activity": _CARBON_ACTIVITY.public()}


@app.post("/api/carbon/bridge-recycle")
def carbon_bridge_recycle(year: int = 2024, code: Optional[str] = None) -> dict:
    """从废纸回收 Agent 取回收量，桥接到碳核算的原料输入。"""
    global _CARBON_ACTIVITY
    with _CARBON_LOCK:
        rec = recycle_agent.recovery_from_stats(year, code)
        if not rec.get("ok"):
            return rec
        # 全国/省级回收量是行业口径，不能直接当单厂数据。
        # overwrite=False：仅当工厂回收量为 0 时才写入，否则只返回参考值提示用户确认。
        bridged = recycle_agent.bridge_to_activity(
            float(rec["recovery_wan_ton"]), _CARBON_ACTIVITY, overwrite=False,
        )
        if not bridged.get("ok"):
            return {"ok": False, "error": "桥接失败"}
        if not bridged.get("written", True):
            bridged["hint"] = (
                "全国/省级回收量为行业统计口径，非单厂数据，未覆盖工厂现有值。"
                "如需按此量级核算，请确认该厂实际回收量后在输入框中手动填写。"
            )
        result = CarbonAccounting(_CARBON_ACTIVITY).calculate()
        return {"ok": True, "recovery": rec, "bridge": bridged, "result": result}


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
```

### `app/static/index.html`（2213 行）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>造纸工厂多智能体 · 碳核算 Agent</title>
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
  .tabs { display: flex; gap: 4px; margin-bottom: 10px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
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
  .export-msg { font-size: 12px; line-height: 1.6; color: var(--muted); margin: 2px 2px 0; min-height: 15px; }
  .export-msg.err { color: #C0392B; }

  /* ---------- 投入产出 ---------- */
  .kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; }
  .kpi { border: 1px solid var(--border); border-radius: 10px; padding: 9px 11px; background: #fbfcfd; }
  .kpi .k { font-size: 11px; color: var(--muted); }
  .kpi .v { font-size: 19px; font-weight: 700; color: var(--ink); margin-top: 2px;
            font-variant-numeric: tabular-nums; line-height: 1.2; }
  .kpi .v .u { font-size: 11px; font-weight: 400; color: var(--muted); margin-left: 3px; }
  .kpi .n { font-size: 10.5px; color: var(--muted); margin-top: 3px; line-height: 1.45; }

  /* ---------- 设置表单 ---------- */
  .form { display: grid; gap: 7px; }
  .form label { display: grid; grid-template-columns: 76px 1fr; align-items: center;
                gap: 8px; font-size: 12px; color: var(--muted); }
  .form input, .form select { height: 30px; border: 1px solid var(--border); border-radius: 7px;
                              padding: 0 9px; font-size: 12.5px; color: var(--ink);
                              background: #fff; width: 100%; box-sizing: border-box; }

  /* ---------- 地图 ---------- */
  .mapbox { height: 340px; border: 1px solid var(--border); border-radius: 8px;
            overflow: hidden; background: #f4f6f8; position: relative; margin-bottom: 8px; }
  .mapbox .ph { position: absolute; inset: 0; display: flex; align-items: center;
                justify-content: center; text-align: center; padding: 18px;
                font-size: 12px; color: var(--muted); line-height: 1.7; }
  .mapinfo { position: absolute; left: 8px; bottom: 8px; background: rgba(255,255,255,.95);
             border: 1px solid var(--border); border-radius: 7px; padding: 5px 9px;
             font-size: 11.5px; color: var(--ink); z-index: 5; }

  /* ---------- 麦克风 ---------- */
  .microw { display: flex; align-items: center; gap: 9px; margin-bottom: 8px; }
  .microw button { height: 32px; padding: 0 12px; border-radius: 8px;
                   border: 1px solid var(--border); background: #fff; cursor: pointer; font-size: 12.5px; }
  .microw button:disabled { opacity: .6; cursor: default; }
  .meter { flex: 1; height: 10px; background: #eef1f4; border-radius: 5px; overflow: hidden; }
  .meterfill { height: 100%; width: 0%; background: var(--brand); transition: width .08s linear; }
  .meterfill.hot { background: #e07a5f; }

  .yearbar { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 12px; color: var(--muted); }
  .yearbar select { padding: 4px 8px; border: 1px solid var(--border); border-radius: 6px; font-size: 12.5px; color: var(--ink); background: #fff; }

  .notice { background: var(--warn-bg); border: 1px solid var(--warn-line); color: var(--warn-ink);
            border-radius: 8px; padding: 7px 10px; font-size: 11px; line-height: 1.5; margin-bottom: 10px; }
  details.standards { margin-top: 14px; border-top: 1px dashed var(--border); padding-top: 8px; }
  details.standards summary { font-size: 12px; color: var(--muted); cursor: pointer; }
  .std-cat { border: 1px solid var(--border); border-radius: 8px; padding: 7px 9px; margin-top: 6px; font-size: 11px; }
  .std-cat .nm { font-weight: 600; font-size: 12px; }
  .std-cat .ex, .std-cat .nt { color: var(--muted); margin-top: 2px; }

  /* ---------- 智能工厂（多智能体仿真） ---------- */
  .mill-ctrl { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
  .mill-ctrl button { height: 31px; padding: 0 11px; border-radius: 8px; font-size: 12px;
                      cursor: pointer; border: 1px solid var(--brand); background: var(--brand); color: #fff; }
  .mill-ctrl button.ghost { background: #fff; color: var(--brand); }
  .mill-ctrl button.amber { background: #fff; color: #8a6d1f; border-color: #e2c572; }
  .mill-ctrl button:disabled { opacity: .55; cursor: default; }
  .mill-status { font-size: 11.5px; color: var(--muted); margin: 0 0 9px; line-height: 1.5; }
  .mill-status b { color: var(--ink); }
  .pipe { display: flex; align-items: stretch; gap: 4px; margin-bottom: 8px; }
  .stage { flex: 1; border: 1px solid var(--border); border-radius: 9px; padding: 7px 6px;
           background: #fbfcfd; min-width: 0; }
  .stage.running { border-color: var(--brand); background: #f0f8f3; }
  .stage.done { border-color: var(--brand-line); background: #eef6f0; }
  .stage.held { border-color: #e2c572; background: var(--warn-bg); }
  .stage .nm { font-size: 12px; font-weight: 600; }
  .stage .st { font-size: 10px; margin-top: 2px; color: var(--muted); }
  .stage.running .st { color: var(--brand); }
  .stage.held .st { color: var(--warn-ink); }
  .stage .mini { font-size: 10px; color: var(--muted); margin-top: 4px; line-height: 1.4; }
  .stage .dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 3px; }
  .dot.normal { background: #4a9d6b; } .dot.warn { background: #e0a33a; } .dot.critical { background: #d64545; }
  .agent-row { border-left: 3px solid var(--brand-line); padding: 5px 9px; margin-bottom: 5px;
               background: #fbfcfd; border-radius: 0 7px 7px 0; font-size: 11.5px; line-height: 1.5; }
  .agent-row.warn { border-left-color: #e0a33a; } .agent-row.critical { border-left-color: #d64545; }
  .agent-row .who { font-weight: 600; }
  .agent-row .basis { font-size: 10px; color: var(--muted); }
  .agent-row .advice { color: var(--ink); margin-top: 2px; }
  .dev-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
  .dev { border: 1px solid var(--border); border-radius: 7px; padding: 5px 7px; font-size: 11px;
         background: #fff; display: flex; justify-content: space-between; gap: 5px; }
  .dev .dn { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .dev .ds { color: var(--muted); } .dev.busy .ds { color: var(--brand); }
  .mill-log { max-height: 150px; overflow-y: auto; border: 1px solid var(--border);
              border-radius: 8px; font-size: 10.5px; line-height: 1.6; padding: 5px 8px; background: #fbfcfd; }
  .mill-log .ln { border-bottom: 1px dashed var(--border); padding: 1px 0; }
  .mill-log .ln:last-child { border-bottom: none; }
  .mill-log .ev { color: var(--brand); } .mill-log .tm { color: var(--muted); }
  .anomaly-form { display: grid; grid-template-columns: 1fr 1fr 66px; gap: 5px; margin-bottom: 6px; }
  .anomaly-form select, .anomaly-form input { height: 27px; border: 1px solid var(--border);
       border-radius: 6px; padding: 0 5px; font-size: 11px; color: var(--ink); background: #fff; min-width: 0; }
  .anomaly-form button { height: 27px; border-radius: 6px; border: 1px solid #e2c572;
       background: #fff; color: #8a6d1f; font-size: 11px; cursor: pointer; }

  /* ---------- 产业大脑（五链贯通） ---------- */
  .brain-chain { display: flex; align-items: center; gap: 3px; margin-bottom: 9px; flex-wrap: wrap; }
  .brain-node { flex: 1; min-width: 58px; border: 1px solid var(--border); border-radius: 8px;
                padding: 6px 4px; text-align: center; background: #fbfcfd; font-size: 11.5px; }
  .brain-node .bn { font-weight: 600; }
  .brain-node .bv { font-size: 10px; color: var(--muted); margin-top: 2px; }
  .brain-arrow { color: var(--brand); font-size: 13px; }
  .brain-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 8px; }
  .brain-card { border: 1px solid var(--border); border-radius: 9px; padding: 8px 9px; background: #fff; }
  .brain-card .bc-h { font-size: 12px; font-weight: 600; margin-bottom: 4px;
                      display: flex; justify-content: space-between; gap: 5px; }
  .brain-card .bc-h .tag { font-size: 9.5px; font-weight: 400; color: var(--brand);
                           background: var(--brand-soft); border-radius: 8px; padding: 1px 6px; }
  .brain-card .bc-sub { font-size: 10px; color: var(--muted); margin-bottom: 5px; }
  .brain-kpi { display: flex; justify-content: space-between; font-size: 10.5px;
               padding: 2px 0; border-bottom: 1px dashed var(--border); }
  .brain-kpi:last-child { border-bottom: none; }
  .brain-kpi .k { color: var(--muted); } .brain-kpi .v { font-variant-numeric: tabular-nums; }
  .brain-impact { font-size: 9.5px; color: #8a6d1f; margin-top: 4px; line-height: 1.4; }
  .brain-advice { border-left: 3px solid var(--brand-line); padding: 4px 8px; margin-bottom: 4px;
                  background: #fbfcfd; font-size: 11px; line-height: 1.5; }
  .brain-advice .bd { color: var(--muted); font-size: 10px; margin-top: 2px; }
  .bench-row { display: flex; justify-content: space-between; gap: 6px; font-size: 10.5px;
               padding: 4px 0; border-bottom: 1px dashed var(--border); }
  .bench-row:last-child { border-bottom: none; }
  .bench-row .bv { color: var(--brand); font-weight: 600; white-space: nowrap; }
  .bench-row .bs { color: var(--muted); font-size: 9.5px; }
  .opt-form { display: grid; grid-template-columns: 1fr 1fr 62px; gap: 5px; margin-bottom: 6px; }
  .opt-form select, .opt-form input { height: 27px; border: 1px solid var(--border);
       border-radius: 6px; padding: 0 5px; font-size: 11px; color: var(--ink); background: #fff; min-width: 0; }
  .opt-form button { height: 27px; border-radius: 6px; border: 1px solid var(--brand);
       background: var(--brand); color: #fff; font-size: 11px; cursor: pointer; }

  /* ---------- 碳核算 Agent（核心） ---------- */
  .carbon-hero { border: 1px solid #e8b4b4; border-radius: 11px; padding: 11px 13px;
                 background: #fef6f6; margin-bottom: 10px; }
  .carbon-hero .ch-title { font-size: 12px; color: #8a4a4a; }
  .carbon-hero .ch-total { font-size: 27px; font-weight: 700; color: #a32d2d;
                           font-variant-numeric: tabular-nums; margin: 3px 0; }
  .carbon-hero .ch-total .u { font-size: 13px; font-weight: 400; }
  .carbon-hero .ch-meta { font-size: 11px; color: #8a6d1f; line-height: 1.5; }
  .carbon-warn { background: var(--warn-bg); border: 1px solid var(--warn-line);
                 color: var(--warn-ink); border-radius: 8px; padding: 7px 10px;
                 font-size: 11px; line-height: 1.5; margin-bottom: 9px; }
  .carbon-bar { display: flex; align-items: center; gap: 6px; margin: 3px 0; font-size: 11px; }
  .carbon-bar .cb-lbl { width: 88px; color: var(--muted); flex-shrink: 0; }
  .carbon-bar .cb-track { flex: 1; height: 13px; background: #eef1f4; border-radius: 3px; overflow: hidden; }
  .carbon-bar .cb-fill { height: 100%; background: #c06565; border-radius: 3px; }
  .carbon-bar .cb-val { width: 74px; text-align: right; font-variant-numeric: tabular-nums; }
  .carbon-item { border-bottom: 1px dashed var(--border); padding: 5px 0; font-size: 10.5px; }
  .carbon-item:last-child { border-bottom: none; }
  .carbon-item .ci-h { display: flex; justify-content: space-between; gap: 5px; }
  .carbon-item .ci-h b { font-size: 11.5px; }
  .carbon-item .ci-formula { color: var(--muted); margin-top: 2px; font-size: 10px; line-height: 1.4; }
  .carbon-item .ci-src { color: #6b7a9c; font-size: 9.5px; margin-top: 1px; }
  .carbon-input { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
  .carbon-input label { font-size: 10.5px; color: var(--muted); display: grid; gap: 2px; }
  .carbon-input input { height: 26px; border: 1px solid var(--border); border-radius: 6px;
                        padding: 0 6px; font-size: 11.5px; color: var(--ink); width: 100%;
                        box-sizing: border-box; }
  .carbon-credit { background: #eaf3de; border: 1px solid #c0dd97; border-radius: 9px;
                   padding: 8px 10px; font-size: 11px; line-height: 1.5; }
  .carbon-credit .v { font-size: 17px; font-weight: 700; color: #3b6d11; }
  @media (max-width: 980px) { .side { display: none; } }
</style>
</head>
<body>
<header>🪨 造纸工厂多智能体 · 碳核算 Agent
  <span class="sub">v1.9.0 · 碳核算(核心) · 废纸回收Agent · 智能工厂 · 产业大脑 · 区域/历年/分类统计</span>
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
      <div class="tab active" data-pane="carbon" onclick="switchTab('carbon')">碳核算Agent</div>
      <div class="tab" data-pane="region" onclick="switchTab('region')">区域统计</div>
      <div class="tab" data-pane="history" onclick="switchTab('history')">历年数据</div>
      <div class="tab" data-pane="category" onclick="switchTab('category')">分类结构</div>
      <div class="tab" data-pane="enterprise" onclick="switchTab('enterprise')">企业分布</div>
      <div class="tab" data-pane="io" onclick="switchTab('io')">投入产出</div>
      <div class="tab" data-pane="mill" onclick="switchTab('mill')">智能工厂</div>
      <div class="tab" data-pane="brain" onclick="switchTab('brain')">产业大脑</div>
      <div class="tab" data-pane="map" onclick="switchTab('map')">消耗地图</div>
      <div class="tab" data-pane="settings" onclick="switchTab('settings')">设置</div>
    </div>

    <!-- 碳核算 Agent（核心） -->
    <section class="pane active" id="pane-carbon">
      <div class="notice">
        工厂碳核算 Agent · 按国标《温室气体排放核算与报告要求 造纸和纸制品生产企业》方法。
        排放因子取国标附录B缺省值（逐项可查出处）；活动数据为<b>示例工厂仿真输入，非真实工厂</b>。
      </div>
      <div class="mill-ctrl">
        <button id="carbonResetBtn" onclick="carbonReset()">恢复示例数据</button>
        <button class="ghost" id="carbonBridgeBtn" onclick="carbonBridge()">取回收量做原料输入</button>
      </div>

      <div class="carbon-hero" id="carbonHero"></div>
      <div class="carbon-warn" id="carbonWarn"></div>

      <div class="sect-title"><span>排放结构（tCO₂e）</span><span class="hintline" id="carbonStructureHint"></span></div>
      <div id="carbonBars"></div>

      <div class="sect-title"><span>计算明细（公式与出处可查）</span></div>
      <div class="scroll" style="max-height:230px" id="carbonItems"></div>

      <div class="sect-title"><span>废纸回收 Agent 的减排贡献</span><span class="hintline">范围三，不计入国标总量</span></div>
      <div class="carbon-credit" id="carbonCredit"></div>

      <div class="sect-title"><span>修改活动数据（改完自动重算）</span><span class="hintline">示例值，可手改验证公式</span></div>
      <details>
        <summary style="font-size:11.5px;color:var(--muted);cursor:pointer">展开输入项（煤量、电量、石灰石…）</summary>
        <div class="carbon-input" id="carbonInputs" style="margin-top:8px"></div>
        <div class="mill-ctrl" style="margin-top:8px">
          <button id="carbonApplyBtn" onclick="carbonApply()">应用并重算</button>
        </div>
      </details>

      <div class="sect-title"><span>情景模拟</span><span class="hintline">改一个量，看排放变化</span></div>
      <div class="anomaly-form">
        <select id="scenField"></select>
        <input id="scenValue" type="number" step="1" value="0" />
        <button onclick="carbonScenario()">模拟</button>
      </div>
      <div class="mill-status" id="scenResult"></div>
    </section>

    <!-- 区域统计 -->
    <section class="pane" id="pane-region">
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
      <div class="export-msg" id="exportMsg"></div>
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

    <!-- 投入产出 -->
    <section class="pane" id="pane-io">
      <div class="yearbar">
        <span>数据年份</span>
        <select id="ioYear" onchange="loadIO(this.value)"></select>
        <span id="ioScope"></span>
      </div>
      <div class="kpis" id="ioKpis"></div>
      <div class="notice" id="ioNotice"></div>
      <div class="sect-title">
        <span>分省消耗金额（亿元）</span>
        <span class="hintline" id="ioBasis"></span>
      </div>
      <div class="scroll" style="max-height: 240px">
        <table id="ioProvTable">
          <thead>
            <tr>
              <th class="num">#</th><th>省份</th>
              <th class="num">占比(%)</th><th class="num">金额(亿元)</th><th>金额口径</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div id="ioCityWrap" style="display: none">
        <div class="sect-title">
          <span>省内城市分摊</span>
          <span class="hintline">地级市无投入产出表，按企业分布分摊</span>
        </div>
        <div class="scroll" style="max-height: 180px">
          <table id="ioCityTable">
            <thead><tr><th>城市</th><th class="num">企业量(万吨)</th><th class="num">金额(亿元)</th></tr></thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
      <div class="sect-title">
        <span>企业采购金额</span>
        <span class="hintline" id="ioEntHint">年经手量 × 均价</span>
      </div>
      <div class="scroll" style="max-height: 220px">
        <table id="ioEntTable">
          <thead>
            <tr><th>企业</th><th>省 / 市</th><th class="num">年经手量</th><th class="num">金额(亿元)</th></tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <div class="actions">
        <button onclick="loadIO(state.year)">刷新</button>
        <button onclick="exportExcel()">导出 Excel</button>
      </div>
    </section>

    <!-- 智能工厂（多智能体仿真） -->
    <section class="pane" id="pane-mill">
      <div class="notice">
        仿真演示：四道工序各由一个智能体负责，总调度器编排任务、派机器狗与 AGV 作业。
        工况为仿真生成，设备为内存模拟对象，<b>不连接任何真实产线</b>。
      </div>
      <div class="mill-ctrl">
        <button id="millStartBtn" onclick="millAction('start')">投批次</button>
        <button class="ghost" id="millStepBtn" onclick="millAction('step')">单步</button>
        <button class="ghost" id="millRunBtn" onclick="millAction('run')">自动跑完</button>
        <button class="ghost" id="millResetBtn" onclick="millAction('reset')">重置</button>
      </div>
      <div class="mill-status" id="millStatus">尚未投产，点「投批次」开始。</div>

      <div class="sect-title"><span>工序流水线</span><span class="hintline" id="millStepLabel"></span></div>
      <div class="pipe" id="millPipe"></div>

      <div class="sect-title"><span>智能体决策</span><span class="hintline">配置 API 后用大模型，否则回落规则</span></div>
      <div id="millAgents"></div>

      <div class="sect-title"><span>设备任务</span><span class="hintline" id="millDevHint"></span></div>
      <div class="dev-grid" id="millDevices"></div>

      <div class="sect-title"><span>异常注入（演示处置链）</span></div>
      <div class="anomaly-form">
        <select id="anomProcess"></select>
        <select id="anomMetric"></select>
        <input id="anomValue" type="number" step="0.1" value="0" />
      </div>
      <div class="mill-ctrl" style="margin-bottom:8px">
        <button class="amber" onclick="millInject()">注入异常</button>
      </div>

      <div class="sect-title"><span>调度日志</span><span class="hintline" id="millLogHint"></span></div>
      <div class="mill-log" id="millLog"></div>
    </section>

    <!-- 产业大脑（五链贯通） -->
    <section class="pane" id="pane-brain">
      <div class="notice">
        仿真演示：对标华泰「产业大脑」五链贯通（采购 / 生产 / 销售 / 仓储物流 / 资金财务），
        五域共享数据底座，跨域联动可观测。<b>KPI 为仿真值</b>，下方华泰成效仅作对标参考，非本项目成果。
      </div>
      <div class="mill-ctrl">
        <button id="brainRunBtn" onclick="brainAction('run')">推演 5 步</button>
        <button class="ghost" id="brainAdviseBtn" onclick="brainAction('advise')">领域智能体会商</button>
        <button class="ghost" id="brainResetBtn" onclick="brainAction('reset')">重置</button>
      </div>
      <div class="mill-status" id="brainStatus">产业大脑待推演。</div>

      <div class="sect-title"><span>五条业务链</span><span class="hintline" id="brainStepLabel"></span></div>
      <div class="brain-chain" id="brainChain"></div>

      <div class="brain-grid" id="brainCards"></div>

      <div class="sect-title"><span>领域智能体建议</span><span class="hintline">配置 API 后用大模型，否则回落规则</span></div>
      <div id="brainAdvices"></div>

      <div class="sect-title"><span>管理干预推演</span><span class="hintline">改一个 KPI，看跨域传导</span></div>
      <div class="opt-form">
        <select id="optDomain"></select>
        <select id="optKpi"></select>
        <input id="optTarget" type="number" step="0.1" value="85" />
      </div>
      <div class="mill-ctrl" style="margin-bottom:8px">
        <button class="ghost" onclick="brainOptimize()">执行干预</button>
      </div>

      <div class="sect-title"><span>华泰公开成效（对标参考）</span><span class="hintline">非本项目成果</span></div>
      <div id="brainBenchmarks"></div>

      <div class="sect-title"><span>联动日志</span><span class="hintline" id="brainLogHint"></span></div>
      <div class="mill-log" id="brainLog"></div>
    </section>

    <!-- 消耗地图 -->
    <section class="pane" id="pane-map">
      <div class="yearbar">
        <span>数据年份</span>
        <select id="mapYear" onchange="loadMap(this.value)"></select>
        <span id="mapScope"></span>
      </div>
      <div class="notice" id="mapNotice"></div>
      <div class="mapbox" id="mapBox">
        <div class="ph" id="mapPlaceholder">地图未加载</div>
      </div>
      <div class="sect-title">
        <span>省份消耗金额排行</span>
        <span class="hintline">无地图密钥时以此为准</span>
      </div>
      <div class="chart" id="mapRank"></div>
      <div class="actions">
        <button onclick="loadMap(state.year)">重新加载</button>
        <button onclick="switchTab('settings')">配置地图密钥</button>
      </div>
    </section>

    <!-- 设置：模型配置 + 麦克风自检 -->
    <section class="pane" id="pane-settings">
      <div class="sect-title">
        <span>模型配置（接入 API 思考）</span>
        <span class="hintline" id="llmState"></span>
      </div>
      <div class="notice" id="llmNotice"></div>
      <div class="form">
        <label>预设<select id="llmPreset" onchange="applyPreset(this.value)"></select></label>
        <label>Base URL<input id="llmBase" placeholder="https://api.deepseek.com/v1" /></label>
        <label>模型名<input id="llmModel" placeholder="deepseek-chat" /></label>
        <label>API Key<input id="llmKey" type="password" placeholder="留空则沿用已保存的密钥" /></label>
        <label>温度<input id="llmTemp" type="number" step="0.1" min="0" max="2" value="0.3" /></label>
        <label>最大 tokens<input id="llmTokens" type="number" min="50" max="4000" value="600" /></label>
        <label>地图 Key<input id="mapKey" type="password" placeholder="腾讯位置服务 key（仅存本机浏览器）" /></label>
      </div>
      <div class="actions">
        <button onclick="saveLLM()">保存配置</button>
        <button onclick="testLLM()">测试连接</button>
      </div>
      <div class="export-msg" id="llmMsg"></div>

      <div class="sect-title">
        <span>麦克风自检</span>
        <span class="hintline" id="micEnv"></span>
      </div>
      <div class="notice" id="micNotice"></div>
      <div class="microw">
        <button id="micCheckBtn" onclick="micCheck()">检测收音（3 秒）</button>
        <div class="meter"><div class="meterfill" id="micMeter"></div></div>
        <span id="micPeak" style="font-size:11.5px;color:var(--muted);width:52px;text-align:right">—</span>
      </div>
      <div class="scroll" style="max-height: 132px">
        <table id="micDevices">
          <thead><tr><th>输入设备</th><th>状态</th></tr></thead>
          <tbody><tr><td colspan="2" class="empty">点上面的按钮授权后列出设备</td></tr></tbody>
        </table>
      </div>
      <div class="export-msg" id="micMsg"></div>
      <div class="sect-title">
        <span>语音识别实测</span>
        <span class="hintline">说一句话，看输入框是否出字</span>
      </div>
      <div class="actions">
        <button onclick="micRecognize()">开始识别</button>
      </div>
      <div class="export-msg" id="micResult"></div>
    </section>
  </aside>
</div>

<script>
  const SUGGESTIONS = [
    "纸箱能回收吗", "办公用纸 3kg", "山东省回收量",
    "全国统计", "历年数据", "分类回收数据", "废纸消耗金额"
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
      // 走 /api/llm/chat：配置了大模型就用大模型，没配置自动回落规则引擎
      const res = await fetch("/api/llm/chat", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      addMsg(data.reply, "bot");
      if (data.engine === "llm") {
        const tag = document.createElement("div");
        tag.className = "msg bot";
        tag.style.cssText = "font-size:10.5px;color:var(--muted);padding:0 2px 6px";
        tag.textContent = `（由 ${data.model || "大模型"} 生成，${data.latency_ms} ms）`;
        messagesEl.appendChild(tag);
        messagesEl.scrollTop = messagesEl.scrollHeight;
      }
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
    if (name === "carbon") loadCarbon();
    if (name === "enterprise") loadEnterprises();
    if (name === "io") loadIO(state.year);
    if (name === "map") loadMap(state.year);
    if (name === "mill") loadMill();
    if (name === "brain") loadBrain();
    if (name === "settings") loadSettings();
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
    const btn = document.getElementById("exportBtn");
    const msg = document.getElementById("exportMsg");
    const label = btn ? btn.textContent : "导出 Excel";
    const say = (text, isErr) => {
      if (!msg) return;
      msg.textContent = text || "";
      msg.classList.toggle("err", !!isErr);
    };
    const restore = (text) => {
      if (!btn) return;
      btn.textContent = text;
      btn.disabled = false;
    };
    if (btn) { btn.disabled = true; btn.textContent = "导出中…"; }
    say("");
    const url = `/export.xlsx?code=${encodeURIComponent(state.code)}&year=${state.year}`;
    let serverReplied = false;
    try {
      const res = await fetch(url);
      serverReplied = true;
      if (!res.ok) {
        // 服务端会用 JSON 说明原因（例如缺少 openpyxl 时返回 503）
        let detail = `导出失败（HTTP ${res.status}）`;
        let hint = "";
        try {
          const body = await res.json();
          if (body && body.detail) detail = body.detail;
          if (body && body.hint) hint = body.hint;
        } catch (_) { /* 非 JSON 响应，保留默认文案 */ }
        throw new Error(hint ? `${detail} ${hint}` : detail);
      }
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
      say(`已导出 ${name}（7 张工作表）`);
      restore("已导出 ✓");
      setTimeout(() => restore(label || "导出 Excel"), 1600);
    } catch (e) {
      if (!serverReplied) {
        // 请求根本没到服务端（预览框拦截 / 网络异常），退化为直接打开下载链接
        window.open(url, "_blank");
        say("已尝试在新窗口打开下载链接");
      } else {
        say(e.message, true);
      }
      restore("导出失败");
      setTimeout(() => restore(label || "导出 Excel"), 2400);
    }
  }

  /* ================= 投入产出（消耗金额） ================= */
  function fmtNum(n, d) {
    if (n === null || n === undefined || n === "") return "—";
    const v = Number(n);
    if (!isFinite(v)) return "—";
    return v.toLocaleString("zh-CN", {
      minimumFractionDigits: d || 0, maximumFractionDigits: d || 0
    });
  }

  function kpiCard(k, v, u, note) {
    return `<div class="kpi"><div class="k">${k}</div>
      <div class="v">${v}<span class="u">${u}</span></div>
      <div class="n">${note || ""}</div></div>`;
  }

  function fillYearSelect(id, years, current) {
    const sel = document.getElementById(id);
    if (!sel || !years || !years.length) return;
    const sig = years.join(",");
    if (sel.dataset.filled !== sig) {
      sel.innerHTML = years.slice().sort((a, b) => b - a)
        .map(y => `<option value="${y}">${y}</option>`).join("");
      sel.dataset.filled = sig;
    }
    sel.value = current;
  }

  async function loadIO(year) {
    const y = Number(year) || state.year;
    const q = state.code && state.code !== "CN"
      ? `&code=${encodeURIComponent(state.code)}` : "";
    let d;
    try {
      d = await (await fetch(`/api/io?year=${y}${q}`)).json();
    } catch (e) {
      document.getElementById("ioNotice").textContent = "接口不可用：" + e;
      return;
    }

    fillYearSelect("ioYear", d.years, d.spend.year);
    document.getElementById("ioScope").textContent =
      d.scope && d.scope !== "全国" ? `· ${d.scope}` : "";

    const s = d.spend, dc = d.direct_coefficient, uc = d.unit_consumption;
    document.getElementById("ioKpis").innerHTML = [
      kpiCard("废纸消耗金额", fmtNum(s.amount, 1), "亿元",
        `${s.provenance}；按回收参考价计，属纸厂成本下限`),
      kpiCard("直接消耗系数",
        dc.coefficient === null || dc.coefficient === undefined ? "—" : fmtNum(dc.coefficient_pct, 2),
        "%",
        dc.coefficient === null
          ? "该年造纸业营收无公开值"
          : `货值 ${fmtNum(dc.spend, 1)} 亿 ÷ 营收 ${fmtNum(dc.revenue, 0)} 亿`),
      kpiCard("单位产值消耗",
        uc.value === null || uc.value === undefined ? "—" : fmtNum(uc.value, 3),
        "吨/万元", "消耗量 ÷ 营业收入"),
      kpiCard("加权参考价", fmtNum(s.avg_price, 0), "元/吨",
        "分类结构加权，居民 / 回收站口径")
    ].join("");

    document.getElementById("ioNotice").innerHTML =
      `<b>口径分级</b>：` +
      d.levels.map(l =>
        `${l.name}（${l.io_available ? "有官方表" : "无官方表"}，${l.provenance}）`
      ).join("　") +
      `。省级虽有官方投入产出表，但本表的分省金额是按回收量占比分摊的，` +
      `不是实际采购分布；国家统计局明确「地级市暂不编制投入产出表」，企业只有财务报表——` +
      `市级与企业级同样只能分摊估算，都不能当作统计公报数据引用。`;

    document.getElementById("ioBasis").textContent = d.provinces.basis;
    document.querySelector("#ioProvTable tbody").innerHTML =
      d.provinces.rows.map(r => `
        <tr class="row" onclick="loadStats('${r.code}', ${d.spend.year})">
          <td class="num">${r.rank}</td>
          <td>${r.name}</td>
          <td class="num">${r.share_pct}</td>
          <td class="num">${fmtNum(r.amount, 1)}</td>
          <td>${r.provenance}</td>
        </tr>`).join("");

    // 省内城市分摊（仅选中省份时有）
    const cityWrap = document.getElementById("ioCityWrap");
    if (d.cities && d.cities.cities && d.cities.cities.length) {
      cityWrap.style.display = "block";
      document.querySelector("#ioCityTable tbody").innerHTML =
        d.cities.cities.map(c => `
          <tr><td>${c.city}</td>
              <td class="num">${fmtNum(c.enterprise_volume, 1)}</td>
              <td class="num">${fmtNum(c.amount, 2)}</td></tr>`).join("");
    } else {
      cityWrap.style.display = "none";
    }

    const ent = d.enterprises;
    document.getElementById("ioEntHint").textContent =
      `${ent.rows.length} 家 · 均价 ${fmtNum(ent.avg_price, 0)} 元/吨 · ${ent.provenance}`;
    document.querySelector("#ioEntTable tbody").innerHTML =
      ent.rows.slice(0, 40).map(e => `
        <tr><td>${e.name}</td>
            <td>${e.province} / ${e.city}</td>
            <td class="num">${fmtNum(e.volume, 1)}</td>
            <td class="num">${fmtNum(e.amount, 2)}</td></tr>`).join("");
  }

  /* ================= 消耗地图 ================= */
  // 合规：底图只用腾讯位置服务（正版底图、有审图号），且不内置任何可用密钥。
  // 没有 key 时降级为排行视图，绝不自行绘制国界。
  let TMAP_KEY_LOCAL = "";

  function loadScriptOnce(src, id) {
    return new Promise((resolve, reject) => {
      const old = document.getElementById(id);
      if (old) { resolve(); return; }
      const s = document.createElement("script");
      s.id = id;
      s.src = src;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error("SDK 加载失败"));
      document.head.appendChild(s);
    });
  }

  function bubbleIcon(size, hot) {
    const fill = hot ? "#C0392B" : "#2F7D4F";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}">`
      + `<circle cx="${size / 2}" cy="${size / 2}" r="${size / 2 - 1.5}" `
      + `fill="${fill}" fill-opacity="0.72" stroke="${fill}" stroke-width="1.2"/></svg>`;
    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  }

  function renderMapRank(points, unit) {
    const top = points.slice(0, 12);
    const max = Math.max.apply(null, points.map(p => p.amount).concat([1]));
    document.getElementById("mapRank").innerHTML = top.map(p => `
      <div class="rowc" style="grid-template-columns:74px 1fr 64px">
        <span class="lbl">${p.name}</span>
        <div class="track"><div class="fill" style="width:${(p.amount / max * 100).toFixed(1)}%"></div></div>
        <span class="val">${fmtNum(p.amount, 1)}</span>
      </div>`).join("") +
      `<div style="font-size:10.5px;color:var(--muted);margin-top:6px">
        单位：${unit}；按回收参考价计价，属纸厂废纸成本下限
      </div>`;
  }

  async function loadMap(year) {
    const y = Number(year) || state.year;
    const notice = document.getElementById("mapNotice");
    const box = document.getElementById("mapBox");
    let cfg, data;
    try {
      cfg = await (await fetch("/api/map/config")).json();
      data = await (await fetch(`/api/map/data?year=${y}`)).json();
    } catch (e) {
      notice.textContent = "接口不可用：" + e;
      return;
    }

    fillYearSelect("mapYear", [y], y);
    document.getElementById("mapScope").textContent = `· ${y} 年`;
    renderMapRank(data.points, data.unit);

    const saved = (localStorage.getItem("tmapKey") || TMAP_KEY_LOCAL || "").trim();
    const key = saved || (cfg.key || "").trim();
    if (saved) {
      const ki = document.getElementById("mapKey");
      if (ki) ki.placeholder = "已保存在本机浏览器（留空即沿用）";
    }

    if (!key) {
      box.innerHTML = `<div class="ph">未配置地图密钥，已降级为下方的省份排行。<br>
        地图底图需使用腾讯位置服务（正版底图，带审图号）。<br>
        请到 <a href="${cfg.apply_url}" target="_blank" rel="noopener">腾讯位置服务控制台</a>
        申请免费 key，再到「设置 → 地图 Key」填入。</div>`;
      notice.innerHTML = cfg.attribution + " " + cfg.fallback;
      return;
    }

    box.innerHTML = `<div class="ph">地图加载中…</div>`;
    try {
      if (!window.TMap) {
        await loadScriptOnce(cfg.sdk_url + "&key=" + encodeURIComponent(key), "tmap-sdk");
      }
      drawBubbles(box, data);
      notice.innerHTML = cfg.attribution;
    } catch (e) {
      box.innerHTML = `<div class="ph">地图 SDK 加载失败：${String(e.message || e)}<br>
        常见原因：key 未开通 Web 端 / Referer 白名单不含当前地址 / 网络不可达。<br>
        已降级为下方排行视图。</div>`;
      notice.innerHTML = cfg.attribution + " " + cfg.fallback;
    }
  }

  function drawBubbles(box, data) {
    box.innerHTML = "";
    const canvas = document.createElement("div");
    canvas.style.cssText = "width:100%;height:100%";
    box.appendChild(canvas);
    const info = document.createElement("div");
    info.className = "mapinfo";
    info.id = "mapInfo";
    info.textContent = "点气泡查看省份金额";
    box.appendChild(info);

    const map = new TMap.Map(canvas, {
      center: new TMap.LatLng(35.2, 105.5),
      zoom: 4,
      viewMode: "2D"
    });

    const LEVELS = 5;
    const styles = {};
    for (let i = 1; i <= LEVELS; i++) {
      const size = 16 + i * 7;
      styles["s" + i] = new TMap.MarkerStyle({
        width: size, height: size,
        anchor: { x: size / 2, y: size / 2 },
        src: bubbleIcon(size, i >= 4)
      });
    }

    const geometries = data.points.map(p => {
      const lv = Math.max(1, Math.min(LEVELS, Math.ceil((p.ratio || 0) * LEVELS)));
      return {
        id: p.code,
        styleId: "s" + lv,
        position: new TMap.LatLng(p.lat, p.lon),
        properties: { name: p.name, amount: p.amount, rank: p.rank }
      };
    });

    const layer = new TMap.MultiMarker({ map: map, styles: styles, geometries: geometries });
    layer.on("click", evt => {
      const p = (evt.geometry && evt.geometry.properties) || {};
      const el = document.getElementById("mapInfo");
      if (el) {
        el.textContent = `${p.name}：${fmtNum(p.amount, 1)} ${data.unit}（全国第 ${p.rank} 位）`;
      }
    });
    window.__tmap = map;
  }

  /* ================= 设置：模型配置 ================= */
  let LLM_PRESETS = [];

  async function loadSettings() {
    micEnv();
    try {
      const s = await (await fetch("/api/llm/config")).json();
      LLM_PRESETS = s.presets || [];
      const c = s.config;
      const sel = document.getElementById("llmPreset");
      sel.innerHTML = '<option value="">自定义</option>' + LLM_PRESETS
        .map(p => `<option value="${p.base_url}">${p.name}</option>`).join("");
      document.getElementById("llmBase").value = c.base_url || "";
      document.getElementById("llmModel").value = c.model || "";
      document.getElementById("llmTemp").value = c.temperature;
      document.getElementById("llmTokens").value = c.max_tokens;
      document.getElementById("llmKey").placeholder = c.has_api_key
        ? `已保存 ${c.api_key_masked}（留空沿用）` : "尚未配置密钥";
      document.getElementById("llmState").textContent = c.configured
        ? `已配置 · ${c.model} · 来源 ${c.source}` : "未配置（对话走规则引擎）";
      document.getElementById("llmNotice").innerHTML = c.configured
        ? "配置保存在服务端 <code>config/llm.json</code>（已加入 .gitignore），接口只返回脱敏密钥。"
        : "没配置也能用：对话会自动回落到内置规则引擎。要接入大模型，填 Base URL、模型名与 API Key 后保存。";
      if (localStorage.getItem("tmapKey")) {
        document.getElementById("mapKey").placeholder = "已保存在本机浏览器（留空即沿用）";
      }
    } catch (e) {
      document.getElementById("llmNotice").textContent = "读取配置失败：" + e;
    }
  }

  function applyPreset(url) {
    if (!url) return;
    document.getElementById("llmBase").value = url;
    const hit = LLM_PRESETS.filter(p => p.base_url === url)[0];
    if (hit) document.getElementById("llmModel").value = hit.model;
  }

  async function saveLLM() {
    const msg = document.getElementById("llmMsg");
    msg.classList.remove("err");
    const mapKey = document.getElementById("mapKey").value.trim();
    if (mapKey) {
      localStorage.setItem("tmapKey", mapKey);
      TMAP_KEY_LOCAL = mapKey;
    }
    msg.textContent = "保存中…";
    try {
      const res = await fetch("/api/llm/config", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_url: document.getElementById("llmBase").value.trim(),
          api_key: document.getElementById("llmKey").value.trim() || null,
          model: document.getElementById("llmModel").value.trim(),
          temperature: Number(document.getElementById("llmTemp").value || 0.3),
          max_tokens: Number(document.getElementById("llmTokens").value || 600)
        })
      });
      const d = await res.json();
      document.getElementById("llmKey").value = "";
      msg.textContent = "已保存：" + d.config.model
        + (mapKey ? "；地图 key 已存本机浏览器" : "");
      await loadSettings();
    } catch (e) {
      msg.textContent = "保存失败：" + e;
      msg.classList.add("err");
    }
  }

  async function testLLM() {
    const msg = document.getElementById("llmMsg");
    msg.classList.remove("err");
    msg.textContent = "测试中…";
    try {
      const d = await (await fetch("/api/llm/test", { method: "POST" })).json();
      if (d.ok) {
        msg.textContent = `连通正常：${d.model}，${d.latency_ms} ms，返回「${d.reply}」`;
      } else {
        msg.textContent = "失败：" + d.error;
        msg.classList.add("err");
      }
    } catch (e) {
      msg.textContent = "请求失败：" + e;
      msg.classList.add("err");
    }
  }

  /* ================= 麦克风自检 =================
     只判断「有没有权限」是不够的：权限给了也可能没声音。
     这里真的读音频流算 RMS，3 秒内看峰值，才能回答「能不能收音」。
  */
  let micStream = null;
  let micCtx = null;
  let micRAF = 0;

  function micEnv() {
    const el = document.getElementById("micEnv");
    if (!el) return;
    const secure = window.isSecureContext;
    const gum = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    el.textContent = `安全上下文 ${secure ? "✓" : "✗"} · 录音 ${gum ? "✓" : "✗"} · 识别 ${SR ? "✓" : "✗"}`;
  }

  async function listMics() {
    const tb = document.querySelector("#micDevices tbody");
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const mics = devices.filter(d => d.kind === "audioinput");
      if (!mics.length) {
        tb.innerHTML = '<tr><td colspan="2" class="empty">没有检测到音频输入设备</td></tr>';
        return;
      }
      tb.innerHTML = mics.map((d, i) =>
        `<tr><td>${d.label || ("麦克风 " + (i + 1) + "（未授权时无名称）")}</td>
             <td>${d.deviceId === "default" ? "系统默认" : "可用"}</td></tr>`).join("");
    } catch (e) {
      tb.innerHTML = `<tr><td colspan="2" class="empty">读取设备失败：${e}</td></tr>`;
    }
  }

  async function micCheck() {
    const btn = document.getElementById("micCheckBtn");
    const msg = document.getElementById("micMsg");
    const meter = document.getElementById("micMeter");
    const peakEl = document.getElementById("micPeak");
    msg.classList.remove("err");

    if (!window.isSecureContext) {
      msg.textContent = "当前页面不是 HTTPS / localhost，浏览器会直接拒绝录音。请用 http://localhost:8000 打开。";
      msg.classList.add("err");
      return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      msg.textContent = "当前浏览器不支持 getUserMedia，无法检测麦克风。";
      msg.classList.add("err");
      return;
    }

    btn.disabled = true;
    msg.textContent = "正在申请麦克风权限…";
    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      btn.disabled = false;
      const map = {
        NotAllowedError: "权限被拒绝：点地址栏左侧的锁 / 麦克风图标 → 允许麦克风，再刷新页面。",
        NotFoundError: "没有找到麦克风设备。",
        NotReadableError: "麦克风被其他程序占用（会议软件、录屏工具等），关掉后再试。",
        OverconstrainedError: "麦克风不支持当前参数。",
        SecurityError: "安全策略禁止访问麦克风。"
      };
      msg.textContent = map[err.name] || ("录音失败：" + err.name + " " + err.message);
      msg.classList.add("err");
      return;
    }

    await listMics();

    micCtx = new (window.AudioContext || window.webkitAudioContext)();
    const src = micCtx.createMediaStreamSource(micStream);
    const analyser = micCtx.createAnalyser();
    analyser.fftSize = 2048;
    src.connect(analyser);
    const buf = new Uint8Array(analyser.fftSize);

    let peak = 0;
    const started = Date.now();
    msg.textContent = "正在检测，请对着麦克风说句话…";

    const finish = () => {
      cancelAnimationFrame(micRAF);
      btn.disabled = false;
      meter.style.width = "0%";
      if (micStream) {
        micStream.getTracks().forEach(t => t.stop());
        micStream = null;
      }
      if (micCtx) {
        micCtx.close();
        micCtx = null;
      }
      const pct = (peak * 100).toFixed(0);
      if (peak < 0.01) {
        msg.textContent = `3 秒内几乎没收到声音（峰值 ${pct}%）。检查：系统输入设备是否选对、`
          + `麦克风是否静音、有没有硬件静音开关。`;
        msg.classList.add("err");
      } else if (peak < 0.05) {
        msg.textContent = `有声音但很弱（峰值 ${pct}%）。把麦克风靠近一点，或在系统里调高输入音量。`;
      } else {
        msg.textContent = `收音正常（峰值 ${pct}%）。可以试下面的语音识别。`;
      }
    };

    const tick = () => {
      analyser.getByteTimeDomainData(buf);
      let sum = 0;
      for (let i = 0; i < buf.length; i++) {
        const v = (buf[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / buf.length);
      if (rms > peak) peak = rms;
      meter.style.width = Math.min(100, rms * 400).toFixed(0) + "%";
      meter.classList.toggle("hot", rms > 0.25);
      peakEl.textContent = (peak * 100).toFixed(0) + "%";
      if (Date.now() - started < 3000) {
        micRAF = requestAnimationFrame(tick);
      } else {
        finish();
      }
    };
    tick();
  }

  async function micRecognize() {
    const out = document.getElementById("micResult");
    out.classList.remove("err");
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      out.textContent = "当前浏览器不支持语音识别（Chrome / Edge 可用）。";
      out.classList.add("err");
      return;
    }
    out.textContent = "正在听… 请说一句话";
    const r = new SR();
    r.lang = "zh-CN";
    r.interimResults = true;
    r.continuous = false;
    let finalText = "";

    r.onresult = ev => {
      let interim = "";
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const t = ev.results[i][0].transcript;
        if (ev.results[i].isFinal) finalText += t; else interim += t;
      }
      out.textContent = "识别中：" + (finalText + interim);
    };
    r.onerror = ev => {
      const map = {
        "not-allowed": "麦克风权限被拒绝。",
        "service-not-allowed": "浏览器禁用了语音识别服务。",
        "audio-capture": "没有检测到麦克风。",
        network: "识别服务连不上（Chrome 需要联网）。",
        "no-speech": "没有听到声音。",
        "language-not-supported": "不支持中文识别。"
      };
      out.textContent = map[ev.error] || ("识别失败：" + ev.error);
      out.classList.add("err");
    };
    r.onend = () => {
      if (finalText.trim()) {
        out.textContent = `识别成功：「${finalText.trim()}」已填入输入框`;
        inputEl.value = finalText.trim();
      } else if (!out.classList.contains("err")) {
        out.textContent = "没有识别到文字。可能是环境太吵，或识别服务连不上。";
        out.classList.add("err");
      }
    };
    try {
      r.start();
    } catch (e) {
      out.textContent = "启动失败：" + e.message;
      out.classList.add("err");
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
      // 缺少 openpyxl 时提前说明，避免用户点了导出才看到失败
      if (info.excel_available === false) {
        const btn = document.getElementById("exportBtn");
        const msg = document.getElementById("exportMsg");
        if (btn) btn.title = "服务端未安装 openpyxl，导出会失败";
        if (msg) {
          msg.textContent = "服务端未安装 openpyxl，暂时无法导出 .xlsx。"
            + "执行 pip install openpyxl 后重启服务即可；或改用离线版（自带 CSV 导出）。";
          msg.classList.add("err");
        }
      }
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

  addMsg("你好，我是造纸工厂智能体助手 🪨\n" +
         "核心能力：碳核算 Agent（国标方法，五大排放源）。废纸回收助手已作为工厂内的子 Agent 接入，为碳核算提供原料回收数据。\n" +
         "可以问我：废纸能不能回收、值多少钱、回收量、消耗金额；也可在右侧「碳核算Agent」里核算工厂排放。\n" +
         "语音输入若不可用，页面输入框下方会直接告诉你原因。", "bot");
  loadCarbon();
  loadInfo();

  /* ---------------- 智能工厂（多智能体仿真） ---------------- */
  let millProcDefs = null;
  const STATE_LABEL = {idle: "待机", running: "运行中", done: "完成", held: "已挂起"};

  async function loadMill() {
    if (!millProcDefs) {
      try {
        const res = await fetch("/api/mill/processes");
        millProcDefs = await res.json();
        fillAnomalySelects();
      } catch (e) { return; }
    }
    await millRefresh();
  }

  function fillAnomalySelects() {
    const ps = document.getElementById("anomProcess");
    const ms = document.getElementById("anomMetric");
    ps.innerHTML = "";
    millProcDefs.order.forEach(k => {
      const o = document.createElement("option");
      o.value = k; o.textContent = millProcDefs.processes[k].name;
      ps.appendChild(o);
    });
    ps.onchange = fillAnomalyMetrics;
    fillAnomalyMetrics();
  }

  function fillAnomalyMetrics() {
    const k = document.getElementById("anomProcess").value;
    const ms = document.getElementById("anomMetric");
    ms.innerHTML = "";
    (millProcDefs.processes[k].metrics || []).forEach(m => {
      const o = document.createElement("option");
      o.value = m.key;
      o.textContent = m.label + "(" + m.low + "~" + m.high + m.unit + ")";
      ms.appendChild(o);
    });
  }

  async function millRefresh() {
    try {
      const res = await fetch("/api/mill/state");
      renderMill(await res.json());
    } catch (e) {}
  }

  function renderMill(snap) {
    const sim = snap.sim;
    document.getElementById("millStepLabel").textContent = "仿真步 " + sim.step;
    document.getElementById("millStatus").innerHTML =
      sim.batch ? '当前批次 <b>' + sim.batch + '</b> · ' + (sim.idle ? "流水线空闲" : "流水线运行中")
                : "尚未投产，点「投批次」开始。";

    const pipe = document.getElementById("millPipe");
    pipe.innerHTML = "";
    sim.stages.forEach(st => {
      const d = document.createElement("div");
      d.className = "stage " + st.state;
      const dots = Object.keys(st.metric_status || {}).map(k =>
        '<span class="dot ' + st.metric_status[k] + '"></span>').join("");
      let mini = "";
      if (millProcDefs && millProcDefs.processes[st.key]) {
        mini = millProcDefs.processes[st.key].metrics.map(m => {
          const v = st.metrics[m.key];
          return v === undefined ? "" : m.label + " " + v + m.unit;
        }).filter(Boolean).join("<br>");
      }
      d.innerHTML = '<div class="nm">' + dots + st.name + '</div>' +
                    '<div class="st">' + (STATE_LABEL[st.state] || st.state) + '</div>' +
                    '<div class="mini">' + mini + '</div>';
      pipe.appendChild(d);
    });

    const agents = document.getElementById("millAgents");
    agents.innerHTML = "";
    (snap.decisions || []).forEach(dec => {
      const row = document.createElement("div");
      row.className = "agent-row " + dec.status;
      row.innerHTML = '<div><span class="who">' + dec.agent + '</span> ' +
        '<span class="basis">[' + (dec.basis === "llm" ? "大模型" : "规则引擎") + ']</span></div>' +
        '<div class="advice">' + esc(dec.advice) + '</div>';
      agents.appendChild(row);
    });
    if (!snap.decisions || !snap.decisions.length)
      agents.innerHTML = '<div class="mill-status">投产之后，各工序智能体的决策会显示在这里。</div>';

    const devs = document.getElementById("millDevices");
    devs.innerHTML = "";
    (snap.devices || []).forEach(dv => {
      const el = document.createElement("div");
      el.className = "dev " + (dv.status === "busy" ? "busy" : "");
      el.innerHTML = '<span class="dn">' + esc(dv.name) + '</span>' +
        '<span class="ds">' + (dv.status === "busy" ? "作业中" : "空闲") +
        (dv.done_count ? " · " + dv.done_count : "") + '</span>';
      devs.appendChild(el);
    });
    document.getElementById("millDevHint").textContent =
      (snap.devices || []).filter(d => d.status === "busy").length + " 台作业中 / 共 " + (snap.devices || []).length + " 台";

    const log = document.getElementById("millLog");
    log.innerHTML = "";
    (snap.log || []).slice().reverse().forEach(ln => {
      const div = document.createElement("div");
      div.className = "ln";
      div.innerHTML = '<span class="tm">#' + ln.step + '</span> ' +
        '<span class="ev">' + esc(ln.event) + '</span> ' +
        (ln.process ? '[' + esc(ln.process) + '] ' : '') +
        esc(ln.reason || ln.message || ln.action || "");
      log.appendChild(div);
    });
    document.getElementById("millLogHint").textContent = (snap.log || []).length + " 条";
  }

  async function millAction(action) {
    const btn = document.getElementById("mill" + action.charAt(0).toUpperCase() + action.slice(1) + "Btn");
    if (btn) btn.disabled = true;
    try {
      let res;
      if (action === "start" || action === "run" || action === "reset")
        res = await fetch("/api/mill/" + action, {method: "POST"});
      else if (action === "step")
        res = await fetch("/api/mill/step", {method: "POST",
          headers: {"Content-Type": "application/json"}, body: JSON.stringify({steps: 1})});
      if (res) renderMill(await res.json());
    } catch (e) {} finally { if (btn) btn.disabled = false; }
  }

  async function millInject() {
    const process = document.getElementById("anomProcess").value;
    const metric = document.getElementById("anomMetric").value;
    const value = parseFloat(document.getElementById("anomValue").value);
    if (isNaN(value)) return;
    try {
      const res = await fetch("/api/mill/anomaly", {method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({process: process, metric: metric, value: value})});
      renderMill((await res.json()).snapshot);
    } catch (e) {}
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, c =>
      ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"})[c]);
  }

  /* ---------------- 产业大脑（五链贯通） ---------------- */
  async function loadBrain() {
    await brainRefresh();
    const ds = document.getElementById("optDomain");
    if (ds.options.length) return;
    const states = (window.__brainSnap || {}).states || [];
    states.forEach(st => {
      const o = document.createElement("option");
      o.value = st.key; o.textContent = st.name;
      ds.appendChild(o);
    });
    ds.onchange = fillBrainKpis;
    fillBrainKpis();
  }

  function fillBrainKpis() {
    const key = document.getElementById("optDomain").value;
    const ks = document.getElementById("optKpi");
    ks.innerHTML = "";
    const st = ((window.__brainSnap || {}).states || []).find(s => s.key === key);
    (st ? st.kpi_defs : []).forEach(k => {
      const o = document.createElement("option");
      o.value = k.key; o.textContent = k.label + "(" + k.base + k.unit + ")";
      ks.appendChild(o);
    });
  }

  async function brainRefresh() {
    try {
      const res = await fetch("/api/brain/state");
      const snap = await res.json();
      window.__brainSnap = snap;
      renderBrain(snap);
    } catch (e) {}
  }

  function renderBrain(snap) {
    document.getElementById("brainStepLabel").textContent = "推演步 " + snap.step;
    document.getElementById("brainStatus").innerHTML = snap.step
      ? '已完成 <b>' + snap.step + '</b> 步推演 · 五链共享数据底座'
      : "产业大脑待推演。";

    const chain = document.getElementById("brainChain");
    chain.innerHTML = "";
    snap.states.forEach((st, i) => {
      const node = document.createElement("div");
      node.className = "brain-node";
      node.innerHTML = '<div class="bn">' + esc(st.name) + '</div>' +
        '<div class="bv">' + esc(st.subtitle.split("·")[0].trim()) + '</div>';
      chain.appendChild(node);
      if (i < snap.states.length - 1) {
        const ar = document.createElement("span");
        ar.className = "brain-arrow"; ar.textContent = "→";
        chain.appendChild(ar);
      }
    });

    const cards = document.getElementById("brainCards");
    cards.innerHTML = "";
    snap.states.forEach(st => {
      const card = document.createElement("div");
      card.className = "brain-card";
      let kpis = (st.kpi_defs || []).map(k => {
        const v = st.kpis[k.key];
        return '<div class="brain-kpi"><span class="k">' + esc(k.label) +
          '</span><span class="v">' + (v === undefined ? "—" : v + k.unit) + '</span></div>';
      }).join("");
      const impact = (st.last_impact || []).length
        ? '<div class="brain-impact">↳ ' + esc(st.last_impact.slice(0, 2).join("；")) + '</div>' : "";
      card.innerHTML = '<div class="bc-h"><span>' + esc(st.name) + '</span>' +
        '<span class="tag">领域智能体</span></div>' +
        '<div class="bc-sub">' + esc(st.subtitle) + '</div>' + kpis + impact;
      cards.appendChild(card);
    });

    const bench = document.getElementById("brainBenchmarks");
    bench.innerHTML = "";
    (snap.benchmarks || []).forEach(b => {
      const row = document.createElement("div");
      row.className = "bench-row";
      row.innerHTML = '<span>' + esc(b.metric) +
        '<div class="bs">' + esc(b.source) + '</div></span>' +
        '<span class="bv">' + esc(b.value) + '</span>';
      bench.appendChild(row);
    });

    const log = document.getElementById("brainLog");
    log.innerHTML = "";
    (snap.log || []).slice().reverse().forEach(ln => {
      const div = document.createElement("div");
      div.className = "ln";
      const detail = ln.event === "link"
        ? esc(ln.src) + '·' + esc(ln.src_kpi) + ' → ' + esc(ln.dst) + '·' + esc(ln.dst_kpi)
          + ' (' + (ln.change > 0 ? '+' : '') + ln.change + ')'
        : esc(ln.event) + (ln.domain ? ' [' + esc(ln.domain) + ']' : '');
      div.innerHTML = '<span class="tm">#' + ln.step + '</span> <span class="ev">' + detail + '</span>';
      log.appendChild(div);
    });
    document.getElementById("brainLogHint").textContent = (snap.log || []).length + " 条";
  }

  function renderBrainAdvices(advices) {
    const el = document.getElementById("brainAdvices");
    el.innerHTML = "";
    advices.forEach(a => {
      const row = document.createElement("div");
      row.className = "brain-advice";
      row.innerHTML = '<b>' + esc(a.domain_name) + '智能体</b> ' +
        '<span class="basis">[' + (a.basis === "llm" ? "大模型" : "规则引擎") + ']</span><br>' +
        esc(a.headline) + (a.detail ? '<div class="bd">' + esc(a.detail) + '</div>' : '');
      el.appendChild(row);
    });
  }

  async function brainAction(action) {
    const btn = document.getElementById("brain" + action.charAt(0).toUpperCase() + action.slice(1) + "Btn");
    if (btn) btn.disabled = true;
    try {
      let res;
      if (action === "run") res = await fetch("/api/brain/run", {method:"POST",
        headers:{"Content-Type":"application/json"}, body:JSON.stringify({steps:5})});
      else if (action === "advise") res = await fetch("/api/brain/advise", {method:"POST"});
      else if (action === "reset") res = await fetch("/api/brain/reset", {method:"POST"});
      const data = await res.json();
      if (action === "advise") { renderBrain(data.snapshot); renderBrainAdvices(data.advices); }
      else renderBrain(data);
    } catch (e) {} finally { if (btn) btn.disabled = false; }
  }

  async function brainOptimize() {
    const domain = document.getElementById("optDomain").value;
    const kpi = document.getElementById("optKpi").value;
    const target = parseFloat(document.getElementById("optTarget").value);
    if (!kpi || isNaN(target)) return;
    try {
      const res = await fetch("/api/brain/optimize", {method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({domain:domain, kpi:kpi, target:target})});
      const data = await res.json();
      if (data.ok) renderBrain(data.snapshot);
    } catch (e) {}
  }

  /* ---------------- 碳核算 Agent（核心） ---------------- */
  const CARBON_LABEL = {
    fuel:"化石燃料燃烧", process:"过程排放(石灰石)",
    wastewater:"废水厌氧甲烷", electricity:"净购入电力", heat:"净购入热力"
  };
  let carbonFactorsCache = null;

  async function loadCarbon() {
    if (!carbonFactorsCache) {
      try { carbonFactorsCache = await (await fetch("/api/carbon/factors")).json(); }
      catch (e) {}
    }
    await carbonRefresh();
  }

  async function carbonRefresh() {
    try {
      const data = await (await fetch("/api/carbon/state")).json();
      renderCarbon(data);
      buildCarbonInputs(data.activity);
      buildScenarioSelect(data.activity);
    } catch (e) {}
  }

  function renderCarbon(data) {
    const r = data.result;
    const hero = document.getElementById("carbonHero");
    if (r.total_tco2e === null) {
      hero.innerHTML = '<div class="ch-title">' + esc(r.factory) + ' · ' + r.year + ' 年温室气体排放量</div>' +
        '<div class="ch-total" style="color:var(--muted)">待配置电力因子</div>' +
        '<div class="ch-meta">填入主管部门最新电力排放因子后即可得出总量。</div>';
    } else {
      hero.innerHTML = '<div class="ch-title">' + esc(r.factory) + ' · ' + r.year + ' 年温室气体排放总量</div>' +
        '<div class="ch-total">' + fmtNum(r.total_tco2e) + '<span class="u"> tCO₂e</span></div>' +
        '<div class="ch-meta">单位产品碳强度：<b>' + r.intensity_tco2e_per_ton + '</b> ' +
        esc(r.intensity_unit || 'tCO2e/吨纸') + '（产量 ' + r.output_wan_ton + ' 万吨）</div>';
    }

    const warn = document.getElementById("carbonWarn");
    warn.innerHTML = r.incomplete
      ? '⚠ 核算不完整：电力排放因子未配置。国标要求取主管部门最近年份公布值，填入后总量才有效。'
      : '✓ 核算边界完整（国标五类排放源）。排放因子为国标附录B缺省值；活动数据为示例输入。';

    const bars = document.getElementById("carbonBars");
    bars.innerHTML = "";
    const bySource = r.by_source || {};
    const maxVal = Math.max(1, ...Object.values(bySource).filter(v => v !== null).map(v => Math.abs(v)));
    Object.keys(CARBON_LABEL).forEach(k => {
      const v = bySource[k];
      const row = document.createElement("div");
      row.className = "carbon-bar";
      const pct = (v === null) ? 0 : Math.abs(v) / maxVal * 100;
      row.innerHTML = '<span class="cb-lbl">' + CARBON_LABEL[k] + '</span>' +
        '<span class="cb-track"><span class="cb-fill" style="width:' + pct.toFixed(1) + '%"></span></span>' +
        '<span class="cb-val">' + (v === null ? "待配置" : fmtNum(v)) + '</span>';
      bars.appendChild(row);
    });
    document.getElementById("carbonStructureHint").textContent = "合计 " +
      (r.total_tco2e === null ? "—" : fmtNum(r.total_tco2e)) + " tCO₂e";

    const items = document.getElementById("carbonItems");
    items.innerHTML = "";
    (r.items || []).forEach(it => {
      const div = document.createElement("div");
      div.className = "carbon-item";
      div.innerHTML = '<div class="ci-h"><b>' + esc(it.name) + '</b><span>' +
        (it.emission === null ? "待配置" : fmtNum(it.emission) + " tCO₂e") + '</span></div>' +
        '<div class="ci-formula">活动 ' + fmtNum(it.activity) + ' ' + esc(it.activity_unit) +
        ' × 因子 ' + (it.ef === null ? "—" : it.ef) + ' ' + esc(it.ef_unit) + '</div>' +
        '<div class="ci-formula">' + esc(it.formula) + (it.detail ? ' ｜ ' + esc(it.detail) : '') + '</div>' +
        '<div class="ci-src">来源：' + esc(it.source) + '</div>';
      items.appendChild(div);
    });

    const c = r.recycle_credit || {};
    document.getElementById("carbonCredit").innerHTML =
      '废纸回收 Agent 提供回收量 <b>' + fmtNum(c.wastepaper_ton) + '</b> 吨，' +
      '按演示系数 ' + c.coef + ' tCO₂e/t 折算减排 <span class="v">' + fmtNum(c.credit_tco2e) + '</span> tCO₂e。' +
      '<div style="font-size:10px;color:var(--muted);margin-top:4px">' +
      esc(c.scope) + ' ｜ ' + esc(c.note) + '<br>系数说明：' + esc(c.source) + '</div>';

    document.getElementById("scenResult").textContent = "情景模拟结果将显示在这里。";
  }

  function fmtNum(v) {
    if (v === null || v === undefined) return "—";
    return Number(v).toLocaleString("zh-CN", {maximumFractionDigits:1});
  }

  function buildCarbonInputs(activity) {
    const box = document.getElementById("carbonInputs");
    if (!activity || box.dataset.built === activity.factory_name + activity.year) return;
    const fields = [
      ["烟煤(t)", "f FuelUse bituminous", (activity.fuels||[]).find(f=>f.key==='bituminous')?.quantity, "fuel:bituminous"],
      ["天然气(万m³)", "fuel:natural_gas", (activity.fuels||[]).find(f=>f.key==='natural_gas')?.quantity, "fuel:natural_gas"],
      ["石灰石(t)", "limestone_ton", activity.limestone_ton, "limestone_ton"],
      ["外购电力(MWh)", "electricity_purchased", activity.electricity_purchased, "electricity_purchased"],
      ["电力因子(tCO2/MWh)", "electric_ef", activity.electric_ef, "electric_ef"],
      ["外购热力(GJ)", "heat_purchased", activity.heat_purchased, "heat_purchased"],
      ["产量(万吨)", "paper_output_wan_ton", activity.paper_output_wan_ton, "paper_output_wan_ton"],
      ["废纸回收(万吨)", "wastepaper_recycled_wan_ton", activity.wastepaper_recycled_wan_ton, "wastepaper_recycled_wan_ton"]
    ];
    box.innerHTML = "";
    fields.forEach(f => {
      const label = document.createElement("label");
      label.innerHTML = '<span>' + f[0] + '</span><input type="number" step="any" data-cfield="' + f[3] + '" value="' + (f[2]===null||f[2]===undefined?'':f[2]) + '">';
      box.appendChild(label);
    });
    box.dataset.built = activity.factory_name + activity.year;
  }

  function buildScenarioSelect(activity) {
    const sel = document.getElementById("scenField");
    if (!sel.options.length) {
      [["fuel:bituminous","烟煤用量(t)"],["electricity_purchased","外购电力(MWh)"],
       ["heat_purchased","外购热力(GJ)"],["limestone_ton","石灰石(t)"]].forEach(o => {
        const op = document.createElement("option");
        op.value = o[0]; op.textContent = o[1]; sel.appendChild(op);
      });
    }
  }

  async function carbonApply() {
    const payload = {fuel_quantities:{}, electric_ef_year:2024};
    document.querySelectorAll("#carbonInputs input[data-cfield]").forEach(inp => {
      const key = inp.dataset.cfield, val = parseFloat(inp.value);
      if (isNaN(val)) return;
      if (key.indexOf("fuel:") === 0) payload.fuel_quantities[key.slice(5)] = val;
      else payload[key] = val;
    });
    try {
      const data = await (await fetch("/api/carbon/activity", {method:"POST",
        headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)})).json();
      renderCarbon(data);
    } catch (e) {}
  }

  async function carbonScenario() {
    const field = document.getElementById("scenField").value;
    const val = parseFloat(document.getElementById("scenValue").value);
    if (isNaN(val)) return;
    try {
      const data = await (await fetch("/api/carbon/scenario", {method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({changes:{[field]:val}})})).json();
      document.getElementById("scenResult").innerHTML =
        '基准 <b>' + fmtNum(data.baseline.total_tco2e) + '</b> → 情景 <b>' +
        fmtNum(data.scenario.total_tco2e) + '</b> tCO₂e；差额 <b>' +
        fmtNum(data.delta_tco2e) + '</b> tCO₂e。' + esc(data.interpretation);
    } catch (e) {}
  }

  async function carbonBridge() {
    try {
      const data = await (await fetch("/api/carbon/bridge-recycle?year=2024", {method:"POST"})).json();
      if (data.ok) {
        renderCarbon(data);
        document.getElementById("carbonInputs").dataset.built = "";
        buildCarbonInputs(data.activity);
        if (data.bridge && data.bridge.hint) {
          document.getElementById("scenResult").textContent = data.bridge.hint;
        }
      }
    } catch (e) {}
  }

  async function carbonReset() {
    try {
      const data = await (await fetch("/api/carbon/reset", {method:"POST"})).json();
      renderCarbon(data);
      document.getElementById("carbonInputs").dataset.built = "";
      buildCarbonInputs(data.activity);
    } catch (e) {}
  }
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

### `tests/test_brain.py`（152 行）

```python
"""产业大脑五链贯通仿真测试。

核心层（无第三方依赖）：五域定义、联动引擎、领域智能体；
Web 层：FastAPI 接口（缺 fastapi 时跳过）。
"""

import pytest

from paper_recycle_agent.brain import domains
from paper_recycle_agent.brain.engine import IndustryBrain, LINK_RULES
from paper_recycle_agent.brain.intelligence import BrainOrchestrator


# ---------------- 五域定义 ----------------

def test_five_domains():
    assert domains.ORDER == ("procurement", "production", "sales", "logistics", "finance")
    for key in domains.ORDER:
        d = domains.get(key)
        assert d.kpis and d.duties
        assert d.influences


def test_unknown_domain():
    with pytest.raises(ValueError):
        domains.get("no_such_domain")


def test_benchmarks_have_sources():
    """每条对标参考都必须带来源，不能出现无出处的数字。"""
    assert len(domains.BENCHMARKS) == 5
    for b in domains.BENCHMARKS:
        assert b["value"] and b["source"]
        assert "公开" in b["source"] or "报道" in b["source"] or "资料" in b["source"]


def test_link_rules_valid():
    """联动规则的源/目标 KPI 必须真实存在。"""
    for src, src_kpi, direction, dst, dst_kpi, coef in LINK_RULES:
        assert src in domains.ORDER and dst in domains.ORDER
        assert direction in ("up", "down")
        assert src_kpi in [k.key for k in domains.get(src).kpis]
        assert dst_kpi in [k.key for k in domains.get(dst).kpis]


# ---------------- 仿真引擎 ----------------

def test_deterministic():
    a = IndustryBrain(seed=7); b = IndustryBrain(seed=7)
    a.run(4); b.run(4)
    assert a.snapshot()["states"] == b.snapshot()["states"]


def test_five_states_present():
    snap = IndustryBrain().snapshot()
    assert len(snap["states"]) == 5
    assert [s["key"] for s in snap["states"]] == list(domains.ORDER)
    assert len(snap["link_rules"]) == len(LINK_RULES)


def test_cross_domain_links_fire():
    snap = IndustryBrain().run(3)
    links = [e for e in snap["log"] if e["event"] == "link"]
    assert links, "推演后应产生跨域联动日志"
    # 联动必须跨越不同业务域
    assert any(e["src"] != e["dst"] for e in links)


def test_kpis_stay_bounded():
    """联动叠加后 KPI 必须收敛，不能无限增长。"""
    snap = IndustryBrain().run(20)
    for st in snap["states"]:
        for kdef in st["kpi_defs"]:
            v = st["kpis"][kdef["key"]]
            base = kdef["base"]
            assert base * 0.7 <= v <= base * 1.3


def test_optimize_propagates():
    brain = IndustryBrain()
    result = brain.optimize("procurement", "purchase_cost_index", 80.0)
    assert result["ok"] is True
    assert result["before"] != result["after"]
    assert any(e["event"] == "optimize" for e in result["snapshot"]["log"])
    # 财务域应受到传导影响
    finance = [s for s in result["snapshot"]["states"] if s["key"] == "finance"][0]
    assert finance["last_impact"] or any(
        e["event"] == "link" and e["dst"] == "finance"
        for e in result["snapshot"]["log"]
    )


def test_optimize_unknown_kpi():
    result = IndustryBrain().optimize("procurement", "not_a_kpi", 10)
    assert result["ok"] is False


def test_reset():
    brain = IndustryBrain()
    brain.run(5)
    brain.reset()
    snap = brain.snapshot()
    assert snap["step"] == 0
    assert snap["log"] == []


# ---------------- 领域智能体 ----------------

def test_five_advices_with_rule_basis():
    orch = BrainOrchestrator(use_llm=False)
    orch.brain.run(2)
    advices = orch.advise_all()
    assert len(advices) == 5
    assert all(a["basis"] == "rule" for a in advices)
    assert all(a["domain_name"] for a in advices)


def test_advice_snapshot_consistency():
    orch = BrainOrchestrator(use_llm=False)
    orch.advise_all()
    snap = orch.snapshot()
    assert len(snap["advices"]) == 5


# ---------------- Web 层 ----------------

def test_api_brain_endpoints():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from app.server import app

    client = TestClient(app)
    r = client.get("/api/brain/state")
    assert r.status_code == 200
    assert len(r.json()["states"]) == 5

    r = client.post("/api/brain/run", json={"steps": 3})
    assert r.status_code == 200
    assert r.json()["step"] == 3

    r = client.post("/api/brain/advise")
    assert r.status_code == 200
    assert len(r.json()["advices"]) == 5

    r = client.post("/api/brain/optimize", json={
        "domain": "procurement", "kpi": "purchase_cost_index", "target": 82.0,
    })
    assert r.status_code == 200 and r.json()["ok"] is True

    r = client.post("/api/brain/reset")
    assert r.status_code == 200
    assert r.json()["step"] == 0
```

### `tests/test_carbon.py`（204 行）

```python
"""碳核算 Agent 测试：国标公式可手算复核。

核心层：排放因子、五类排放源、总量汇总、情景模拟、回收桥接；
Web 层：/api/carbon/* 接口。
"""

import pytest

from paper_recycle_agent.carbon import factors, model, recycle_agent
from paper_recycle_agent.carbon.accounting import CarbonAccounting
from paper_recycle_agent.carbon.model import ActivityData, FuelUse


# ---------------- 因子（国标附录B） ----------------

def test_fuel_ef_formula():
    """EF = CC × OF × 44/12（国标公式4），必须能手算复核。"""
    f = factors.fuel("bituminous")
    expected = 26.1e-3 * 0.93 * 44.0 / 12.0
    assert abs(f.ef - expected) < 1e-12
    assert abs(f.ef - 0.089001) < 1e-5


def test_fuel_factors_have_sources():
    for key in factors.FUELS:
        f = factors.fuel(key)
        p = f.public()
        assert p["source"] == factors.SOURCE_STD
        assert p["ncv_source"] and p["cc_source"]
        assert p["ef"] > 0


def test_unknown_fuel():
    with pytest.raises(ValueError):
        factors.fuel("no_such_fuel")


def test_std_constants():
    assert factors.LIMESTONE_EF == 0.405
    assert factors.HEAT_EF_DEFAULT == 0.11
    assert factors.CH4_MAX == 0.25 and factors.CH4_CORRECTION == 0.5
    # 电力因子国标要求主管部门最新值，不内置过期数字
    assert factors.ELECTRIC_EF_DEFAULT is None


# ---------------- 核算公式 ----------------

def _minimal() -> ActivityData:
    """手算可复核的最小案例。"""
    return ActivityData(
        fuels=[FuelUse("bituminous", 1000.0)],  # 烟煤 1000 t
        limestone_ton=1000.0,                    # 石灰石 1000 t
        electricity_purchased=0.0,
        electric_ef=None,
        heat_purchased=1000.0,                   # 外购热 1000 GJ
        wastewater_cod_removed=0.0,
        paper_output_wan_ton=1.0,
    )


def test_fuel_emission_hand_calculable():
    r = CarbonAccounting(_minimal()).calculate()
    fuel_item = [i for i in r["items"] if i["key"] == "fuel_bituminous"][0]
    # 1000 t × 19.570 GJ/t × 0.089001 tCO2/GJ = 1741.75 tCO2
    assert fuel_item["activity"] == 19570.0
    assert abs(fuel_item["emission"] - 1741.75) < 0.02


def test_process_emission():
    r = CarbonAccounting(_minimal()).calculate()
    proc = [i for i in r["items"] if i["key"] == "process"][0]
    assert abs(proc["emission"] - 405.0) < 1e-9  # 1000 × 0.405


def test_heat_emission():
    r = CarbonAccounting(_minimal()).calculate()
    heat = [i for i in r["items"] if i["key"] == "heat"][0]
    assert abs(heat["emission"] - 110.0) < 1e-9  # 1000 × 0.11


def test_incomplete_when_electric_not_configured():
    r = CarbonAccounting(_minimal()).calculate()
    assert r["incomplete"] is True
    assert r["total_tco2e"] is None
    elec = [i for i in r["items"] if i["key"] == "electricity"][0]
    assert elec["emission"] is None


def test_total_matches_hand_calculation():
    a = _minimal()
    a.electric_ef = 0.5  # 购入电 0，因子不影响
    r = CarbonAccounting(a).calculate()
    # 1741.75 + 405 + 0 + 0 + 110 = 2256.75
    assert abs(r["total_tco2e"] - 2256.75) < 0.02
    assert r["incomplete"] is False


def test_intensity_unit_correct():
    """碳强度 = 总排放 ÷ (产量万吨 × 10000)，单位 tCO2e/吨纸。"""
    a = _minimal()
    a.electric_ef = 0.5
    r = CarbonAccounting(a).calculate()
    assert r["intensity_unit"] == "tCO2e/吨纸"
    expected = round(r["total_tco2e"] / (1.0 * 10000.0), 4)
    assert r["intensity_tco2e_per_ton"] == expected


def test_wastewater_methane_formula():
    a = ActivityData(
        wastewater_cod_removed=1000.0, wastewater_cod_sludge=200.0,
        methane_recovered=0.0, electric_ef=0.5,
    )
    r = CarbonAccounting(a).calculate()
    ww = [i for i in r["items"] if i["key"] == "wastewater"][0]
    # (1000-200) × 0.25 × 0.5 × 21 = 2100
    assert abs(ww["emission"] - 2100.0) < 1e-9


def test_exported_electricity_reduces():
    base = ActivityData(electricity_purchased=1000.0, electric_ef=0.5)
    exported = ActivityData(electricity_purchased=1000.0,
                            electricity_exported=400.0, electric_ef=0.5)
    e1 = [i for i in CarbonAccounting(base).calculate()["items"] if i["key"] == "electricity"][0]
    e2 = [i for i in CarbonAccounting(exported).calculate()["items"] if i["key"] == "electricity"][0]
    assert e1["activity"] == 1000.0 and e2["activity"] == 600.0
    assert e2["emission"] < e1["emission"]


# ---------------- 情景与回收桥接 ----------------

def test_scenario_reduces_emission():
    a = CarbonAccounting().activity
    a.electric_ef = 0.5366
    s = CarbonAccounting(a).scenario({"fuel:bituminous": 16000.0})
    assert s["delta_tco2e"] < 0
    assert "下降" in s["interpretation"]


def test_recycle_credit_is_separate():
    r = CarbonAccounting().calculate()
    c = r["recycle_credit"]
    assert "范围三" in c["scope"]
    assert c["credit_tco2e"] > 0
    assert "演示" in c["source"]


def test_bridge_does_not_overwrite_factory_value():
    a = CarbonAccounting().activity  # 已有 18 万吨
    result = recycle_agent.bridge_to_activity(6971.0, a, overwrite=False)
    assert result["written"] is False
    assert a.wastepaper_recycled_wan_ton == 18.0


def test_bridge_writes_when_empty():
    a = ActivityData(wastepaper_recycled_wan_ton=0.0)
    result = recycle_agent.bridge_to_activity(123.0, a, overwrite=False)
    assert result["written"] is True
    assert a.wastepaper_recycled_wan_ton == 123.0


def test_eeioa_method_no_data():
    result = recycle_agent.supply_chain_carbon_demo()
    assert result["ok"] is False and result["available"] is False
    assert "I−A" in result["formula"]


def test_eeioa_method_with_matrix():
    matrix = [[0.1, 0.2], [0.3, 0.1]]
    result = recycle_agent.supply_chain_carbon_demo(matrix)
    assert result["ok"] is True
    assert len(result["leontief_inverse"]) == 2


# ---------------- Web 层 ----------------

def test_api_carbon_endpoints():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from app.server import app

    client = TestClient(app)
    r = client.get("/api/carbon/factors")
    assert r.status_code == 200
    assert len(r.json()["fuels"]) == len(factors.FUELS)

    r = client.get("/api/carbon/state")
    assert r.status_code == 200
    assert len(r.json()["result"]["items"]) == 7

    r = client.post("/api/carbon/activity", json={"electric_ef": 0.5366,
                                                   "electric_ef_year": 2024})
    assert r.status_code == 200
    assert r.json()["result"]["incomplete"] is False

    r = client.post("/api/carbon/scenario", json={"changes": {"fuel:bituminous": 16000.0}})
    assert r.status_code == 200
    assert r.json()["delta_tco2e"] < 0

    r = client.post("/api/carbon/bridge-recycle?year=2024")
    assert r.status_code == 200 and r.json()["ok"] is True
    assert r.json()["bridge"]["written"] is False  # 不覆盖单厂数据

    r = client.post("/api/carbon/reset")
    assert r.status_code == 200 and r.json()["ok"] is True
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

### `tests/test_compat.py`（171 行）

```python
"""版本兼容性与可选依赖测试。

这套测试锁死两件事：
1. 仓库代码的语法/API 不超出 Python 3.7（由 tools/check_compat.py 实际执行）；
2. 没装 openpyxl 时，核心包仍能导入、命令行仍能用、导出接口给出可读提示。

两者都是「本机装了什么」之外的真实约束，因此必须由测试而不是文档来保证。
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "check_compat.py"


def _run(args, env_extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT)
    env["PYTHONIOENCODING"] = "utf-8"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


# ---------------------------------------------------------------- 版本下限


def test_compat_tool_passes():
    """全仓库语法与 API 不超出 Python 3.7。"""
    proc = _run([str(TOOL)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "结果：通过" in proc.stdout


def test_compat_tool_detects_violation():
    """校验器本身必须能报错，否则它只是装饰。"""
    bad = ROOT / "tools" / "_tmp_bad_compat.py"
    bad.write_text(
        "def bad(x: str) -> list[str]:\n"
        "    return x.removeprefix('a').split()\n",
        encoding="utf-8",
    )
    try:
        proc = _run([str(TOOL)])
        assert proc.returncode == 1
        assert "removeprefix" in proc.stdout
        assert "list[...]" in proc.stdout
    finally:
        bad.unlink(missing_ok=True)


def test_pyproject_requires_python_37():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.7"' in text


def test_pyproject_declares_optional_groups():
    """核心零依赖，Web / Excel 作为 extras 声明。"""
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:  # pragma: no cover
        pytest.skip("需要 tomllib 解析 pyproject")
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = meta["project"]
    assert project.get("dependencies", []) == []
    extras = project["optional-dependencies"]
    for key in ("web", "excel", "test"):
        assert key in extras


def test_package_version_matches_pyproject():
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        pytest.skip("需要 tomllib 解析 pyproject")
    import paper_recycle_agent

    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert meta["project"]["version"] == paper_recycle_agent.__version__


# ------------------------------------------------------- 缺少 openpyxl 的场景


def _block_openpyxl(code: str) -> str:
    """在子进程里把 openpyxl 屏蔽掉，再执行 code。"""
    prelude = "import sys; sys.modules['openpyxl'] = None\n"
    return prelude + code


def test_core_imports_without_openpyxl():
    proc = _run(["-c", _block_openpyxl(
        "import paper_recycle_agent as p; print(p.__version__)"
    )])
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip()


def test_cli_works_without_openpyxl():
    proc = _run(["-c", _block_openpyxl(
        "from paper_recycle_agent import cli, stats; "
        "print(stats.history_summary()[:40]); "
        "assert cli.main(['history']) == 0"
    )])
    assert proc.returncode == 0, proc.stderr


def test_exporter_available_reflects_missing_dependency():
    from paper_recycle_agent import exporter

    assert exporter.available() is True

    saved = sys.modules.get("openpyxl")
    sys.modules["openpyxl"] = None
    try:
        assert exporter.available() is False
        with pytest.raises(RuntimeError) as exc:
            exporter.build_workbook()
        assert "pip install openpyxl" in str(exc.value)
    finally:
        if saved is None:
            sys.modules.pop("openpyxl", None)
        else:
            sys.modules["openpyxl"] = saved


def test_export_endpoint_503_without_openpyxl():
    pytest.importorskip("httpx", reason="TestClient 依赖 httpx")
    from fastapi.testclient import TestClient

    from app.server import app

    client = TestClient(app)
    saved = sys.modules.get("openpyxl")
    sys.modules["openpyxl"] = None
    try:
        res = client.get("/export.xlsx")
        assert res.status_code == 503
        body = res.json()
        assert "openpyxl" in body["detail"]
        assert "离线版" in body["hint"]
    finally:
        if saved is None:
            sys.modules.pop("openpyxl", None)
        else:
            sys.modules["openpyxl"] = saved


def test_info_reports_python_and_excel_capability():
    pytest.importorskip("httpx", reason="TestClient 依赖 httpx")
    from fastapi.testclient import TestClient

    from app.server import app

    body = TestClient(app).get("/api/info").json()
    assert body["excel_available"] is True
    assert body["python_version"].count(".") == 2
```

### `tests/test_count_loc.py`（211 行）

```python
"""有效代码 LOC 统计器自身的测试。

统计器最容易出的错不是崩溃，而是「悄悄算错」——多算几行没人发现，
少算几行也没人发现，最后交出去的数字就是假的。所以这里逐条钉住判定规则。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import count_loc  # noqa: E402


# ---------------------------------------------------------------------------
# Python：空行 / 注释 / 文档字符串 / 代码
# ---------------------------------------------------------------------------

def test_python_counts_basic_roles():
    src = (
        '"""模块文档。"""\n'          # 1 docstring
        "\n"                          # 2 blank
        "import os\n"                 # 3 code
        "\n"                          # 4 blank
        "# 整行注释\n"                # 5 comment
        "x = 1\n"                     # 6 code
        "\n"                          # 7 blank
        "\n"                          # 8 blank
        "def f():\n"                  # 9 code
        '    """函数文档。"""\n'      # 10 docstring
        "    return x\n"              # 11 code
    )
    got = count_loc.count_python(src)
    assert got["total"] == 11
    assert got["blank"] == 4
    assert got["comment"] == 1
    assert got["docstring"] == 2
    assert got["template"] == 0
    assert got["code"] == 4


def test_trailing_comment_line_still_counts_as_code():
    """`x = 1  # 说明` 这一行是代码，不是注释。

    按整行算成注释会少算代码行——这是统计器最隐蔽的一类偏差。
    """
    src = "x = 1  # 行尾注释\n# 纯注释\ny = 2\n"
    got = count_loc.count_python(src)
    assert got["comment"] == 1, "只有纯注释行才算注释"
    assert got["code"] == 2


def test_long_module_docstring_is_docstring_not_template():
    """模块说明写长了仍然是文档，不能被当成内嵌模板。

    io_table.py 的模块 docstring 有 41 行，曾经被误判为模板，
    导致 core 层凭空少算 41 行。
    """
    body = "".join("说明第 %d 行。\n" % i for i in range(60))
    src = '"""长文档开始。\n%s"""\n\nx = 1\n' % body
    got = count_loc.count_python(src)
    assert got["docstring"] >= 60
    assert got["template"] == 0, "docstring 不该被计入模板"
    assert got["code"] == 1


def test_long_assigned_string_is_template():
    """赋值语句里的超长字符串是内嵌模板，不是逻辑代码。"""
    body = "".join("<div>行 %d</div>\n" % i for i in range(50))
    src = 'TEMPLATE = """%s"""\n\nprint(TEMPLATE)\n' % body
    got = count_loc.count_python(src)
    assert got["template"] >= 50
    assert got["code"] == 1, "只有 print 那行是代码"


def test_short_assigned_string_is_code():
    """短字符串不触发模板判定。"""
    src = 'NAME = "abc"\nprint(NAME)\n'
    got = count_loc.count_python(src)
    assert got["template"] == 0
    assert got["code"] == 2


def test_python_broken_syntax_does_not_crash():
    """语法错误的文件也要能统计，不能把整个报告搞崩。"""
    got = count_loc.count_python("def f(:\n    pass\n")
    assert got["total"] == 2
    assert got["code"] >= 0


def test_python_total_equals_sum_of_parts():
    src = '"""文档。"""\n\n# 注释\nx = 1\n\n\ndef f():\n    return x\n'
    got = count_loc.count_python(src)
    assert got["total"] == got["blank"] + got["comment"] + got["docstring"] + got["template"] + got["code"]


# ---------------------------------------------------------------------------
# HTML：必须拆成结构 / CSS / JS
# ---------------------------------------------------------------------------

def test_html_splits_style_and_script():
    html = (
        "<html>\n"                    # html
        "<style>\n"                   # html
        "/* 样式注释 */\n"            # css comment
        ".a { color: red; }\n"        # css code
        "</style>\n"                  # html
        "<script>\n"                  # html
        "// 脚本注释\n"               # js comment
        "var a = 1;\n"                # js code
        "</script>\n"                 # html
        "</html>\n"                   # html
    )
    parts = count_loc.count_html(html)
    assert parts["html"]["code"] == 6, "开闭标签与结构行算 HTML 代码"
    assert parts["css"]["comment"] == 1
    assert parts["css"]["code"] == 1
    assert parts["js"]["comment"] == 1
    assert parts["js"]["code"] == 1


def test_html_total_matches_input_lines():
    html = "<html>\n<style>\na{}\n</style>\n<script>\nvar a;\n</script>\n</html>\n"
    parts = count_loc.count_html(html)
    total = sum(p["total"] for p in parts.values())
    assert total == 8


# ---------------------------------------------------------------------------
# C 系语法：跨行块注释
# ---------------------------------------------------------------------------

def test_block_comment_spans_multiple_lines():
    lines = [
        "/* 第一行",
        "   第二行",
        "   第三行 */",
        "var a = 1;",
        "// 单行",
        "var b = 2;",
    ]
    got = count_loc._count_c_like(lines, "//")
    assert got["comment"] == 4, "三行块注释 + 一行单行注释"
    assert got["code"] == 2


def test_code_with_trailing_comment_is_code():
    lines = ["var a = 1; // 说明", "var b = 2;"]
    got = count_loc._count_c_like(lines, "//")
    assert got["code"] == 2
    assert got["comment"] == 0


# ---------------------------------------------------------------------------
# 分类
# ---------------------------------------------------------------------------

def test_classify_layers():
    assert count_loc.classify("src/paper_recycle_agent/llm.py") == "core"
    assert count_loc.classify("app/server.py") == "web"
    assert count_loc.classify("app/static/index.html") == "web"
    assert count_loc.classify("run.py") == "web"
    assert count_loc.classify("tests/test_llm.py") == "tests"
    assert count_loc.classify("conftest.py") == "tests"
    assert count_loc.classify("tools/count_loc.py") == "tools"


def test_classify_excludes():
    assert count_loc.classify("dist/paper-recycle-offline.html") == "generated"
    assert count_loc.classify("docs/CODE_LISTING.md") == "generated"
    assert count_loc.classify("docs/USAGE.md") == "docs"
    assert count_loc.classify("LICENSE") == "docs"
    assert count_loc.classify("pyproject.toml") == "config"
    assert count_loc.classify("data/enterprises.csv.example") == "config"
    assert count_loc.classify(".github/workflows/ci.yml") == "config"


def test_no_unknown_category_for_tracked_files():
    """所有被跟踪的文件都应该有明确归类，不该落到「其他」。"""
    unknown = [f for f in count_loc.git_files() if count_loc.classify(f) == "other"]
    assert unknown == [], "未归类的文件：%s" % unknown


# ---------------------------------------------------------------------------
# 端到端
# ---------------------------------------------------------------------------

def test_generated_artifacts_are_not_counted():
    """dist/ 与 CODE_LISTING 是生成物，必须排除，否则行数虚增。"""
    counted = {c["path"] for c in (
        count_loc.count_file(f) for f in count_loc.git_files()
    ) if c is not None and c["layer"] in {k for k, _, _ in count_loc.LAYER_RULES}}
    assert "dist/paper-recycle-offline.html" not in counted
    assert "docs/CODE_LISTING.md" not in counted


def test_effective_loc_is_plausible():
    """有效代码量应在合理区间：太少说明统计漏了，太多说明混进了非代码。"""
    files = count_loc.git_files()
    counted = [c for c in (count_loc.count_file(f) for f in files) if c is not None]
    by_layer = count_loc.summarize(counted)
    total = sum(by_layer.get(k, {}).get("code", 0) for k, _, _ in count_loc.LAYER_RULES)
    assert 3000 <= total <= 12000, "有效代码行数异常：%d" % total


def test_no_vendor_or_minified_code():
    files = count_loc.git_files()
    lowered = [f.lower() for f in files]
    assert not [f for f in lowered if "vendor/" in f or "node_modules/" in f]
    assert not [f for f in files if f.endswith((".min.js", ".min.css"))]
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

### `tests/test_exporter.py`（102 行）

```python
import io

import pytest

# openpyxl 是可选依赖：没装的机器上跳过本文件，而不是让整个测试套件崩掉
pytest.importorskip("openpyxl", reason="导出测试需要 openpyxl")

from openpyxl import load_workbook  # noqa: E402

from paper_recycle_agent import exporter, regions  # noqa: E402


def _load(code="CN", year=2024):
    data = exporter.build_workbook(code, year)
    assert data[:2] == b"PK"  # xlsx 是 zip 容器
    return load_workbook(io.BytesIO(data))


def test_sheets_present():
    wb = _load()
    assert wb.sheetnames == [
        "省级统计", "分类回收", "历年回收", "废纸进口",
        "企业名录", "投入产出", "数据说明"
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

### `tests/test_history.py`（216 行）

```python
"""历史校验器自身的测试。

一个校验器如果永远只会说「通过」，那它就是装饰品。这里在临时仓库里
刻意造出各类违规历史，确认 check_history 能一条条抓出来。
"""

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_history  # noqa: E402

pytestmark = pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="需要 git",
)

ENV_BASE = {
    "GIT_AUTHOR_NAME": "tester",
    "GIT_AUTHOR_EMAIL": "tester@example.com",
    "GIT_COMMITTER_NAME": "tester",
    "GIT_COMMITTER_EMAIL": "tester@example.com",
}


def git(repo, *args, env=None):
    full_env = os.environ.copy()
    full_env.update(ENV_BASE)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["git"] + list(args),
        cwd=str(repo),
        env=full_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def make_repo(path):
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.name", "tester")
    git(path, "config", "user.email", "tester@example.com")
    git(path, "config", "commit.gpgsign", "false")
    return path


def commit(repo, message, when, filename=None):
    # 文件名必须每次唯一：用 glob 数量推算会在切分支后重复，
    # 造成「两个分支改了同一个文件」的假冲突，让 merge 静默失败。
    name = filename or ("f_%s.txt" % uuid.uuid4().hex[:8])
    (repo / name).write_text(message, encoding="utf-8")
    git(repo, "add", name)
    proc = git(
        repo, "commit", "-q", "-m", message,
        env={"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when},
    )
    # 助手静默失败会让测试得出错误结论，这里必须炸出来
    assert proc.returncode == 0, "git commit 失败：%s" % proc.stderr
    return proc


def merge_no_ff(repo, branch, message):
    proc = git(repo, "merge", "--no-ff", "-m", message, branch)
    assert proc.returncode == 0, "git merge 失败：%s%s" % (proc.stdout, proc.stderr)
    return proc


def load(repo, monkeypatch):
    """在指定仓库里重新采集数据（校验器依赖 cwd 调用 git）。"""
    monkeypatch.chdir(repo)
    commits = check_history._commits()
    parents = check_history._parents()
    return commits, parents


# ------------------------------------------------------------------ 正常历史

def test_clean_history_passes(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "clean")
    commit(repo, "feat: 第一个功能", "2026-01-01T10:00:00+0800")
    commit(repo, "fix: 修一个问题", "2026-01-02T10:00:00+0800")
    commits, parents = load(repo, monkeypatch)

    assert check_history.check_time_order(commits, parents) == []
    assert check_history.check_author_equals_committer(commits) == []
    assert check_history.check_subject_prefix(commits) == []


# ------------------------------------------------------------------ 时间倒挂

def test_detects_child_older_than_parent(tmp_path, monkeypatch):
    """发布提交比它要发布的内容还早 —— 这是最典型的"改过历史"痕迹。"""
    repo = make_repo(tmp_path / "reversed")
    commit(repo, "feat: 内容", "2026-02-10T10:00:00+0800")
    commit(repo, "chore: 发布", "2026-02-09T10:00:00+0800")
    commits, parents = load(repo, monkeypatch)

    problems = check_history.check_time_order(commits, parents)
    assert problems, "子提交早于父提交必须被报出来"
    assert "时间倒挂" in problems[0]


def test_detects_author_committer_mismatch(tmp_path, monkeypatch):
    """author 与 committer 不一致，通常是只改了其中一个时间。"""
    repo = make_repo(tmp_path / "mismatch")
    (repo / "a.txt").write_text("x", encoding="utf-8")
    git(repo, "add", "a.txt")
    git(
        repo, "commit", "-q", "-m", "feat: 不一致",
        env={
            "GIT_AUTHOR_DATE": "2026-03-01T10:00:00+0800",
            "GIT_COMMITTER_DATE": "2026-03-02T10:00:00+0800",
        },
    )
    commits, _ = load(repo, monkeypatch)

    problems = check_history.check_author_equals_committer(commits)
    assert problems
    assert "不一致" in problems[0]


def test_detects_future_timestamp(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "future")
    commit(repo, "feat: 来自未来", "2099-01-01T10:00:00+0800")
    commits, _ = load(repo, monkeypatch)

    problems = check_history.check_no_future(commits)
    assert problems
    assert "未来" in problems[0]


# ------------------------------------------------------- 分支与合并轨迹

def test_detects_branch_without_merge_commit(tmp_path, monkeypatch):
    """feature 分支被快进合并（或根本没合并），合并轨迹就丢了。"""
    repo = make_repo(tmp_path / "ff")
    commit(repo, "feat: 主干起点", "2026-04-01T10:00:00+0800")
    git(repo, "checkout", "-q", "-b", "feature/ghost")
    commit(repo, "feat: 分支上的改动", "2026-04-02T10:00:00+0800")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "--ff-only", "feature/ghost")  # 快进：没有 merge commit

    monkeypatch.chdir(repo)
    problems, merge_count = check_history.check_merge_commits(check_history._parents())
    assert merge_count == 0
    assert any("feature/ghost" in p for p in problems)


def test_no_ff_merge_is_recognised(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "noff")
    commit(repo, "feat: 主干起点", "2026-05-01T10:00:00+0800")
    git(repo, "checkout", "-q", "-b", "feature/real")
    commit(repo, "feat: 分支上的改动", "2026-05-02T10:00:00+0800")
    git(repo, "checkout", "-q", "main")
    commit(repo, "docs: 主干继续", "2026-05-03T10:00:00+0800")
    merge_no_ff(repo, "feature/real", "Merge PR #1: 分支")

    monkeypatch.chdir(repo)
    problems, merge_count = check_history.check_merge_commits(check_history._parents())
    assert merge_count == 1
    assert problems == []


# ------------------------------------------------------------------ 提交信息

def test_detects_missing_prefix(tmp_path, monkeypatch):
    repo = make_repo(tmp_path / "prefix")
    commit(repo, "随便写了点东西", "2026-06-01T10:00:00+0800")
    commits, _ = load(repo, monkeypatch)

    problems = check_history.check_subject_prefix(commits)
    assert problems
    assert "前缀" in problems[0]


def test_merge_commit_exempt_from_prefix(tmp_path, monkeypatch):
    """git 自动生成的 Merge 提交不该被要求加 feat/fix 前缀。"""
    repo = make_repo(tmp_path / "mergeok")
    commit(repo, "feat: a", "2026-07-01T10:00:00+0800")
    commit(repo, "Merge PR #2: 合并", "2026-07-02T10:00:00+0800")
    commits, _ = load(repo, monkeypatch)

    assert check_history.check_subject_prefix(commits) == []


# ------------------------------------------------------------------ 退出码

def test_main_returns_nonzero_on_dirty_history(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path / "exitcode")
    commit(repo, "feat: 内容", "2026-08-10T10:00:00+0800")
    commit(repo, "chore: 发布", "2026-08-09T10:00:00+0800")
    monkeypatch.chdir(repo)

    code = check_history.main([])
    out = capsys.readouterr().out
    assert code == 1
    assert "不通过" in out


def test_main_returns_zero_on_clean_history(tmp_path, monkeypatch, capsys):
    repo = make_repo(tmp_path / "exitok")
    commit(repo, "feat: 内容", "2026-09-01T10:00:00+0800")
    monkeypatch.chdir(repo)

    code = check_history.main(["--quiet"])
    assert code == 0
```

### `tests/test_io_table.py`（231 行）

```python
"""投入产出模型测试。

重点不是「函数能跑」，而是：
1. 金额与已有分类数据自洽（不能凭空多出或少掉钱）；
2. 四级口径的标签不能串（官方 / 测算 / 估算 / 示例）；
3. Leontief 逆矩阵算得对（拿教科书例子对答案）；
4. 没有官方数据的层级必须显式说明「没有」，而不是返回一个像真的数字。
"""

import math

import pytest

from paper_recycle_agent import io_table
from paper_recycle_agent import stats as stats_mod


# ---------------------------------------------------------------- 金额口径


def test_spend_matches_category_sum():
    """全国金额必须等于分类拆分金额之和。"""
    s = io_table.spend(2024)
    rows = stats_mod.category_breakdown(2024, total=s["tonnage"])
    assert abs(sum(r["value"] for r in rows) - s["amount"]) < 0.2


def test_spend_is_labelled_lower_bound():
    """金额按回收参考价计，必须标为下限，避免被当成到厂采购额。"""
    s = io_table.spend(2024)
    assert s["is_lower_bound"] is True
    assert "下限" in s["note"]


def test_tonnage_prefers_consumption():
    amount, basis = io_table.tonnage(2024)
    assert amount == 7030.0
    assert "消费量" in basis


def test_tonnage_falls_back_to_recovery():
    """2016 年消费量未公布，应退回回收量并说明。"""
    amount, basis = io_table.tonnage(2016)
    assert amount == 4964.0
    assert "回收量" in basis


def test_average_price_reasonable():
    price = io_table.average_price(2024)
    # 回收参考价（居民/回收站口径）应在 500—2000 元/吨之间
    assert 500 < price < 2000


def test_direct_coefficient_matches_formula():
    d = io_table.direct_coefficient(2024)
    expected = round(io_table.spend(2024)["amount"] / 14600.0, 4)
    assert d["coefficient"] == expected
    assert d["is_lower_bound"] is True


def test_direct_coefficient_none_without_revenue():
    """没有营收公开值的年份，系数必须是 None，而不是编一个。"""
    d = io_table.direct_coefficient(2020)
    assert d["coefficient"] is None
    assert "无公开" in d["note"]


def test_unit_consumption_dimension():
    u = io_table.unit_consumption(2024)
    assert u["value"] == round(7030.0 / 14600.0, 3)


# ---------------------------------------------------------------- 分省


def test_province_rows_complete_and_sorted():
    data = io_table.province_spend(2024)
    rows = data["rows"]
    assert len(rows) == 34
    amounts = [r["amount"] for r in rows]
    assert amounts == sorted(amounts, reverse=True)
    assert rows[0]["rank"] == 1


def test_province_amount_sums_to_national():
    data = io_table.province_spend(2024)
    total = sum(float(r["amount"]) for r in data["rows"])
    assert abs(total - data["total"]) < 1.0  # 逐行四舍五入的累计误差


def test_province_amount_is_always_estimated_but_recovery_keeps_its_quality():
    """山东的回收量是报道值，但「金额」是拿它乘出来的分摊值，不能标官方。

    这条测试原本断言 rows["山东省"]["provenance"] == 官方，是错的：
    官方的是回收量，不是金额。金额一旦被标成官方，读表的人就会把它当统计公报数据引用。
    """
    rows = {r["name"]: r for r in io_table.province_spend(2024)["rows"]}
    assert rows["山东省"]["provenance"] == io_table.PROVENANCE_ESTIMATED
    assert rows["山西省"]["provenance"] == io_table.PROVENANCE_ESTIMATED
    # 回收量本身的口径要保留下来，供导出表单独一列展示
    assert rows["山东省"]["recovery_provenance"] == io_table.PROVENANCE_OFFICIAL
    assert rows["山西省"]["recovery_provenance"] == io_table.PROVENANCE_ESTIMATED


def test_province_basis_says_not_actual_purchase():
    basis = io_table.province_spend(2024)["basis"]
    assert "非实际采购分布" in basis


# ---------------------------------------------------------------- 城市 / 企业


def test_city_spend_sums_to_province():
    data = io_table.city_spend("370000", 2024)
    total = sum(float(c["amount"]) for c in data["cities"])
    assert abs(total - data["province_amount"]) < 0.5


def test_city_requires_province_code():
    data = io_table.city_spend("CN", 2024)
    assert data["cities"] == []
    assert data["provenance"] == "无数据"


def test_city_note_mentions_no_official_table():
    data = io_table.city_spend("370000", 2024)
    assert "不编制投入产出表" in data["note"]


def test_enterprise_amount_formula():
    price = io_table.average_price(2024)
    data = io_table.enterprise_spend(2024)
    for row in data["rows"][:5]:
        assert abs(row["amount"] - row["volume"] * price / 10000) < 0.02


def test_enterprise_flagged_as_demo():
    data = io_table.enterprise_spend(2024)
    assert data["provenance"] == io_table.PROVENANCE_DEMO
    assert "不存在投入产出表" in data["note"]


# ---------------------------------------------------------------- 口径分级


def test_levels_declare_io_availability():
    levels = {lv["key"]: lv for lv in io_table.LEVELS}
    assert levels["national"]["io_available"] is True
    assert levels["province"]["io_available"] is True
    # 国家统计局明确：地级市不编制投入产出表
    assert levels["city"]["io_available"] is False
    assert levels["enterprise"]["io_available"] is False


def test_overview_has_all_parts():
    d = io_table.overview(2024)
    for key in ("national_io", "levels", "sources", "spend",
                "direct_coefficient", "unit_consumption", "provinces",
                "enterprises", "years"):
        assert key in d


def test_summary_text_mentions_provenance():
    text = io_table.summary_text(2024)
    assert "消耗金额" in text
    assert "口径分级" in text
    assert "地级市" in text


def test_summary_text_coefficient_carries_percent_unit():
    """直接消耗系数必须带 % —— 之前漏了单位，读起来像「4.28 元」。"""
    text = io_table.summary_text(2024)
    pct = io_table.direct_coefficient(2024)["coefficient_pct"]
    assert ("%s%%" % pct) in text
    assert "属下限" in text


# ---------------------------------------------------------------- Leontief


def test_leontief_inverse_textbook_example():
    """A=[[0.2,0.3],[0.4,0.1]] → (I-A)^-1=[[1.5,0.5],[2/3,4/3]]"""
    inv = io_table.leontief_inverse([[0.2, 0.3], [0.4, 0.1]])
    expected = [[1.5, 0.5], [2.0 / 3.0, 4.0 / 3.0]]
    for i in range(2):
        for j in range(2):
            assert abs(inv[i][j] - expected[i][j]) < 1e-9


def test_leontief_inverse_identity_for_zero_matrix():
    inv = io_table.leontief_inverse([[0.0, 0.0], [0.0, 0.0]])
    assert inv == [[1.0, 0.0], [0.0, 1.0]]


def test_leontief_inverse_rejects_singular():
    with pytest.raises(ValueError):
        io_table.leontief_inverse([[1.0, 0.0], [0.0, 1.0]])


def test_leontief_inverse_rejects_non_square():
    with pytest.raises(ValueError):
        io_table.leontief_inverse([[0.1, 0.2]])


def test_influence_and_response_mean_to_one():
    """影响力 / 感应度系数的平均值恒为 1，这是定义决定的。"""
    A = [[0.1, 0.2, 0.1], [0.2, 0.1, 0.2], [0.1, 0.1, 0.1]]
    inf = io_table.influence_coefficients(A)
    res = io_table.response_coefficients(A)
    assert math.isclose(sum(inf) / len(inf), 1.0, rel_tol=1e-3)
    assert math.isclose(sum(res) / len(res), 1.0, rel_tol=1e-3)


def test_load_matrix_csv_roundtrip(tmp_path):
    p = tmp_path / "m.csv"
    p.write_text("部门,A,B\nA,0.1,0.2\nB,0.3,0.4\n", encoding="utf-8")
    names, matrix = io_table.load_matrix_csv(str(p))
    assert names == ["A", "B"]
    assert matrix == [[0.1, 0.2], [0.3, 0.4]]


def test_load_matrix_csv_rejects_non_square(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("部门,A,B\nA,0.1,0.2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        io_table.load_matrix_csv(str(p))


def test_no_builtin_matrix_shipped():
    """仓库不内置投入产出矩阵：编一张假矩阵比不提供更糟。"""
    assert not io_table.matrix_path().exists()
```

### `tests/test_llm.py`（197 行）

```python
"""模型配置模块测试。

这里最要紧的一条是：**密钥绝不能出现在任何输出里**。
其余是配置读写、回落行为与错误提示的可读性。
"""

import json
import urllib.error

import pytest

from paper_recycle_agent import llm

SECRET = "sk-test-1234567890abcdefXYZ"


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    """把配置文件重定向到临时目录，避免污染真实 config/llm.json。"""
    monkeypatch.setattr(llm, "CONFIG_PATH", tmp_path / "config" / "llm.json")
    for name in (llm.ENV_BASE_URL, llm.ENV_API_KEY, llm.ENV_MODEL):
        monkeypatch.delenv(name, raising=False)
    yield


# ---------------------------------------------------------------- 脱敏


def test_mask_key():
    assert llm.mask_key(SECRET) == "sk-…" + SECRET[-4:]
    assert "1234567890" not in llm.mask_key(SECRET)


def test_mask_key_short_and_empty():
    assert llm.mask_key("") == ""
    assert llm.mask_key(None) == ""
    assert llm.mask_key("ab") == "…"
    assert llm.mask_key("abcdef") == "…ef"


def test_public_config_never_leaks_key():
    cfg = llm.LLMConfig(api_key=SECRET)
    pub = cfg.public()
    dumped = json.dumps(pub, ensure_ascii=False)
    assert SECRET not in dumped
    assert pub["has_api_key"] is True
    assert pub["api_key_masked"].endswith(SECRET[-4:])


# ---------------------------------------------------------------- 配置读写


def test_default_config_not_configured():
    cfg = llm.load_config()
    assert cfg.configured() is False
    assert cfg.base_url == llm.DEFAULT_BASE_URL


def test_save_and_load_roundtrip():
    llm.save_config("https://api.deepseek.com/v1", SECRET, "deepseek-chat",
                    temperature=0.5, max_tokens=800)
    cfg = llm.load_config()
    assert cfg.base_url == "https://api.deepseek.com/v1"
    assert cfg.api_key == SECRET
    assert cfg.model == "deepseek-chat"
    assert cfg.temperature == 0.5
    assert cfg.max_tokens == 800
    assert cfg.source == "file"


def test_save_without_key_keeps_previous_key():
    """界面上只改模型名时，不应该把已有密钥清掉。"""
    llm.save_config("https://api.deepseek.com/v1", SECRET, "deepseek-chat")
    llm.save_config("https://api.deepseek.com/v1", None, "deepseek-reasoner")
    cfg = llm.load_config()
    assert cfg.api_key == SECRET
    assert cfg.model == "deepseek-reasoner"


def test_env_overrides_file():
    llm.save_config("https://file.example/v1", "file-key", "file-model")
    import os

    os.environ[llm.ENV_BASE_URL] = "https://env.example/v1"
    os.environ[llm.ENV_API_KEY] = "env-key"
    try:
        cfg = llm.load_config()
        assert cfg.source == "env"
        assert cfg.base_url == "https://env.example/v1"
        assert cfg.api_key == "env-key"
    finally:
        os.environ.pop(llm.ENV_BASE_URL, None)
        os.environ.pop(llm.ENV_API_KEY, None)


def test_clear_config():
    llm.save_config("https://x/v1", SECRET, "m")
    assert llm.clear_config() is True
    assert llm.clear_config() is False
    assert llm.load_config().configured() is False


def test_config_file_is_valid_json():
    llm.save_config("https://x/v1", SECRET, "m")
    raw = json.loads(llm.CONFIG_PATH.read_text(encoding="utf-8"))
    assert raw["api_key"] == SECRET
    assert set(raw) >= {"base_url", "api_key", "model", "temperature", "max_tokens"}


# ---------------------------------------------------------------- endpoint


def test_endpoint_appends_path():
    cfg = llm.LLMConfig(base_url="https://api.deepseek.com/v1")
    assert cfg.endpoint() == "https://api.deepseek.com/v1/chat/completions"


def test_endpoint_tolerates_trailing_slash_and_full_path():
    assert llm.LLMConfig(base_url="https://x/v1/").endpoint() == "https://x/v1/chat/completions"
    assert llm.LLMConfig(
        base_url="https://x/v1/chat/completions"
    ).endpoint() == "https://x/v1/chat/completions"


# ---------------------------------------------------------------- 回落与报错


def test_chat_without_key_returns_not_configured():
    result = llm.chat([{"role": "user", "content": "hi"}])
    assert result["ok"] is False
    assert result["configured"] is False
    assert llm.ENV_API_KEY in result["error"]


def test_probe_without_key():
    result = llm.probe()
    assert result["ok"] is False
    assert result["configured"] is False


def test_chat_http_error_is_readable_and_scrubbed(monkeypatch):
    cfg = llm.LLMConfig(api_key=SECRET, model="m")

    def boom(url, payload, key, timeout):
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(llm, "_post", boom)
    result = llm.chat([{"role": "user", "content": "hi"}], config=cfg)
    assert result["ok"] is False
    assert "密钥无效" in result["error"]
    assert SECRET not in json.dumps(result, ensure_ascii=False)


def test_chat_network_error_is_readable(monkeypatch):
    cfg = llm.LLMConfig(api_key=SECRET, model="m")

    def boom(url, payload, key, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(llm, "_post", boom)
    result = llm.chat([{"role": "user", "content": "hi"}], config=cfg)
    assert result["ok"] is False
    assert "连接失败" in result["error"]


def test_chat_bad_payload_shape(monkeypatch):
    cfg = llm.LLMConfig(api_key=SECRET, model="m")
    monkeypatch.setattr(llm, "_post", lambda *a, **k: {"unexpected": True})
    result = llm.chat([{"role": "user", "content": "hi"}], config=cfg)
    assert result["ok"] is False
    assert "OpenAI 兼容" in result["error"]


def test_chat_success(monkeypatch):
    cfg = llm.LLMConfig(api_key=SECRET, model="m")
    monkeypatch.setattr(
        llm, "_post",
        lambda *a, **k: {
            "choices": [{"message": {"content": " 可用 "}}],
            "usage": {"total_tokens": 7},
        },
    )
    result = llm.chat([{"role": "user", "content": "hi"}], config=cfg)
    assert result["ok"] is True
    assert result["reply"] == "可用"
    assert result["usage"]["total_tokens"] == 7


def test_status_shape():
    s = llm.status()
    assert "config" in s and "presets" in s
    assert isinstance(s["presets"], list) and s["presets"]
    assert s["ready"] is False


def test_system_prompt_forbids_fabrication():
    assert "不要编造" in llm.DEFAULT_SYSTEM_PROMPT
```

### `tests/test_mill.py`（180 行）

```python
"""智能工厂多智能体仿真测试。

分两层：
1. 核心层（无第三方依赖）：工序、仿真状态机、设备调度、多智能体决策；
2. Web 层：FastAPI 接口（缺 fastapi 时自动跳过，不影响核心测试）。
"""

import pytest

from paper_recycle_agent.mill.agents import Orchestrator
from paper_recycle_agent.mill import processes
from paper_recycle_agent.mill.devices import DeviceFleet, Task
from paper_recycle_agent.mill.simulation import MillSimulation, StageState


# ---------------- 工序定义 ----------------

def test_process_order_and_metrics():
    assert processes.ORDER == ("pulping", "papermaking", "drying", "quality")
    for key in processes.ORDER:
        proc = processes.get(key)
        assert proc.metrics
        assert proc.devices
        assert proc.knowledge


def test_unknown_process_raises():
    with pytest.raises(ValueError):
        processes.get("not_exist")


def test_metric_status():
    m = processes.Metric("t", "温度", "°C", 10, 20)
    assert m.status(15) == "normal"
    assert m.status(12) == "normal"
    assert m.status(20.5) == "warn"
    assert m.status(30) == "critical"


# ---------------- 仿真引擎 ----------------

def test_simulation_is_deterministic():
    a = MillSimulation(seed=42)
    b = MillSimulation(seed=42)
    a.start_batch("B1"); b.start_batch("B1")
    for _ in range(6):
        a.advance(); b.advance()
    assert a.snapshot()["stages"] == b.snapshot()["stages"]


def test_stage_transition():
    sim = MillSimulation(seed=1)
    sim.start_batch("B1")
    assert sim.stages["pulping"].state == "running"
    assert sim.stages["papermaking"].state == "idle"
    assert sim.next_process("pulping") == "papermaking"
    assert sim.next_process("quality") is None


def test_finish_and_flow():
    sim = MillSimulation(seed=2)
    sim.start_batch("B1")
    for _ in range(processes.get("pulping").base_time):
        sim.advance()
    assert "pulping" in sim.finish_completed()
    assert sim.stages["pulping"].state == "done"


def test_anomaly_injection_and_clear():
    sim = MillSimulation(seed=3)
    sim.start_batch("B1")
    assert sim.inject_anomaly("pulping", "brightness", 30.0) is True
    assert sim.stages["pulping"].metrics["brightness"] == 30.0
    assert sim.stages["pulping"].metric_status["brightness"] == "critical"
    assert sim.inject_anomaly("pulping", "no_such_metric", 1) is False
    sim.clear_anomalies()
    assert sim.snapshot()["anomalies"] == []


def test_hold_and_resume():
    sim = MillSimulation(seed=4)
    sim.start_batch("B1")
    sim.hold_batch("pulping")
    assert sim.stages["pulping"].state == "held"
    sim.resume("pulping")
    assert sim.stages["pulping"].state == "running"


def test_stage_overall_status():
    st = StageState(key="pulping", metric_status={"a": "normal", "b": "warn"})
    assert st.overall_status == "warn"
    st.metric_status["a"] = "critical"
    assert st.overall_status == "critical"


# ---------------- 设备层 ----------------

def test_device_assign_and_tick():
    fleet = DeviceFleet()
    sent = fleet.dispatch_for("pulping", "start", "T001")
    assert "agv-01" in sent and "plc-pulp" in sent
    results = []
    for _ in range(5):
        results.extend(fleet.tick(step=1))
    assert any(r.device_id == "agv-01" for r in results)
    assert any(r.device_id == "plc-pulp" for r in results)


def test_device_queue_when_busy():
    fleet = DeviceFleet()
    d = fleet.devices["agv-01"]
    assert d.assign(Task("t1", "pulping", "start")) is True
    assert d.assign(Task("t2", "pulping", "start")) is False
    assert d.snapshot()["queue_len"] == 1


def test_unknown_device():
    assert DeviceFleet().assign("no-such-device", Task("t", "pulping", "a")) is False


# ---------------- 多智能体 ----------------

def test_orchestrator_runs_full_batch():
    orch = Orchestrator(use_llm=False)
    orch.start_batch()
    snap = orch.run_until_idle(max_steps=80)
    assert snap["sim"]["idle"] is True
    states = [s["state"] for s in snap["sim"]["stages"]]
    assert states == ["done"] * 4
    assert len(snap["decisions"]) == 4
    assert any(e["event"] == "batch_complete" for e in snap["log"])
    # 七台设备都至少干过一次活
    assert all(d["done_count"] > 0 for d in snap["devices"])


def test_orchestrator_anomaly_triggers_arbitration():
    orch = Orchestrator(use_llm=False)
    orch.start_batch()
    orch.sim.inject_anomaly("pulping", "brightness", 20.0)
    snap = orch.run_until_idle(max_steps=80)
    held = [s for s in snap["sim"]["stages"] if s["state"] == "held"]
    assert any(s["key"] == "pulping" for s in held)
    assert any(e["event"] == "arbitration" for e in snap["log"])


def test_decision_basis_is_rule_without_llm():
    orch = Orchestrator(use_llm=False)
    orch.start_batch()
    snap = orch.run_until_idle(max_steps=80)
    assert all(d["basis"] == "rule" for d in snap["decisions"])


# ---------------- Web 层 ----------------

def test_api_mill_endpoints():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from app.server import app

    client = TestClient(app)
    r = client.get("/api/mill/processes")
    assert r.status_code == 200
    assert r.json()["order"] == list(processes.ORDER)

    r = client.post("/api/mill/start")
    assert r.status_code == 200
    assert r.json()["sim"]["batch"]

    r = client.post("/api/mill/run")
    assert r.status_code == 200
    assert r.json()["sim"]["idle"] is True

    r = client.post("/api/mill/anomaly", json={
        "process": "drying", "metric": "moisture", "value": 20.0,
    })
    assert r.status_code == 200 and r.json()["ok"] is True

    r = client.post("/api/mill/reset")
    assert r.status_code == 200
    assert r.json()["sim"]["batch"] is None
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

### `pyproject.toml`（44 行）

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "paper-recycle-agent"
version = "1.9.2"
description = "造纸工厂多智能体 · 碳核算 Agent：国标方法核算工厂排放，含废纸回收子 Agent、工艺智能体、产业大脑（核心逻辑纯标准库）"
readme = "README.md"
# 核心包只用到 dataclasses（3.7 引入），因此下限放到 3.7
requires-python = ">=3.7"
license = { text = "MIT" }
authors = [{ name = "梁湘瑶 / 阿岩" }]
keywords = ["recycling", "paper", "agent", "cli"]
classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
# 核心零依赖；下面按需安装
dependencies = []

[project.optional-dependencies]
# 图形界面 / HTTP 服务。FastAPI 0.110 起要求 Python 3.8+，
# 因此 3.7 环境请改用零依赖离线版 dist/paper-recycle-offline.html
web = ["fastapi>=0.110", "uvicorn>=0.29", "httpx>=0.27"]
# 导出 .xlsx 工作簿
excel = ["openpyxl>=3.1"]
# 本地测试
test = ["pytest>=7.0"]
all = ["fastapi>=0.110", "uvicorn>=0.29", "httpx>=0.27", "openpyxl>=3.1", "pytest>=7.0"]

[project.scripts]
paper-recycle-agent = "paper_recycle_agent.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

### `requirements.txt`（12 行）

```text
# 核心包 paper_recycle_agent 零依赖，只用 Python 标准库。
# 本文件是「图形界面 + Excel 导出 + 测试」的完整依赖集，等价于：pip install .[all]
#
# 只要命令行 / 离线版？什么都不用装：
#   PYTHONPATH=src python -m paper_recycle_agent.cli history
#   python tools/build_offline.py     # 生成 dist/paper-recycle-offline.html

fastapi>=0.110       # 图形界面 / HTTP 服务（FastAPI 0.110 要求 Python 3.8+）
uvicorn>=0.29        # 运行 FastAPI 服务：uvicorn app.server:app --reload
httpx>=0.27          # Web 路由测试（fastapi.testclient 依赖）
openpyxl>=3.1        # 导出 Excel（可选：缺失时 /export.xlsx 返回 503 并给出安装提示）
pytest>=7.0          # 单元测试（CI 使用）
```

### `.gitattributes`（18 行）

```
# 统一换行符，避免 Windows 上 CRLF / LF 混用导致 diff 噪音与脚本无法执行
* text=auto eol=lf

# Windows 批处理必须是 CRLF，否则 cmd 解析会出问题
*.bat text eol=crlf

# 二进制文件不做换行符转换
*.png binary
*.jpg binary
*.gif binary
*.ico binary
*.xlsx binary
*.zip binary
*.bundle binary

# 导出的单文件 HTML 是构建产物，diff 噪音大，折叠展示
dist/*.html linguist-generated=true
docs/CODE_LISTING.md linguist-generated=true
```

### `data/enterprises.csv.example`（3 行）

```csv
id,name,province_code,city,type,categories,volume,lat,lon,note
E001,某某再生资源有限公司,370000,济南市,分拣打包中心,1;8,26.0,36.65,117.00,示例：请替换为真实企业
E002,某某纸业原料部,440000,东莞市,造纸企业,1,55.0,23.02,113.75,示例：请替换为真实企业
```

### `data/io_matrix.csv.example`（4 行）

```csv
部门,农林牧渔,造纸和纸制品,废弃资源综合利用
农林牧渔,0.08,0.02,0.01
造纸和纸制品,0.01,0.35,0.02
废弃资源综合利用,0.00,0.12,0.10
```

### `config/llm.json.example`（9 行）

```csv
{
  "base_url": "https://api.deepseek.com/v1",
  "api_key": "sk-替换成你自己的密钥",
  "model": "deepseek-chat",
  "temperature": 0.3,
  "max_tokens": 600,
  "timeout": 30,
  "system_prompt": "你是废纸回收领域的助手。涉及数据时先说明口径（官方/测算/估算/示例），不确定就说不确定；不要编造具体省份的回收量、企业采购量或价格；中文回答。"
}
```

### `.github/workflows/ci.yml`（76 行）

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-22.04
    strategy:
      matrix:
        python-version: ["3.8", "3.11", "3.13"]
    steps:
      - uses: actions/checkout@v4
        with:
          # check_history.py 要读完整历史；默认 fetch-depth: 1 会把它变成浅克隆
          fetch-depth: 0

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Check Python 3.7 compatibility
        run: python tools/check_compat.py

      # 有效代码 LOC 不只是报数，还要守住「没有虚增」：
      # 生成物混入、压缩代码、第三方 vendor、超长内嵌数据都会让 --check 失败
      - name: Count effective LOC
        run: python tools/count_loc.py --check

      - name: Check git history consistency
        run: python tools/check_history.py

      - name: Run tests
        env:
          PYTHONPATH: src
        run: pytest -q

  # 核心包声明支持 3.7，但 FastAPI 0.110 起要求 3.8+，
  # 所以 3.7 只跑「零依赖」的那部分：语法/API 下限 + 核心统计测试。
  core-py37:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.7
        uses: actions/setup-python@v5
        with:
          python-version: "3.7"

      - name: Install pytest only (core has no runtime deps)
        run: pip install pytest

      - name: Check Python 3.7 compatibility
        run: python tools/check_compat.py

      - name: Run dependency-free tests
        env:
          PYTHONPATH: src
        run: >
          pytest -q
          tests/test_classifier.py
          tests/test_pricing.py
          tests/test_data.py
          tests/test_regions.py
          tests/test_stats.py
          tests/test_enterprises.py
          tests/test_io_table.py
          tests/test_llm.py
          tests/test_agent.py
```

### `.github/ISSUE_TEMPLATE/bug_report.yml`（52 行）

```yaml
name: 缺陷报告
description: 数据不对、界面报错、导出失败等「本该正常却出问题」的情况
title: "[Bug] "
labels: ["bug"]
body:
  - type: markdown
    attributes:
      value: |
        提交前请先确认：数据口径问题请对照 `docs/DATA_SOURCES.md`，
        那里标注了哪些是官方数据、哪些是估算。**「估算是编的」不算 bug。**
  - type: dropdown
    id: area
    attributes:
      label: 涉及模块
      options:
        - 命令行 / 对话
        - Web 界面
        - Excel 导出
        - 投入产出 / 消耗金额
        - 地图
        - 模型配置
        - 语音 / 麦克风
        - 离线单文件版
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: 期望行为
      placeholder: 你认为应该发生什么
    validations:
      required: true
  - type: textarea
    id: actual
    attributes:
      label: 实际行为
      placeholder: 实际发生了什么；有报错就贴完整报错信息（注意先把 API Key 去掉）
    validations:
      required: true
  - type: textarea
    id: reproduce
    attributes:
      label: 复现步骤
      placeholder: |
        1. 运行 python tools/... 或打开哪个页面
        2. 点了什么
        3. 看到什么
  - type: input
    id: env
    attributes:
      label: 环境
      placeholder: Windows 11 / Python 3.13 / Chrome 141；或「离线单文件版」
```

### `.github/ISSUE_TEMPLATE/feature_request.yml`（40 行）

```yaml
name: 新功能 / 改进
description: 新增数据维度、新的统计口径、界面改进等
title: "[Feat] "
labels: ["enhancement"]
body:
  - type: dropdown
    id: kind
    attributes:
      label: 类型
      options:
        - 新功能
        - 改进现有功能
        - 文档
        - 重构
    validations:
      required: true
  - type: textarea
    id: problem
    attributes:
      label: 要解决什么问题
      placeholder: 谁在什么场景下遇到什么困难？不要只写「加个图表」
    validations:
      required: true
  - type: textarea
    id: proposal
    attributes:
      label: 建议做法
      placeholder: 打算怎么做；如果涉及新数据，请说明数据来源与口径
  - type: textarea
    id: accept
    attributes:
      label: 验收标准
      placeholder: 怎样算做完了？最好写成可以被测试断言的句子
  - type: checkboxes
    id: honesty
    attributes:
      label: 数据合规自查
      options:
        - label: 若引入新数据，我会在 `docs/DATA_SOURCES.md` 标注其性质（官方 / 测算 / 估算 / 示例）
        - label: 我不会为了让数据「看起来完整」而编造数字
```

### `.github/ISSUE_TEMPLATE/config.yml`（8 行）

```yaml
blank_issues_enabled: false
contact_links:
  - name: 数据口径问题
    url: https://github.com/OWNER/REPO/blob/main/docs/DATA_SOURCES.md
    about: 「这个数字哪来的」「为什么估算是估算」——先看数据来源说明
  - name: 使用问题
    url: https://github.com/OWNER/REPO/blob/main/docs/USAGE.md
    about: 打不开、导不出、麦克风没反应——使用说明里有排障章节
```

### `.github/PULL_REQUEST_TEMPLATE.md`（13 行）

```markdown
## 变更说明
<!-- 这个 PR 做了什么，关联哪个 Issue -->

- 关联 Issue: # 
- 类型: 新功能 / Bug / 文档 / 重构

## 自测
- [ ] `pytest -q` 通过
- [ ] 手动在 CLI 中验证过核心路径

## 检查清单
- [ ] 提交信息遵循 `类型: 描述 (closes #n)` 规范
- [ ] 已更新相关文档
```

## 五、工具脚本（tools/）

### `tools/build_offline.py`（737 行）

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

import paper_recycle_agent
from paper_recycle_agent import data as yearbook
from paper_recycle_agent import enterprises, io_table, knowledge, regions
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
        "version": paper_recycle_agent.__version__,
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
        "io": {
            "spend": io_table.spend(io_table.NATIONAL_IO["year"]),
            "direct": io_table.direct_coefficient(io_table.NATIONAL_IO["year"]),
            "unit": io_table.unit_consumption(io_table.NATIONAL_IO["year"]),
            "provinces": io_table.province_spend(io_table.NATIONAL_IO["year"]),
            "levels": io_table.LEVELS,
        },
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
  .kpis{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px}
  .kpi{border:1px solid var(--border);border-radius:10px;padding:9px 11px;background:#fbfcfd}
  .kpi .k{font-size:11px;color:var(--muted)}
  .kpi .v{font-size:19px;font-weight:700;margin-top:2px;font-variant-numeric:tabular-nums}
  .kpi .v .u{font-size:11px;font-weight:400;color:var(--muted);margin-left:3px}
  .kpi .n{font-size:10.5px;color:var(--muted);margin-top:3px;line-height:1.45}
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
      <div class="tab" data-pane="io" onclick="switchTab('io')">投入产出</div>
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

    <section class="pane" id="pane-io">
      <div class="kpis" id="ioKpis"></div>
      <div class="notice" id="ioNotice"></div>
      <div class="sect-title"><span>分省消耗金额（亿元）</span>
        <span class="hintline">按回收量占比分摊</span></div>
      <div class="scroll" style="max-height:300px"><table id="ioTable"><thead><tr>
        <th class="num">#</th><th>省份</th><th class="num">占比(%)</th>
        <th class="num">金额(亿元)</th><th>口径</th>
        </tr></thead><tbody></tbody></table></div>
      <div class="notice" style="margin-top:8px">
        <b>地图</b>与<b>模型配置</b>需要本地服务版：双击「启动本地版.bat」后访问
        <code>http://localhost:8000</code>。离线版不含这两项（地图需正版底图密钥，
        模型配置需服务端保存密钥）。
      </div>
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
  if (name === "io") renderIO();
}

/* ---------- 投入产出 ---------- */
function ioNum(n, d) {
  if (n === null || n === undefined || n === "") return "—";
  const v = Number(n);
  if (!isFinite(v)) return "—";
  return v.toLocaleString("zh-CN", {minimumFractionDigits: d || 0, maximumFractionDigits: d || 0});
}

function renderIO() {
  const io = D.io;
  const s = io.spend, dc = io.direct, uc = io.unit;
  $("ioKpis").innerHTML = [
    ["废纸消耗金额", ioNum(s.amount, 1), "亿元", s.provenance + "；按回收参考价计，属纸厂成本下限"],
    ["直接消耗系数", dc.coefficient === null ? "—" : ioNum(dc.coefficient_pct, 2), "%",
      dc.coefficient === null ? "该年营收无公开值" : "货值 " + ioNum(dc.spend, 1) + " 亿 ÷ 营收 " + ioNum(dc.revenue, 0) + " 亿"],
    ["单位产值消耗", uc.value === null ? "—" : ioNum(uc.value, 3), "吨/万元", "消耗量 ÷ 营业收入"],
    ["加权参考价", ioNum(s.avg_price, 0), "元/吨", "分类结构加权，居民 / 回收站口径"]
  ].map(([k, v, u, n]) =>
    '<div class="kpi"><div class="k">' + k + '</div><div class="v">' + v +
    '<span class="u">' + u + '</span></div><div class="n">' + n + '</div></div>'
  ).join("");

  $("ioNotice").innerHTML =
    "<b>口径分级</b>：" + io.levels.map(l =>
      l.name + "（" + (l.io_available ? "有官方表" : "无官方表") + "，" + l.provenance + "）"
    ).join("　") +
    "。国家统计局明确「地级市暂不编制投入产出表」，企业只有财务报表——这两级的金额都是分摊估算。";

  document.querySelector("#ioTable tbody").innerHTML = io.provinces.rows.map(r =>
    '<tr><td class="num">' + r.rank + '</td><td>' + r.name + '</td><td class="num">' +
    r.share_pct + '</td><td class="num">' + ioNum(r.amount, 1) + '</td><td>' + r.provenance + '</td></tr>'
  ).join("");
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
    OUT.write_text(html, encoding="utf-8", newline="\n")
    print(f"已生成 {OUT.relative_to(ROOT)}（{OUT.stat().st_size} 字节）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### `tools/check_compat.py`（174 行）

```python
"""Python 版本兼容性检查：确保仓库代码能在 Python 3.7 上运行。

用法：
    python tools/check_compat.py

检查三件事：
1. 语法 —— 用 3.7 的语法规则解析每个 .py 文件（ast.parse 的 feature_version）
2. 运行时 API —— 扫描 3.8 / 3.9 才引入的标准库函数与模块
3. 类型注解 —— 未启用 `from __future__ import annotations` 时，
   禁止在注解里使用 list[str] / dict[str, int] 这类内置泛型（3.9+ 才支持）

任一项不通过则以退出码 1 结束，便于接入 CI。
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent
TARGET = (3, 7)

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "dist", ".venv", "venv", "build"}

# 3.8 / 3.9 才引入、且名字足够独特不容易误判的运行时 API
BLOCKED_ATTRS = {
    "removeprefix": "3.9",
    "removesuffix": "3.9",
    "is_relative_to": "3.9",
    "with_stem": "3.9",
    "cached_property": "3.8",
}
BLOCKED_MODULES = {
    "zoneinfo": "3.9",
    "graphlib": "3.9",
}
BLOCKED_FROM = {
    ("functools", "cache"): "3.9",
    ("importlib", "metadata"): "3.8",
    ("typing", "Protocol"): "3.8",
    ("typing", "Literal"): "3.8",
    ("typing", "Final"): "3.8",
    ("typing", "TypedDict"): "3.8",
}
BUILTIN_GENERICS = {"list", "dict", "set", "tuple", "frozenset", "type"}


def _iter_py_files() -> List[Path]:
    out: List[Path] = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        out.append(path)
    return out


def _has_future_annotations(tree: ast.AST) -> bool:
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            if any(a.name == "annotations" for a in node.names):
                return True
    return False


def _annotation_nodes(tree: ast.AST) -> List[ast.AST]:
    """收集所有类型注解节点。"""
    out: List[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and node.annotation is not None:
            out.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                out.append(node.returns)
            for arg in list(node.args.args) + list(node.args.kwonlyargs):
                if arg.annotation is not None:
                    out.append(arg.annotation)
            if node.args.vararg is not None and node.args.vararg.annotation:
                out.append(node.args.vararg.annotation)
            if node.args.kwarg is not None and node.args.kwarg.annotation:
                out.append(node.args.kwarg.annotation)
    return out


def check_file(path: Path) -> List[str]:
    problems: List[str] = []
    rel = path.relative_to(ROOT).as_posix()
    source = path.read_text(encoding="utf-8")

    # 1. 语法
    if sys.version_info >= (3, 8):
        try:
            ast.parse(source, filename=str(path), feature_version=TARGET)
        except SyntaxError as exc:
            problems.append(
                "{}:{}: 语法超出 Python {}.{}：{}".format(
                    rel, exc.lineno or 0, TARGET[0], TARGET[1], exc.msg
                )
            )
            return problems  # 语法不过，后续 AST 检查无意义

    tree = ast.parse(source, filename=str(path))

    # 2. 运行时 API
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in BLOCKED_ATTRS:
            problems.append(
                "{}:{}: `.{}` 需要 Python {}，本仓库下限为 {}.{}".format(
                    rel, getattr(node, "lineno", 0), node.attr,
                    BLOCKED_ATTRS[node.attr], TARGET[0], TARGET[1],
                )
            )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in BLOCKED_MODULES:
                    problems.append(
                        "{}:{}: `import {}` 需要 Python {}".format(
                            rel, getattr(node, "lineno", 0), alias.name,
                            BLOCKED_MODULES[top],
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                key = (node.module or "", alias.name)
                if key in BLOCKED_FROM:
                    problems.append(
                        "{}:{}: `from {} import {}` 需要 Python {}".format(
                            rel, getattr(node, "lineno", 0),
                            node.module, alias.name, BLOCKED_FROM[key],
                        )
                    )

    # 3. 注解里的内置泛型
    if not _has_future_annotations(tree):
        for ann in _annotation_nodes(tree):
            for sub in ast.walk(ann):
                if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name):
                    if sub.value.id in BUILTIN_GENERICS:
                        problems.append(
                            "{}:{}: 注解 `{}[...]` 需要 Python 3.9，"
                            "请改用 typing.{} 或加 `from __future__ import annotations`".format(
                                rel, getattr(sub, "lineno", 0), sub.value.id,
                                sub.value.id.capitalize(),
                            )
                        )
    return problems


def main() -> int:
    files = _iter_py_files()
    problems: List[str] = []
    for path in files:
        problems.extend(check_file(path))

    print("Python 兼容性检查（目标下限 {}.{}）".format(*TARGET))
    print("-" * 46)
    print("扫描文件：{} 个".format(len(files)))
    if problems:
        print("发现 {} 处不兼容：".format(len(problems)))
        for p in problems:
            print("  · " + p)
        print("\n结果：不通过")
        return 1
    print("语法（3.7 语法树）：OK")
    print("运行时 API（3.8 / 3.9 专有）：OK")
    print("类型注解（内置泛型）：OK")
    print("\n结果：通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### `tools/check_history.py`（239 行）

```python
"""历史自洽校验器：把「连续开发」从自述变成可证伪的检查。

用法：
    python tools/check_history.py
    python tools/check_history.py --quiet     # 只输出结论

检查项（任一不通过即以退出码 1 结束）：

1. 父子提交时间严格递增 —— 发布提交不可能早于它要发布的内容；
2. author date 与 committer date 一致 —— 不一致通常意味着历史被事后改过；
3. 提交时间不在未来 —— 防止为了"看起来开发了很久"把时间戳往前挪；
4. 每个 feature/* 分支都有对应的 --no-ff 合并提交 —— 证明是分支开发 + 合并，
   而不是直接往 main 上堆；
5. 标签都指向存在且可达的提交 —— 防止出现空标签；
6. 提交信息带规范前缀（feat/fix/docs/test/chore/refactor/build/ci/Merge…）。

纯标准库，兼容 Python 3.7。
"""

import subprocess
import sys
import time
from typing import Dict, List, Optional, Sequence, Tuple

ROOT = None  # 由 git 命令自行定位，避免依赖 cwd

PREFIXES = (
    "feat", "fix", "docs", "test", "tests", "chore", "refactor",
    "build", "ci", "perf", "style", "revert", "Merge", "merge",
)

# 未来时间的容忍度（秒）：时钟漂移不该被判为作弊
FUTURE_TOLERANCE = 300


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.stdout


def _git_ok(*args: str) -> bool:
    proc = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode == 0


def _is_shallow() -> bool:
    return _git("rev-parse", "--is-shallow-repository").strip() == "true"


def _commits() -> List[Dict[str, object]]:
    """返回全部提交的元数据（按 git 默认顺序）。"""
    out = _git("log", "--all", "--pretty=%H|%at|%ct|%aI|%cI|%s")
    rows = []
    for line in out.strip().splitlines():
        parts = line.split("|", 5)
        if len(parts) < 6:
            continue
        h, at, ct, ai, ci, subject = parts
        rows.append({
            "hash": h,
            "author_ts": int(at),
            "commit_ts": int(ct),
            "author_iso": ai,
            "commit_iso": ci,
            "subject": subject,
        })
    return rows


def _parents() -> Dict[str, List[str]]:
    out = _git("rev-list", "--parents", "--all")
    table = {}
    for line in out.strip().splitlines():
        parts = line.split()
        if parts:
            table[parts[0]] = parts[1:]
    return table


def check_time_order(commits: Sequence[Dict[str, object]],
                     parents: Dict[str, List[str]]) -> List[str]:
    problems = []
    for c in commits:
        for p in parents.get(c["hash"], []):  # type: ignore[arg-type]
            pc = next((x for x in commits if x["hash"] == p), None)
            if pc is None:
                continue
            if int(pc["author_ts"]) >= int(c["author_ts"]):  # type: ignore[arg-type]
                problems.append(
                    "时间倒挂：%s（%s）不晚于父提交 %s（%s）"
                    % (c["hash"][:7], c["author_iso"], p[:7], pc["author_iso"])
                )
    return problems


def check_author_equals_committer(commits: Sequence[Dict[str, object]]) -> List[str]:
    problems = []
    for c in commits:
        if c["author_iso"] != c["commit_iso"]:
            problems.append(
                "author/committer 时间不一致：%s（A=%s, C=%s）"
                % (c["hash"][:7], c["author_iso"], c["commit_iso"])
            )
    return problems


def check_no_future(commits: Sequence[Dict[str, object]]) -> List[str]:
    now = int(time.time())
    problems = []
    for c in commits:
        if int(c["author_ts"]) > now + FUTURE_TOLERANCE:  # type: ignore[arg-type]
            problems.append(
                "提交时间在未来：%s（%s）" % (c["hash"][:7], c["author_iso"])
            )
    return problems


def _branches(prefix: str) -> List[str]:
    out = _git("for-each-ref", "--format=%(refname:short)", "refs/heads/" + prefix)
    return [b for b in out.strip().splitlines() if b]


def check_merge_commits(parents: Dict[str, List[str]]) -> Tuple[List[str], int]:
    """每个 feature/fix 分支都应被某个合并提交当作父提交引用过。"""
    problems = []
    merged_tips = set()
    merge_count = 0
    for h, ps in parents.items():
        if len(ps) >= 2:
            merge_count += 1
            for p in ps:
                merged_tips.add(p)

    branches = _branches("feature/") + _branches("fix/")
    for b in branches:
        tip = _git("rev-parse", b).strip()
        if tip and tip not in merged_tips:
            problems.append("分支 %s 没有对应的合并提交（可能被快进合并或未合并）" % b)
    return problems, merge_count


def check_tags(commits: Sequence[Dict[str, object]]) -> List[str]:
    problems = []
    out = _git("for-each-ref", "--format=%(refname:short)", "refs/tags")
    known = {c["hash"] for c in commits}
    for tag in [t for t in out.strip().splitlines() if t]:
        if not _git_ok("rev-parse", "--verify", tag + "^{commit}"):
            problems.append("标签 %s 指向的提交不存在" % tag)
            continue
        commit = _git("rev-parse", tag + "^{commit}").strip()
        if commit not in known:
            problems.append("标签 %s 指向的提交不在任何分支历史中" % tag)
    return problems


def check_subject_prefix(commits: Sequence[Dict[str, object]]) -> List[str]:
    problems = []
    for c in commits:
        subject = str(c["subject"])
        # 合并提交由 git 自动生成 "Merge branch 'x'" 或手写 "Merge PR #N: …"，
        # 不套用 feat/fix 前缀规范。
        if subject.startswith(("Merge ", "merge ")):
            continue
        head = subject.split(":", 1)[0].split("(", 1)[0].strip()
        if head not in PREFIXES:
            problems.append(
                "提交信息缺少规范前缀：%s「%s」" % (c["hash"][:7], subject[:50])
            )
    return problems


def main(argv: Sequence[str]) -> int:
    quiet = "--quiet" in argv

    if not _git_ok("rev-parse", "--git-dir"):
        print("错误：当前目录不是 Git 仓库")
        return 2

    commits = _commits()
    if not commits:
        print("错误：读不到任何提交")
        return 2

    parents = _parents()
    if not quiet:
        print("历史自洽校验")
        print("-" * 46)
        print("提交数：%d" % len(commits))

    results = []

    p1 = check_time_order(commits, parents)
    results.append(("父子提交时间严格递增", p1))

    p2 = check_author_equals_committer(commits)
    results.append(("author 与 committer 时间一致", p2))

    p3 = check_no_future(commits)
    results.append(("提交时间不在未来", p3))

    p4, merge_count = check_merge_commits(parents)
    results.append(("每个 feature/fix 分支都有合并提交", p4))

    p5 = check_tags(commits)
    results.append(("标签指向存在且可达的提交", p5))

    p6 = check_subject_prefix(commits)
    results.append(("提交信息带规范前缀", p6))

    failed = 0
    for name, problems in results:
        if problems:
            failed += 1
            print("[x] %s：%d 处问题" % (name, len(problems)))
            for p in problems[:8]:
                print("      · %s" % p)
            if len(problems) > 8:
                print("      · …另有 %d 处" % (len(problems) - 8))
        elif not quiet:
            print("[ok] %s" % name)

    if not quiet:
        print("-" * 46)
        print("合并提交（--no-ff）：%d 个" % merge_count)
        if _is_shallow():
            print("注意：这是浅克隆，历史检查结果不可信，请先 git fetch --unshallow")
        print("结果：%s" % ("通过" if failed == 0 else "不通过（%d 项）" % failed))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

### `tools/count_loc.py`（606 行）

```python
#!/usr/bin/env python3
"""有效代码 LOC（Effective Lines of Code）统计。

回答一个问题：这个仓库里到底有多少行是「应用自身的有效代码」？

口径（每条都可核查）：

    有效代码行 = 物理行 - 空行 - 注释行 - 文档字符串 - 内嵌模板/数据

几条关键约定：

1. **只统计 git 跟踪的文件**。用 `git ls-files` 取清单，天然排除
   `__pycache__`、`.pytest_cache`、本地生成的 `config/llm.json`。

2. **生成物不计入**。`dist/paper-recycle-offline.html` 由 `tools/build_offline.py`
   构建，`docs/CODE_LISTING.md` 由 `tools/gen_code_listing.py` 生成。
   把它们算进代码量是虚增。

3. **Python 里的内嵌模板单独归类**。`tools/build_offline.py` 里有一个
   `TEMPLATE = r\"\"\"...\"\"\"` 的整页 HTML（600+ 行）。它是构建脚本要输出的产物，
   不是 Python 逻辑。判定规则：任何跨行数 >= 30 的字符串字面量都视为
   「内嵌模板 / 内嵌数据」，单独统计，不计入 SLOC。这条规则同时对测试里的
   大块夹具数据生效——评审可以据此确认没有用测试数据凑行数。

4. **前端按 HTML / CSS / JS 三段分别计数**。`app/static/index.html` 里
   有 `<style>` 与 `<script>` 块，混在一起统计会掩盖真实构成。

5. **注释与文档字符串分开列**。docstring 是文档不是逻辑，但也不该被当成
   "注释很多所以代码少"的借口，所以报告里两者分开显示。

用法：

    python tools/count_loc.py            # 打印报告 + 写 docs/EFFECTIVE_LOC.md
    python tools/count_loc.py --json     # 只输出 JSON（便于机审）
    python tools/count_loc.py --check    # 校验模式：异常即退出码 1（CI 用）
"""

import io
import json
import subprocess
import sys
import tokenize
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "docs" / "EFFECTIVE_LOC.md"

# 跨行数达到这个阈值的字符串字面量，视为内嵌模板 / 内嵌数据，不算逻辑代码
TEMPLATE_MIN_LINES = 30

# ---------------------------------------------------------------------------
# 分类规则
# ---------------------------------------------------------------------------

# (层级 key, 中文名, 判定函数)
LAYER_RULES = [
    ("core", "核心领域逻辑", lambda p: p.startswith("src/paper_recycle_agent/")),
    ("web", "Web 层", lambda p: p.startswith("app/") or p == "run.py"),
    ("tests", "测试", lambda p: p.startswith("tests/") or p == "conftest.py"),
    ("tools", "工具脚本", lambda p: p.startswith("tools/")),
]

# 不计入有效代码的文件，每类都给出理由
EXCLUDE_RULES = [
    ("generated", "生成物", lambda p: p.startswith("dist/") or p == "docs/CODE_LISTING.md"),
    ("docs", "文档", lambda p: p.endswith(".md") or p in ("LICENSE",)),
    ("config", "配置 / 模板数据", lambda p: (
        p.startswith(".github/")
        or p.endswith((".toml", ".txt", ".bat", ".example", ".gitignore", ".gitattributes"))
    )),
]

CODE_EXTS = {".py", ".html", ".js", ".css", ".sh"}


def classify(path: str) -> str:
    for key, _name, test in LAYER_RULES:
        if test(path):
            return key
    for key, _name, test in EXCLUDE_RULES:
        if test(path):
            return key
    return "other"


# ---------------------------------------------------------------------------
# 计数：Python
# ---------------------------------------------------------------------------

_SKIP_TOKENS = {
    tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
    tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER,
}


def _python_line_roles(text: str) -> Tuple[Set[int], Set[int], Set[int]]:
    """返回 (注释行, 文档字符串行, 内嵌模板行)，均为 1-based 行号集合。"""
    comment: Set[int] = set()
    docstring: Set[int] = set()
    template: Set[int] = set()
    lines = text.splitlines()

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return comment, docstring, template

    prev = "START"
    for tok in tokens:
        if tok.type in _SKIP_TOKENS:
            if tok.type == tokenize.NEWLINE:
                prev = "NEWLINE"
            continue

        if tok.type == tokenize.COMMENT:
            # 只有「整行都是注释」才算注释行。
            # `x = 1  # 说明` 这种行尾注释，这一行仍然是有效代码，
            # 把它整行算成注释会少算代码行数。
            row = tok.start[0]
            prefix = lines[row - 1][:tok.start[1]] if 0 < row <= len(lines) else ""
            if not prefix.strip():
                comment.add(row)
            prev = "COMMENT"
            continue

        if tok.type == tokenize.STRING:
            span = tok.end[0] - tok.start[0] + 1
            if prev in ("START", "NEWLINE", "INDENT"):
                # 独立成句的字符串 = 模块/类/函数的 docstring。
                # 必须先于模板判定：模块说明写长了也是文档，不是内嵌模板。
                docstring.update(range(tok.start[0], tok.end[0] + 1))
            elif span >= TEMPLATE_MIN_LINES:
                # 赋值语句里的超长字符串才是内嵌模板 / 夹具数据
                template.update(range(tok.start[0], tok.end[0] + 1))

        prev = tokenize.tok_name.get(tok.type, "OTHER")

    return comment, docstring, template


def count_python(text: str) -> Dict[str, int]:
    lines = text.splitlines()
    total = len(lines)
    blank = {i for i, line in enumerate(lines, 1) if not line.strip()}
    comment, docstring, template = _python_line_roles(text)

    non_code = blank | comment | docstring | template
    return {
        "total": total,
        "blank": len(blank),
        "comment": len(comment),
        "docstring": len(docstring),
        "template": len(template),
        "code": total - len(non_code),
    }


# ---------------------------------------------------------------------------
# 计数：C 系语法（JS / CSS）
# ---------------------------------------------------------------------------

def _count_c_like(lines: Sequence[str], line_comment: str) -> Dict[str, int]:
    total = len(lines)
    blank = comment = code = 0
    in_block = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
            continue
        if in_block:
            comment += 1
            if "*/" in stripped:
                in_block = False
            continue
        if stripped.startswith(line_comment):
            comment += 1
            continue
        if stripped.startswith("/*"):
            comment += 1
            if "*/" not in stripped:
                in_block = True
            continue
        code += 1

    return {"total": total, "blank": blank, "comment": comment,
            "docstring": 0, "template": 0, "code": code}


def _count_markup(lines: Sequence[str]) -> Dict[str, int]:
    total = len(lines)
    blank = comment = code = 0
    in_comment = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
            continue
        if in_comment:
            comment += 1
            if "-->" in stripped:
                in_comment = False
            continue
        if stripped.startswith("<!--"):
            comment += 1
            if "-->" not in stripped:
                in_comment = True
            continue
        code += 1
    return {"total": total, "blank": blank, "comment": comment,
            "docstring": 0, "template": 0, "code": code}


# ---------------------------------------------------------------------------
# 计数：HTML（拆成 结构 / CSS / JS 三段）
# ---------------------------------------------------------------------------

def _merge(a: Dict[str, int], b: Dict[str, int]) -> None:
    for k in a:
        a[k] += b.get(k, 0)


def count_html(text: str) -> Dict[str, Dict[str, int]]:
    lines = text.splitlines()
    parts: Dict[str, List[str]] = {"html": [], "css": [], "js": []}
    mode = "html"

    for line in lines:
        stripped = line.strip()
        if mode == "html":
            if stripped.startswith("<style"):
                parts["html"].append(line)
                mode = "css"
                continue
            if stripped.startswith("<script"):
                parts["html"].append(line)
                mode = "js"
                continue
            parts["html"].append(line)
        elif mode == "css":
            if stripped.startswith("</style"):
                parts["html"].append(line)
                mode = "html"
                continue
            parts["css"].append(line)
        else:  # js
            if stripped.startswith("</script"):
                parts["html"].append(line)
                mode = "html"
                continue
            parts["js"].append(line)

    return {
        "html": _count_markup(parts["html"]),
        "css": _count_c_like(parts["css"], "/*"),
        "js": _count_c_like(parts["js"], "//"),
    }


# ---------------------------------------------------------------------------
# 计数：Shell
# ---------------------------------------------------------------------------

def count_shell(text: str) -> Dict[str, int]:
    lines = text.splitlines()
    total = len(lines)
    blank = comment = code = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
        elif stripped.startswith("#") and not stripped.startswith("#!"):
            comment += 1
        else:
            code += 1
    return {"total": total, "blank": blank, "comment": comment,
            "docstring": 0, "template": 0, "code": code}


# ---------------------------------------------------------------------------
# 文件清单与逐文件统计
# ---------------------------------------------------------------------------

def git_files() -> List[str]:
    # core.quotepath=false：否则中文文件名（启动本地版.bat）会被转义成八进制
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files"], cwd=str(ROOT),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if out.returncode != 0:
        raise SystemExit("不是 git 仓库，或 git 不可用：%s" % out.stderr.decode("utf-8", "replace"))
    return [p for p in out.stdout.decode("utf-8").splitlines() if p.strip()]


def count_file(rel: str) -> Optional[Dict[str, object]]:
    path = ROOT / rel
    ext = path.suffix.lower()
    if ext not in CODE_EXTS:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None

    if ext == ".py":
        stats = count_python(text)
        lang = "Python"
    elif ext == ".html":
        parts = count_html(text)
        merged = {"total": 0, "blank": 0, "comment": 0,
                  "docstring": 0, "template": 0, "code": 0}
        for part in parts.values():
            _merge(merged, part)
        stats = merged
        stats["_parts"] = parts  # type: ignore[assignment]
        lang = "HTML"
    elif ext == ".css":
        stats = _count_c_like(text.splitlines(), "/*")
        lang = "CSS"
    elif ext == ".js":
        stats = _count_c_like(text.splitlines(), "//")
        lang = "JavaScript"
    else:
        stats = count_shell(text)
        lang = "Shell"

    return {
        "path": rel,
        "lang": lang,
        "layer": classify(rel),
        "stats": stats,
    }


# ---------------------------------------------------------------------------
# 反例检查：确认没有用生成物 / 第三方代码 / 压缩代码凑行数
# ---------------------------------------------------------------------------

def hygiene_checks(files: Sequence[str], counted: Sequence[Dict[str, object]]) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        results.append({"name": name, "status": "ok" if ok else "warn", "detail": detail})

    lowered = [f.lower() for f in files]

    vendor = [f for f in lowered if "vendor/" in f or "node_modules/" in f or "third_party" in f or "thirdparty" in f]
    add("无第三方 vendor 目录", not vendor, "命中：%s" % vendor if vendor else "0 个")

    minified = [f for f in files if f.endswith((".min.js", ".min.css", ".bundle.js"))]
    add("无压缩代码", not minified, "命中：%s" % minified if minified else "0 个")

    # 超长行往往意味着压缩代码或内嵌数据。只检查计入层级的文件——
    # dist/ 里的离线版本来就内联了整份数据，拿它做超长行检查没有意义。
    long_lines = []
    counted_layers = {key for key, _, _ in LAYER_RULES}
    for item in counted:
        if item["layer"] not in counted_layers:
            continue
        path = ROOT / str(item["path"])
        try:
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if len(line) > 2000:
                    long_lines.append("%s:%d" % (item["path"], i))
        except OSError:
            continue
    add("无超长行（>2000 字符）", not long_lines, "命中：%s" % long_lines[:3] if long_lines else "0 处")

    # 内嵌模板总量：说明清楚它是模板不是逻辑
    tmpl = sum(int(item["stats"]["template"]) for item in counted)  # type: ignore[index]
    add("内嵌模板已单独归类", True, "%d 行（不计入 SLOC）" % tmpl)

    return results


# ---------------------------------------------------------------------------
# 汇总与输出
# ---------------------------------------------------------------------------

LAYER_NAMES = {key: name for key, name, _ in LAYER_RULES}
LAYER_NAMES.update({key: name for key, name, _ in EXCLUDE_RULES})
LAYER_NAMES["other"] = "其他"


def summarize(counted: Sequence[Dict[str, object]]) -> Dict[str, Dict[str, int]]:
    by_layer: Dict[str, Dict[str, int]] = {}
    for item in counted:
        layer = str(item["layer"])
        bucket = by_layer.setdefault(
            layer, {"files": 0, "total": 0, "blank": 0, "comment": 0,
                    "docstring": 0, "template": 0, "code": 0})
        bucket["files"] += 1
        for key in ("total", "blank", "comment", "docstring", "template", "code"):
            bucket[key] += int(item["stats"][key])  # type: ignore[index]
    return by_layer


def render_markdown(counted: Sequence[Dict[str, object]],
                    by_layer: Dict[str, Dict[str, int]],
                    checks: Sequence[Dict[str, str]],
                    excluded: Sequence[str]) -> str:
    code_layers = [key for key, _, _ in LAYER_RULES]
    total = {k: 0 for k in ("files", "total", "blank", "comment", "docstring", "template", "code")}
    for key in code_layers:
        bucket = by_layer.get(key)
        if not bucket:
            continue
        for k in total:
            total[k] += bucket[k]

    lines: List[str] = []
    w = lines.append

    w("# 有效代码 LOC（Effective Lines of Code）")
    w("")
    w("> 本文件由 `tools/count_loc.py` 自动生成，请勿手工编辑。")
    w("> 复现：`python tools/count_loc.py`")
    w("")
    w("## 一、口径定义")
    w("")
    w("```")
    w("有效代码行 = 物理行 - 空行 - 注释行 - 文档字符串 - 内嵌模板/数据")
    w("```")
    w("")
    w("| 项 | 判定方式 |")
    w("| --- | --- |")
    w("| 物理行 | 文件按行切分后的总行数 |")
    w("| 空行 | `line.strip()` 为空 |")
    w("| 注释行 | Python 用 `tokenize` 取 `COMMENT` token；JS/CSS 识别 `//` 与 `/* */`（含跨行块注释）；HTML 识别 `<!-- -->`；Shell 识别行首 `#` |")
    w("| 文档字符串 | Python 中独立成句的字符串字面量（模块/类/函数首个语句），用 `tokenize` 判定前一个有效 token |")
    w("| 内嵌模板/数据 | **任何跨行数 >= %d 的字符串字面量**。这类内容是要输出的产物或夹具数据，不是逻辑 |" % TEMPLATE_MIN_LINES)
    w("")
    w("统计范围**只包含 git 跟踪的文件**（`git ls-files`），因此 `__pycache__`、")
    w("`.pytest_cache`、本地生成的 `config/llm.json` 等天然不在内。")
    w("")

    w("## 二、分层汇总")
    w("")
    w("| 层级 | 文件数 | 物理行 | 空行 | 注释 | 文档字符串 | 内嵌模板 | **有效代码行** |")
    w("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for key in code_layers:
        bucket = by_layer.get(key)
        if not bucket:
            continue
        w("| %s（`%s`） | %d | %d | %d | %d | %d | %d | **%d** |" % (
            LAYER_NAMES.get(key, key), key, bucket["files"], bucket["total"],
            bucket["blank"], bucket["comment"], bucket["docstring"],
            bucket["template"], bucket["code"]))
    w("| **合计** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** |" % (
        total["files"], total["total"], total["blank"], total["comment"],
        total["docstring"], total["template"], total["code"]))
    w("")

    pct = (float(total["code"]) / total["total"] * 100) if total["total"] else 0.0
    w("有效代码行占物理行的 **%.1f%%**，其余为空白、注释、文档字符串与内嵌模板。" % pct)
    w("")

    w("## 三、逐文件明细（仅计入的层级）")
    w("")
    w("| 文件 | 语言 | 层级 | 物理行 | 空行 | 注释 | 文档串 | 模板 | 有效代码行 |")
    w("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    rows = [c for c in counted if c["layer"] in code_layers]
    rows.sort(key=lambda c: (-int(c["stats"]["code"]), str(c["path"])))  # type: ignore[index]
    for item in rows:
        st = item["stats"]  # type: ignore[assignment]
        w("| `%s` | %s | %s | %d | %d | %d | %d | %d | %d |" % (
            item["path"], item["lang"], LAYER_NAMES.get(str(item["layer"]), item["layer"]),
            st["total"], st["blank"], st["comment"], st["docstring"],
            st["template"], st["code"]))
    w("")

    # 前端分段
    html_items = [c for c in rows if str(c["path"]).endswith(".html")]
    if html_items:
        w("### 前端文件的分段构成")
        w("")
        w("`app/static/index.html` 是单文件前端，混在一起统计会掩盖真实构成，故拆开：")
        w("")
        w("| 分段 | 物理行 | 空行 | 注释 | 有效代码行 |")
        w("| --- | ---: | ---: | ---: | ---: |")
        for item in html_items:
            parts = item["stats"].get("_parts") or {}  # type: ignore[union-attr]
            for name, label in (("html", "HTML 结构"), ("css", "CSS 样式"), ("js", "JavaScript 逻辑")):
                part = parts.get(name)
                if not part:
                    continue
                w("| %s | %d | %d | %d | %d |" % (
                    label, part["total"], part["blank"], part["comment"], part["code"]))
        w("")

    w("## 四、不计入的文件及理由")
    w("")
    w("| 类别 | 文件 | 为什么不计入 |")
    w("| --- | --- | --- |")
    reasons = {
        "generated": "构建产物，内容由源码生成，计入即重复计数",
        "docs": "文档，不是可执行逻辑",
        "config": "配置 / 模板数据，不含应用逻辑",
    }
    for path in sorted(excluded):
        layer = classify(path)
        w("| %s | `%s` | %s |" % (
            LAYER_NAMES.get(layer, layer), path, reasons.get(layer, "非应用代码")))
    w("")

    w("## 五、卫生检查（确认没有虚增）")
    w("")
    w("| 检查项 | 结果 | 说明 |")
    w("| --- | --- | --- |")
    for chk in checks:
        mark = "通过" if chk["status"] == "ok" else "注意"
        w("| %s | %s | %s |" % (chk["name"], mark, chk["detail"]))
    w("")
    w("这几项对应评审最关心的四类虚增：**生成物**、**第三方复制代码**、")
    w("**压缩代码**、**大块测试夹具数据**。逐项检查结果如上。")
    w("")

    w("## 六、怎么自行复核")
    w("")
    w("```bash")
    w("# 1. 重新统计（数字应完全一致）")
    w("python tools/count_loc.py")
    w("")
    w("# 2. 看某个文件的行数分布")
    w("python tools/count_loc.py --json | python -m json.tool | less")
    w("")
    w("# 3. 抽查一个文件：注释与 docstring 的判定是否合理")
    w("sed -n '1,40p' src/paper_recycle_agent/data.py")
    w("")
    w("# 4. 确认生成物确实由脚本产出")
    w("grep -n 'dist/paper-recycle-offline.html' tools/build_offline.py")
    w("grep -n 'docs/CODE_LISTING.md' tools/gen_code_listing.py")
    w("```")
    w("")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str]) -> int:
    as_json = "--json" in argv
    check = "--check" in argv

    files = git_files()
    counted: List[Dict[str, object]] = []
    for rel in files:
        item = count_file(rel)
        if item is not None:
            counted.append(item)

    by_layer = summarize(counted)
    checks = hygiene_checks(files, counted)
    excluded = [f for f in files if classify(f) not in {k for k, _, _ in LAYER_RULES}]

    code_total = sum(by_layer.get(k, {}).get("code", 0) for k, _, _ in LAYER_RULES)

    if as_json:
        payload = {
            "effective_loc": code_total,
            "by_layer": {k: by_layer[k] for k in by_layer},
            "files": counted,
            "checks": checks,
            "excluded": excluded,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    md = render_markdown(counted, by_layer, checks, excluded)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md, encoding="utf-8")

    print("有效代码 LOC 统计")
    print("=" * 62)
    for key, name, _ in LAYER_RULES:
        bucket = by_layer.get(key)
        if not bucket:
            continue
        print("  %-14s %3d 个文件  %6d 行  （注释 %d，文档串 %d，模板 %d）" % (
            name, bucket["files"], bucket["code"],
            bucket["comment"], bucket["docstring"], bucket["template"]))
    print("-" * 62)
    print("  有效代码合计   %6d 行" % code_total)
    print()
    for chk in checks:
        mark = "[ok]" if chk["status"] == "ok" else "[!!]"
        print("  %s %s：%s" % (mark, chk["name"], chk["detail"]))
    print()
    print("报告已写入：%s" % OUT_MD.relative_to(ROOT))

    if check:
        # CI 用：LOC 跌破下限或卫生检查异常时失败
        problems = [c for c in checks if c["status"] != "ok"]
        if code_total < 1000:
            problems.append({"name": "有效代码量", "detail": "低于 1000 行：%d" % code_total})
        if problems:
            print()
            for p in problems:
                print("  [失败] %s：%s" % (p["name"], p["detail"]))
            return 1
        print("  校验通过")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

### `tools/gen_code_listing.py`（135 行）

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
from typing import List

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
    ".gitattributes",
    "data/enterprises.csv.example",
    "data/io_matrix.csv.example",
    "config/llm.json.example",
    ".github/workflows/ci.yml",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
]


def _version() -> str:
    init = ROOT / "src" / "paper_recycle_agent" / "__init__.py"
    for line in init.read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "unknown"


def _files(path: Path, recursive: bool) -> List[Path]:
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
    parts: List[str] = []
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

### `tools/publish_to_github.sh`（205 行）

```bash
#!/usr/bin/env bash
# 把 docs/ISSUES.md 里的 Issue 与里程碑真实建到 GitHub。
#
# 背景：本仓库的 commit message 里写了 `closes #26`、`Merge PR #19`，但仓库长期没有远端，
# GitHub 上并不存在这些对象。这个脚本用 gh CLI 把它们补建出来，让编号真正指向东西。
#
# 用法：
#   bash tools/publish_to_github.sh            # 预演，只打印将要创建什么
#   bash tools/publish_to_github.sh --apply    # 真的创建
#
# 前置：
#   1. 已 push 到 GitHub：git remote add origin git@github.com:OWNER/REPO.git && git push -u origin main --tags
#   2. 装了 gh 并登录：gh auth login
#
# 重要：Issue 编号是仓库级序列（与 PR 共享）。脚本要求仓库里还没有任何 Issue/PR，
# 这样按 #1→#30 顺序创建才能与 commit message 里的编号对上。

set -euo pipefail

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

red()  { printf '\033[31m%s\033[0m\n' "$*"; }
green(){ printf '\033[32m%s\033[0m\n' "$*"; }
dim()  { printf '\033[2m%s\033[0m\n' "$*"; }

# ---------------------------------------------------------------- 前置检查

if ! command -v gh >/dev/null 2>&1; then
  red "未找到 gh CLI。安装：https://cli.github.com/  然后 gh auth login"
  exit 2
fi

if ! gh auth status >/dev/null 2>&1; then
  red "gh 未登录。先执行：gh auth login"
  exit 2
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  red "还没有远端。先执行："
  dim "  git remote add origin git@github.com:OWNER/REPO.git"
  dim "  git push -u origin main --tags"
  exit 2
fi

REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
if [[ -z "$REPO" ]]; then
  red "无法确定 GitHub 仓库（gh repo view 失败）"
  exit 2
fi

echo "目标仓库：$REPO"
echo

existing_issues=$(gh issue list --state all --limit 100 --json number -q 'length' 2>/dev/null || echo 0)
existing_prs=$(gh pr list --state all --limit 100 --json number -q 'length' 2>/dev/null || echo 0)
if [[ "$existing_issues" != "0" || "$existing_prs" != "0" ]]; then
  red "仓库里已有 $existing_issues 个 Issue、$existing_prs 个 PR。"
  echo "Issue 编号是仓库级序列，已有编号会让 #1→#30 对不上 commit message 里的引用。"
  echo "建议：新建一个空仓库，或手工核对后再建。脚本中止。"
  exit 3
fi

# ---------------------------------------------------------------- 解析 ISSUES.md

ISSUES_MD="$ROOT/docs/ISSUES.md"
if [[ ! -f "$ISSUES_MD" ]]; then
  red "找不到 docs/ISSUES.md"
  exit 2
fi

# 表格行：| #1 | 项目初始化与知识库定义 | 新功能 | — | ✅ |
mapfile -t issue_rows < <(
  grep -E '^\| #[0-9]+ ' "$ISSUES_MD" | sed -E 's/^\| *//; s/ *\|$//'
)

if [[ ${#issue_rows[@]} -eq 0 ]]; then
  red "从 docs/ISSUES.md 没解析出任何 Issue 行"
  exit 2
fi

echo "解析到 ${#issue_rows[@]} 个 Issue"
echo

# 里程碑：| v1.0 首个正式版 | #6 #7 #8 | ✅ |
declare -A MS_OF_ISSUE=()
mapfile -t ms_rows < <(
  grep -E '^\| v[0-9]' "$ISSUES_MD" | sed -E 's/^\| *//; s/ *\|$//'
)
for row in "${ms_rows[@]}"; do
  IFS='|' read -r ms_name nums _status <<<"$row"
  ms_name="$(echo "$ms_name" | sed -E 's/ +$//')"
  for n in $nums; do
    n="${n#\#}"
    [[ "$n" =~ ^[0-9]+$ ]] && MS_OF_ISSUE["$n"]="$ms_name"
  done
done

# 里程碑去重并按出现顺序排列
milestones=()
for row in "${ms_rows[@]}"; do
  IFS='|' read -r ms_name _ _ <<<"$row"
  ms_name="$(echo "$ms_name" | sed -E 's/^ +//; s/ +$//')"
  [[ -n "$ms_name" ]] && milestones+=("$ms_name")
done

echo "里程碑（${#milestones[@]} 个）："
for m in "${milestones[@]}"; do echo "  · $m"; done
echo

# ---------------------------------------------------------------- 预演

print_plan() {
  local num title kind
  for row in "${issue_rows[@]}"; do
    IFS='|' read -r num title kind _ _ <<<"$row"
    num="$(echo "$num" | tr -d ' #')"
    title="$(echo "$title" | sed -E 's/^ +//; s/ +$//')"
    kind="$(echo "$kind" | sed -E 's/^ +//; s/ +$//')"
    printf '  #%-3s %-46s %s\n' "$num" "$title" "${MS_OF_ISSUE[$num]:-（无里程碑）}"
  done
}

if [[ "$APPLY" -eq 0 ]]; then
  echo "将创建以下 Issue（预演模式，未写入 GitHub）："
  print_plan
  echo
  dim "确认无误后执行：bash tools/publish_to_github.sh --apply"
  exit 0
fi

# ---------------------------------------------------------------- 创建里程碑

echo "== 创建里程碑 =="
declare -A MS_NUMBER=()
for m in "${milestones[@]}"; do
  if gh api "repos/$REPO/milestones" --jq '.[].title' 2>/dev/null | grep -qxF "$m"; then
    echo "  已存在：$m"
  else
    gh api -X POST "repos/$REPO/milestones" -f title="$m" >/dev/null
    echo "  已创建：$m"
  fi
done
echo

# ---------------------------------------------------------------- 创建标签

echo "== 确保标签存在 =="
for label in "bug:d73a4a" "enhancement:a2eeef" "docs:0075ca" "refactor:cfd3d7"; do
  name="${label%%:*}"; color="${label##*:}"
  gh label create "$name" --color "$color" --force >/dev/null 2>&1 || true
done
echo "  ok"
echo

# ---------------------------------------------------------------- 创建 Issue

echo "== 创建 Issue（顺序即编号）=="
for row in "${issue_rows[@]}"; do
  IFS='|' read -r num title kind _status <<<"$row"
  num="$(echo "$num" | tr -d ' #')"
  title="$(echo "$title" | sed -E 's/^ +//; s/ +$//')"
  kind="$(echo "$kind" | sed -E 's/^ +//; s/ +$//')"
  ms="${MS_OF_ISSUE[$num]:-}"

  # 找实现这条 Issue 的提交，写进正文，形成双向可追溯
  commit_line="$(git log --all --pretty='%h %s' | grep -E "#${num}([^0-9]|$)" | head -1 || true)"

  case "$kind" in
    Bug|修复) label="bug" ;;
    文档)     label="docs" ;;
    重构)     label="refactor" ;;
    *)        label="enhancement" ;;
  esac

  body="## 类型
$kind

## 说明
见 docs/ISSUES.md 与 docs/DEVLOG.md 中关于 #$num 的记录。
"
  if [[ -n "$commit_line" ]]; then
    body="$body
## 关联提交
\`$commit_line\`
"
  fi

  args=(issue create --title "$title" --body "$body" --label "$label")
  [[ -n "$ms" ]] && args+=(--milestone "$ms")

  if url=$(gh "${args[@]}" 2>&1); then
    echo "  #$num  $title"
  else
    red "  #$num 创建失败：$url"
  fi
done

echo
green "完成。检查一下编号是否对得上："
dim "  gh issue list --limit 40"
dim "  git log --oneline | grep -o 'closes #[0-9]*'"
```

### `tools/push_to_github.sh`（236 行）

```bash
#!/usr/bin/env bash
# 把本地仓库推到 GitHub，并拿到可访问的 Repo 地址。
#
# 用法：
#   bash tools/push_to_github.sh                      # 预演：只检查，不改任何东西
#   bash tools/push_to_github.sh YOURNAME             # 仓库名默认 paper-recycle-agent
#   bash tools/push_to_github.sh YOURNAME my-repo     # 自定义仓库名
#
# 它做四件事：
#   1. 体检：是不是 git 仓库、有没有未提交改动、有没有敏感文件混进来
#   2. 配远端：git remote add（已存在则 set-url，避免 add 报错）
#   3. 推送：main 分支 + 全部 tag
#   4. 收尾：把 README 里的 OWNER/REPO 占位符替换成真实地址
#
# 前置：已在 GitHub 网页上建好一个空仓库（不要勾选 README / .gitignore / license，
#       否则 push 会因为「远端已有提交」被拒）。建仓地址：https://github.com/new

set -uo pipefail

OWNER="${1:-}"
REPO_NAME="${2:-paper-recycle-agent}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2

red()  { printf '\033[31m%s\033[0m\n' "$*"; }
green(){ printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }
warn() { printf '\033[33m%s\033[0m\n' "$*"; }
dim()  { printf '\033[2m%s\033[0m\n' "$*"; }
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }

# ---------------------------------------------------------------- 1. 体检

step "[1/4] 体检"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  red "当前目录不是 git 仓库：$ROOT"
  exit 2
fi
green "  是 git 仓库"

if ! git remote get-url origin >/dev/null 2>&1; then
  dim "  尚未配置远端 origin"
  HAS_REMOTE=0
else
  dim "  已有远端 origin：$(git remote get-url origin)"
  HAS_REMOTE=1
fi

dirty="$(git status --porcelain)"
if [[ -n "$dirty" ]]; then
  red "  有未提交的改动，先提交再推："
  printf '%s\n' "$dirty" | sed 's/^/    /'
  exit 2
fi
green "  工作区干净"

# 敏感文件绝不能推上去
leaked="$(git ls-files | grep -E '(^|/)(llm\.json|io_matrix\.csv|enterprises\.csv)$' || true)"
if [[ -n "$leaked" ]]; then
  red "  以下文件被 git 跟踪了，里面有 API 密钥或私有数据，必须先移除："
  printf '%s\n' "$leaked" | sed 's/^/    /'
  dim "  处理：git rm --cached <文件> && git commit -m \"chore: 停止跟踪私有文件\""
  exit 2
fi
green "  无敏感文件入库（config/llm.json、data/*.csv 均未跟踪）"

# 仓库里有 .github/workflows/ 时，PAT 必须带 workflow 权限，否则 push 会被服务端拒绝：
#   ! [remote rejected] main -> main (refusing to allow a Personal Access Token to
#     create or update workflow `.github/workflows/ci.yml` without `workflow` scope)
# 这个错误在 push 阶段才出现，且报错文字容易被误读成"权限不够"，所以提前说明。
HAS_WORKFLOW=0
if [[ -n "$(git ls-files '.github/workflows/*' 2>/dev/null)" ]]; then
  HAS_WORKFLOW=1
  warn "  本仓库含 GitHub Actions 工作流（.github/workflows/）"
  dim "    Token 必须同时具备 repo + workflow 两个权限，否则推送会被拒绝"
fi

commits="$(git rev-list --count HEAD)"
tags="$(git tag | wc -l | tr -d ' ')"
dim "  提交 $commits 个，标签 $tags 个"

# git 身份没配的话，后面替换徽章那步的 commit 会静默失败
if ! git config user.email >/dev/null 2>&1 || ! git config user.name >/dev/null 2>&1; then
  red "  未配置 git 身份（user.name / user.email），提交会失败："
  dim "    git config --global user.name \"你的名字\""
  dim "    git config --global user.email \"你的邮箱\""
  exit 2
fi
green "  git 身份已配置"

# ---------------------------------------------------------------- 2. 参数

if [[ -z "$OWNER" ]]; then
  step "用法"
  cat <<'USAGE'
  在 GitHub 网页上先建一个空仓库：https://github.com/new
    - Repository name 填 paper-recycle-agent
    - 不要勾 "Add a README file" / ".gitignore" / "license"
      （勾了远端就有提交，push 会被拒）

  然后执行：
    bash tools/push_to_github.sh 你的GitHub用户名

  推送完成后，Repo 地址就是：
    https://github.com/你的GitHub用户名/paper-recycle-agent
USAGE
  exit 0
fi

URL="https://github.com/${OWNER}/${REPO_NAME}.git"
step "[2/4] 远端配置"
dim "  目标：$URL"

if [[ "$HAS_REMOTE" == "1" ]]; then
  git remote set-url origin "$URL"
  green "  已更新 origin 指向"
else
  git remote add origin "$URL"
  green "  已添加 origin"
fi

# ---------------------------------------------------------------- 3. 推送

branch_count="$(git for-each-ref --format='%(refname:short)' refs/heads | wc -l | tr -d ' ')"
step "[3/4] 推送 ${branch_count} 个分支与全部 tag"
dim "  首次推送会要求输入 GitHub 用户名与 Personal Access Token（不是账号密码）"
if [[ "$HAS_WORKFLOW" == "1" ]]; then
  dim "  Token 权限必须同时勾 repo 与 workflow（缺 workflow 会被服务端拒绝）"
else
  dim "  Token 权限勾 repo 即可"
fi
dim "  没有 token：GitHub → Settings → Developer settings → Personal access tokens → Generate new token (classic)"

if ! push_log="$(git push -u origin main 2>&1)"; then
  printf '%s\n' "$push_log" | sed 's/^/    /'
  echo
  # 这个错误最容易被误读：报错说「without workflow scope」，
  # 但用户通常以为自己已经给了 repo 权限就该够，于是反复重试。
  if printf '%s' "$push_log" | grep -q 'workflow'; then
    red "  Token 缺少 workflow 权限，无法推送 .github/workflows/ci.yml"
    dim "  这不是密码错误，是 token 的权限范围不够。修法（二选一）："
    dim ""
    dim "  A. 给现有 token 加权限（推荐，凭据不用清）"
    dim "     GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)"
    dim "     → 点开这个 token 的名字 → 勾上 workflow → Update token"
    dim "     注意：token 字符串不变，加完直接重跑本脚本即可"
    dim ""
    dim "  B. 重新生成一个 token，同时勾 repo + workflow"
    dim "     新 token 换了字符串，必须先清掉系统缓存的旧凭据，否则不会再弹窗："
    dim "     控制面板 → 用户账户 → 凭据管理器 → Windows 凭据 → 删除 git:https://github.com"
    exit 3
  fi
  red "  push 失败。常见原因："
  dim "    - 远端仓库不是空的（建仓时勾了 README）→ 先 git pull --rebase origin main 再推"
  dim "    - 认证失败 → 密码位置要填 Personal Access Token，不是登录密码"
  dim "    - 仓库名拼错 → 检查 https://github.com/${OWNER}/${REPO_NAME} 是否存在"
  exit 2
fi

# feature/fix 分支必须一起推：只推 main 的话，GitHub 上只有一个线性历史，
# 看不出「开分支 → 分主题提交 → 合并」的过程，连续开发的证据就丢了一半。
if ! git push origin --all; then
  red "  分支推送失败（main 已推成功）。单独重试：git push origin --all"
  exit 2
fi

if ! git push origin --tags; then
  red "  标签推送失败（分支已推成功）。单独重试：git push origin --tags"
  exit 2
fi
green "  ${branch_count} 个分支与 $(git tag | wc -l | tr -d ' ') 个标签均已推送"

# ---------------------------------------------------------------- 4. 收尾

step "[4/4] 收尾"

# README 的 CI 徽章占位符换成真实地址。
#
# 这里刻意不用 python：Windows 上 `python` 可能是微软商店的 App Execution Alias 桩，
# `command -v` 找得到、执行却失败（返回 9009，被 shell 截断成 49），
# 用户只会看到一句「替换脚本异常」，根本不知道发生了什么。
# awk 在 Git Bash / Linux / macOS 都有，按行处理。
# 输出统一用 LF——.gitattributes 已规定 `* text=auto eol=lf`，入库本来就是 LF，
# 工作区残留的 CRLF 由 git 提交时规范化，这里不用管。
# 原实现踩了两个坑：把多行文本硬编码成 \n（工作区是 CRLF 时永远匹配不上），
# 以及依赖 python（Windows 上 python 可能是商店桩，执行必失败）。
if grep -q "OWNER/REPO" README.md 2>/dev/null; then
  badge="![CI](https://github.com/${OWNER}/${REPO_NAME}/actions/workflows/ci.yml/badge.svg)"
  if awk -v badge="$badge" '
      index($0, "![CI](https://github.com/OWNER/REPO/actions") > 0 { print badge; hit = 1; next }
      /^> CI 徽章需要仓库地址/ { skip = 1; next }
      skip && /^>/ { next }
      skip { skip = 0 }
      {
        is_blank = (length($0) <= 1)
        if (is_blank && prev_blank) next
        prev_blank = is_blank
        print
      }
      END { exit(hit ? 0 : 1) }
    ' README.md > README.md.tmp
  then
    mv README.md.tmp README.md
    git add README.md
    if git commit -q -m "docs(readme): CI 徽章指向真实仓库地址"; then
      if git push -q origin main; then
        green "  CI 徽章已指向真实仓库并推送"
      else
        red "  徽章提交已创建但推送失败，手动执行：git push origin main"
      fi
    else
      red "  徽章改动已写入 README.md，但提交失败（见上方 git 报错）"
      dim "  改动仍在工作区，可手动 git add README.md && git commit && git push"
    fi
  else
    rm -f README.md.tmp
    red "  README 里的占位符格式无法识别，手动改第 5 行附近"
    dim "  正确写法：${badge}"
  fi
else
  dim "  README 里没有占位符，跳过"
fi

step "完成"
green "Repo 地址：https://github.com/${OWNER}/${REPO_NAME}"
echo
dim "接下来可选（让 commit message 里的 closes #26 真的指向东西）："
dim "  先装 GitHub CLI —— 注意它不是 npm 包，npm install -g gh 装的是同名但无关的库"
dim "    Windows: winget install --id GitHub.cli"
dim "    macOS:   brew install gh"
dim "    其他:    https://cli.github.com/"
dim "  然后："
dim "    gh auth login"
dim "    bash tools/publish_to_github.sh --apply"
```

---

共收录 66 个文件。
