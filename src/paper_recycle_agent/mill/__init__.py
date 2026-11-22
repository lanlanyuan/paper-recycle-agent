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
