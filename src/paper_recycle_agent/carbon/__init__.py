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
