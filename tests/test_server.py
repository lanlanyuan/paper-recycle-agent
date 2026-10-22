"""Web 层路由测试：锁死「打开就是 Not Found」这类回归。

历史上踩过两次：
1. 只注册了 `/`，预览面板请求 `/index.html` → 404；
2. 托管环境用 HEAD 探测 / 或带路径前缀访问 → 405 / 404。

因此这里对每个入口路径都断言状态码，并检查首页确实带版本号。
"""

import re

import pytest

pytest.importorskip("httpx", reason="TestClient 依赖 httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.server import app  # noqa: E402

client = TestClient(app)


def test_root_ok():
    r = client.get("/")
    assert r.status_code == 200
    assert "废纸回收 Agent" in r.text
    # 版本号格式固定，具体数字随发布变化，不做硬编码
    assert re.search(r"v\d+\.\d+\.\d+", r.text)


def test_index_html_ok():
    r = client.get("/index.html")
    assert r.status_code == 200
    assert "<!DOCTYPE html>" in r.text


def test_head_root_ok():
    """托管平台会用 HEAD 探测，405 会被显示成页面不可用。"""
    assert client.head("/").status_code == 200
    assert client.head("/index.html").status_code == 200


@pytest.mark.parametrize("path", ["/index", "/home", "/app/", "/some/prefix/"])
def test_unknown_page_falls_back_to_index(path):
    r = client.get(path)
    assert r.status_code == 200
    assert "<!DOCTYPE html>" in r.text


@pytest.mark.parametrize("path", ["/api/nope", "/logo.png", "/export.csv"])
def test_api_and_assets_still_404(path):
    r = client.get(path)
    assert r.status_code == 404


def test_favicon_no_content():
    assert client.get("/favicon.ico").status_code == 204


def test_stats_api():
    r = client.get("/api/stats", params={"code": "CN", "year": 2024})
    assert r.status_code == 200
    data = r.json()
    assert data["node"]["code"] == "CN"
    assert len(data["children"]) == 34
    assert len(data["categories"]) == 8
    assert len(data["history"]) >= 8


def test_stats_province_keeps_full_list():
    r = client.get("/api/stats", params={"code": "370000"})
    data = r.json()
    assert data["node"]["name"] == "山东省"
    # 选中省份后仍要返回全部省份，否则排名表会变空
    assert len(data["children"]) == 34


def test_info_api():
    data = client.get("/api/info").json()
    assert len(data["categories"]) == 8
    assert 2024 in data["years"]
    assert data["enterprise_types"]


def test_enterprises_api():
    data = client.get("/api/enterprises").json()
    assert data["totals"]["count"] >= 20
    assert data["list"]
    assert data["is_demo"] is True
    assert len(data["by_category"]) == 8


def test_enterprises_api_filtered():
    data = client.get("/api/enterprises", params={"province": "370000"}).json()
    assert data["list"]
    assert all(e["province_code"] == "370000" for e in data["list"])


def test_export_xlsx():
    r = client.get("/export.xlsx", params={"code": "CN", "year": 2024})
    assert r.status_code == 200
    assert r.content[:2] == b"PK"
    assert "spreadsheetml" in r.headers["content-type"]


def test_chat():
    r = client.post("/chat", json={"message": "纸箱 2kg"})
    assert r.status_code == 200
    assert "reply" in r.json()


def test_health():
    assert client.get("/health").json() == {"status": "ok"}
