"""智能工厂多智能体仿真测试。

分两层：
1. 核心层（无第三方依赖）：工序、仿真状态机、设备调度、多智能体决策；
2. Web 层：FastAPI 接口（缺 fastapi 时自动跳过，不影响核心测试）。
"""

import pytest

from paper_recycle_agent.mill.agents import Orchestrator
from paper_recycle_agent.mill import processes
from paper_recycle_agent.mill.devices import DeviceFleet, Task
from paper_recycle_agent.mill.simulation import MillSimulation, StageState


# ---------------- 工序定义 ----------------

def test_process_order_and_metrics():
    assert processes.ORDER == ("pulping", "papermaking", "drying", "quality")
    for key in processes.ORDER:
        proc = processes.get(key)
        assert proc.metrics
        assert proc.devices
        assert proc.knowledge


def test_unknown_process_raises():
    with pytest.raises(ValueError):
        processes.get("not_exist")


def test_metric_status():
    m = processes.Metric("t", "温度", "°C", 10, 20)
    assert m.status(15) == "normal"
    assert m.status(12) == "normal"
    assert m.status(20.5) == "warn"
    assert m.status(30) == "critical"


# ---------------- 仿真引擎 ----------------

def test_simulation_is_deterministic():
    a = MillSimulation(seed=42)
    b = MillSimulation(seed=42)
    a.start_batch("B1"); b.start_batch("B1")
    for _ in range(6):
        a.advance(); b.advance()
    assert a.snapshot()["stages"] == b.snapshot()["stages"]


def test_stage_transition():
    sim = MillSimulation(seed=1)
    sim.start_batch("B1")
    assert sim.stages["pulping"].state == "running"
    assert sim.stages["papermaking"].state == "idle"
    assert sim.next_process("pulping") == "papermaking"
    assert sim.next_process("quality") is None


def test_finish_and_flow():
    sim = MillSimulation(seed=2)
    sim.start_batch("B1")
    for _ in range(processes.get("pulping").base_time):
        sim.advance()
    assert "pulping" in sim.finish_completed()
    assert sim.stages["pulping"].state == "done"


def test_anomaly_injection_and_clear():
    sim = MillSimulation(seed=3)
    sim.start_batch("B1")
    assert sim.inject_anomaly("pulping", "brightness", 30.0) is True
    assert sim.stages["pulping"].metrics["brightness"] == 30.0
    assert sim.stages["pulping"].metric_status["brightness"] == "critical"
    assert sim.inject_anomaly("pulping", "no_such_metric", 1) is False
    sim.clear_anomalies()
    assert sim.snapshot()["anomalies"] == []


def test_hold_and_resume():
    sim = MillSimulation(seed=4)
    sim.start_batch("B1")
    sim.hold_batch("pulping")
    assert sim.stages["pulping"].state == "held"
    sim.resume("pulping")
    assert sim.stages["pulping"].state == "running"


def test_stage_overall_status():
    st = StageState(key="pulping", metric_status={"a": "normal", "b": "warn"})
    assert st.overall_status == "warn"
    st.metric_status["a"] = "critical"
    assert st.overall_status == "critical"


# ---------------- 设备层 ----------------

def test_device_assign_and_tick():
    fleet = DeviceFleet()
    sent = fleet.dispatch_for("pulping", "start", "T001")
    assert "agv-01" in sent and "plc-pulp" in sent
    results = []
    for _ in range(5):
        results.extend(fleet.tick(step=1))
    assert any(r.device_id == "agv-01" for r in results)
    assert any(r.device_id == "plc-pulp" for r in results)


def test_device_queue_when_busy():
    fleet = DeviceFleet()
    d = fleet.devices["agv-01"]
    assert d.assign(Task("t1", "pulping", "start")) is True
    assert d.assign(Task("t2", "pulping", "start")) is False
    assert d.snapshot()["queue_len"] == 1


def test_unknown_device():
    assert DeviceFleet().assign("no-such-device", Task("t", "pulping", "a")) is False


# ---------------- 多智能体 ----------------

def test_orchestrator_runs_full_batch():
    orch = Orchestrator(use_llm=False)
    orch.start_batch()
    snap = orch.run_until_idle(max_steps=80)
    assert snap["sim"]["idle"] is True
    states = [s["state"] for s in snap["sim"]["stages"]]
    assert states == ["done"] * 4
    assert len(snap["decisions"]) == 4
    assert any(e["event"] == "batch_complete" for e in snap["log"])
    # 七台设备都至少干过一次活
    assert all(d["done_count"] > 0 for d in snap["devices"])


def test_orchestrator_anomaly_triggers_arbitration():
    orch = Orchestrator(use_llm=False)
    orch.start_batch()
    orch.sim.inject_anomaly("pulping", "brightness", 20.0)
    snap = orch.run_until_idle(max_steps=80)
    held = [s for s in snap["sim"]["stages"] if s["state"] == "held"]
    assert any(s["key"] == "pulping" for s in held)
    assert any(e["event"] == "arbitration" for e in snap["log"])


def test_decision_basis_is_rule_without_llm():
    orch = Orchestrator(use_llm=False)
    orch.start_batch()
    snap = orch.run_until_idle(max_steps=80)
    assert all(d["basis"] == "rule" for d in snap["decisions"])


# ---------------- Web 层 ----------------

def test_api_mill_endpoints():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from app.server import app

    client = TestClient(app)
    r = client.get("/api/mill/processes")
    assert r.status_code == 200
    assert r.json()["order"] == list(processes.ORDER)

    r = client.post("/api/mill/start")
    assert r.status_code == 200
    assert r.json()["sim"]["batch"]

    r = client.post("/api/mill/run")
    assert r.status_code == 200
    assert r.json()["sim"]["idle"] is True

    r = client.post("/api/mill/anomaly", json={
        "process": "drying", "metric": "moisture", "value": 20.0,
    })
    assert r.status_code == 200 and r.json()["ok"] is True

    r = client.post("/api/mill/reset")
    assert r.status_code == 200
    assert r.json()["sim"]["batch"] is None
