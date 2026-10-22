# 废纸回收 Agent 对话助手 · 代码清单

> 本文档由 `gen_code_listing.py` 自动生成，内容与仓库源码保持一致。

## 项目简介

纯标准库实现的废纸回收助手：分类、估价、对话；接入《中国造纸年鉴》/行业报告数据；支持国家→省→市→县区四级区域统计、Excel 导出、Web 图形界面与语音输入。

## 如何运行

```bash
pip install -r requirements.txt
PYTHONPATH=src pytest -q            # 跑测试
python run.py                        # 图形界面 http://localhost:8000
```

## 项目元信息

### pyproject.toml

_pyproject.toml_

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "paper-recycle-agent"
version = "1.1.0"
description = "废纸回收 Agent 对话助手：分类、估价与交互（纯标准库）"
readme = "README.md"
requires-python = ">=3.9"
license = { text = "MIT" }
authors = [{ name = "梁湘瑶 / 阿岩" }]
keywords = ["recycling", "paper", "agent", "cli"]

[project.scripts]
paper-recycle-agent = "paper_recycle_agent.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

### requirements.txt

_requirements.txt_

```txt
# 运行时依赖：无（核心包仅使用 Python 标准库）
# 开发 / 测试 / 图形界面依赖见下方注释
pytest>=7.0          # 单元测试（CI 使用）
fastapi>=0.110       # 图形界面 / HTTP 对话服务（app/server.py）
uvicorn>=0.29        # 运行 FastAPI 服务：uvicorn app.server:app --reload
openpyxl>=3.1        # 导出 Excel（/export.xlsx）
```

### .github/workflows/ci.yml

_.github/workflows/ci.yml_

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.11"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        env:
          PYTHONPATH: src
        run: pytest -q
```

## 启动入口

### run.py（读取 PORT 启动）

_run.py_

```python
"""统一启动入口：读取 PORT 环境变量并启动 FastAPI 服务。

本地：python run.py            （默认 8000）
部署：平台注入 PORT，python run.py
"""

import os
import sys
from pathlib import Path

# 让 src/ 下的核心包可被导入
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import uvicorn  # noqa: E402

from app.server import app as fastapi_app  # noqa: E402


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port)
```

## 核心包 src/paper_recycle_agent

### __init__.py

_src/paper_recycle_agent/__init__.py_

```text
"""废纸回收 Agent 对话助手。"""

from . import agent, classifier, knowledge, pricing
from .agent import respond

__version__ = "1.1.0"

__all__ = ["agent", "classifier", "knowledge", "pricing", "respond"]
```

### knowledge.py（知识库）

_src/paper_recycle_agent/knowledge.py_

```text
"""废纸回收知识库：分类规则与回收指引数据。

所有分类规则集中在此，便于后续维护与扩展。
"""

from dataclasses import dataclass
from typing import List


@dataclass
class PaperCategory:
    """单个废纸类别的定义。"""

    key: str
    name: str
    aliases: List[str]
    recyclable: bool
    value_per_kg: float  # 参考回收价（元/kg），不可回收为 0.0
    tips: str


# 类别顺序：可回收在前、不可回收在后，便于阅读与优先级排序。
CATEGORIES: List[PaperCategory] = [
    PaperCategory(
        key="office",
        name="办公用纸",
        aliases=["打印纸", "复印纸", "a4", "文件", "办公纸", "办公用纸", "白纸", "资料"],
        recyclable=True,
        value_per_kg=1.1,
        tips="订书钉可保留，回形针建议取下；涉密文件请碎纸后交专业渠道。",
    ),
    PaperCategory(
        key="cardboard",
        name="纸箱/纸板",
        aliases=["纸箱", "纸板", "瓦楞纸", "快递箱", "纸盒", "包装盒"],
        recyclable=True,
        value_per_kg=0.9,
        tips="清空内容物、压平折叠，胶带尽量撕掉。",
    ),
    PaperCategory(
        key="newspaper",
        name="报纸",
        aliases=["报纸", "新闻纸", "旧报"],
        recyclable=True,
        value_per_kg=0.8,
        tips="去除塑料薄膜与装订后可整捆回收。",
    ),
    PaperCategory(
        key="magazine",
        name="书刊杂志",
        aliases=["杂志", "期刊", "书本", "书", "刊物"],
        recyclable=True,
        value_per_kg=0.7,
        tips="胶装书刊可整体回收；塑料封膜请分离。",
    ),
    PaperCategory(
        key="kraft",
        name="牛皮纸",
        aliases=["牛皮纸", "牛皮纸箱", "牛皮袋"],
        recyclable=True,
        value_per_kg=0.85,
        tips="干净干燥即可回收。",
    ),
    PaperCategory(
        key="tissue",
        name="纸巾/卫生纸",
        aliases=["纸巾", "卫生纸", "餐巾纸", "湿巾"],
        recyclable=False,
        value_per_kg=0.0,
        tips="已被污染且纤维过短，不可进入再生纸系统，请作为其他垃圾处理。",
    ),
    PaperCategory(
        key="thermal",
        name="热敏/涂布纸",
        aliases=["热敏纸", "小票", "收银条", "传真纸", "涂布纸"],
        recyclable=False,
        value_per_kg=0.0,
        tips="表面含显色涂层，不可回收，请作为其他垃圾。",
    ),
    PaperCategory(
        key="contaminated",
        name="污染/厨余纸",
        aliases=["油纸", "沾油", "披萨盒", "厨房纸巾", "被污染"],
        recyclable=False,
        value_per_kg=0.0,
        tips="油污、食物残渣会破坏纸浆，不可回收。",
    ),
    PaperCategory(
        key="composite",
        name="复合包装",
        aliases=["利乐包", "纸塑铝", "牛奶盒", "饮料纸盒"],
        recyclable=False,
        value_per_kg=0.0,
        tips="属纸塑铝复合材质，需专用回收线，请勿投入普通废纸。",
    ),
]

# 扁平化的「类别-关键词」索引，供分类引擎快速匹配。
KEYWORD_INDEX = [(cat, kw) for cat in CATEGORIES for kw in cat.aliases]
```

### data.py（年鉴/行业数据）

_src/paper_recycle_agent/data.py_

```text
"""中国造纸年鉴 / 行业报告中的废纸分类与行业数据。

所有数据均标注来源，便于核验：
- GB/T 20811-2018《废纸分类技术要求》（国家市场监督管理总局、中国国家标准化管理委员会，
  2018-12-28 发布，2019-07-01 实施）：将废纸分为 8 大类 42 小类。
- 中国造纸协会《中国造纸工业2024年度报告》（2025-05-07 发布）：废纸回收利用核心指标。
- 生态环境部等《关于全面禁止进口固体废物有关事项的公告》（2021-01-01 施行）：废纸进口清零。
"""

from typing import Dict, List

# ---- 废纸分类（GB/T 20811-2018，共 8 大类 42 小类；此处列 8 大类及代表性小类）----
CATEGORIES_8: List[Dict[str, object]] = [
    {
        "code": "1",
        "name": "废瓦楞纸箱类",
        "examples": ["牛皮挂面旧瓦楞纸箱(101)", "新瓦楞纸箱(102)", "混合旧瓦楞纸箱(104)"],
        "note": "杂质≤1.0%、不可利用物≤3.0%；新箱更严。回收用于箱板纸/瓦楞原纸。",
    },
    {
        "code": "2",
        "name": "废纸盒及废卡纸类",
        "examples": ["工厂回收白色纸盒切边(201)"],
        "note": "白色纸盒切边杂质≤0.25%、不可利用物≤1.0%。",
    },
    {
        "code": "3",
        "name": "包装废纸类",
        "examples": ["白色包装纸(301)", "牛皮包装纸(302)"],
        "note": "不应有杂质，不可利用物≤0.5%。",
    },
    {
        "code": "4",
        "name": "废新闻纸类",
        "examples": ["新闻纸切边(401)", "未出售报纸(402)"],
        "note": "不应有杂质，不可利用物≤0.5%。",
    },
    {
        "code": "5",
        "name": "废书刊杂志类",
        "examples": ["白色未涂布纸切边(501)", "混合旧书刊杂志(505)"],
        "note": "混合旧书刊杂质≤0.5%、不可利用物≤2.5%。",
    },
    {
        "code": "6",
        "name": "办公废纸类",
        "examples": ["混合办公废纸(606)"],
        "note": "混合办公废纸杂质≤0.5%、不可利用物≤2.5%。",
    },
    {
        "code": "7",
        "name": "特种废纸类",
        "examples": ["白色湿强废纸(701)", "工厂使用过的特种废纸(709)"],
        "note": "部分品种不应有杂质；湿强废纸杂质≤0.5%、不可利用物≤2.0%。",
    },
    {
        "code": "8",
        "name": "混合废纸类",
        "examples": [
            "非纸箱纸盒类混合废纸(801)",
            "纸箱纸盒类混合废纸(802)",
            "混合废纸(803)",
        ],
        "note": "803 为不鼓励贸易类别；杂质≤1.0%~1.5%。",
    },
]

# 通用质量要求（GB/T 20811-2018）
QUALITY_RULES: Dict[str, str] = {
    "水分": "实测水分应 ≤ 12%（或按合同规定）",
    "质量差百分率": "应 ≥ -1.0%",
    "包装物质量": "应不大于对应实测质量的 1.0%",
}

# ---- 行业数据（中国造纸协会《中国造纸工业2024年度报告》）----
INDUSTRY_DATA: List[Dict[str, object]] = [
    {"year": 2024, "指标": "国内回收废纸总量", "数值": "6971 万吨", "同比": "+3.47%"},
    {"year": 2024, "指标": "废纸回收率", "数值": "51.1%", "同比": "—"},
    {"year": 2024, "指标": "废纸利用率", "数值": "51.6%", "同比": "—"},
    {"year": 2024, "指标": "纸及纸板产量", "数值": "13625 万吨", "同比": "+5.09%"},
    {"year": 2024, "指标": "全行业营业收入", "数值": "1.46 万亿元", "同比": "+3.88%"},
    {"year": 2024, "指标": "利润总额", "数值": "520 亿元", "同比": "+5.23%"},
    {"year": 2024, "指标": "废纸进口量", "数值": "基本清零（≈0）", "同比": "禁废令后维持低位"},
]

SOURCES: List[str] = [
    "GB/T 20811-2018《废纸分类技术要求》（国家市场监督管理总局、中国国家标准化管理委员会）",
    "中国造纸协会《中国造纸工业2024年度报告》（2025-05-07 发布）",
    "生态环境部等《关于全面禁止进口固体废物有关事项的公告》（2021-01-01 施行）",
]


def get_categories() -> List[Dict[str, object]]:
    """返回 GB/T 20811-2018 的 8 大类废纸分类。"""
    return CATEGORIES_8


def get_industry_data(year: int = 2024) -> List[Dict[str, object]]:
    """返回指定年份的行业数据。"""
    return [d for d in INDUSTRY_DATA if d["year"] == year]


def summary_text() -> str:
    """生成一段人类可读的「分类 + 行业数据」摘要。"""
    lines = ["【废纸分类（GB/T 20811-2018，共 8 大类 42 小类）】"]
    for c in CATEGORIES_8:
        lines.append(f"{c['code']}. {c['name']}：{', '.join(c['examples'])}")
    lines.append("")
    lines.append("【2024 年废纸回收利用（中国造纸协会年度报告）】")
    for d in get_industry_data(2024):
        lines.append(f"- {d['指标']}：{d['数值']}（{d['同比']}）")
    lines.append("")
    lines.append("数据来源：" + "；".join(SOURCES))
    return "\n".join(lines)
```

### regions.py（国家→省→市→县区统计）

_src/paper_recycle_agent/regions.py_

```text
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
```

### classifier.py（分类引擎）

_src/paper_recycle_agent/classifier.py_

```text
"""废纸分类引擎：基于关键词与规则的轻量级分类。"""

from typing import Dict, List

from .knowledge import CATEGORIES, KEYWORD_INDEX, PaperCategory


def classify(text: str) -> Dict[str, object]:
    """根据用户输入文本判断废纸类别。

    返回字典包含：matched / category / key / recyclable / value_per_kg /
    tips / confidence / message。
    """
    if not text or not text.strip():
        return _empty()

    t = text.lower()
    hits: List[PaperCategory] = []
    for cat, kw in KEYWORD_INDEX:
        if kw.lower() in t:
            hits.append(cat)

    if not hits:
        # 关键词未命中时，尝试用类别主键兜底（如「cardboard」）。
        for cat in CATEGORIES:
            if cat.key in t:
                hits.append(cat)

    if not hits:
        return {
            "matched": False,
            "category": None,
            "recyclable": None,
            "confidence": 0.0,
            "message": "未能识别废纸类型，请描述更具体的物品（如：纸箱、报纸、纸巾、热敏小票）。",
        }

    cat = _prioritize(hits)
    confidence = 0.9 if len(hits) == 1 else 0.7
    return {
        "matched": True,
        "category": cat.name,
        "key": cat.key,
        "recyclable": cat.recyclable,
        "value_per_kg": cat.value_per_kg,
        "tips": cat.tips,
        "confidence": confidence,
        "message": _message(cat),
    }


def _prioritize(cats: List[PaperCategory]) -> PaperCategory:
    """多命中时，优先展示可回收且价值更高的类别。"""
    return sorted(cats, key=lambda c: (not c.recyclable, -c.value_per_kg))[0]


def _message(cat: PaperCategory) -> str:
    if cat.recyclable:
        return (
            f"识别为【{cat.name}】，可回收，参考回收价约 "
            f"{cat.value_per_kg} 元/kg。{cat.tips}"
        )
    return f"识别为【{cat.name}】，暂不可回收。{cat.tips}"


def _empty() -> Dict[str, object]:
    return {
        "matched": False,
        "category": None,
        "recyclable": None,
        "confidence": 0.0,
        "message": "请输入要查询的废纸物品。",
    }


def list_categories() -> List[Dict[str, object]]:
    """返回全部类别的概览，供 CLI / 文档使用。"""
    return [
        {
            "key": c.key,
            "name": c.name,
            "recyclable": c.recyclable,
            "value_per_kg": c.value_per_kg,
        }
        for c in CATEGORIES
    ]
```

### pricing.py（估价）

_src/paper_recycle_agent/pricing.py_

```text
"""回收估价：根据类别与重量估算回收价值。"""

from typing import Dict

from .classifier import classify


def estimate(text: str, weight_kg: float) -> Dict[str, object]:
    """估算指定废纸物品在给定重量下的回收价值。

    weight_kg 为负时按 0 处理。
    """
    result = classify(text)
    if not result["matched"]:
        return {
            **result,
            "weight_kg": weight_kg,
            "estimated_value": 0.0,
        }

    value_per_kg = float(result["value_per_kg"])  # type: ignore
    if not result["recyclable"]:
        return {
            "matched": True,
            "category": result["category"],
            "recyclable": False,
            "weight_kg": weight_kg,
            "estimated_value": 0.0,
            "message": (
                f"【{result['category']}】不可回收，无回收价值。"
                f"{result.get('tips', '')}"
            ),
        }

    value = round(value_per_kg * max(weight_kg, 0.0), 2)
    return {
        "matched": True,
        "category": result["category"],
        "recyclable": True,
        "weight_kg": weight_kg,
        "value_per_kg": value_per_kg,
        "estimated_value": value,
        "message": (
            f"【{result['category']}】{weight_kg} kg，"
            f"预计回收价值约 {value} 元。"
        ),
    }
```

### agent.py（对话引擎）

_src/paper_recycle_agent/agent.py_

```text
"""对话引擎：把分类 / 估价能力包装成自然语言回复。"""

import re
from typing import Dict, Optional

from . import classifier, data, pricing, regions

_GREETING = {"你好", "您好", "hi", "hello", "在吗", "在么"}
_HELP = {"帮助", "help", "怎么用", "功能", "能做什么", "用法"}
_DATA = {"年鉴", "行业数据", "进口", "标准", "分类标准", "gb/t", "20811",
         "造纸", "废纸分几类", "废纸分类"}
_REGION = {"回收量", "利用率", "回收率", "统计", "企业数", "从业人员", "数据"}


def _extract_weight(text: str) -> Optional[float]:
    """从文本中提取重量，支持 kg / 公斤 / 千克 / 斤（斤自动折算为 kg）。"""
    m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|公斤|千克|斤)", text, re.IGNORECASE)
    if not m:
        return None
    val = float(m.group(1))
    if m.group(2) == "斤":
        val = val / 2.0
    return val


def respond(user_input: str) -> str:
    """根据用户输入返回一句自然语言回复。"""
    text = (user_input or "").strip()
    if not text:
        return "请输入你想查询的废纸物品，例如「纸箱 2kg 能卖多少钱」。"

    low = text.lower()
    if low in _GREETING:
        return (
            "你好，我是废纸回收助手 🪨。告诉我废纸物品名称"
            "（如纸箱、报纸、纸巾），或加上重量估算回收价值。输入「帮助」查看用法。"
        )
    if any(k in text for k in _HELP):
        return _help_text()

    # 年鉴 / 行业数据 / 分类标准类查询
    if any(k in text for k in _DATA):
        return data.summary_text()

    # 区域分层统计查询（国家 / 省 / 市 / 县区）
    if any(k in text for k in _REGION):
        node = regions.find(text)
        return regions.summary(node["code"] if node else "CN")

    weight = _extract_weight(text)
    if weight is not None:
        return pricing.estimate(text, weight)["message"]

    # 默认走分类查询
    return classifier.classify(text)["message"]


def _help_text() -> str:
    return "\n".join(
        [
            "废纸回收助手使用说明：",
            "1) 查询是否可回收：直接说物品名，如「纸箱」「报纸」「纸巾」。",
            "2) 估算回收价值：物品名 + 重量，如「办公用纸 3kg」「纸箱 5 斤」。",
            "3) 查看全部类别：输入「类别」。",
            "4) 年鉴与行业数据：输入「年鉴」「行业数据」「废纸分类」。",
            "5) 区域分层统计：输入省/市/县名 + 「回收量」，如「广东省回收量」。",
        ]
    )
```

### cli.py（命令行）

_src/paper_recycle_agent/cli.py_

```text
"""命令行交互入口。"""

import argparse
import sys

from . import agent, classifier, data, pricing


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="paper-recycle-agent", description="废纸回收 Agent 对话助手"
    )
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("chat", help="进入交互式对话")
    c = sub.add_parser("classify", help="分类查询")
    c.add_argument("text", help="物品描述")
    pr = sub.add_parser("price", help="估价")
    pr.add_argument("text", help="物品描述")
    pr.add_argument("weight", type=float, help="重量(kg)")
    sub.add_parser("categories", help="列出所有类别")
    sub.add_parser("info", help="废纸分类标准与行业数据")
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "chat":
        _chat_loop()
    elif args.cmd == "classify":
        print(classifier.classify(args.text)["message"])
    elif args.cmd == "price":
        print(pricing.estimate(args.text, args.weight)["message"])
    elif args.cmd == "categories":
        for c in classifier.list_categories():
            tag = "可回收" if c["recyclable"] else "不可回收"
            print(f"- {c['name']} [{tag}]")
    elif args.cmd == "info":
        print(data.summary_text())
    else:
        _chat_loop()
    return 0


def _chat_loop() -> None:
    print("废纸回收助手（输入 exit 退出）")
    while True:
        try:
            line = input("你: ")
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break
        if line.strip().lower() in {"exit", "quit", "退出"}:
            print("再见。")
            break
        print("助手:", agent.respond(line))


if __name__ == "__main__":
    sys.exit(main())
```

## 图形界面 app

### server.py（FastAPI 服务）

_app/server.py_

```text
"""FastAPI 服务：提供废纸回收 Agent 的图形界面与对话接口。

运行：uvicorn app.server:app --reload
接口：
  GET  / 与 /index.html -> 图形界面（聊天 + 年鉴/行业数据面板）
  GET  /api/info        -> {categories, industry, quality, sources}
  POST /chat            -> {"reply": "..."}
  GET  /health          -> {"status": "ok"}
"""

import io
from pathlib import Path

from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from paper_recycle_agent import data as yearbook
from paper_recycle_agent import regions
from paper_recycle_agent import respond

app = FastAPI(title="废纸回收 Agent 对话助手")

_STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


class ChatReq(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    # 避免浏览器请求 favicon 时产生 404 噪音
    return Response(status_code=204)


@app.get("/api/info")
def info() -> dict:
    return {
        "categories": yearbook.get_categories(),
        "industry": yearbook.get_industry_data(2024),
        "quality": yearbook.QUALITY_RULES,
        "sources": yearbook.SOURCES,
    }


def _shallow(node: dict) -> dict:
    return {k: v for k, v in node.items() if k != "children"}


@app.get("/api/regions")
def regions_tree() -> dict:
    return regions.tree()


@app.get("/api/stats")
def stats(code: str = "CN") -> dict:
    node = regions.get_node(code) or regions.get_node("CN")
    children = regions.get_children(str(node["code"]))
    return {
        "node": _shallow(node),
        "children": [_shallow(c) for c in children],
        "breadcrumb": regions.breadcrumb(str(node["code"])),
    }


@app.get("/export.xlsx")
def export(code: str = "CN") -> StreamingResponse:
    node = regions.get_node(code) or regions.get_node("CN")
    content = regions.export_xlsx(str(node["code"]))
    return StreamingResponse(
        io.BytesIO(content),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": 'attachment; filename="paper_recycle_stats.xlsx"'},
    )


@app.post("/chat")
def chat(req: ChatReq) -> dict:
    return {"reply": respond(req.message)}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

### static/index.html（聊天+区域统计界面）

_app/static/index.html_

```text
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>废纸回收 Agent 对话助手</title>
<style>
  :root {
    --bg: #f5f7fa; --panel: #ffffff; --ink: #1f2329; --muted: #6b7280;
    --brand: #2f7d4f; --brand-soft: #e8f3ec; --border: #e5e7eb;
    --user-bubble: #2f7d4f; --bot-bubble: #eef1f5;
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
         background: var(--bg); color: var(--ink); height: 100vh; display: flex; flex-direction: column; }
  header { background: var(--brand); color: #fff; padding: 12px 20px; font-size: 17px; font-weight: 600;
           display: flex; align-items: center; gap: 10px; }
  header .sub { font-size: 12px; font-weight: 400; opacity: .85; }
  .layout { flex: 1; display: flex; min-height: 0; }
  .chat { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  .messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
  .msg { max-width: 80%; padding: 9px 13px; border-radius: 13px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; font-size: 14px; }
  .msg.bot { background: var(--bot-bubble); align-self: flex-start; border-bottom-left-radius: 4px; }
  .msg.user { background: var(--user-bubble); color: #fff; align-self: flex-end; border-bottom-right-radius: 4px; }
  .chips { display: flex; gap: 8px; flex-wrap: wrap; padding: 0 16px 8px; }
  .chip { background: var(--brand-soft); color: var(--brand); border: 1px solid #cfe6da; border-radius: 15px;
          padding: 5px 11px; font-size: 12px; cursor: pointer; }
  .chip:hover { background: #dcefe2; }
  .inputbar { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid var(--border); background: var(--panel); align-items: center; }
  .inputbar input { flex: 1; padding: 10px 13px; border: 1px solid var(--border); border-radius: 9px; font-size: 14px; outline: none; }
  .inputbar input:focus { border-color: var(--brand); }
  .inputbar button { background: var(--brand); color: #fff; border: none; border-radius: 9px; padding: 0 18px; height: 38px; font-size: 14px; cursor: pointer; }
  .inputbar button:disabled { opacity: .5; cursor: default; }
  #micBtn { background: #fff; color: var(--brand); border: 1px solid var(--border); width: 40px; padding: 0; font-size: 17px; }
  #micBtn.listening { background: #fde8e8; border-color: #f5b5b5; animation: pulse 1s infinite; }
  @keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(220,80,80,.4);} 70%{box-shadow:0 0 0 10px rgba(220,80,80,0);} 100%{box-shadow:0 0 0 0 rgba(220,80,80,0);} }
  .side { width: 440px; border-left: 1px solid var(--border); background: var(--panel); overflow-y: auto; padding: 14px 16px; }
  .side h3 { margin: 0 0 4px; font-size: 15px; color: var(--brand); }
  .side .hint { font-size: 11px; color: var(--muted); margin-bottom: 10px; line-height: 1.5; }
  .crumb { font-size: 13px; margin-bottom: 10px; display: flex; flex-wrap: wrap; align-items: center; gap: 2px; }
  .crumb-item { color: var(--brand); cursor: pointer; }
  .crumb-item:hover { text-decoration: underline; }
  .crumb .sep { color: var(--muted); }
  .summary { border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; margin-bottom: 12px; background: #fbfcfd; }
  .sum-name { font-weight: 700; font-size: 15px; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
  .badge { font-size: 11px; font-weight: 400; color: var(--brand); background: var(--brand-soft); border-radius: 10px; padding: 2px 8px; }
  .sum-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; }
  .sum-grid div { display: flex; justify-content: space-between; font-size: 12px; }
  .sum-grid span { color: var(--muted); }
  .sum-grid b { color: var(--ink); }
  .prov { font-size: 10px; color: var(--muted); margin-top: 8px; line-height: 1.4; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th, td { border-bottom: 1px solid var(--border); padding: 6px 6px; text-align: left; }
  th { background: var(--brand-soft); color: var(--brand); font-weight: 600; }
  tbody tr.row { cursor: pointer; }
  tbody tr.row:hover { background: #f2f8f4; }
  td.empty { color: var(--muted); text-align: center; padding: 14px 0; }
  .actions { display: flex; gap: 8px; margin: 10px 0 6px; }
  .actions button { flex: 1; height: 34px; border-radius: 8px; font-size: 13px; cursor: pointer; border: 1px solid var(--border); background: #fff; color: var(--ink); }
  .actions #exportBtn { background: var(--brand); color: #fff; border-color: var(--brand); }
  details.standards { margin-top: 12px; border-top: 1px dashed var(--border); padding-top: 8px; }
  details.standards summary { font-size: 12px; color: var(--muted); cursor: pointer; }
  .std-cat { border: 1px solid var(--border); border-radius: 8px; padding: 7px 9px; margin-top: 6px; font-size: 11px; }
  .std-cat .nm { font-weight: 600; font-size: 12px; }
  .std-cat .ex, .std-cat .nt { color: var(--muted); margin-top: 2px; }
  @media (max-width: 900px) { .side { display: none; } }
</style>
</head>
<body>
<header>🪨 废纸回收 Agent 对话助手 <span class="sub">四级区域统计 · 分类估价 · 语音输入 · Excel 导出</span></header>
<div class="layout">
  <div class="chat">
    <div class="messages" id="messages"></div>
    <div class="chips" id="chips"></div>
    <div class="inputbar">
      <button id="micBtn" title="语音输入（需 Chrome/Edge）">🎤</button>
      <input id="input" placeholder="说或输入：纸箱 2kg / 广东省回收量 / 废纸分类" onkeydown="if(event.key==='Enter')send()" />
      <button id="sendBtn" onclick="send()">发送</button>
    </div>
  </div>
  <aside class="side">
    <h3>区域废纸回收统计</h3>
    <div class="hint">点击表格中的区域可逐级下钻：全国 → 省 → 市 → 县区。国家级为官方口径，省市县为分层测算（可替换真实数据）。</div>
    <div class="crumb" id="crumb"></div>
    <div class="summary" id="summary"></div>
    <table id="statsTable">
      <thead><tr><th>区域</th><th>回收量(万吨)</th><th>回收率(%)</th><th>利用率(%)</th></tr></thead>
      <tbody></tbody>
    </table>
    <div class="actions">
      <button id="backBtn" onclick="goBack()">返回上一级</button>
      <button id="exportBtn" onclick="exportExcel()">导出 Excel</button>
    </div>
    <details class="standards">
      <summary>内部参考：行业标准（GB/T 20811-2018）</summary>
      <div id="standardsBody"></div>
    </details>
  </aside>
</div>

<script>
  const SUGGESTIONS = ["纸箱能回收吗", "办公用纸 3kg", "广东省回收量", "废纸分类", "全国统计"];
  const messagesEl = document.getElementById("messages");
  const chipsEl = document.getElementById("chips");
  const inputEl = document.getElementById("input");
  const sendBtn = document.getElementById("sendBtn");
  const micBtn = document.getElementById("micBtn");
  const LEVEL = { national: "国家", province: "省", city: "市", county: "县区" };

  let currentCode = "CN";
  let breadcrumb = [];

  function addMsg(text, who) {
    const div = document.createElement("div");
    div.className = "msg " + who;
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  SUGGESTIONS.forEach(s => {
    const c = document.createElement("span");
    c.className = "chip"; c.textContent = s;
    c.onclick = () => { inputEl.value = s; send(); };
    chipsEl.appendChild(c);
  });

  async function send() {
    const text = inputEl.value.trim();
    if (!text) return;
    addMsg(text, "user");
    inputEl.value = "";
    sendBtn.disabled = true;
    try {
      const res = await fetch("/chat", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      addMsg(data.reply, "bot");
    } catch (e) {
      addMsg("服务暂时不可用：" + e, "bot");
    } finally {
      sendBtn.disabled = false;
    }
  }

  function renderCrumb(items) {
    const el = document.getElementById("crumb");
    el.innerHTML = "";
    items.forEach((it, i) => {
      const a = document.createElement("span");
      a.className = "crumb-item"; a.textContent = it.name;
      a.onclick = () => loadStats(it.code);
      el.appendChild(a);
      if (i < items.length - 1) {
        const s = document.createElement("span"); s.className = "sep"; s.textContent = " / ";
        el.appendChild(s);
      }
    });
  }

  function renderSummary(node) {
    const s = node.stats;
    document.getElementById("summary").innerHTML =
      `<div class="sum-name">${node.name} <span class="badge">${LEVEL[node.level] || node.level}</span></div>
       <div class="sum-grid">
         <div><span>回收量</span><b>${s["回收量(万吨)"]} 万吨</b></div>
         <div><span>回收率</span><b>${s["回收率(%)"]}%</b></div>
         <div><span>利用率</span><b>${s["利用率(%)"]}%</b></div>
         <div><span>企业数</span><b>${s["回收企业数(家)"]}</b></div>
       </div>
       <div class="prov">${node.provenance}</div>`;
  }

  function renderTable(children) {
    const tb = document.querySelector("#statsTable tbody");
    tb.innerHTML = "";
    if (!children.length) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="4" class="empty">该区域为最末级（县区），无下级明细</td>`;
      tb.appendChild(tr);
      return;
    }
    children.forEach(c => {
      const tr = document.createElement("tr");
      tr.className = "row";
      tr.onclick = () => loadStats(c.code);
      tr.innerHTML = `<td>${c.name}</td><td>${c.stats["回收量(万吨)"]}</td>` +
                     `<td>${c.stats["回收率(%)"]}</td><td>${c.stats["利用率(%)"]}</td>`;
      tb.appendChild(tr);
    });
  }

  async function loadStats(code) {
    try {
      const res = await fetch(`/api/stats?code=${encodeURIComponent(code)}`);
      const data = await res.json();
      currentCode = data.node.code;
      breadcrumb = data.breadcrumb;
      renderCrumb(data.breadcrumb);
      renderSummary(data.node);
      renderTable(data.children);
    } catch (e) { /* ignore */ }
  }

  function goBack() {
    if (breadcrumb.length > 1) loadStats(breadcrumb[breadcrumb.length - 2].code);
  }

  function exportExcel() {
    window.location.href = `/export.xlsx?code=${encodeURIComponent(currentCode)}`;
  }

  async function loadInfo() {
    try {
      const res = await fetch("/api/info");
      const info = await res.json();
      const box = document.getElementById("standardsBody");
      info.categories.forEach(c => {
        const d = document.createElement("div");
        d.className = "std-cat";
        d.innerHTML = `<div class="nm">${c.code}. ${c.name}</div>` +
                      `<div class="ex">${c.examples.join("、")}</div>` +
                      `<div class="nt">${c.note}</div>`;
        box.appendChild(d);
      });
    } catch (e) { /* ignore */ }
  }

  // 语音输入（浏览器 Web Speech API，无需第三方）
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recog = null;
  if (SR) {
    recog = new SR();
    recog.lang = "zh-CN";
    recog.interimResults = false;
    recog.maxAlternatives = 1;
    recog.onresult = (e) => {
      const text = e.results[0][0].transcript;
      inputEl.value = text;
      send();
    };
    recog.onerror = () => micBtn.classList.remove("listening");
    recog.onend = () => micBtn.classList.remove("listening");
  }
  micBtn.onclick = () => {
    if (!recog) { alert("当前浏览器不支持语音输入，请用 Chrome / Edge 打开。"); return; }
    micBtn.classList.add("listening");
    try { recog.start(); } catch (e) { recog.stop(); }
  };

  addMsg("你好，我是废纸回收助手 🪨。可以问我废纸是否可回收、估算价值，或查询某个省/市/县区的回收统计。右侧可直接下钻并导出 Excel。", "bot");
  loadStats("CN");
  loadInfo();
</script>
</body>
</html>
```

## 单元测试 tests

### test_classifier.py

_tests/test_classifier.py_

```text
from paper_recycle_agent import classifier


def test_classify_cardboard():
    r = classifier.classify("我有一个快递纸箱")
    assert r["matched"] is True
    assert r["category"] == "纸箱/纸板"
    assert r["recyclable"] is True


def test_classify_tissue_not_recyclable():
    r = classifier.classify("用过的纸巾")
    assert r["recyclable"] is False


def test_classify_empty():
    r = classifier.classify("")
    assert r["matched"] is False


def test_classify_unknown():
    r = classifier.classify("塑料瓶")
    assert r["matched"] is False


def test_list_categories_nonempty():
    cats = classifier.list_categories()
    assert len(cats) >= 5
    assert any(c["recyclable"] for c in cats)
```

### test_pricing.py

_tests/test_pricing.py_

```text
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
```

### test_agent.py

_tests/test_agent.py_

```text
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
```

### test_data.py

_tests/test_data.py_

```text
from paper_recycle_agent import data


def test_eight_categories():
    cats = data.get_categories()
    assert len(cats) == 8
    assert all("name" in c and "examples" in c for c in cats)


def test_industry_2024_has_volume():
    rows = data.get_industry_data(2024)
    volume = [r for r in rows if r["指标"] == "国内回收废纸总量"]
    assert volume, "应存在废纸回收总量记录"
    assert "6971" in volume[0]["数值"]


def test_summary_text_mentions_standard():
    txt = data.summary_text()
    assert "GB/T 20811" in txt
    assert "6971" in txt


def test_quality_rules_present():
    assert "水分" in data.QUALITY_RULES
```

### test_regions.py

_tests/test_regions.py_

```text
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
```
