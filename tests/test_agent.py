from paper_recycle_agent import agent


def test_respond_greeting():
    out = agent.respond("你好")
    assert "废纸回收助手" in out


def test_respond_help():
    out = agent.respond("帮助")
    assert "使用说明" in out


def test_respond_classify():
    out = agent.respond("纸箱")
    assert "纸箱" in out


def test_respond_price_with_weight():
    out = agent.respond("办公用纸 3kg")
    assert "回收价值" in out


def test_respond_jin_conversion():
    out = agent.respond("纸箱 2斤")
    assert "回收价值" in out


def test_respond_yearbook_query():
    out = agent.respond("废纸分类标准")
    assert "GB/T 20811" in out
    assert "6971" in out


def test_respond_industry_data():
    out = agent.respond("回收量多少")
    assert "回收量" in out or "6971" in out


def test_respond_history_intent():
    out = agent.respond("历年数据")
    assert "历年" in out
    assert "2014" in out


def test_respond_history_trend_intent():
    out = agent.respond("近五年趋势")
    assert "历年" in out


def test_respond_category_stats_intent():
    out = agent.respond("分类回收数据")
    assert "废瓦楞纸箱类" in out
    assert "八大类" in out


def test_respond_category_stats_with_year():
    out = agent.respond("2020 年分类数据")
    assert "2020" in out
    assert "废瓦楞纸箱类" in out


def test_respond_province_only():
    out = agent.respond("山东省")
    assert "山东省" in out
    assert "763" in out


def test_no_city_data_claim():
    """市级数据已下线，助手不应再声称能查市县。"""
    out = agent.respond("帮助")
    assert "仅全国与省级" in out
