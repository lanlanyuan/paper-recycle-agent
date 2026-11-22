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
