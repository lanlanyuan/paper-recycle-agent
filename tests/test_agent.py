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
