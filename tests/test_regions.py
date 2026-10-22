from paper_recycle_agent import regions


def test_national_node_official():
    node = regions.get_node("CN")
    assert node is not None
    assert node["name"] == "全国"
    assert node["stats"]["回收量(万吨)"] == 6971.0
    assert "官方" in node["provenance"]


def test_children_levels():
    provinces = regions.get_children("CN")
    assert len(provinces) >= 30
    assert all(p["level"] == "province" for p in provinces)
    # 广东省 -> 市 -> 县区
    gd = regions.find("广东省")
    assert gd is not None
    cities = regions.get_children(gd["code"])
    assert cities and all(c["level"] == "city" for c in cities)
    counties = regions.get_children(cities[0]["code"])
    assert counties and all(c["level"] == "county" for c in counties)


def test_breadcrumb_order():
    gd = regions.find("广东省")
    city = regions.get_children(gd["code"])[0]
    crumb = regions.breadcrumb(city["code"])
    assert crumb[0]["code"] == "CN"
    assert crumb[-1]["code"] == city["code"]


def test_summary_contains_name():
    text = regions.summary("CN")
    assert "全国" in text
    assert "6971" in text


def test_export_xlsx_bytes():
    data = regions.export_xlsx("CN")
    assert data[:2] == b"PK"  # xlsx 是 zip 容器
    assert len(data) > 1000
