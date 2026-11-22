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

__version__ = "1.9.0"

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
