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
