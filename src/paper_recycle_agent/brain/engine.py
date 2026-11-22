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
