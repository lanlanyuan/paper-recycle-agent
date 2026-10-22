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
