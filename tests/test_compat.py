"""版本兼容性与可选依赖测试。

这套测试锁死两件事：
1. 仓库代码的语法/API 不超出 Python 3.7（由 tools/check_compat.py 实际执行）；
2. 没装 openpyxl 时，核心包仍能导入、命令行仍能用、导出接口给出可读提示。

两者都是「本机装了什么」之外的真实约束，因此必须由测试而不是文档来保证。
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "check_compat.py"


def _run(args, env_extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + str(ROOT)
    env["PYTHONIOENCODING"] = "utf-8"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


# ---------------------------------------------------------------- 版本下限


def test_compat_tool_passes():
    """全仓库语法与 API 不超出 Python 3.7。"""
    proc = _run([str(TOOL)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "结果：通过" in proc.stdout


def test_compat_tool_detects_violation():
    """校验器本身必须能报错，否则它只是装饰。"""
    bad = ROOT / "tools" / "_tmp_bad_compat.py"
    bad.write_text(
        "def bad(x: str) -> list[str]:\n"
        "    return x.removeprefix('a').split()\n",
        encoding="utf-8",
    )
    try:
        proc = _run([str(TOOL)])
        assert proc.returncode == 1
        assert "removeprefix" in proc.stdout
        assert "list[...]" in proc.stdout
    finally:
        bad.unlink(missing_ok=True)


def test_pyproject_requires_python_37():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.7"' in text


def test_pyproject_declares_optional_groups():
    """核心零依赖，Web / Excel 作为 extras 声明。"""
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:  # pragma: no cover
        pytest.skip("需要 tomllib 解析 pyproject")
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = meta["project"]
    assert project.get("dependencies", []) == []
    extras = project["optional-dependencies"]
    for key in ("web", "excel", "test"):
        assert key in extras


def test_package_version_matches_pyproject():
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover
        pytest.skip("需要 tomllib 解析 pyproject")
    import paper_recycle_agent

    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert meta["project"]["version"] == paper_recycle_agent.__version__


# ------------------------------------------------------- 缺少 openpyxl 的场景


def _block_openpyxl(code: str) -> str:
    """在子进程里把 openpyxl 屏蔽掉，再执行 code。"""
    prelude = "import sys; sys.modules['openpyxl'] = None\n"
    return prelude + code


def test_core_imports_without_openpyxl():
    proc = _run(["-c", _block_openpyxl(
        "import paper_recycle_agent as p; print(p.__version__)"
    )])
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip()


def test_cli_works_without_openpyxl():
    proc = _run(["-c", _block_openpyxl(
        "from paper_recycle_agent import cli, stats; "
        "print(stats.history_summary()[:40]); "
        "assert cli.main(['history']) == 0"
    )])
    assert proc.returncode == 0, proc.stderr


def test_exporter_available_reflects_missing_dependency():
    from paper_recycle_agent import exporter

    assert exporter.available() is True

    saved = sys.modules.get("openpyxl")
    sys.modules["openpyxl"] = None
    try:
        assert exporter.available() is False
        with pytest.raises(RuntimeError) as exc:
            exporter.build_workbook()
        assert "pip install openpyxl" in str(exc.value)
    finally:
        if saved is None:
            sys.modules.pop("openpyxl", None)
        else:
            sys.modules["openpyxl"] = saved


def test_export_endpoint_503_without_openpyxl():
    pytest.importorskip("httpx", reason="TestClient 依赖 httpx")
    from fastapi.testclient import TestClient

    from app.server import app

    client = TestClient(app)
    saved = sys.modules.get("openpyxl")
    sys.modules["openpyxl"] = None
    try:
        res = client.get("/export.xlsx")
        assert res.status_code == 503
        body = res.json()
        assert "openpyxl" in body["detail"]
        assert "离线版" in body["hint"]
    finally:
        if saved is None:
            sys.modules.pop("openpyxl", None)
        else:
            sys.modules["openpyxl"] = saved


def test_info_reports_python_and_excel_capability():
    pytest.importorskip("httpx", reason="TestClient 依赖 httpx")
    from fastapi.testclient import TestClient

    from app.server import app

    body = TestClient(app).get("/api/info").json()
    assert body["excel_available"] is True
    assert body["python_version"].count(".") == 2
