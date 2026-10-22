"""投入产出模型测试。

重点不是「函数能跑」，而是：
1. 金额与已有分类数据自洽（不能凭空多出或少掉钱）；
2. 四级口径的标签不能串（官方 / 测算 / 估算 / 示例）；
3. Leontief 逆矩阵算得对（拿教科书例子对答案）；
4. 没有官方数据的层级必须显式说明「没有」，而不是返回一个像真的数字。
"""

import math

import pytest

from paper_recycle_agent import io_table
from paper_recycle_agent import stats as stats_mod


# ---------------------------------------------------------------- 金额口径


def test_spend_matches_category_sum():
    """全国金额必须等于分类拆分金额之和。"""
    s = io_table.spend(2024)
    rows = stats_mod.category_breakdown(2024, total=s["tonnage"])
    assert abs(sum(r["value"] for r in rows) - s["amount"]) < 0.2


def test_spend_is_labelled_lower_bound():
    """金额按回收参考价计，必须标为下限，避免被当成到厂采购额。"""
    s = io_table.spend(2024)
    assert s["is_lower_bound"] is True
    assert "下限" in s["note"]


def test_tonnage_prefers_consumption():
    amount, basis = io_table.tonnage(2024)
    assert amount == 7030.0
    assert "消费量" in basis


def test_tonnage_falls_back_to_recovery():
    """2016 年消费量未公布，应退回回收量并说明。"""
    amount, basis = io_table.tonnage(2016)
    assert amount == 4964.0
    assert "回收量" in basis


def test_average_price_reasonable():
    price = io_table.average_price(2024)
    # 回收参考价（居民/回收站口径）应在 500—2000 元/吨之间
    assert 500 < price < 2000


def test_direct_coefficient_matches_formula():
    d = io_table.direct_coefficient(2024)
    expected = round(io_table.spend(2024)["amount"] / 14600.0, 4)
    assert d["coefficient"] == expected
    assert d["is_lower_bound"] is True


def test_direct_coefficient_none_without_revenue():
    """没有营收公开值的年份，系数必须是 None，而不是编一个。"""
    d = io_table.direct_coefficient(2020)
    assert d["coefficient"] is None
    assert "无公开" in d["note"]


def test_unit_consumption_dimension():
    u = io_table.unit_consumption(2024)
    assert u["value"] == round(7030.0 / 14600.0, 3)


# ---------------------------------------------------------------- 分省


def test_province_rows_complete_and_sorted():
    data = io_table.province_spend(2024)
    rows = data["rows"]
    assert len(rows) == 34
    amounts = [r["amount"] for r in rows]
    assert amounts == sorted(amounts, reverse=True)
    assert rows[0]["rank"] == 1


def test_province_amount_sums_to_national():
    data = io_table.province_spend(2024)
    total = sum(float(r["amount"]) for r in data["rows"])
    assert abs(total - data["total"]) < 1.0  # 逐行四舍五入的累计误差


def test_province_provenance_reflects_quality():
    """山东是公开报道值，不能被标成「估算」。"""
    rows = {r["name"]: r for r in io_table.province_spend(2024)["rows"]}
    assert rows["山东省"]["provenance"] == io_table.PROVENANCE_OFFICIAL
    assert rows["山西省"]["provenance"] == io_table.PROVENANCE_ESTIMATED


def test_province_basis_says_not_actual_purchase():
    basis = io_table.province_spend(2024)["basis"]
    assert "非实际采购分布" in basis


# ---------------------------------------------------------------- 城市 / 企业


def test_city_spend_sums_to_province():
    data = io_table.city_spend("370000", 2024)
    total = sum(float(c["amount"]) for c in data["cities"])
    assert abs(total - data["province_amount"]) < 0.5


def test_city_requires_province_code():
    data = io_table.city_spend("CN", 2024)
    assert data["cities"] == []
    assert data["provenance"] == "无数据"


def test_city_note_mentions_no_official_table():
    data = io_table.city_spend("370000", 2024)
    assert "不编制投入产出表" in data["note"]


def test_enterprise_amount_formula():
    price = io_table.average_price(2024)
    data = io_table.enterprise_spend(2024)
    for row in data["rows"][:5]:
        assert abs(row["amount"] - row["volume"] * price / 10000) < 0.02


def test_enterprise_flagged_as_demo():
    data = io_table.enterprise_spend(2024)
    assert data["provenance"] == io_table.PROVENANCE_DEMO
    assert "不存在投入产出表" in data["note"]


# ---------------------------------------------------------------- 口径分级


def test_levels_declare_io_availability():
    levels = {lv["key"]: lv for lv in io_table.LEVELS}
    assert levels["national"]["io_available"] is True
    assert levels["province"]["io_available"] is True
    # 国家统计局明确：地级市不编制投入产出表
    assert levels["city"]["io_available"] is False
    assert levels["enterprise"]["io_available"] is False


def test_overview_has_all_parts():
    d = io_table.overview(2024)
    for key in ("national_io", "levels", "sources", "spend",
                "direct_coefficient", "unit_consumption", "provinces",
                "enterprises", "years"):
        assert key in d


def test_summary_text_mentions_provenance():
    text = io_table.summary_text(2024)
    assert "消耗金额" in text
    assert "口径分级" in text
    assert "地级市" in text


def test_summary_text_coefficient_carries_percent_unit():
    """直接消耗系数必须带 % —— 之前漏了单位，读起来像「4.28 元」。"""
    text = io_table.summary_text(2024)
    pct = io_table.direct_coefficient(2024)["coefficient_pct"]
    assert ("%s%%" % pct) in text
    assert "属下限" in text


# ---------------------------------------------------------------- Leontief


def test_leontief_inverse_textbook_example():
    """A=[[0.2,0.3],[0.4,0.1]] → (I-A)^-1=[[1.5,0.5],[2/3,4/3]]"""
    inv = io_table.leontief_inverse([[0.2, 0.3], [0.4, 0.1]])
    expected = [[1.5, 0.5], [2.0 / 3.0, 4.0 / 3.0]]
    for i in range(2):
        for j in range(2):
            assert abs(inv[i][j] - expected[i][j]) < 1e-9


def test_leontief_inverse_identity_for_zero_matrix():
    inv = io_table.leontief_inverse([[0.0, 0.0], [0.0, 0.0]])
    assert inv == [[1.0, 0.0], [0.0, 1.0]]


def test_leontief_inverse_rejects_singular():
    with pytest.raises(ValueError):
        io_table.leontief_inverse([[1.0, 0.0], [0.0, 1.0]])


def test_leontief_inverse_rejects_non_square():
    with pytest.raises(ValueError):
        io_table.leontief_inverse([[0.1, 0.2]])


def test_influence_and_response_mean_to_one():
    """影响力 / 感应度系数的平均值恒为 1，这是定义决定的。"""
    A = [[0.1, 0.2, 0.1], [0.2, 0.1, 0.2], [0.1, 0.1, 0.1]]
    inf = io_table.influence_coefficients(A)
    res = io_table.response_coefficients(A)
    assert math.isclose(sum(inf) / len(inf), 1.0, rel_tol=1e-3)
    assert math.isclose(sum(res) / len(res), 1.0, rel_tol=1e-3)


def test_load_matrix_csv_roundtrip(tmp_path):
    p = tmp_path / "m.csv"
    p.write_text("部门,A,B\nA,0.1,0.2\nB,0.3,0.4\n", encoding="utf-8")
    names, matrix = io_table.load_matrix_csv(str(p))
    assert names == ["A", "B"]
    assert matrix == [[0.1, 0.2], [0.3, 0.4]]


def test_load_matrix_csv_rejects_non_square(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("部门,A,B\nA,0.1,0.2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        io_table.load_matrix_csv(str(p))


def test_no_builtin_matrix_shipped():
    """仓库不内置投入产出矩阵：编一张假矩阵比不提供更糟。"""
    assert not io_table.matrix_path().exists()
