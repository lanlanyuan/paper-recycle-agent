"""有效代码 LOC 统计器自身的测试。

统计器最容易出的错不是崩溃，而是「悄悄算错」——多算几行没人发现，
少算几行也没人发现，最后交出去的数字就是假的。所以这里逐条钉住判定规则。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import count_loc  # noqa: E402


# ---------------------------------------------------------------------------
# Python：空行 / 注释 / 文档字符串 / 代码
# ---------------------------------------------------------------------------

def test_python_counts_basic_roles():
    src = (
        '"""模块文档。"""\n'          # 1 docstring
        "\n"                          # 2 blank
        "import os\n"                 # 3 code
        "\n"                          # 4 blank
        "# 整行注释\n"                # 5 comment
        "x = 1\n"                     # 6 code
        "\n"                          # 7 blank
        "\n"                          # 8 blank
        "def f():\n"                  # 9 code
        '    """函数文档。"""\n'      # 10 docstring
        "    return x\n"              # 11 code
    )
    got = count_loc.count_python(src)
    assert got["total"] == 11
    assert got["blank"] == 4
    assert got["comment"] == 1
    assert got["docstring"] == 2
    assert got["template"] == 0
    assert got["code"] == 4


def test_trailing_comment_line_still_counts_as_code():
    """`x = 1  # 说明` 这一行是代码，不是注释。

    按整行算成注释会少算代码行——这是统计器最隐蔽的一类偏差。
    """
    src = "x = 1  # 行尾注释\n# 纯注释\ny = 2\n"
    got = count_loc.count_python(src)
    assert got["comment"] == 1, "只有纯注释行才算注释"
    assert got["code"] == 2


def test_long_module_docstring_is_docstring_not_template():
    """模块说明写长了仍然是文档，不能被当成内嵌模板。

    io_table.py 的模块 docstring 有 41 行，曾经被误判为模板，
    导致 core 层凭空少算 41 行。
    """
    body = "".join("说明第 %d 行。\n" % i for i in range(60))
    src = '"""长文档开始。\n%s"""\n\nx = 1\n' % body
    got = count_loc.count_python(src)
    assert got["docstring"] >= 60
    assert got["template"] == 0, "docstring 不该被计入模板"
    assert got["code"] == 1


def test_long_assigned_string_is_template():
    """赋值语句里的超长字符串是内嵌模板，不是逻辑代码。"""
    body = "".join("<div>行 %d</div>\n" % i for i in range(50))
    src = 'TEMPLATE = """%s"""\n\nprint(TEMPLATE)\n' % body
    got = count_loc.count_python(src)
    assert got["template"] >= 50
    assert got["code"] == 1, "只有 print 那行是代码"


def test_short_assigned_string_is_code():
    """短字符串不触发模板判定。"""
    src = 'NAME = "abc"\nprint(NAME)\n'
    got = count_loc.count_python(src)
    assert got["template"] == 0
    assert got["code"] == 2


def test_python_broken_syntax_does_not_crash():
    """语法错误的文件也要能统计，不能把整个报告搞崩。"""
    got = count_loc.count_python("def f(:\n    pass\n")
    assert got["total"] == 2
    assert got["code"] >= 0


def test_python_total_equals_sum_of_parts():
    src = '"""文档。"""\n\n# 注释\nx = 1\n\n\ndef f():\n    return x\n'
    got = count_loc.count_python(src)
    assert got["total"] == got["blank"] + got["comment"] + got["docstring"] + got["template"] + got["code"]


# ---------------------------------------------------------------------------
# HTML：必须拆成结构 / CSS / JS
# ---------------------------------------------------------------------------

def test_html_splits_style_and_script():
    html = (
        "<html>\n"                    # html
        "<style>\n"                   # html
        "/* 样式注释 */\n"            # css comment
        ".a { color: red; }\n"        # css code
        "</style>\n"                  # html
        "<script>\n"                  # html
        "// 脚本注释\n"               # js comment
        "var a = 1;\n"                # js code
        "</script>\n"                 # html
        "</html>\n"                   # html
    )
    parts = count_loc.count_html(html)
    assert parts["html"]["code"] == 6, "开闭标签与结构行算 HTML 代码"
    assert parts["css"]["comment"] == 1
    assert parts["css"]["code"] == 1
    assert parts["js"]["comment"] == 1
    assert parts["js"]["code"] == 1


def test_html_total_matches_input_lines():
    html = "<html>\n<style>\na{}\n</style>\n<script>\nvar a;\n</script>\n</html>\n"
    parts = count_loc.count_html(html)
    total = sum(p["total"] for p in parts.values())
    assert total == 8


# ---------------------------------------------------------------------------
# C 系语法：跨行块注释
# ---------------------------------------------------------------------------

def test_block_comment_spans_multiple_lines():
    lines = [
        "/* 第一行",
        "   第二行",
        "   第三行 */",
        "var a = 1;",
        "// 单行",
        "var b = 2;",
    ]
    got = count_loc._count_c_like(lines, "//")
    assert got["comment"] == 4, "三行块注释 + 一行单行注释"
    assert got["code"] == 2


def test_code_with_trailing_comment_is_code():
    lines = ["var a = 1; // 说明", "var b = 2;"]
    got = count_loc._count_c_like(lines, "//")
    assert got["code"] == 2
    assert got["comment"] == 0


# ---------------------------------------------------------------------------
# 分类
# ---------------------------------------------------------------------------

def test_classify_layers():
    assert count_loc.classify("src/paper_recycle_agent/llm.py") == "core"
    assert count_loc.classify("app/server.py") == "web"
    assert count_loc.classify("app/static/index.html") == "web"
    assert count_loc.classify("run.py") == "web"
    assert count_loc.classify("tests/test_llm.py") == "tests"
    assert count_loc.classify("conftest.py") == "tests"
    assert count_loc.classify("tools/count_loc.py") == "tools"


def test_classify_excludes():
    assert count_loc.classify("dist/paper-recycle-offline.html") == "generated"
    assert count_loc.classify("docs/CODE_LISTING.md") == "generated"
    assert count_loc.classify("docs/USAGE.md") == "docs"
    assert count_loc.classify("LICENSE") == "docs"
    assert count_loc.classify("pyproject.toml") == "config"
    assert count_loc.classify("data/enterprises.csv.example") == "config"
    assert count_loc.classify(".github/workflows/ci.yml") == "config"


def test_no_unknown_category_for_tracked_files():
    """所有被跟踪的文件都应该有明确归类，不该落到「其他」。"""
    unknown = [f for f in count_loc.git_files() if count_loc.classify(f) == "other"]
    assert unknown == [], "未归类的文件：%s" % unknown


# ---------------------------------------------------------------------------
# 端到端
# ---------------------------------------------------------------------------

def test_generated_artifacts_are_not_counted():
    """dist/ 与 CODE_LISTING 是生成物，必须排除，否则行数虚增。"""
    counted = {c["path"] for c in (
        count_loc.count_file(f) for f in count_loc.git_files()
    ) if c is not None and c["layer"] in {k for k, _, _ in count_loc.LAYER_RULES}}
    assert "dist/paper-recycle-offline.html" not in counted
    assert "docs/CODE_LISTING.md" not in counted


def test_effective_loc_is_plausible():
    """有效代码量应在合理区间：太少说明统计漏了，太多说明混进了非代码。"""
    files = count_loc.git_files()
    counted = [c for c in (count_loc.count_file(f) for f in files) if c is not None]
    by_layer = count_loc.summarize(counted)
    total = sum(by_layer.get(k, {}).get("code", 0) for k, _, _ in count_loc.LAYER_RULES)
    assert 3000 <= total <= 12000, "有效代码行数异常：%d" % total


def test_no_vendor_or_minified_code():
    files = count_loc.git_files()
    lowered = [f.lower() for f in files]
    assert not [f for f in lowered if "vendor/" in f or "node_modules/" in f]
    assert not [f for f in files if f.endswith((".min.js", ".min.css"))]
