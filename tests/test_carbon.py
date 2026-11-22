"""碳核算 Agent 测试：国标公式可手算复核。

核心层：排放因子、五类排放源、总量汇总、情景模拟、回收桥接；
Web 层：/api/carbon/* 接口。
"""

import pytest

from paper_recycle_agent.carbon import factors, model, recycle_agent
from paper_recycle_agent.carbon.accounting import CarbonAccounting
from paper_recycle_agent.carbon.model import ActivityData, FuelUse


# ---------------- 因子（国标附录B） ----------------

def test_fuel_ef_formula():
    """EF = CC × OF × 44/12（国标公式4），必须能手算复核。"""
    f = factors.fuel("bituminous")
    expected = 26.1e-3 * 0.93 * 44.0 / 12.0
    assert abs(f.ef - expected) < 1e-12
    assert abs(f.ef - 0.089001) < 1e-5


def test_fuel_factors_have_sources():
    for key in factors.FUELS:
        f = factors.fuel(key)
        p = f.public()
        assert p["source"] == factors.SOURCE_STD
        assert p["ncv_source"] and p["cc_source"]
        assert p["ef"] > 0


def test_unknown_fuel():
    with pytest.raises(ValueError):
        factors.fuel("no_such_fuel")


def test_std_constants():
    assert factors.LIMESTONE_EF == 0.405
    assert factors.HEAT_EF_DEFAULT == 0.11
    assert factors.CH4_MAX == 0.25 and factors.CH4_CORRECTION == 0.5
    # 电力因子国标要求主管部门最新值，不内置过期数字
    assert factors.ELECTRIC_EF_DEFAULT is None


# ---------------- 核算公式 ----------------

def _minimal() -> ActivityData:
    """手算可复核的最小案例。"""
    return ActivityData(
        fuels=[FuelUse("bituminous", 1000.0)],  # 烟煤 1000 t
        limestone_ton=1000.0,                    # 石灰石 1000 t
        electricity_purchased=0.0,
        electric_ef=None,
        heat_purchased=1000.0,                   # 外购热 1000 GJ
        wastewater_cod_removed=0.0,
        paper_output_wan_ton=1.0,
    )


def test_fuel_emission_hand_calculable():
    r = CarbonAccounting(_minimal()).calculate()
    fuel_item = [i for i in r["items"] if i["key"] == "fuel_bituminous"][0]
    # 1000 t × 19.570 GJ/t × 0.089001 tCO2/GJ = 1741.75 tCO2
    assert fuel_item["activity"] == 19570.0
    assert abs(fuel_item["emission"] - 1741.75) < 0.02


def test_process_emission():
    r = CarbonAccounting(_minimal()).calculate()
    proc = [i for i in r["items"] if i["key"] == "process"][0]
    assert abs(proc["emission"] - 405.0) < 1e-9  # 1000 × 0.405


def test_heat_emission():
    r = CarbonAccounting(_minimal()).calculate()
    heat = [i for i in r["items"] if i["key"] == "heat"][0]
    assert abs(heat["emission"] - 110.0) < 1e-9  # 1000 × 0.11


def test_incomplete_when_electric_not_configured():
    r = CarbonAccounting(_minimal()).calculate()
    assert r["incomplete"] is True
    assert r["total_tco2e"] is None
    elec = [i for i in r["items"] if i["key"] == "electricity"][0]
    assert elec["emission"] is None


def test_total_matches_hand_calculation():
    a = _minimal()
    a.electric_ef = 0.5  # 购入电 0，因子不影响
    r = CarbonAccounting(a).calculate()
    # 1741.75 + 405 + 0 + 0 + 110 = 2256.75
    assert abs(r["total_tco2e"] - 2256.75) < 0.02
    assert r["incomplete"] is False


def test_intensity_unit_correct():
    """碳强度 = 总排放 ÷ (产量万吨 × 10000)，单位 tCO2e/吨纸。"""
    a = _minimal()
    a.electric_ef = 0.5
    r = CarbonAccounting(a).calculate()
    assert r["intensity_unit"] == "tCO2e/吨纸"
    expected = round(r["total_tco2e"] / (1.0 * 10000.0), 4)
    assert r["intensity_tco2e_per_ton"] == expected


def test_wastewater_methane_formula():
    a = ActivityData(
        wastewater_cod_removed=1000.0, wastewater_cod_sludge=200.0,
        methane_recovered=0.0, electric_ef=0.5,
    )
    r = CarbonAccounting(a).calculate()
    ww = [i for i in r["items"] if i["key"] == "wastewater"][0]
    # (1000-200) × 0.25 × 0.5 × 21 = 2100
    assert abs(ww["emission"] - 2100.0) < 1e-9


def test_exported_electricity_reduces():
    base = ActivityData(electricity_purchased=1000.0, electric_ef=0.5)
    exported = ActivityData(electricity_purchased=1000.0,
                            electricity_exported=400.0, electric_ef=0.5)
    e1 = [i for i in CarbonAccounting(base).calculate()["items"] if i["key"] == "electricity"][0]
    e2 = [i for i in CarbonAccounting(exported).calculate()["items"] if i["key"] == "electricity"][0]
    assert e1["activity"] == 1000.0 and e2["activity"] == 600.0
    assert e2["emission"] < e1["emission"]


# ---------------- 情景与回收桥接 ----------------

def test_scenario_reduces_emission():
    a = CarbonAccounting().activity
    a.electric_ef = 0.5366
    s = CarbonAccounting(a).scenario({"fuel:bituminous": 16000.0})
    assert s["delta_tco2e"] < 0
    assert "下降" in s["interpretation"]


def test_recycle_credit_is_separate():
    r = CarbonAccounting().calculate()
    c = r["recycle_credit"]
    assert "范围三" in c["scope"]
    assert c["credit_tco2e"] > 0
    assert "演示" in c["source"]


def test_bridge_does_not_overwrite_factory_value():
    a = CarbonAccounting().activity  # 已有 18 万吨
    result = recycle_agent.bridge_to_activity(6971.0, a, overwrite=False)
    assert result["written"] is False
    assert a.wastepaper_recycled_wan_ton == 18.0


def test_bridge_writes_when_empty():
    a = ActivityData(wastepaper_recycled_wan_ton=0.0)
    result = recycle_agent.bridge_to_activity(123.0, a, overwrite=False)
    assert result["written"] is True
    assert a.wastepaper_recycled_wan_ton == 123.0


def test_eeioa_method_no_data():
    result = recycle_agent.supply_chain_carbon_demo()
    assert result["ok"] is False and result["available"] is False
    assert "I−A" in result["formula"]


def test_eeioa_method_with_matrix():
    matrix = [[0.1, 0.2], [0.3, 0.1]]
    result = recycle_agent.supply_chain_carbon_demo(matrix)
    assert result["ok"] is True
    assert len(result["leontief_inverse"]) == 2


# ---------------- Web 层 ----------------

def test_api_carbon_endpoints():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    from app.server import app

    client = TestClient(app)
    r = client.get("/api/carbon/factors")
    assert r.status_code == 200
    assert len(r.json()["fuels"]) == len(factors.FUELS)

    r = client.get("/api/carbon/state")
    assert r.status_code == 200
    assert len(r.json()["result"]["items"]) == 7

    r = client.post("/api/carbon/activity", json={"electric_ef": 0.5366,
                                                   "electric_ef_year": 2024})
    assert r.status_code == 200
    assert r.json()["result"]["incomplete"] is False

    r = client.post("/api/carbon/scenario", json={"changes": {"fuel:bituminous": 16000.0}})
    assert r.status_code == 200
    assert r.json()["delta_tco2e"] < 0

    r = client.post("/api/carbon/bridge-recycle?year=2024")
    assert r.status_code == 200 and r.json()["ok"] is True
    assert r.json()["bridge"]["written"] is False  # 不覆盖单厂数据

    r = client.post("/api/carbon/reset")
    assert r.status_code == 200 and r.json()["ok"] is True
