# 废纸回收 Agent 对话助手 · 代码清单

> 本文档由 `gen_code_listing.py` 自动生成，内容与仓库源码保持一致。

## 项目简介

一个纯标准库实现的废纸回收助手：识别废纸类型、判断是否可回收、按重量估价，并接入《中国造纸年鉴》/行业报告的废纸分类（GB/T 20811-2018）与行业数据，提供命令行与 Web 图形界面（FastAPI + 聊天页）。

## 如何运行

```bash
pip install -r requirements.txt
PYTHONPATH=src pytest -q            # 跑测试
PYTHONPATH=src python -m paper_recycle_agent.cli chat   # 命令行
uvicorn app.server:app --reload      # 图形界面 http://localhost:8000
```

## 项目元信息

### pyproject.toml

_pyproject.toml_

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "paper-recycle-agent"
version = "1.0.0"
description = "废纸回收 Agent 对话助手：分类、估价与交互（纯标准库）"
readme = "README.md"
requires-python = ">=3.9"
license = { text = "MIT" }
authors = [{ name = "梁湘瑶 / 阿岩" }]
keywords = ["recycling", "paper", "agent", "cli"]

[project.scripts]
paper-recycle-agent = "paper_recycle_agent.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

### requirements.txt

_requirements.txt_

```txt
# 运行时依赖：无（核心包仅使用 Python 标准库）
# 开发 / 测试 / 图形界面依赖见下方注释
pytest>=7.0          # 单元测试（CI 使用）
fastapi>=0.110       # 图形界面 / HTTP 对话服务（app/server.py）
uvicorn>=0.29        # 运行 FastAPI 服务：uvicorn app.server:app --reload
```

### .github/workflows/ci.yml

_.github/workflows/ci.yml_

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.11"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: pip install pytest

      - name: Run tests
        env:
          PYTHONPATH: src
        run: pytest -q
```

## 核心包 src/paper_recycle_agent

### __init__.py

_src/paper_recycle_agent/__init__.py_

```text
"""废纸回收 Agent 对话助手。"""

from . import agent, classifier, knowledge, pricing
from .agent import respond

__version__ = "1.0.0"

__all__ = ["agent", "classifier", "knowledge", "pricing", "respond"]
```

### knowledge.py（知识库）

_src/paper_recycle_agent/knowledge.py_

```text
"""废纸回收知识库：分类规则与回收指引数据。

所有分类规则集中在此，便于后续维护与扩展。
"""

from dataclasses import dataclass
from typing import List


@dataclass
class PaperCategory:
    """单个废纸类别的定义。"""

    key: str
    name: str
    aliases: List[str]
    recyclable: bool
    value_per_kg: float  # 参考回收价（元/kg），不可回收为 0.0
    tips: str


# 类别顺序：可回收在前、不可回收在后，便于阅读与优先级排序。
CATEGORIES: List[PaperCategory] = [
    PaperCategory(
        key="office",
        name="办公用纸",
        aliases=["打印纸", "复印纸", "a4", "文件", "办公纸", "办公用纸", "白纸", "资料"],
        recyclable=True,
        value_per_kg=1.1,
        tips="订书钉可保留，回形针建议取下；涉密文件请碎纸后交专业渠道。",
    ),
    PaperCategory(
        key="cardboard",
        name="纸箱/纸板",
        aliases=["纸箱", "纸板", "瓦楞纸", "快递箱", "纸盒", "包装盒"],
        recyclable=True,
        value_per_kg=0.9,
        tips="清空内容物、压平折叠，胶带尽量撕掉。",
    ),
    PaperCategory(
        key="newspaper",
        name="报纸",
        aliases=["报纸", "新闻纸", "旧报"],
        recyclable=True,
        value_per_kg=0.8,
        tips="去除塑料薄膜与装订后可整捆回收。",
    ),
    PaperCategory(
        key="magazine",
        name="书刊杂志",
        aliases=["杂志", "期刊", "书本", "书", "刊物"],
        recyclable=True,
        value_per_kg=0.7,
        tips="胶装书刊可整体回收；塑料封膜请分离。",
    ),
    PaperCategory(
        key="kraft",
        name="牛皮纸",
        aliases=["牛皮纸", "牛皮纸箱", "牛皮袋"],
        recyclable=True,
        value_per_kg=0.85,
        tips="干净干燥即可回收。",
    ),
    PaperCategory(
        key="tissue",
        name="纸巾/卫生纸",
        aliases=["纸巾", "卫生纸", "餐巾纸", "湿巾"],
        recyclable=False,
        value_per_kg=0.0,
        tips="已被污染且纤维过短，不可进入再生纸系统，请作为其他垃圾处理。",
    ),
    PaperCategory(
        key="thermal",
        name="热敏/涂布纸",
        aliases=["热敏纸", "小票", "收银条", "传真纸", "涂布纸"],
        recyclable=False,
        value_per_kg=0.0,
        tips="表面含显色涂层，不可回收，请作为其他垃圾。",
    ),
    PaperCategory(
        key="contaminated",
        name="污染/厨余纸",
        aliases=["油纸", "沾油", "披萨盒", "厨房纸巾", "被污染"],
        recyclable=False,
        value_per_kg=0.0,
        tips="油污、食物残渣会破坏纸浆，不可回收。",
    ),
    PaperCategory(
        key="composite",
        name="复合包装",
        aliases=["利乐包", "纸塑铝", "牛奶盒", "饮料纸盒"],
        recyclable=False,
        value_per_kg=0.0,
        tips="属纸塑铝复合材质，需专用回收线，请勿投入普通废纸。",
    ),
]

# 扁平化的「类别-关键词」索引，供分类引擎快速匹配。
KEYWORD_INDEX = [(cat, kw) for cat in CATEGORIES for kw in cat.aliases]
```

### data.py（年鉴/行业数据）

_src/paper_recycle_agent/data.py_

```text
"""中国造纸年鉴 / 行业报告中的废纸分类与行业数据。

所有数据均标注来源，便于核验：
- GB/T 20811-2018《废纸分类技术要求》（国家市场监督管理总局、中国国家标准化管理委员会，
  2018-12-28 发布，2019-07-01 实施）：将废纸分为 8 大类 42 小类。
- 中国造纸协会《中国造纸工业2024年度报告》（2025-05-07 发布）：废纸回收利用核心指标。
- 生态环境部等《关于全面禁止进口固体废物有关事项的公告》（2021-01-01 施行）：废纸进口清零。
"""

from typing import Dict, List

# ---- 废纸分类（GB/T 20811-2018，共 8 大类 42 小类；此处列 8 大类及代表性小类）----
CATEGORIES_8: List[Dict[str, object]] = [
    {
        "code": "1",
        "name": "废瓦楞纸箱类",
        "examples": ["牛皮挂面旧瓦楞纸箱(101)", "新瓦楞纸箱(102)", "混合旧瓦楞纸箱(104)"],
        "note": "杂质≤1.0%、不可利用物≤3.0%；新箱更严。回收用于箱板纸/瓦楞原纸。",
    },
    {
        "code": "2",
        "name": "废纸盒及废卡纸类",
        "examples": ["工厂回收白色纸盒切边(201)"],
        "note": "白色纸盒切边杂质≤0.25%、不可利用物≤1.0%。",
    },
    {
        "code": "3",
        "name": "包装废纸类",
        "examples": ["白色包装纸(301)", "牛皮包装纸(302)"],
        "note": "不应有杂质，不可利用物≤0.5%。",
    },
    {
        "code": "4",
        "name": "废新闻纸类",
        "examples": ["新闻纸切边(401)", "未出售报纸(402)"],
        "note": "不应有杂质，不可利用物≤0.5%。",
    },
    {
        "code": "5",
        "name": "废书刊杂志类",
        "examples": ["白色未涂布纸切边(501)", "混合旧书刊杂志(505)"],
        "note": "混合旧书刊杂质≤0.5%、不可利用物≤2.5%。",
    },
    {
        "code": "6",
        "name": "办公废纸类",
        "examples": ["混合办公废纸(606)"],
        "note": "混合办公废纸杂质≤0.5%、不可利用物≤2.5%。",
    },
    {
        "code": "7",
        "name": "特种废纸类",
        "examples": ["白色湿强废纸(701)", "工厂使用过的特种废纸(709)"],
        "note": "部分品种不应有杂质；湿强废纸杂质≤0.5%、不可利用物≤2.0%。",
    },
    {
        "code": "8",
        "name": "混合废纸类",
        "examples": [
            "非纸箱纸盒类混合废纸(801)",
            "纸箱纸盒类混合废纸(802)",
            "混合废纸(803)",
        ],
        "note": "803 为不鼓励贸易类别；杂质≤1.0%~1.5%。",
    },
]

# 通用质量要求（GB/T 20811-2018）
QUALITY_RULES: Dict[str, str] = {
    "水分": "实测水分应 ≤ 12%（或按合同规定）",
    "质量差百分率": "应 ≥ -1.0%",
    "包装物质量": "应不大于对应实测质量的 1.0%",
}

# ---- 行业数据（中国造纸协会《中国造纸工业2024年度报告》）----
INDUSTRY_DATA: List[Dict[str, object]] = [
    {"year": 2024, "指标": "国内回收废纸总量", "数值": "6971 万吨", "同比": "+3.47%"},
    {"year": 2024, "指标": "废纸回收率", "数值": "51.1%", "同比": "—"},
    {"year": 2024, "指标": "废纸利用率", "数值": "51.6%", "同比": "—"},
    {"year": 2024, "指标": "纸及纸板产量", "数值": "13625 万吨", "同比": "+5.09%"},
    {"year": 2024, "指标": "全行业营业收入", "数值": "1.46 万亿元", "同比": "+3.88%"},
    {"year": 2024, "指标": "利润总额", "数值": "520 亿元", "同比": "+5.23%"},
    {"year": 2024, "指标": "废纸进口量", "数值": "基本清零（≈0）", "同比": "禁废令后维持低位"},
]

SOURCES: List[str] = [
    "GB/T 20811-2018《废纸分类技术要求》（国家市场监督管理总局、中国国家标准化管理委员会）",
    "中国造纸协会《中国造纸工业2024年度报告》（2025-05-07 发布）",
    "生态环境部等《关于全面禁止进口固体废物有关事项的公告》（2021-01-01 施行）",
]


def get_categories() -> List[Dict[str, object]]:
    """返回 GB/T 20811-2018 的 8 大类废纸分类。"""
    return CATEGORIES_8


def get_industry_data(year: int = 2024) -> List[Dict[str, object]]:
    """返回指定年份的行业数据。"""
    return [d for d in INDUSTRY_DATA if d["year"] == year]


def summary_text() -> str:
    """生成一段人类可读的「分类 + 行业数据」摘要。"""
    lines = ["【废纸分类（GB/T 20811-2018，共 8 大类 42 小类）】"]
    for c in CATEGORIES_8:
        lines.append(f"{c['code']}. {c['name']}：{', '.join(c['examples'])}")
    lines.append("")
    lines.append("【2024 年废纸回收利用（中国造纸协会年度报告）】")
    for d in get_industry_data(2024):
        lines.append(f"- {d['指标']}：{d['数值']}（{d['同比']}）")
    lines.append("")
    lines.append("数据来源：" + "；".join(SOURCES))
    return "\n".join(lines)
```

### classifier.py（分类引擎）

_src/paper_recycle_agent/classifier.py_

```text
"""废纸分类引擎：基于关键词与规则的轻量级分类。"""

from typing import Dict, List

from .knowledge import CATEGORIES, KEYWORD_INDEX, PaperCategory


def classify(text: str) -> Dict[str, object]:
    """根据用户输入文本判断废纸类别。

    返回字典包含：matched / category / key / recyclable / value_per_kg /
    tips / confidence / message。
    """
    if not text or not text.strip():
        return _empty()

    t = text.lower()
    hits: List[PaperCategory] = []
    for cat, kw in KEYWORD_INDEX:
        if kw.lower() in t:
            hits.append(cat)

    if not hits:
        # 关键词未命中时，尝试用类别主键兜底（如「cardboard」）。
        for cat in CATEGORIES:
            if cat.key in t:
                hits.append(cat)

    if not hits:
        return {
            "matched": False,
            "category": None,
            "recyclable": None,
            "confidence": 0.0,
            "message": "未能识别废纸类型，请描述更具体的物品（如：纸箱、报纸、纸巾、热敏小票）。",
        }

    cat = _prioritize(hits)
    confidence = 0.9 if len(hits) == 1 else 0.7
    return {
        "matched": True,
        "category": cat.name,
        "key": cat.key,
        "recyclable": cat.recyclable,
        "value_per_kg": cat.value_per_kg,
        "tips": cat.tips,
        "confidence": confidence,
        "message": _message(cat),
    }


def _prioritize(cats: List[PaperCategory]) -> PaperCategory:
    """多命中时，优先展示可回收且价值更高的类别。"""
    return sorted(cats, key=lambda c: (not c.recyclable, -c.value_per_kg))[0]


def _message(cat: PaperCategory) -> str:
    if cat.recyclable:
        return (
            f"识别为【{cat.name}】，可回收，参考回收价约 "
            f"{cat.value_per_kg} 元/kg。{cat.tips}"
        )
    return f"识别为【{cat.name}】，暂不可回收。{cat.tips}"


def _empty() -> Dict[str, object]:
    return {
        "matched": False,
        "category": None,
        "recyclable": None,
        "confidence": 0.0,
        "message": "请输入要查询的废纸物品。",
    }


def list_categories() -> List[Dict[str, object]]:
    """返回全部类别的概览，供 CLI / 文档使用。"""
    return [
        {
            "key": c.key,
            "name": c.name,
            "recyclable": c.recyclable,
            "value_per_kg": c.value_per_kg,
        }
        for c in CATEGORIES
    ]
```

### pricing.py（估价）

_src/paper_recycle_agent/pricing.py_

```text
"""回收估价：根据类别与重量估算回收价值。"""

from typing import Dict

from .classifier import classify


def estimate(text: str, weight_kg: float) -> Dict[str, object]:
    """估算指定废纸物品在给定重量下的回收价值。

    weight_kg 为负时按 0 处理。
    """
    result = classify(text)
    if not result["matched"]:
        return {
            **result,
            "weight_kg": weight_kg,
            "estimated_value": 0.0,
        }

    value_per_kg = float(result["value_per_kg"])  # type: ignore
    if not result["recyclable"]:
        return {
            "matched": True,
            "category": result["category"],
            "recyclable": False,
            "weight_kg": weight_kg,
            "estimated_value": 0.0,
            "message": (
                f"【{result['category']}】不可回收，无回收价值。"
                f"{result.get('tips', '')}"
            ),
        }

    value = round(value_per_kg * max(weight_kg, 0.0), 2)
    return {
        "matched": True,
        "category": result["category"],
        "recyclable": True,
        "weight_kg": weight_kg,
        "value_per_kg": value_per_kg,
        "estimated_value": value,
        "message": (
            f"【{result['category']}】{weight_kg} kg，"
            f"预计回收价值约 {value} 元。"
        ),
    }
```

### agent.py（对话引擎）

_src/paper_recycle_agent/agent.py_

```text
"""对话引擎：把分类 / 估价能力包装成自然语言回复。"""

import re
from typing import Dict, Optional

from . import classifier, data, pricing

_GREETING = {"你好", "您好", "hi", "hello", "在吗", "在么"}
_HELP = {"帮助", "help", "怎么用", "功能", "能做什么", "用法"}
_DATA = {"年鉴", "行业数据", "回收量", "利用率", "进口", "标准", "分类标准",
         "gb/t", "20811", "造纸", "废纸分几类", "废纸分类"}


def _extract_weight(text: str) -> Optional[float]:
    """从文本中提取重量，支持 kg / 公斤 / 千克 / 斤（斤自动折算为 kg）。"""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|公斤|千克|斤)", text, re.IGNORECASE)
    if not m:
        return None
    val = float(m.group(1))
    if m.group(2) == "斤":
        val = val / 2.0
    return val


def respond(user_input: str) -> str:
    """根据用户输入返回一句自然语言回复。"""
    text = (user_input or "").strip()
    if not text:
        return "请输入你想查询的废纸物品，例如「纸箱 2kg 能卖多少钱」。"

    low = text.lower()
    if low in _GREETING:
        return (
            "你好，我是废纸回收助手 🪨。告诉我废纸物品名称"
            "（如纸箱、报纸、纸巾），或加上重量估算回收价值。输入「帮助」查看用法。"
        )
    if any(k in text for k in _HELP):
        return _help_text()

    # 年鉴 / 行业数据 / 分类标准类查询
    if any(k in text for k in _DATA):
        return data.summary_text()

    weight = _extract_weight(text)
    if weight is not None:
        return pricing.estimate(text, weight)["message"]

    # 默认走分类查询
    return classifier.classify(text)["message"]


def _help_text() -> str:
    return "\n".join(
        [
            "废纸回收助手使用说明：",
            "1) 查询是否可回收：直接说物品名，如「纸箱」「报纸」「纸巾」。",
            "2) 估算回收价值：物品名 + 重量，如「办公用纸 3kg」「纸箱 5 斤」。",
            "3) 查看全部类别：输入「类别」。",
            "4) 年鉴与行业数据：输入「年鉴」「行业数据」「废纸分类」「回收量」。",
        ]
    )
```

### cli.py（命令行）

_src/paper_recycle_agent/cli.py_

```text
"""命令行交互入口。"""

import argparse
import sys

from . import agent, classifier, data, pricing


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="paper-recycle-agent", description="废纸回收 Agent 对话助手"
    )
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("chat", help="进入交互式对话")
    c = sub.add_parser("classify", help="分类查询")
    c.add_argument("text", help="物品描述")
    pr = sub.add_parser("price", help="估价")
    pr.add_argument("text", help="物品描述")
    pr.add_argument("weight", type=float, help="重量(kg)")
    sub.add_parser("categories", help="列出所有类别")
    sub.add_parser("info", help="废纸分类标准与行业数据")
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "chat":
        _chat_loop()
    elif args.cmd == "classify":
        print(classifier.classify(args.text)["message"])
    elif args.cmd == "price":
        print(pricing.estimate(args.text, args.weight)["message"])
    elif args.cmd == "categories":
        for c in classifier.list_categories():
            tag = "可回收" if c["recyclable"] else "不可回收"
            print(f"- {c['name']} [{tag}]")
    elif args.cmd == "info":
        print(data.summary_text())
    else:
        _chat_loop()
    return 0


def _chat_loop() -> None:
    print("废纸回收助手（输入 exit 退出）")
    while True:
        try:
            line = input("你: ")
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break
        if line.strip().lower() in {"exit", "quit", "退出"}:
            print("再见。")
            break
        print("助手:", agent.respond(line))


if __name__ == "__main__":
    sys.exit(main())
```

## 图形界面 app

### server.py（FastAPI 服务）

_app/server.py_

```text
"""FastAPI 服务：提供废纸回收 Agent 的图形界面与对话接口。

运行：uvicorn app.server:app --reload
接口：
  GET  /            -> 图形界面（聊天 + 年鉴/行业数据面板）
  GET  /api/info    -> {categories, industry, quality, sources}
  POST /chat        -> {"reply": "..."}
  GET  /health      -> {"status": "ok"}
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from paper_recycle_agent import data as yearbook
from paper_recycle_agent import respond

app = FastAPI(title="废纸回收 Agent 对话助手")

_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


class ChatReq(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/api/info")
def info() -> dict:
    return {
        "categories": yearbook.get_categories(),
        "industry": yearbook.get_industry_data(2024),
        "quality": yearbook.QUALITY_RULES,
        "sources": yearbook.SOURCES,
    }


@app.post("/chat")
def chat(req: ChatReq) -> dict:
    return {"reply": respond(req.message)}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

### static/index.html（聊天界面）

_app/static/index.html_

```text
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>废纸回收 Agent 对话助手</title>
<style>
  :root {
    --bg: #f5f7fa;
    --panel: #ffffff;
    --ink: #1f2329;
    --muted: #6b7280;
    --brand: #2f7d4f;
    --brand-soft: #e8f3ec;
    --border: #e5e7eb;
    --user-bubble: #2f7d4f;
    --bot-bubble: #eef1f5;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg); color: var(--ink); height: 100vh; display: flex; flex-direction: column;
  }
  header {
    background: var(--brand); color: #fff; padding: 14px 20px; font-size: 18px; font-weight: 600;
    display: flex; align-items: center; gap: 10px;
  }
  header .sub { font-size: 12px; font-weight: 400; opacity: .85; }
  .layout { flex: 1; display: flex; min-height: 0; }
  .chat { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  .messages { flex: 1; overflow-y: auto; padding: 18px; display: flex; flex-direction: column; gap: 12px; }
  .msg { max-width: 78%; padding: 10px 14px; border-radius: 14px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
  .msg.bot { background: var(--bot-bubble); align-self: flex-start; border-bottom-left-radius: 4px; }
  .msg.user { background: var(--user-bubble); color: #fff; align-self: flex-end; border-bottom-right-radius: 4px; }
  .chips { display: flex; gap: 8px; flex-wrap: wrap; padding: 0 18px 8px; }
  .chip { background: var(--brand-soft); color: var(--brand); border: 1px solid #cfe6da; border-radius: 16px;
          padding: 6px 12px; font-size: 13px; cursor: pointer; }
  .chip:hover { background: #dcefe2; }
  .inputbar { display: flex; gap: 10px; padding: 14px 18px; border-top: 1px solid var(--border); background: var(--panel); }
  .inputbar input { flex: 1; padding: 11px 14px; border: 1px solid var(--border); border-radius: 10px; font-size: 15px; outline: none; }
  .inputbar input:focus { border-color: var(--brand); }
  .inputbar button { background: var(--brand); color: #fff; border: none; border-radius: 10px; padding: 0 22px; font-size: 15px; cursor: pointer; }
  .inputbar button:disabled { opacity: .5; cursor: default; }
  .side { width: 340px; border-left: 1px solid var(--border); background: var(--panel); overflow-y: auto; padding: 16px; }
  .side h3 { margin: 0 0 10px; font-size: 15px; color: var(--brand); }
  .side h4 { margin: 18px 0 8px; font-size: 13px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
  .cat { border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; margin-bottom: 8px; }
  .cat .name { font-weight: 600; font-size: 14px; }
  .cat .ex { color: var(--muted); font-size: 12px; margin-top: 3px; }
  .cat .note { color: var(--muted); font-size: 12px; margin-top: 4px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { border: 1px solid var(--border); padding: 6px 8px; text-align: left; }
  th { background: var(--brand-soft); color: var(--brand); }
  .src { font-size: 11px; color: var(--muted); line-height: 1.6; margin-top: 8px; }
  @media (max-width: 820px) { .side { display: none; } }
</style>
</head>
<body>
<header>🪨 废纸回收 Agent 对话助手 <span class="sub">分类 · 估价 · 年鉴数据</span></header>
<div class="layout">
  <div class="chat">
    <div class="messages" id="messages"></div>
    <div class="chips" id="chips"></div>
    <div class="inputbar">
      <input id="input" placeholder="说说废纸物品，如：纸箱 2kg / 废纸分类 / 回收量" onkeydown="if(event.key==='Enter')send()" />
      <button id="sendBtn" onclick="send()">发送</button>
    </div>
  </div>
  <aside class="side">
    <h3>废纸分类（GB/T 20811-2018）</h3>
    <div id="cats"></div>
    <h4>2024 年行业数据</h4>
    <table id="industry"><thead><tr><th>指标</th><th>数值</th><th>同比</th></tr></thead><tbody></tbody></table>
    <h4>数据来源</h4>
    <div class="src" id="src"></div>
  </aside>
</div>

<script>
  const SUGGESTIONS = ["纸箱能回收吗", "办公用纸 3kg", "废纸分类", "回收量多少", "纸巾可回收吗"];
  const messagesEl = document.getElementById("messages");
  const chipsEl = document.getElementById("chips");
  const inputEl = document.getElementById("input");
  const sendBtn = document.getElementById("sendBtn");

  function addMsg(text, who) {
    const div = document.createElement("div");
    div.className = "msg " + who;
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  SUGGESTIONS.forEach(s => {
    const c = document.createElement("span");
    c.className = "chip"; c.textContent = s;
    c.onclick = () => { inputEl.value = s; send(); };
    chipsEl.appendChild(c);
  });

  async function send() {
    const text = inputEl.value.trim();
    if (!text) return;
    addMsg(text, "user");
    inputEl.value = "";
    sendBtn.disabled = true;
    try {
      const res = await fetch("/chat", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      addMsg(data.reply, "bot");
    } catch (e) {
      addMsg("服务暂时不可用：" + e, "bot");
    } finally {
      sendBtn.disabled = false;
    }
  }

  async function loadInfo() {
    try {
      const res = await fetch("/api/info");
      const info = await res.json();
      const cats = document.getElementById("cats");
      info.categories.forEach(c => {
        const d = document.createElement("div");
        d.className = "cat";
        d.innerHTML = `<div class="name">${c.code}. ${c.name}</div>` +
                      `<div class="ex">${c.examples.join("、")}</div>` +
                      `<div class="note">${c.note}</div>`;
        cats.appendChild(d);
      });
      const tb = document.querySelector("#industry tbody");
      info.industry.forEach(r => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${r.指标}</td><td>${r.数值}</td><td>${r.同比}</td>`;
        tb.appendChild(tr);
      });
      document.getElementById("src").innerHTML = info.sources.join("<br/>");
    } catch (e) { /* ignore */ }
  }

  addMsg("你好，我是废纸回收助手 🪨。可以问我废纸是否可回收、估算回收价值，或查询《中国造纸年鉴》废纸分类与行业数据。", "bot");
  loadInfo();
</script>
</body>
</html>
```

## 单元测试 tests

### test_classifier.py

_tests/test_classifier.py_

```text
from paper_recycle_agent import classifier


def test_classify_cardboard():
    r = classifier.classify("我有一个快递纸箱")
    assert r["matched"] is True
    assert r["category"] == "纸箱/纸板"
    assert r["recyclable"] is True


def test_classify_tissue_not_recyclable():
    r = classifier.classify("用过的纸巾")
    assert r["recyclable"] is False


def test_classify_empty():
    r = classifier.classify("")
    assert r["matched"] is False


def test_classify_unknown():
    r = classifier.classify("塑料瓶")
    assert r["matched"] is False


def test_list_categories_nonempty():
    cats = classifier.list_categories()
    assert len(cats) >= 5
    assert any(c["recyclable"] for c in cats)
```

### test_pricing.py

_tests/test_pricing.py_

```text
from paper_recycle_agent import pricing


def test_estimate_value():
    r = pricing.estimate("办公用纸", 10)
    assert r["recyclable"] is True
    assert r["estimated_value"] == 11.0  # 1.1 * 10


def test_estimate_nonrecyclable():
    r = pricing.estimate("纸巾", 5)
    assert r["recyclable"] is False
    assert r["estimated_value"] == 0.0


def test_estimate_unknown():
    r = pricing.estimate("玻璃", 1)
    assert r["matched"] is False


def test_estimate_negative_weight():
    r = pricing.estimate("纸箱", -3)
    assert r["estimated_value"] == 0.0
```

### test_agent.py

_tests/test_agent.py_

```text
from paper_recycle_agent import agent


def test_respond_greeting():
    out = agent.respond("你好")
    assert "废纸回收助手" in out


def test_respond_help():
    out = agent.respond("帮助")
    assert "使用说明" in out


def test_respond_classify():
    out = agent.respond("纸箱")
    assert "纸箱" in out


def test_respond_price_with_weight():
    out = agent.respond("办公用纸 3kg")
    assert "回收价值" in out


def test_respond_jin_conversion():
    out = agent.respond("纸箱 2斤")
    assert "回收价值" in out


def test_respond_yearbook_query():
    out = agent.respond("废纸分类标准")
    assert "GB/T 20811" in out
    assert "6971" in out


def test_respond_industry_data():
    out = agent.respond("回收量多少")
    assert "回收量" in out or "6971" in out
```

### test_data.py

_tests/test_data.py_

```text
from paper_recycle_agent import data


def test_eight_categories():
    cats = data.get_categories()
    assert len(cats) == 8
    assert all("name" in c and "examples" in c for c in cats)


def test_industry_2024_has_volume():
    rows = data.get_industry_data(2024)
    volume = [r for r in rows if r["指标"] == "国内回收废纸总量"]
    assert volume, "应存在废纸回收总量记录"
    assert "6971" in volume[0]["数值"]


def test_summary_text_mentions_standard():
    txt = data.summary_text()
    assert "GB/T 20811" in txt
    assert "6971" in txt


def test_quality_rules_present():
    assert "水分" in data.QUALITY_RULES
```
