"""企业维度测试：名录、按省/按类/按类型汇总、覆盖率与对话摘要。"""

from paper_recycle_agent import enterprises, regions


def test_enterprises_loaded():
    assert len(enterprises.ENTERPRISES) >= 20
    assert enterprises.IS_DEMO is True  # 未放 data/enterprises.csv 时为示例数据


def test_fields_complete():
    for e in enterprises.ENTERPRISES:
        assert e["id"] and e["name"]
        assert e["province_code"] in regions._INDEX
        assert e["type"] in enterprises.TYPES
        assert e["categories"]
        assert float(e["volume"]) > 0
        assert -90 <= float(e["lat"]) <= 90
        assert 73 <= float(e["lon"]) <= 136


def test_list_sorted_desc():
    rows = enterprises.list_enterprises()
    vols = [float(r["volume"]) for r in rows]
    assert vols == sorted(vols, reverse=True)


def test_filter_by_province():
    rows = enterprises.list_enterprises("370000")
    assert rows
    assert all(r["province_code"] == "370000" for r in rows)


def test_filter_by_category():
    rows = enterprises.list_enterprises(category="6")  # 办公废纸
    assert rows
    assert all("6" in r["categories"] for r in rows)


def test_filter_by_type():
    rows = enterprises.list_enterprises(etype="造纸企业")
    assert rows
    assert all(r["type"] == "造纸企业" for r in rows)


def test_by_province_totals_match():
    rows = enterprises.by_province()
    total = sum(float(r["volume"]) for r in rows)
    assert round(total, 1) == enterprises.totals()["volume"]
    assert sum(int(r["count"]) for r in rows) == len(enterprises.ENTERPRISES)


def test_by_province_sorted():
    vols = [float(r["volume"]) for r in enterprises.by_province()]
    assert vols == sorted(vols, reverse=True)


def test_by_category_covers_all_eight():
    rows = enterprises.by_category()
    assert len(rows) == 8
    assert all(r["name"] for r in rows)


def test_by_type_totals():
    rows = enterprises.by_type()
    assert sum(int(r["count"]) for r in rows) == len(enterprises.ENTERPRISES)


def test_find_by_name():
    e = enterprises.find("鲁清再生")
    assert e is not None
    assert e["city"] == "济南市"


def test_find_short_name_returns_none():
    assert enterprises.find("废") is None


def test_summary_national():
    text = enterprises.summary()
    assert "回收企业概览" in text
    assert "示例" in text  # 必须声明是示例数据
    assert "按类型" in text


def test_summary_province_has_coverage():
    text = enterprises.summary("370000")
    assert "山东" in text
    assert "名录覆盖率" in text


def test_province_volume_not_exceed_official():
    """名录是样本，不应超过该省官方回收量（否则数据明显有问题）。"""
    for row in enterprises.by_province():
        node = regions.get_node(str(row["province_code"]))
        if not node:
            continue
        official = float(node["stats"]["回收量(万吨)"])  # type: ignore[index]
        assert float(row["volume"]) <= official, f"{node['name']} 企业量超过官方回收量"
