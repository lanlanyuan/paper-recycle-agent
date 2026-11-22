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
