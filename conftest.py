"""pytest 全局配置：让 `src/` 与仓库根目录都可直接 import。

- `src/`：核心包 paper_recycle_agent
- 仓库根：Web 应用 app.server（测试需要导入 FastAPI 实例）
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

for path in (ROOT, ROOT / "src"):
    entry = str(path)
    if entry not in sys.path:
        sys.path.insert(0, entry)
