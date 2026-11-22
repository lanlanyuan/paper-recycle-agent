"""排放因子库：全部取自国标附录 B，逐条带出处。

来源
----
《温室气体排放核算与报告要求 造纸和纸制品生产企业》(GB/T 报批稿)
附录 B「相关参数缺省值」表 B.1 / B.2 / B.3，以及正文 5.2.5.3。

表 B.1 的上标逐个对应原始出处：
    a 《中国能源统计年鉴 2013》
    b 《省级温室气体清单指南（试行）》
    c 《2006 年 IPCC 国家温室气体清单指南》
    d 行业经验数据

本模块**不编造任何因子**：每个数值都能指回上表或其出处。
电力因子国标正文要求「选用国家主管部门最近年份公布的数据」，
这里不硬编码一个可能过期的数值，而是暴露成可配置项并标注来源说明。
"""

from dataclasses import dataclass
from typing import Dict, Optional

# 排放因子来源体系（供界面逐条展示）
SOURCE_STD = "国标附录B（造纸核算标准 报批稿）"
SOURCE_ENERGY = "《中国能源统计年鉴 2013》（经国标附录B引用）"
SOURCE_PROV = "《省级温室气体清单指南（试行）》（经国标附录B引用）"
SOURCE_IPCC = "《2006年IPCC国家温室气体清单指南》（经国标附录B引用）"
SOURCE_EXP = "行业经验数据（经国标附录B引用）"
SOURCE_MEE = "生态环境部公布的全国电网平均排放因子（需按最新年份填入）"


@dataclass(frozen=True)
class FuelFactor:
    """一种化石燃料的参数（国标表 B.1）。"""

    key: str
    name: str
    unit: str  # 计量单位：t / 10^4 Nm3
    ncv: float  # 低位发热量 GJ/t 或 GJ/10^4Nm3
    cc: float  # 单位热值含碳量 tC/GJ
    of: float  # 碳氧化率
    ncv_source: str
    cc_source: str

    @property
    def ef(self) -> float:
        """二氧化碳排放因子 tCO2/GJ = CC × OF × 44/12（国标公式4）。"""
        return self.cc * self.of * 44.0 / 12.0

    def public(self) -> Dict[str, object]:
        return {
            "key": self.key,
            "name": self.name,
            "unit": self.unit,
            "ncv": self.ncv,
            "ncv_unit": "GJ/t" if self.unit == "t" else "GJ/10^4Nm3",
            "cc": self.cc,
            "of": self.of,
            "ef": round(self.ef, 6),
            "source": SOURCE_STD,
            "ncv_source": self.ncv_source,
            "cc_source": self.cc_source,
        }


# 国标表 B.1 常用化石燃料参数（选取造纸厂常见品种）
# 数值逐字取自 PDF 表 B.1；上标字母映射到上面的来源常量。
FUELS: Dict[str, FuelFactor] = {
    "anthracite": FuelFactor("anthracite", "无烟煤", "t", 26.7, 27.4e-3, 0.94,
                             SOURCE_IPCC, SOURCE_PROV),
    "bituminous": FuelFactor("bituminous", "烟煤", "t", 19.570, 26.1e-3, 0.93,
                             SOURCE_EXP, SOURCE_PROV),
    "lignite": FuelFactor("lignite", "褐煤", "t", 11.9, 28.0e-3, 0.96,
                          SOURCE_IPCC, SOURCE_PROV),
    "washed_coal": FuelFactor("washed_coal", "洗精煤", "t", 26.334, 25.41e-3, 0.90,
                              SOURCE_ENERGY, SOURCE_PROV),
    "coke": FuelFactor("coke", "焦炭", "t", 28.435, 29.5e-3, 0.93,
                       SOURCE_ENERGY, SOURCE_PROV),
    "petroleum_coke": FuelFactor("petroleum_coke", "石油焦", "t", 32.5, 27.5e-3, 1.00,
                                 SOURCE_IPCC, SOURCE_PROV),
    "fuel_oil": FuelFactor("fuel_oil", "燃料油", "t", 41.816, 21.1e-3, 0.98,
                           SOURCE_ENERGY, SOURCE_PROV),
    "diesel": FuelFactor("diesel", "柴油", "t", 42.652, 20.2e-3, 0.98,
                         SOURCE_ENERGY, SOURCE_PROV),
    "gasoline": FuelFactor("gasoline", "汽油", "t", 43.070, 18.9e-3, 0.98,
                           SOURCE_ENERGY, SOURCE_PROV),
    "lng": FuelFactor("lng", "液化天然气", "t", 44.2, 17.2e-3, 0.98,
                      SOURCE_IPCC, SOURCE_PROV),
    "lpg": FuelFactor("lpg", "液化石油气", "t", 50.179, 17.2e-3, 0.98,
                      SOURCE_ENERGY, SOURCE_PROV),
    "natural_gas": FuelFactor("natural_gas", "天然气", "10^4Nm3", 389.31, 15.3e-3, 0.99,
                              SOURCE_ENERGY, SOURCE_PROV),
}


def fuel(key: str) -> FuelFactor:
    """取燃料因子，未知 key 抛 ValueError。"""
    if key not in FUELS:
        raise ValueError("未知燃料：%s" % key)
    return FUELS[key]


# 过程排放：石灰石分解因子（国标表 B.2）
LIMESTONE_EF = 0.405  # tCO2/t
LIMESTONE_EF_SOURCE = "国标附录B 表B.2（行业经验数据）"

# 废水厌氧处理（国标表 B.3）
CH4_MAX = 0.25  # tCH4/kgCOD 最大生产能力
CH4_CORRECTION = 0.5  # 甲烷修正因子
WAWWATER_SOURCE = "国标附录B 表B.3（行业经验数据）"
GWP_CH4 = 21  # CH4 的全球变暖潜势（100年），国标正文用于折算 CO2e

# 热力缺省因子（国标正文 5.2.5.3）
HEAT_EF_DEFAULT = 0.11  # tCO2/GJ
HEAT_EF_SOURCE = "国标正文 5.2.5.3 缺省值（也可取主管部门最新公布数据）"

# 电力因子：国标要求用主管部门最近年份数据，不内置可能过期的数值。
# 默认留空，由用户在界面/配置里填；填了必须同时填来源年份。
ELECTRIC_EF_DEFAULT: Optional[float] = None
ELECTRIC_EF_SOURCE = SOURCE_MEE

# 生物质：国标口径下生物质燃烧的 CO2 不计入（碳中性假设），
# 但 CH4 / N2O 需按实际排放因子计入。这里只做口径说明，不做数值假设。
BIOMASS_NOTE = (
    "生物质燃料（如黑液、树皮、废纸渣）燃烧产生的 CO2 按碳中性不计入化石排放；"
    "其 CH4 / N2O 排放如有数据应单独计入（国标 4.2.1 注）。"
)


def all_factors() -> Dict[str, object]:
    """给界面的完整因子表（含出处）。"""
    return {
        "fuels": [f.public() for f in FUELS.values()],
        "limestone": {"ef": LIMESTONE_EF, "unit": "tCO2/t", "source": LIMESTONE_EF_SOURCE},
        "wastewater": {
            "ch4_max": CH4_MAX, "correction": CH4_CORRECTION,
            "gwp_ch4": GWP_CH4, "source": WAWWATER_SOURCE,
        },
        "heat": {"ef": HEAT_EF_DEFAULT, "unit": "tCO2/GJ", "source": HEAT_EF_SOURCE},
        "electric": {
            "ef": ELECTRIC_EF_DEFAULT, "unit": "tCO2/MWh",
            "source": ELECTRIC_EF_SOURCE,
            "note": "国标要求取主管部门最近年份公布值，请填写并标注年份",
        },
        "biomass_note": BIOMASS_NOTE,
        "formula": {
            "fuel_ef": "EF = CC × OF × 44/12（国标公式4）",
            "fuel_ad": "AD = FC × NCV（国标公式3）",
            "fuel_emission": "E燃烧 = Σ(AD_i × EF_i)（国标公式2）",
            "process": "E过程 = L × EF石灰（国标公式5）",
            "total": "E总 = 燃烧 + 过程 + 废水CH4 + 购入电/热 − 输出电/热（国标公式1）",
        },
    }
