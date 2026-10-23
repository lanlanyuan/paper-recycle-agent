#!/usr/bin/env python3
"""有效代码 LOC（Effective Lines of Code）统计。

回答一个问题：这个仓库里到底有多少行是「应用自身的有效代码」？

口径（每条都可核查）：

    有效代码行 = 物理行 - 空行 - 注释行 - 文档字符串 - 内嵌模板/数据

几条关键约定：

1. **只统计 git 跟踪的文件**。用 `git ls-files` 取清单，天然排除
   `__pycache__`、`.pytest_cache`、本地生成的 `config/llm.json`。

2. **生成物不计入**。`dist/paper-recycle-offline.html` 由 `tools/build_offline.py`
   构建，`docs/CODE_LISTING.md` 由 `tools/gen_code_listing.py` 生成。
   把它们算进代码量是虚增。

3. **Python 里的内嵌模板单独归类**。`tools/build_offline.py` 里有一个
   `TEMPLATE = r\"\"\"...\"\"\"` 的整页 HTML（600+ 行）。它是构建脚本要输出的产物，
   不是 Python 逻辑。判定规则：任何跨行数 >= 30 的字符串字面量都视为
   「内嵌模板 / 内嵌数据」，单独统计，不计入 SLOC。这条规则同时对测试里的
   大块夹具数据生效——评审可以据此确认没有用测试数据凑行数。

4. **前端按 HTML / CSS / JS 三段分别计数**。`app/static/index.html` 里
   有 `<style>` 与 `<script>` 块，混在一起统计会掩盖真实构成。

5. **注释与文档字符串分开列**。docstring 是文档不是逻辑，但也不该被当成
   "注释很多所以代码少"的借口，所以报告里两者分开显示。

用法：

    python tools/count_loc.py            # 打印报告 + 写 docs/EFFECTIVE_LOC.md
    python tools/count_loc.py --json     # 只输出 JSON（便于机审）
    python tools/count_loc.py --check    # 校验模式：异常即退出码 1（CI 用）
"""

import io
import json
import subprocess
import sys
import tokenize
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "docs" / "EFFECTIVE_LOC.md"

# 跨行数达到这个阈值的字符串字面量，视为内嵌模板 / 内嵌数据，不算逻辑代码
TEMPLATE_MIN_LINES = 30

# ---------------------------------------------------------------------------
# 分类规则
# ---------------------------------------------------------------------------

# (层级 key, 中文名, 判定函数)
LAYER_RULES = [
    ("core", "核心领域逻辑", lambda p: p.startswith("src/paper_recycle_agent/")),
    ("web", "Web 层", lambda p: p.startswith("app/") or p == "run.py"),
    ("tests", "测试", lambda p: p.startswith("tests/") or p == "conftest.py"),
    ("tools", "工具脚本", lambda p: p.startswith("tools/")),
]

# 不计入有效代码的文件，每类都给出理由
EXCLUDE_RULES = [
    ("generated", "生成物", lambda p: p.startswith("dist/") or p == "docs/CODE_LISTING.md"),
    ("docs", "文档", lambda p: p.endswith(".md") or p in ("LICENSE",)),
    ("config", "配置 / 模板数据", lambda p: (
        p.startswith(".github/")
        or p.endswith((".toml", ".txt", ".bat", ".example", ".gitignore", ".gitattributes"))
    )),
]

CODE_EXTS = {".py", ".html", ".js", ".css", ".sh"}


def classify(path: str) -> str:
    for key, _name, test in LAYER_RULES:
        if test(path):
            return key
    for key, _name, test in EXCLUDE_RULES:
        if test(path):
            return key
    return "other"


# ---------------------------------------------------------------------------
# 计数：Python
# ---------------------------------------------------------------------------

_SKIP_TOKENS = {
    tokenize.NL, tokenize.NEWLINE, tokenize.INDENT,
    tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER,
}


def _python_line_roles(text: str) -> Tuple[Set[int], Set[int], Set[int]]:
    """返回 (注释行, 文档字符串行, 内嵌模板行)，均为 1-based 行号集合。"""
    comment: Set[int] = set()
    docstring: Set[int] = set()
    template: Set[int] = set()
    lines = text.splitlines()

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return comment, docstring, template

    prev = "START"
    for tok in tokens:
        if tok.type in _SKIP_TOKENS:
            if tok.type == tokenize.NEWLINE:
                prev = "NEWLINE"
            continue

        if tok.type == tokenize.COMMENT:
            # 只有「整行都是注释」才算注释行。
            # `x = 1  # 说明` 这种行尾注释，这一行仍然是有效代码，
            # 把它整行算成注释会少算代码行数。
            row = tok.start[0]
            prefix = lines[row - 1][:tok.start[1]] if 0 < row <= len(lines) else ""
            if not prefix.strip():
                comment.add(row)
            prev = "COMMENT"
            continue

        if tok.type == tokenize.STRING:
            span = tok.end[0] - tok.start[0] + 1
            if prev in ("START", "NEWLINE", "INDENT"):
                # 独立成句的字符串 = 模块/类/函数的 docstring。
                # 必须先于模板判定：模块说明写长了也是文档，不是内嵌模板。
                docstring.update(range(tok.start[0], tok.end[0] + 1))
            elif span >= TEMPLATE_MIN_LINES:
                # 赋值语句里的超长字符串才是内嵌模板 / 夹具数据
                template.update(range(tok.start[0], tok.end[0] + 1))

        prev = tokenize.tok_name.get(tok.type, "OTHER")

    return comment, docstring, template


def count_python(text: str) -> Dict[str, int]:
    lines = text.splitlines()
    total = len(lines)
    blank = {i for i, line in enumerate(lines, 1) if not line.strip()}
    comment, docstring, template = _python_line_roles(text)

    non_code = blank | comment | docstring | template
    return {
        "total": total,
        "blank": len(blank),
        "comment": len(comment),
        "docstring": len(docstring),
        "template": len(template),
        "code": total - len(non_code),
    }


# ---------------------------------------------------------------------------
# 计数：C 系语法（JS / CSS）
# ---------------------------------------------------------------------------

def _count_c_like(lines: Sequence[str], line_comment: str) -> Dict[str, int]:
    total = len(lines)
    blank = comment = code = 0
    in_block = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
            continue
        if in_block:
            comment += 1
            if "*/" in stripped:
                in_block = False
            continue
        if stripped.startswith(line_comment):
            comment += 1
            continue
        if stripped.startswith("/*"):
            comment += 1
            if "*/" not in stripped:
                in_block = True
            continue
        code += 1

    return {"total": total, "blank": blank, "comment": comment,
            "docstring": 0, "template": 0, "code": code}


def _count_markup(lines: Sequence[str]) -> Dict[str, int]:
    total = len(lines)
    blank = comment = code = 0
    in_comment = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
            continue
        if in_comment:
            comment += 1
            if "-->" in stripped:
                in_comment = False
            continue
        if stripped.startswith("<!--"):
            comment += 1
            if "-->" not in stripped:
                in_comment = True
            continue
        code += 1
    return {"total": total, "blank": blank, "comment": comment,
            "docstring": 0, "template": 0, "code": code}


# ---------------------------------------------------------------------------
# 计数：HTML（拆成 结构 / CSS / JS 三段）
# ---------------------------------------------------------------------------

def _merge(a: Dict[str, int], b: Dict[str, int]) -> None:
    for k in a:
        a[k] += b.get(k, 0)


def count_html(text: str) -> Dict[str, Dict[str, int]]:
    lines = text.splitlines()
    parts: Dict[str, List[str]] = {"html": [], "css": [], "js": []}
    mode = "html"

    for line in lines:
        stripped = line.strip()
        if mode == "html":
            if stripped.startswith("<style"):
                parts["html"].append(line)
                mode = "css"
                continue
            if stripped.startswith("<script"):
                parts["html"].append(line)
                mode = "js"
                continue
            parts["html"].append(line)
        elif mode == "css":
            if stripped.startswith("</style"):
                parts["html"].append(line)
                mode = "html"
                continue
            parts["css"].append(line)
        else:  # js
            if stripped.startswith("</script"):
                parts["html"].append(line)
                mode = "html"
                continue
            parts["js"].append(line)

    return {
        "html": _count_markup(parts["html"]),
        "css": _count_c_like(parts["css"], "/*"),
        "js": _count_c_like(parts["js"], "//"),
    }


# ---------------------------------------------------------------------------
# 计数：Shell
# ---------------------------------------------------------------------------

def count_shell(text: str) -> Dict[str, int]:
    lines = text.splitlines()
    total = len(lines)
    blank = comment = code = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            blank += 1
        elif stripped.startswith("#") and not stripped.startswith("#!"):
            comment += 1
        else:
            code += 1
    return {"total": total, "blank": blank, "comment": comment,
            "docstring": 0, "template": 0, "code": code}


# ---------------------------------------------------------------------------
# 文件清单与逐文件统计
# ---------------------------------------------------------------------------

def git_files() -> List[str]:
    # core.quotepath=false：否则中文文件名（启动本地版.bat）会被转义成八进制
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files"], cwd=str(ROOT),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if out.returncode != 0:
        raise SystemExit("不是 git 仓库，或 git 不可用：%s" % out.stderr.decode("utf-8", "replace"))
    return [p for p in out.stdout.decode("utf-8").splitlines() if p.strip()]


def count_file(rel: str) -> Optional[Dict[str, object]]:
    path = ROOT / rel
    ext = path.suffix.lower()
    if ext not in CODE_EXTS:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None

    if ext == ".py":
        stats = count_python(text)
        lang = "Python"
    elif ext == ".html":
        parts = count_html(text)
        merged = {"total": 0, "blank": 0, "comment": 0,
                  "docstring": 0, "template": 0, "code": 0}
        for part in parts.values():
            _merge(merged, part)
        stats = merged
        stats["_parts"] = parts  # type: ignore[assignment]
        lang = "HTML"
    elif ext == ".css":
        stats = _count_c_like(text.splitlines(), "/*")
        lang = "CSS"
    elif ext == ".js":
        stats = _count_c_like(text.splitlines(), "//")
        lang = "JavaScript"
    else:
        stats = count_shell(text)
        lang = "Shell"

    return {
        "path": rel,
        "lang": lang,
        "layer": classify(rel),
        "stats": stats,
    }


# ---------------------------------------------------------------------------
# 反例检查：确认没有用生成物 / 第三方代码 / 压缩代码凑行数
# ---------------------------------------------------------------------------

def hygiene_checks(files: Sequence[str], counted: Sequence[Dict[str, object]]) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        results.append({"name": name, "status": "ok" if ok else "warn", "detail": detail})

    lowered = [f.lower() for f in files]

    vendor = [f for f in lowered if "vendor/" in f or "node_modules/" in f or "third_party" in f or "thirdparty" in f]
    add("无第三方 vendor 目录", not vendor, "命中：%s" % vendor if vendor else "0 个")

    minified = [f for f in files if f.endswith((".min.js", ".min.css", ".bundle.js"))]
    add("无压缩代码", not minified, "命中：%s" % minified if minified else "0 个")

    # 超长行往往意味着压缩代码或内嵌数据。只检查计入层级的文件——
    # dist/ 里的离线版本来就内联了整份数据，拿它做超长行检查没有意义。
    long_lines = []
    counted_layers = {key for key, _, _ in LAYER_RULES}
    for item in counted:
        if item["layer"] not in counted_layers:
            continue
        path = ROOT / str(item["path"])
        try:
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if len(line) > 2000:
                    long_lines.append("%s:%d" % (item["path"], i))
        except OSError:
            continue
    add("无超长行（>2000 字符）", not long_lines, "命中：%s" % long_lines[:3] if long_lines else "0 处")

    # 内嵌模板总量：说明清楚它是模板不是逻辑
    tmpl = sum(int(item["stats"]["template"]) for item in counted)  # type: ignore[index]
    add("内嵌模板已单独归类", True, "%d 行（不计入 SLOC）" % tmpl)

    return results


# ---------------------------------------------------------------------------
# 汇总与输出
# ---------------------------------------------------------------------------

LAYER_NAMES = {key: name for key, name, _ in LAYER_RULES}
LAYER_NAMES.update({key: name for key, name, _ in EXCLUDE_RULES})
LAYER_NAMES["other"] = "其他"


def summarize(counted: Sequence[Dict[str, object]]) -> Dict[str, Dict[str, int]]:
    by_layer: Dict[str, Dict[str, int]] = {}
    for item in counted:
        layer = str(item["layer"])
        bucket = by_layer.setdefault(
            layer, {"files": 0, "total": 0, "blank": 0, "comment": 0,
                    "docstring": 0, "template": 0, "code": 0})
        bucket["files"] += 1
        for key in ("total", "blank", "comment", "docstring", "template", "code"):
            bucket[key] += int(item["stats"][key])  # type: ignore[index]
    return by_layer


def render_markdown(counted: Sequence[Dict[str, object]],
                    by_layer: Dict[str, Dict[str, int]],
                    checks: Sequence[Dict[str, str]],
                    excluded: Sequence[str]) -> str:
    code_layers = [key for key, _, _ in LAYER_RULES]
    total = {k: 0 for k in ("files", "total", "blank", "comment", "docstring", "template", "code")}
    for key in code_layers:
        bucket = by_layer.get(key)
        if not bucket:
            continue
        for k in total:
            total[k] += bucket[k]

    lines: List[str] = []
    w = lines.append

    w("# 有效代码 LOC（Effective Lines of Code）")
    w("")
    w("> 本文件由 `tools/count_loc.py` 自动生成，请勿手工编辑。")
    w("> 复现：`python tools/count_loc.py`")
    w("")
    w("## 一、口径定义")
    w("")
    w("```")
    w("有效代码行 = 物理行 - 空行 - 注释行 - 文档字符串 - 内嵌模板/数据")
    w("```")
    w("")
    w("| 项 | 判定方式 |")
    w("| --- | --- |")
    w("| 物理行 | 文件按行切分后的总行数 |")
    w("| 空行 | `line.strip()` 为空 |")
    w("| 注释行 | Python 用 `tokenize` 取 `COMMENT` token；JS/CSS 识别 `//` 与 `/* */`（含跨行块注释）；HTML 识别 `<!-- -->`；Shell 识别行首 `#` |")
    w("| 文档字符串 | Python 中独立成句的字符串字面量（模块/类/函数首个语句），用 `tokenize` 判定前一个有效 token |")
    w("| 内嵌模板/数据 | **任何跨行数 >= %d 的字符串字面量**。这类内容是要输出的产物或夹具数据，不是逻辑 |" % TEMPLATE_MIN_LINES)
    w("")
    w("统计范围**只包含 git 跟踪的文件**（`git ls-files`），因此 `__pycache__`、")
    w("`.pytest_cache`、本地生成的 `config/llm.json` 等天然不在内。")
    w("")

    w("## 二、分层汇总")
    w("")
    w("| 层级 | 文件数 | 物理行 | 空行 | 注释 | 文档字符串 | 内嵌模板 | **有效代码行** |")
    w("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for key in code_layers:
        bucket = by_layer.get(key)
        if not bucket:
            continue
        w("| %s（`%s`） | %d | %d | %d | %d | %d | %d | **%d** |" % (
            LAYER_NAMES.get(key, key), key, bucket["files"], bucket["total"],
            bucket["blank"], bucket["comment"], bucket["docstring"],
            bucket["template"], bucket["code"]))
    w("| **合计** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** | **%d** |" % (
        total["files"], total["total"], total["blank"], total["comment"],
        total["docstring"], total["template"], total["code"]))
    w("")

    pct = (float(total["code"]) / total["total"] * 100) if total["total"] else 0.0
    w("有效代码行占物理行的 **%.1f%%**，其余为空白、注释、文档字符串与内嵌模板。" % pct)
    w("")

    w("## 三、逐文件明细（仅计入的层级）")
    w("")
    w("| 文件 | 语言 | 层级 | 物理行 | 空行 | 注释 | 文档串 | 模板 | 有效代码行 |")
    w("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    rows = [c for c in counted if c["layer"] in code_layers]
    rows.sort(key=lambda c: (-int(c["stats"]["code"]), str(c["path"])))  # type: ignore[index]
    for item in rows:
        st = item["stats"]  # type: ignore[assignment]
        w("| `%s` | %s | %s | %d | %d | %d | %d | %d | %d |" % (
            item["path"], item["lang"], LAYER_NAMES.get(str(item["layer"]), item["layer"]),
            st["total"], st["blank"], st["comment"], st["docstring"],
            st["template"], st["code"]))
    w("")

    # 前端分段
    html_items = [c for c in rows if str(c["path"]).endswith(".html")]
    if html_items:
        w("### 前端文件的分段构成")
        w("")
        w("`app/static/index.html` 是单文件前端，混在一起统计会掩盖真实构成，故拆开：")
        w("")
        w("| 分段 | 物理行 | 空行 | 注释 | 有效代码行 |")
        w("| --- | ---: | ---: | ---: | ---: |")
        for item in html_items:
            parts = item["stats"].get("_parts") or {}  # type: ignore[union-attr]
            for name, label in (("html", "HTML 结构"), ("css", "CSS 样式"), ("js", "JavaScript 逻辑")):
                part = parts.get(name)
                if not part:
                    continue
                w("| %s | %d | %d | %d | %d |" % (
                    label, part["total"], part["blank"], part["comment"], part["code"]))
        w("")

    w("## 四、不计入的文件及理由")
    w("")
    w("| 类别 | 文件 | 为什么不计入 |")
    w("| --- | --- | --- |")
    reasons = {
        "generated": "构建产物，内容由源码生成，计入即重复计数",
        "docs": "文档，不是可执行逻辑",
        "config": "配置 / 模板数据，不含应用逻辑",
    }
    for path in sorted(excluded):
        layer = classify(path)
        w("| %s | `%s` | %s |" % (
            LAYER_NAMES.get(layer, layer), path, reasons.get(layer, "非应用代码")))
    w("")

    w("## 五、卫生检查（确认没有虚增）")
    w("")
    w("| 检查项 | 结果 | 说明 |")
    w("| --- | --- | --- |")
    for chk in checks:
        mark = "通过" if chk["status"] == "ok" else "注意"
        w("| %s | %s | %s |" % (chk["name"], mark, chk["detail"]))
    w("")
    w("这几项对应评审最关心的四类虚增：**生成物**、**第三方复制代码**、")
    w("**压缩代码**、**大块测试夹具数据**。逐项检查结果如上。")
    w("")

    w("## 六、怎么自行复核")
    w("")
    w("```bash")
    w("# 1. 重新统计（数字应完全一致）")
    w("python tools/count_loc.py")
    w("")
    w("# 2. 看某个文件的行数分布")
    w("python tools/count_loc.py --json | python -m json.tool | less")
    w("")
    w("# 3. 抽查一个文件：注释与 docstring 的判定是否合理")
    w("sed -n '1,40p' src/paper_recycle_agent/data.py")
    w("")
    w("# 4. 确认生成物确实由脚本产出")
    w("grep -n 'dist/paper-recycle-offline.html' tools/build_offline.py")
    w("grep -n 'docs/CODE_LISTING.md' tools/gen_code_listing.py")
    w("```")
    w("")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str]) -> int:
    as_json = "--json" in argv
    check = "--check" in argv

    files = git_files()
    counted: List[Dict[str, object]] = []
    for rel in files:
        item = count_file(rel)
        if item is not None:
            counted.append(item)

    by_layer = summarize(counted)
    checks = hygiene_checks(files, counted)
    excluded = [f for f in files if classify(f) not in {k for k, _, _ in LAYER_RULES}]

    code_total = sum(by_layer.get(k, {}).get("code", 0) for k, _, _ in LAYER_RULES)

    if as_json:
        payload = {
            "effective_loc": code_total,
            "by_layer": {k: by_layer[k] for k in by_layer},
            "files": counted,
            "checks": checks,
            "excluded": excluded,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    md = render_markdown(counted, by_layer, checks, excluded)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md, encoding="utf-8")

    print("有效代码 LOC 统计")
    print("=" * 62)
    for key, name, _ in LAYER_RULES:
        bucket = by_layer.get(key)
        if not bucket:
            continue
        print("  %-14s %3d 个文件  %6d 行  （注释 %d，文档串 %d，模板 %d）" % (
            name, bucket["files"], bucket["code"],
            bucket["comment"], bucket["docstring"], bucket["template"]))
    print("-" * 62)
    print("  有效代码合计   %6d 行" % code_total)
    print()
    for chk in checks:
        mark = "[ok]" if chk["status"] == "ok" else "[!!]"
        print("  %s %s：%s" % (mark, chk["name"], chk["detail"]))
    print()
    print("报告已写入：%s" % OUT_MD.relative_to(ROOT))

    if check:
        # CI 用：LOC 跌破下限或卫生检查异常时失败
        problems = [c for c in checks if c["status"] != "ok"]
        if code_total < 1000:
            problems.append({"name": "有效代码量", "detail": "低于 1000 行：%d" % code_total})
        if problems:
            print()
            for p in problems:
                print("  [失败] %s：%s" % (p["name"], p["detail"]))
            return 1
        print("  校验通过")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
