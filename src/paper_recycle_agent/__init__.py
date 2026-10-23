"""废纸回收 Agent 对话助手。

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

from . import (agent, classifier, data, enterprises, exporter, io_table,  # noqa: E402
               knowledge, llm, pricing, regions, stats)
from .agent import respond  # noqa: E402

__version__ = "1.6.2"

__all__ = [
    "agent",
    "classifier",
    "data",
    "enterprises",
    "exporter",
    "io_table",
    "knowledge",
    "llm",
    "pricing",
    "regions",
    "stats",
    "respond",
]
