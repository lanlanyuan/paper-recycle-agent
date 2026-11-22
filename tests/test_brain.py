"""产业大脑五链贯通仿真测试。

核心层（无第三方依赖）：五域定义、联动引擎、领域智能体；
Web 层：FastAPI 接口（缺 fastapi 时跳过）。
"""

import pytest

from paper_recycle_agent.brain import domains
from paper_recycle_agent.brain.engine import IndustryBrain, LINK_RULES
from paper_recycle_agent.brain.intelligence import BrainOrchestrator


# ---------------- 五域定义 ----------------

def test_five_domains():
    assert domains.ORDER == ("procurement", "production", "sales", "logistics", "finance")
    for key in domains.ORDER:
        d = domains.get(key)
        assert d.kpis and d.duties
        assert d.influences


def test_unknown_domain():
    with pytest.raises(ValueError):
        domains.get("no_such_domain")


def test_benchmarks_have_sources():
    """每条对标参考都必须带来源，不能出现无出处的数字。"""
    assert len(domains.BENCHMARKS) == 5
    for b in domains.BENCHMARKS:
        assert b["value"] and b["source"]
        assert "公开" in b["source"] or "报道" in b["source"] or "资料" in b["source"]


def test_link_rules_valid():
    """联动规则的源/目标 KPI 必须真实存在。"""
    for src, src_kpi, direction, dst, dst_kpi, coef in LINK_RULES:
        assert src in domains.ORDER and dst in domains.ORDER
        assert direction in ("up", "down")
        assert src_kpi in [k.key for k in domains.get(src).kpis]
        assert dst_kpi in [k.key for k in domains.get(dst).kpis]


# ---------------- 仿真引擎 ----------------

def test_deterministic():
    a = IndustryBrain(seed=7); b = IndustryBrain(seed=7)
    a.run(4); b.run(4)
    assert a.snapshot()["states"] == b.snapshot()["states"]


def test_five_states_present():
    snap = IndustryBrain().snapshot()
    assert len(snap["states"]) == 5
    assert [s["key"] for s in snap["states"]] == list(domains.ORDER)
    assert len(snap["link_rules"]) == len(LINK_RULES)


def test_cross_domain_links_fire():
    snap = IndustryBrain().run(3)
    links = [e for e in snap["log"] if e["event"] == "link"]
    assert links, "推演后应产生跨域联动日志"
    # 联动必须跨越不同业务域
    assert any(e["src"] != e["dst"] for e in links)


def test_kpis_stay_bounded():
    """联动叠加后 KPI 必须收敛，不能无限增长。"""
    snap = IndustryBrain().run(20)
    for st in snap["states"]:
        for kdef in st["kpi_defs"]:
            v = st["kpis"][kdef["key"]]
            base = kdef["base"]
            assert base * 0.7 <= v <= base * 1.3


def test_optimize_propagates():
    brain = IndustryBrain()
    result = brain.optimize("procurement", "purchase_cost_index", 80.0)
    assert result["ok"] is True
    assert result["before"] != result["after"]
    assert any(e["event"] == "optimize" for e in result["snapshot"]["log"])
    # 财务域应受到传导影响
    finance = [s for s in result["snapshot"]["states"] if s["key"] == "finance"][0]
    assert finance["last_impact"] or any(
        e["event"] == "link" and e["dst"] == "finance"
        for e in result["snapshot"]["log"]
    )


def test_optimize_unknown_kpi():
    result = IndustryBrain().optimize("procurement", "not_a_kpi", 10)
    assert result["ok"] is False


def test_reset():
    brain = IndustryBrain()
    brain.run(5)
    brain.reset()
    snap = brain.snapshot()
    assert snap["step"] == 0
    assert snap["log"] == []


# ---------------- 领域智能体 ----------------

def test_five_advices_with_rule_basis():
    orch = BrainOrchestrator(use_llm=False)
    orch.brain.run(2)
    advices = orch.advise_all()
    assert len(advices) == 5
    assert all(a["basis"] == "rule" for a in advices)
    assert all(a["domain_name"] for a in advices)


def test_advice_snapshot_consistency():
    orch = BrainOrchestrator(use_llm=False)
    orch.advise_all()
    snap = orch.snapshot()
    assert len(snap["advices"]) == 5


# ---------------- Web 层 ----------------

def test_api_brain_endpoints():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from app.server import app

    client = TestClient(app)
    r = client.get("/api/brain/state")
    assert r.status_code == 200
    assert len(r.json()["states"]) == 5

    r = client.post("/api/brain/run", json={"steps": 3})
    assert r.status_code == 200
    assert r.json()["step"] == 3

    r = client.post("/api/brain/advise")
    assert r.status_code == 200
    assert len(r.json()["advices"]) == 5

    r = client.post("/api/brain/optimize", json={
        "domain": "procurement", "kpi": "purchase_cost_index", "target": 82.0,
    })
    assert r.status_code == 200 and r.json()["ok"] is True

    r = client.post("/api/brain/reset")
    assert r.status_code == 200
    assert r.json()["step"] == 0
