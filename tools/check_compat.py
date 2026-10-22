"""Python 版本兼容性检查：确保仓库代码能在 Python 3.7 上运行。

用法：
    python tools/check_compat.py

检查三件事：
1. 语法 —— 用 3.7 的语法规则解析每个 .py 文件（ast.parse 的 feature_version）
2. 运行时 API —— 扫描 3.8 / 3.9 才引入的标准库函数与模块
3. 类型注解 —— 未启用 `from __future__ import annotations` 时，
   禁止在注解里使用 list[str] / dict[str, int] 这类内置泛型（3.9+ 才支持）

任一项不通过则以退出码 1 结束，便于接入 CI。
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent.parent
TARGET = (3, 7)

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "dist", ".venv", "venv", "build"}

# 3.8 / 3.9 才引入、且名字足够独特不容易误判的运行时 API
BLOCKED_ATTRS = {
    "removeprefix": "3.9",
    "removesuffix": "3.9",
    "is_relative_to": "3.9",
    "with_stem": "3.9",
    "cached_property": "3.8",
}
BLOCKED_MODULES = {
    "zoneinfo": "3.9",
    "graphlib": "3.9",
}
BLOCKED_FROM = {
    ("functools", "cache"): "3.9",
    ("importlib", "metadata"): "3.8",
    ("typing", "Protocol"): "3.8",
    ("typing", "Literal"): "3.8",
    ("typing", "Final"): "3.8",
    ("typing", "TypedDict"): "3.8",
}
BUILTIN_GENERICS = {"list", "dict", "set", "tuple", "frozenset", "type"}


def _iter_py_files() -> List[Path]:
    out: List[Path] = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        out.append(path)
    return out


def _has_future_annotations(tree: ast.AST) -> bool:
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            if any(a.name == "annotations" for a in node.names):
                return True
    return False


def _annotation_nodes(tree: ast.AST) -> List[ast.AST]:
    """收集所有类型注解节点。"""
    out: List[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and node.annotation is not None:
            out.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                out.append(node.returns)
            for arg in list(node.args.args) + list(node.args.kwonlyargs):
                if arg.annotation is not None:
                    out.append(arg.annotation)
            if node.args.vararg is not None and node.args.vararg.annotation:
                out.append(node.args.vararg.annotation)
            if node.args.kwarg is not None and node.args.kwarg.annotation:
                out.append(node.args.kwarg.annotation)
    return out


def check_file(path: Path) -> List[str]:
    problems: List[str] = []
    rel = path.relative_to(ROOT).as_posix()
    source = path.read_text(encoding="utf-8")

    # 1. 语法
    if sys.version_info >= (3, 8):
        try:
            ast.parse(source, filename=str(path), feature_version=TARGET)
        except SyntaxError as exc:
            problems.append(
                "{}:{}: 语法超出 Python {}.{}：{}".format(
                    rel, exc.lineno or 0, TARGET[0], TARGET[1], exc.msg
                )
            )
            return problems  # 语法不过，后续 AST 检查无意义

    tree = ast.parse(source, filename=str(path))

    # 2. 运行时 API
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in BLOCKED_ATTRS:
            problems.append(
                "{}:{}: `.{}` 需要 Python {}，本仓库下限为 {}.{}".format(
                    rel, getattr(node, "lineno", 0), node.attr,
                    BLOCKED_ATTRS[node.attr], TARGET[0], TARGET[1],
                )
            )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in BLOCKED_MODULES:
                    problems.append(
                        "{}:{}: `import {}` 需要 Python {}".format(
                            rel, getattr(node, "lineno", 0), alias.name,
                            BLOCKED_MODULES[top],
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                key = (node.module or "", alias.name)
                if key in BLOCKED_FROM:
                    problems.append(
                        "{}:{}: `from {} import {}` 需要 Python {}".format(
                            rel, getattr(node, "lineno", 0),
                            node.module, alias.name, BLOCKED_FROM[key],
                        )
                    )

    # 3. 注解里的内置泛型
    if not _has_future_annotations(tree):
        for ann in _annotation_nodes(tree):
            for sub in ast.walk(ann):
                if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Name):
                    if sub.value.id in BUILTIN_GENERICS:
                        problems.append(
                            "{}:{}: 注解 `{}[...]` 需要 Python 3.9，"
                            "请改用 typing.{} 或加 `from __future__ import annotations`".format(
                                rel, getattr(sub, "lineno", 0), sub.value.id,
                                sub.value.id.capitalize(),
                            )
                        )
    return problems


def main() -> int:
    files = _iter_py_files()
    problems: List[str] = []
    for path in files:
        problems.extend(check_file(path))

    print("Python 兼容性检查（目标下限 {}.{}）".format(*TARGET))
    print("-" * 46)
    print("扫描文件：{} 个".format(len(files)))
    if problems:
        print("发现 {} 处不兼容：".format(len(problems)))
        for p in problems:
            print("  · " + p)
        print("\n结果：不通过")
        return 1
    print("语法（3.7 语法树）：OK")
    print("运行时 API（3.8 / 3.9 专有）：OK")
    print("类型注解（内置泛型）：OK")
    print("\n结果：通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
