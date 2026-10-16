from paper_recycle_agent import pricing


def test_estimate_value():
    r = pricing.estimate("办公用纸", 10)
    assert r["recyclable"] is True
    assert r["estimated_value"] == 11.0  # 1.1 * 10


def test_estimate_nonrecyclable():
    r = pricing.estimate("纸巾", 5)
    assert r["recyclable"] is False
    assert r["estimated_value"] == 0.0


def test_estimate_unknown():
    r = pricing.estimate("玻璃", 1)
    assert r["matched"] is False


def test_estimate_negative_weight():
    r = pricing.estimate("纸箱", -3)
    assert r["estimated_value"] == 0.0
