from paper_recycle_agent import stats


def test_history_sorted_and_sourced():
    rows = stats.get_history()
    years = [r["year"] for r in rows]
    assert years == sorted(years)
    assert years[0] == 2014
    assert years[-1] == 2025
    assert len(rows) >= 8


def test_history_latest_matches_national():
    rows = {r["year"]: r for r in stats.get_history()}
    assert rows[2024]["recovery"] == 6971.0
    assert rows[2024]["recovery_rate"] == 51.1
    assert rows[2025]["recovery"] == 7195.0
    assert rows[2025]["recovery_rate"] == 51.8


def test_yoy_computed():
    rows = {r["year"]: r for r in stats.get_history()}
    assert rows[2014]["yoy"] is None
    assert rows[2021]["yoy"] is not None
    assert round(rows[2021]["yoy"], 2) == 18.17


def test_import_series_cleared():
    series = {r["year"]: r["value"] for r in stats.get_import_series()}
    assert series[2017] == 2572.0
    assert series[2021] == 54.0
    assert series[2024] == 0.0


def test_category_shares_sum_to_100():
    for year in (2015, 2020, 2024, 2025):
        rows = stats.category_breakdown(year)
        assert len(rows) == 8
        assert abs(sum(r["share"] for r in rows) - 100.0) < 0.05


def test_category_tonnage_sums_to_recovery():
    rows = stats.category_breakdown(2024)
    total = sum(r["tonnage"] for r in rows)
    assert abs(total - 6971.0) < 1.0


def test_category_scaled_by_region_total():
    rows = stats.category_breakdown(2024, total=763.0)
    total = sum(r["tonnage"] for r in rows)
    assert abs(total - 763.0) < 0.5


def test_category_interpolation_between_anchors():
    """2018 年应落在 2015 与 2020 两个锚点之间。"""
    rows = {r["code"]: r for r in stats.category_breakdown(2018)}
    assert 52.0 < rows["1"]["share"] < 56.0
    assert 7.0 < rows["4"]["share"] < 13.0


def test_category_newsprint_declining():
    s2015 = {r["code"]: r["share"] for r in stats.category_breakdown(2015)}
    s2025 = {r["code"]: r["share"] for r in stats.category_breakdown(2025)}
    assert s2025["4"] < s2015["4"]          # 废新闻纸类下滑
    assert s2025["1"] > s2015["1"]          # 废瓦楞纸箱类上升


def test_category_has_provenance():
    for r in stats.category_breakdown(2024):
        assert "估算" in r["provenance"]


def test_category_summary_text():
    text = stats.category_summary(2024)
    assert "八大类" in text
    assert "废瓦楞纸箱类" in text
    assert "估算" in text


def test_history_summary_text():
    text = stats.history_summary()
    assert "历年" in text
    assert "2024" in text
    assert "6971" in text
