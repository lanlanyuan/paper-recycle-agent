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
