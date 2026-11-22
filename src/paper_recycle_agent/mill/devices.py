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
