"""行政区划分层统计：国家 → 省 → 市 → 县区。

数据口径（务必注意）：
- 国家级：中国造纸协会《中国造纸工业2024年度报告》官方数据。
- 省/市/县三级：**分层测算**（按区域权重从国家总量分摊，确定性生成），
  用于演示层级统计、下钻与 Excel 导出；真实统计可通过替换 `_RAW` 或导入 JSON 覆盖。
  每条数据带 `provenance` 字段，标明「官方」或「分层测算」。

层级：national(国家) → province(省) → city(市) → county(县区)。
"""

import zlib
from typing import Dict, List, Optional

# 官方口径（国家级）
NATIONAL_STATS: Dict[str, float] = {
    "回收量(万吨)": 6971.0,
    "纸及纸板产量(万吨)": 13625.0,
    "回收率(%)": 51.1,
    "利用率(%)": 51.6,
    "回收企业数(家)": 4200,
    "从业人员(人)": 620000,
}

PROVENANCE_OFFICIAL = "官方（中国造纸协会《中国造纸工业2024年度报告》）"
PROVENANCE_MODEL = "分层测算（按区域权重分摊，演示用，可替换为真实统计）"

# (省名, 省级代码, 权重, [(市名, [县区名, ...]), ...])
_RAW = [
    ("广东省", "440000", 0.115, [
        ("广州市", ["荔湾区", "天河区"]),
        ("深圳市", ["罗湖区", "南山区"]),
    ]),
    ("江苏省", "320000", 0.105, [
        ("南京市", ["玄武区", "江宁区"]),
        ("苏州市", ["姑苏区", "昆山市"]),
    ]),
    ("山东省", "370000", 0.095, [
        ("济南市", ["历下区", "章丘区"]),
        ("青岛市", ["市南区", "黄岛区"]),
    ]),
    ("浙江省", "330000", 0.080, [
        ("杭州市", ["上城区", "余杭区"]),
        ("宁波市", ["海曙区", "鄞州区"]),
    ]),
    ("河南省", "410000", 0.065, [
        ("郑州市", ["金水区", "中牟县"]),
        ("洛阳市", ["涧西区", "偃师区"]),
    ]),
    ("四川省", "510000", 0.055, [
        ("成都市", ["锦江区", "双流区"]),
        ("绵阳市", ["涪城区", "江油市"]),
    ]),
    ("河北省", "130000", 0.050, [
        ("石家庄市", ["长安区", "正定县"]),
        ("唐山市", ["路南区", "丰润区"]),
    ]),
    ("湖北省", "420000", 0.048, [
        ("武汉市", ["江岸区", "洪山区"]),
        ("宜昌市", ["西陵区", "宜都市"]),
    ]),
    ("湖南省", "430000", 0.045, [
        ("长沙市", ["岳麓区", "长沙县"]),
        ("岳阳市", ["岳阳楼区", "汨罗市"]),
    ]),
    ("福建省", "350000", 0.042, [
        ("福州市", ["鼓楼区", "闽侯县"]),
        ("厦门市", ["思明区", "集美区"]),
    ]),
    ("安徽省", "340000", 0.040, [
        ("合肥市", ["庐阳区", "肥东县"]),
        ("芜湖市", ["镜湖区", "无为市"]),
    ]),
    ("上海市", "310000", 0.038, [
        ("上海市", ["浦东新区", "闵行区"]),
    ]),
    ("江西省", "360000", 0.032, [
        ("南昌市", ["东湖区", "南昌县"]),
        ("赣州市", ["章贡区", "南康区"]),
    ]),
    ("辽宁省", "210000", 0.030, [
        ("沈阳市", ["和平区", "浑南区"]),
        ("大连市", ["中山区", "金州区"]),
    ]),
    ("重庆市", "500000", 0.028, [
        ("重庆市", ["渝北区", "江津区"]),
    ]),
    ("广西壮族自治区", "450000", 0.026, [
        ("南宁市", ["青秀区", "武鸣区"]),
        ("柳州市", ["城中区", "柳江区"]),
    ]),
    ("陕西省", "610000", 0.024, [
        ("西安市", ["雁塔区", "长安区"]),
        ("宝鸡市", ["渭滨区", "凤翔区"]),
    ]),
    ("云南省", "530000", 0.022, [
        ("昆明市", ["五华区", "呈贡区"]),
        ("曲靖市", ["麒麟区", "沾益区"]),
    ]),
    ("山西省", "140000", 0.020, [
        ("太原市", ["小店区", "清徐县"]),
        ("大同市", ["平城区", "云冈区"]),
    ]),
    ("天津市", "120000", 0.018, [
        ("天津市", ["滨海新区", "南开区"]),
    ]),
    ("北京市", "110000", 0.017, [
        ("北京市", ["朝阳区", "海淀区"]),
    ]),
    ("内蒙古自治区", "150000", 0.016, [
        ("呼和浩特市", ["新城区", "赛罕区"]),
        ("包头市", ["昆都仑区", "东河区"]),
    ]),
    ("贵州省", "520000", 0.014, [
        ("贵阳市", ["南明区", "观山湖区"]),
        ("遵义市", ["红花岗区", "播州区"]),
    ]),
    ("黑龙江省", "230000", 0.013, [
        ("哈尔滨市", ["南岗区", "道里区"]),
        ("大庆市", ["萨尔图区", "让胡路区"]),
    ]),
    ("吉林省", "220000", 0.012, [
        ("长春市", ["南关区", "朝阳区"]),
        ("吉林市", ["昌邑区", "船营区"]),
    ]),
    ("新疆维吾尔自治区", "650000", 0.011, [
        ("乌鲁木齐市", ["天山区", "沙依巴克区"]),
        ("昌吉回族自治州", ["昌吉市", "阜康市"]),
    ]),
    ("甘肃省", "620000", 0.010, [
        ("兰州市", ["城关区", "安宁区"]),
        ("天水市", ["秦州区", "麦积区"]),
    ]),
    ("海南省", "460000", 0.008, [
        ("海口市", ["龙华区", "美兰区"]),
        ("三亚市", ["吉阳区", "天涯区"]),
    ]),
    ("宁夏回族自治区", "640000", 0.006, [
        ("银川市", ["兴庆区", "金凤区"]),
        ("吴忠市", ["利通区", "青铜峡市"]),
    ]),
    ("青海省", "630000", 0.004, [
        ("西宁市", ["城中区", "湟中区"]),
        ("海东市", ["乐都区", "平安区"]),
    ]),
    ("西藏自治区", "540000", 0.002, [
        ("拉萨市", ["城关区", "堆龙德庆区"]),
        ("日喀则市", ["桑珠孜区", "江孜县"]),
    ]),
    ("中国香港", "810000", 0.004, [
        ("香港岛", ["中西区", "湾仔区"]),
        ("九龙", ["油尖旺区", "九龙城区"]),
    ]),
    ("中国澳门", "820000", 0.001, [
        ("澳门半岛", ["花地玛堂区", "大堂区"]),
        ("氹仔", ["嘉模堂区", "路氹城"]),
    ]),
    ("中国台湾", "710000", 0.006, [
        ("台北市", ["中正区", "信义区"]),
        ("高雄市", ["鼓山区", "左营区"]),
    ]),
]


def _jitter(seed: str, span: float = 4.0) -> float:
    """确定性抖动，范围约 [-span, span]，让各区指标不完全相同。"""
    return (zlib.crc32(seed.encode("utf-8")) % 1000 / 1000.0 - 0.5) * 2 * span


def _weights(names: List[str]) -> List[float]:
    """按名称生成确定性权重并归一化。"""
    raw = [1.0 + (zlib.crc32(n.encode("utf-8")) % 60) / 100.0 for n in names]
    total = sum(raw)
    return [w / total for w in raw]


def _make_stats(recovery: float, production: float, seed: str) -> Dict[str, object]:
    return {
        "回收量(万吨)": round(recovery, 2),
        "纸及纸板产量(万吨)": round(production, 2),
        "回收率(%)": round(51.1 + _jitter(seed + "r"), 1),
        "利用率(%)": round(51.6 + _jitter(seed + "u"), 1),
        "回收企业数(家)": max(1, int(round(recovery * 0.55))),
        "从业人员(人)": max(10, int(round(recovery * 85))),
    }


def _build() -> Dict[str, object]:
    total_r = NATIONAL_STATS["回收量(万吨)"]
    total_p = NATIONAL_STATS["纸及纸板产量(万吨)"]
    raw_w = [p[2] for p in _RAW]
    wsum = sum(raw_w)

    provinces = []
    for pname, pcode, weight, cities in _RAW:
        pw = weight / wsum
        p_r, p_p = total_r * pw, total_p * pw
        city_ws = _weights([c[0] for c in cities])
        city_nodes = []
        for ci, ((cname, counties), cw) in enumerate(zip(cities, city_ws)):
            c_r, c_p = p_r * cw, p_p * cw
            d_ws = _weights(counties)
            county_nodes = []
            for di, (dname, dw) in enumerate(zip(counties, d_ws)):
                county_nodes.append({
                    "code": f"{pcode}-C{ci + 1}-D{di + 1}",
                    "name": dname,
                    "level": "county",
                    "parent": f"{pcode}-C{ci + 1}",
                    "stats": _make_stats(c_r * dw, c_p * dw, pcode + cname + dname),
                    "provenance": PROVENANCE_MODEL,
                })
            city_nodes.append({
                "code": f"{pcode}-C{ci + 1}",
                "name": cname,
                "level": "city",
                "parent": pcode,
                "stats": _make_stats(c_r, c_p, pcode + cname),
                "provenance": PROVENANCE_MODEL,
                "children": county_nodes,
            })
        provinces.append({
            "code": pcode,
            "name": pname,
            "level": "province",
            "parent": "CN",
            "stats": _make_stats(p_r, p_p, pcode + pname),
            "provenance": PROVENANCE_MODEL,
            "children": city_nodes,
        })

    return {
        "code": "CN",
        "name": "全国",
        "level": "national",
        "parent": None,
        "stats": dict(NATIONAL_STATS),
        "provenance": PROVENANCE_OFFICIAL,
        "children": provinces,
    }


ROOT = _build()

_INDEX: Dict[str, Dict[str, object]] = {}


def _index(node: Dict[str, object]) -> None:
    _INDEX[node["code"]] = node  # type: ignore[index]
    for child in node.get("children", []):  # type: ignore[union-attr]
        _index(child)


_index(ROOT)


def get_node(code: str) -> Optional[Dict[str, object]]:
    return _INDEX.get(code)


def get_children(code: str) -> List[Dict[str, object]]:
    node = _INDEX.get(code)
    return list(node.get("children", [])) if node else []  # type: ignore[union-attr]


def breadcrumb(code: str) -> List[Dict[str, str]]:
    path: List[Dict[str, str]] = []
    node = _INDEX.get(code)
    while node:
        path.append({"code": node["code"], "name": node["name"]})  # type: ignore[arg-type]
        parent = node.get("parent")  # type: ignore[union-attr]
        node = _INDEX.get(parent) if parent else None
    return list(reversed(path))


def find(name: str) -> Optional[Dict[str, object]]:
    """按名称查找区域：先精确匹配，再包含匹配。"""
    if not name:
        return None
    for node in _INDEX.values():
        if node["name"] == name:
            return node
    for node in _INDEX.values():
        n = str(node["name"])
        if n and (n in name or name in n):
            return node
    return None


def summary(code: str = "CN") -> str:
    node = get_node(code)
    if not node:
        return "未找到该区域。"
    stats = node["stats"]
    lines = [f"【{node['name']}】废纸回收统计（{node['provenance']}）"]
    for key, value in stats.items():  # type: ignore[union-attr]
        lines.append(f"- {key}：{value}")
    children = get_children(code)
    if children:
        lines.append(f"下辖 {len(children)} 个区域，可在界面中逐级下钻。")
    return "\n".join(lines)


def tree() -> Dict[str, object]:
    def light(node: Dict[str, object]) -> Dict[str, object]:
        return {
            "code": node["code"],
            "name": node["name"],
            "level": node["level"],
            "children": [light(c) for c in node.get("children", [])],  # type: ignore[union-attr]
        }

    return light(ROOT)


def export_xlsx(code: str = "CN") -> bytes:
    """导出指定区域的下级统计为 Excel（.xlsx）。"""
    from io import BytesIO

    from openpyxl import Workbook

    node = get_node(code) or ROOT
    children = get_children(str(node["code"]))
    rows = children if children else [node]

    wb = Workbook()
    ws = wb.active
    ws.title = "区域统计"
    headers = [
        "区域", "层级", "回收量(万吨)", "纸及纸板产量(万吨)",
        "回收率(%)", "利用率(%)", "回收企业数(家)", "从业人员(人)", "数据来源",
    ]
    ws.append(headers)
    for r in rows:
        s = r["stats"]  # type: ignore[index]
        ws.append([
            r["name"], r["level"],
            s.get("回收量(万吨)"), s.get("纸及纸板产量(万吨)"),
            s.get("回收率(%)"), s.get("利用率(%)"),
            s.get("回收企业数(家)"), s.get("从业人员(人)"),
            r["provenance"],
        ])
    if children:
        total_r = round(sum(float(c["stats"].get("回收量(万吨)", 0)) for c in children), 2)  # type: ignore[index]
        ws.append(["合计", "", total_r, "", "", "", "", "", ""])

    for col, width in zip("ABCDEFGHI", [14, 10, 16, 20, 10, 10, 14, 12, 44]):
        ws.column_dimensions[col].width = width

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
