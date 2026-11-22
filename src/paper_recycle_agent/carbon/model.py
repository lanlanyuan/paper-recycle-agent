"""碳核算数据模型：活动数据输入 + 结果口径标注。

活动数据是**示例工厂的仿真输入**（不是真实工厂实测值），
用户可以逐项修改。每项都带 provenance，界面上明确显示「示例」。

数据量为一家中型新闻纸/包装纸厂的量级，用于演示计算链，
不对应任何真实企业。产量、能耗之间不强行追求行业精确的物料平衡——
仿真演示的目标是让「活动数据 × 排放因子 = 排放量」这条链可核查。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import factors

PROVENANCE_DEMO = "示例（仿真输入，非真实工厂）"
PROVENANCE_STD = "国标缺省值"


@dataclass
class FuelUse:
    """一种燃料的消耗量。"""

    key: str
    quantity: float  # 吨 或 10^4Nm3（按燃料单位）
    provenance: str = PROVENANCE_DEMO

    def public(self) -> Dict[str, object]:
        f = factors.fuel(self.key)
        return {
            "key": self.key,
            "name": f.name,
            "quantity": self.quantity,
            "unit": f.unit,
            "provenance": self.provenance,
        }


@dataclass
class ActivityData:
    """一家工厂一个核算年度的活动数据。"""

    year: int = 2024
    factory_name: str = "示例造纸厂"
    # 化石燃料消耗
    fuels: List[FuelUse] = field(default_factory=list)
    # 过程排放：石灰石消耗量（吨）。无制浆工艺可为 0。
    limestone_ton: float = 0.0
    # 废水厌氧处理：去除的有机物总量（吨 COD）、污泥清除有机物、甲烷回收（吨）
    wastewater_cod_removed: float = 0.0
    wastewater_cod_sludge: float = 0.0
    methane_recovered: float = 0.0
    # 外购 / 输出电力（MWh）
    electricity_purchased: float = 0.0
    electricity_exported: float = 0.0
    electric_ef: Optional[float] = None  # tCO2/MWh，None 表示未配置
    electric_ef_year: Optional[int] = None
    # 外购 / 输出热力（GJ）
    heat_purchased: float = 0.0
    heat_exported: float = 0.0
    # 产品产量（万吨），用于算单位产品碳强度
    paper_output_wan_ton: float = 0.0
    # 废纸回收量（万吨）——来自废纸回收 Agent，仅用于减排演示，不进国标边界
    wastepaper_recycled_wan_ton: float = 0.0
    provenance: str = PROVENANCE_DEMO

    def public(self) -> Dict[str, object]:
        return {
            "year": self.year,
            "factory_name": self.factory_name,
            "fuels": [f.public() for f in self.fuels],
            "limestone_ton": self.limestone_ton,
            "wastewater_cod_removed": self.wastewater_cod_removed,
            "wastewater_cod_sludge": self.wastewater_cod_sludge,
            "methane_recovered": self.methane_recovered,
            "electricity_purchased": self.electricity_purchased,
            "electricity_exported": self.electricity_exported,
            "electric_ef": self.electric_ef,
            "electric_ef_year": self.electric_ef_year,
            "heat_purchased": self.heat_purchased,
            "heat_exported": self.heat_exported,
            "paper_output_wan_ton": self.paper_output_wan_ton,
            "wastepaper_recycled_wan_ton": self.wastepaper_recycled_wan_ton,
            "provenance": self.provenance,
        }


def demo_activity() -> ActivityData:
    """一套示例工厂活动数据（仿真演示用，非真实企业）。

    量级参考：中型纸厂年耗烟煤数万吨、外购电力数万 MWh、
    自备热电联产供汽。数字为演示取整值。
    """
    return ActivityData(
        year=2024,
        factory_name="示例造纸厂（仿真）",
        fuels=[
            FuelUse("bituminous", 32000.0),   # 烟煤 3.2 万吨
            FuelUse("natural_gas", 850.0),    # 天然气 850 万标方
            FuelUse("diesel", 420.0),         # 柴油 420 吨（厂内车辆）
        ],
        limestone_ton=1200.0,
        wastewater_cod_removed=1800.0,
        wastewater_cod_sludge=150.0,
        methane_recovered=0.0,
        electricity_purchased=42000.0,        # 42000 MWh
        electricity_exported=3000.0,          # 自发自用后上网 3000 MWh
        electric_ef=None,                     # 未配置时该项显示「待配置」
        electric_ef_year=None,
        heat_purchased=85000.0,               # 85000 GJ 外购蒸汽
        heat_exported=0.0,
        paper_output_wan_ton=28.0,            # 年产 28 万吨纸
        wastepaper_recycled_wan_ton=18.0,     # 年回收废纸 18 万吨（来自回收Agent）
    )


# 废纸替代原生浆的减排系数（范围三演示）
# 说明：这是文献常见的量级参考，用于演示方法，明确标注为「演示系数」，
# 不作正式核算依据。真实核算需按具体浆种、工艺、数据源确定。
RECYCLE_AVOID_COEF = 0.85  # tCO2e / 吨废纸替代（演示值）
RECYCLE_COEF_SOURCE = "演示系数（文献量级参考，正式核算须按浆种/工艺实测确定）"
