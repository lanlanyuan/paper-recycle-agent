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
