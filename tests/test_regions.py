from paper_recycle_agent import regions


def test_national_node_official():
    node = regions.get_node("CN")
    assert node is not None
    assert node["name"] == "全国"
    assert node["level"] == "national"
    assert node["stats"]["回收量(万吨)"] == 6971.0
    assert "官方" in node["provenance"]


def test_only_two_levels():
    """v1.3.0 起只保留全国 + 省级，不再有市 / 县区。"""
    provinces = regions.get_children("CN")
    assert len(provinces) == 34
    assert all(p["level"] == "province" for p in provinces)
    for p in provinces:
        assert regions.get_children(p["code"]) == []


def test_no_city_or_county_level():
    levels = {node["level"] for node in regions._INDEX.values()}
    assert levels == {"national", "province"}


def test_province_sum_equals_national_total():
    total = sum(p["stats"]["回收量(万吨)"] for p in regions.get_children("CN"))
    assert round(total, 1) == regions.NATIONAL_STATS["回收量(万吨)"]


def test_reported_provinces_flagged():
    sd = regions.find("山东省")
    gd = regions.find("广东省")
    assert sd is not None and gd is not None
    assert sd["quality"] == "reported"
    assert sd["stats"]["回收量(万吨)"] == 763.0
    assert gd["stats"]["回收量(万吨)"] == 733.0


def test_find_short_name():
    node = regions.find("山东")
    assert node is not None
    assert node["name"] == "山东省"


def test_find_national_alias():
    for alias in ["全国", "中国", "国家", "CN"]:
        node = regions.find(alias)
        assert node is not None and node["code"] == "CN"


def test_breadcrumb_two_levels():
    sd = regions.find("山东省")
    crumb = regions.breadcrumb(sd["code"])
    assert len(crumb) == 2
    assert crumb[0]["code"] == "CN"
    assert crumb[-1]["code"] == sd["code"]


def test_share_of_national():
    assert regions.share_of_national("CN") == 1.0
    share = regions.share_of_national("370000")
    assert 0.10 < share < 0.12


def test_summary_contains_history_and_category():
    text = regions.summary("CN")
    assert "全国" in text
    assert "6971" in text
    assert "历年" in text
    assert "废瓦楞纸箱类" in text


def test_summary_province():
    text = regions.summary("370000")
    assert "山东省" in text
    assert "梯队" in text
    assert "占全国比重" in text


def test_tree_structure():
    tree = regions.tree()
    assert tree["code"] == "CN"
    assert len(tree["children"]) == 34
    assert all(c["children"] == [] for c in tree["children"])
