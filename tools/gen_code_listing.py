"""生成 docs/CODE_LISTING.md：把全部源码嵌入一份独立的代码清单文档。

用法：
    python tools/gen_code_listing.py

清单按「包源码 → Web 应用 → 测试 → 工程配置」的顺序组织，
每段前带文件路径与行数，便于评审时逐段对照仓库。
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "CODE_LISTING.md"

LANG = {
    ".py": "python",
    ".html": "html",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".txt": "text",
    ".md": "markdown",
    ".sh": "bash",
}

# (标题, 目录或文件, 是否递归)
SECTIONS = [
    ("一、核心包（src/paper_recycle_agent）", ROOT / "src" / "paper_recycle_agent", True),
    ("二、Web 应用（app/）", ROOT / "app", True),
    ("三、测试（tests/）", ROOT / "tests", True),
    ("四、启动入口与工程配置", None, False),
    ("五、工具脚本（tools/）", ROOT / "tools", False),
]

ROOT_FILES = [
    "run.py",
    "conftest.py",
    "pyproject.toml",
    "requirements.txt",
    ".github/workflows/ci.yml",
]


def _version() -> str:
    init = ROOT / "src" / "paper_recycle_agent" / "__init__.py"
    for line in init.read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "unknown"


def _files(path: Path, recursive: bool) -> list[Path]:
    if path.is_file():
        return [path]
    pattern = "**/*" if recursive else "*"
    return sorted(
        p for p in path.glob(pattern)
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix in LANG
    )


def _block(file: Path) -> str:
    rel = file.relative_to(ROOT).as_posix()
    text = file.read_text(encoding="utf-8")
    lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    lang = LANG.get(file.suffix, "")
    return f"### `{rel}`（{lines} 行）\n\n```{lang}\n{text.rstrip()}\n```\n"


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()
    except OSError:
        return ""


def main() -> int:
    parts: list[str] = []
    version = _version()
    parts.append(
        "# 代码清单\n\n"
        f"> 版本：v{version}　生成日期：{date.today().isoformat()}　"
        "由 `tools/gen_code_listing.py` 自动生成，请勿手工编辑。\n\n"
        "本文档把仓库全部源码按模块顺序嵌入，便于在不打开仓库的情况下通读实现。\n"
    )

    commit = _git("rev-parse", "--short", "HEAD")
    if commit:
        parts.append(f"- 生成时提交：`{commit}`\n")

    parts.append("\n## 目录\n")
    for title, _, _ in SECTIONS:
        parts.append(f"- {title}\n")
    parts.append("\n---\n")

    total = 0
    for title, path, recursive in SECTIONS:
        parts.append(f"\n## {title}\n")
        if path is None:
            files = [ROOT / f for f in ROOT_FILES if (ROOT / f).exists()]
        else:
            files = _files(path, recursive)
        for f in files:
            parts.append("\n" + _block(f))
            total += 1

    parts.append(f"\n---\n\n共收录 {total} 个文件。\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"已生成 {OUT.relative_to(ROOT)}（{total} 个文件，{OUT.stat().st_size} 字节）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
