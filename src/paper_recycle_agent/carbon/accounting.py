"""碳核算引擎：严格实现国标五类排放源的计算公式。

公式逐条对应国标正文（见 factors.all_factors()['formula']）：
    公式4  EF   = CC × OF × 44/12
    公式3  AD   = FC × NCV
    公式2  E燃烧 = Σ(AD_i × EF_i)
    公式5  E过程 = L × EF石灰
    废水   E_CH4 = (TOW − S) × EF × GWP − R × GWP
    公式10 E购入电 = AD电 × EF电
    公式1  E总   = 燃烧 + 过程 + 废水 + 购入电/热 − 输出电/热

每个结果都带 formula 和 source，可手算复核。
电力因子未配置时该项为 None，总量标注 incomplete=True，
不假装算出了一个"完整"结果——这是本项目一贯的口径纪律。
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from . import factors, model
from .model import ActivityData, FuelUse


@dataclass
class LineItem:
    """一个排放源的计算明细。"""

    key: str
    name: str
    activity: float  # 活动数据（按各项单位）
    activity_unit: str
    ef: Optional[float]  # 排放因子
    ef_unit: str
    emission: Optional[float]  # 排放量 tCO2e
    formula: str
    source: str
    detail: str = ""

    def public(self) -> Dict[str, object]:
        return {
            "key": self.key,
            "name": self.name,
            "activity": round(self.activity, 4),
            "activity_unit": self.activity_unit,
            "ef": None if self.ef is None else round(self.ef, 6),
            "ef_unit": self.ef_unit,
            "emission": None if self.emission is None else round(self.emission, 3),
            "formula": self.formula,
            "source": self.source,
            "detail": self.detail,
        }


class CarbonAccounting:
    """碳核算器：输入活动数据，输出按国标口径的核算结果。"""

    def __init__(self, activity: Optional[ActivityData] = None) -> None:
        self.activity = activity or model.demo_activity()

    # ---------- 五类排放源 ----------
    def fuel_items(self) -> List[LineItem]:
        """化石燃料燃烧：逐燃料一行（国标公式2/3/4）。"""
        items: List[LineItem] = []
        for use in self.activity.fuels:
            f = factors.fuel(use.key)
            ad = use.quantity * f.ncv  # 公式3：AD = FC × NCV
            ef = f.ef  # 公式4：EF = CC × OF × 44/12
            emission = ad * ef  # 公式2
            items.append(LineItem(
                key="fuel_" + f.key,
                name=f.name + "燃烧",
                activity=ad,
                activity_unit="GJ",
                ef=ef,
                ef_unit="tCO2/GJ",
                emission=emission,
                formula="E = 消耗量×低位发热×CC×OF×44/12",
                source=factors.SOURCE_STD,
                detail="消耗 %.2f %s × NCV %.3f = %.1f GJ" % (
                    use.quantity, f.unit, f.ncv, ad,
                ),
            ))
        return items

    def process_item(self) -> LineItem:
        """过程排放：石灰石分解（国标公式5）。"""
        ad = self.activity.limestone_ton
        return LineItem(
            key="process",
            name="过程排放（石灰石分解）",
            activity=ad,
            activity_unit="t",
            ef=factors.LIMESTONE_EF,
            ef_unit="tCO2/t",
            emission=ad * factors.LIMESTONE_EF,
            formula="E过程 = L × EF石灰（国标公式5）",
            source=factors.LIMESTONE_EF_SOURCE,
        )

    def wastewater_item(self) -> LineItem:
        """废水厌氧处理甲烷（国标公式8/9）。"""
        a = self.activity
        net_cod = max(0.0, a.wastewater_cod_removed - a.wastewater_cod_sludge)
        # E_CH4 = (TOW − S) × EF × GWP − R × GWP
        emission = net_cod * factors.CH4_MAX * factors.CH4_CORRECTION * factors.GWP_CH4 \
            - a.methane_recovered * factors.GWP_CH4
        return LineItem(
            key="wastewater",
            name="废水厌氧甲烷",
            activity=net_cod,
            activity_unit="tCOD",
            ef=factors.CH4_MAX * factors.CH4_CORRECTION * factors.GWP_CH4,
            ef_unit="tCO2e/tCOD",
            emission=emission,
            formula="E = (TOW−S)×BO×MF×GWP − R×GWP",
            source=factors.WAWWATER_SOURCE,
            detail="净COD %.1f t，BO=%.2f，MF=%.2f，GWP=%d，回收 %.1f tCH4" % (
                net_cod, factors.CH4_MAX, factors.CH4_CORRECTION,
                factors.GWP_CH4, a.methane_recovered,
            ),
        )

    def electricity_item(self) -> LineItem:
        """净购入电力（国标公式10/12，合并为净购入）。"""
        a = self.activity
        net = a.electricity_purchased - a.electricity_exported
        ef = a.electric_ef  # 未配置则 None
        emission = None if ef is None else net * ef
        return LineItem(
            key="electricity",
            name="净购入电力",
            activity=net,
            activity_unit="MWh",
            ef=ef,
            ef_unit="tCO2/MWh",
            emission=emission,
            formula="E = (购入−输出)电量 × EF电（国标公式10/12）",
            source=(factors.ELECTRIC_EF_SOURCE if ef is not None
                    else "未配置电力因子——国标要求取主管部门最近年份公布值"),
            detail=("购入 %.0f − 输出 %.0f = %.0f MWh" % (
                a.electricity_purchased, a.electricity_exported, net,
            )) + ("" if ef is not None else "；请在设置中填入 EF 及年份"),
        )

    def heat_item(self) -> LineItem:
        """净购入热力（国标公式11/13）。"""
        a = self.activity
        net = a.heat_purchased - a.heat_exported
        emission = net * factors.HEAT_EF_DEFAULT
        return LineItem(
            key="heat",
            name="净购入热力",
            activity=net,
            activity_unit="GJ",
            ef=factors.HEAT_EF_DEFAULT,
            ef_unit="tCO2/GJ",
            emission=emission,
            formula="E = (购入−输出)热力 × EF热（国标公式11/13）",
            source=factors.HEAT_EF_SOURCE,
            detail="购入 %.0f − 输出 %.0f = %.0f GJ" % (
                a.heat_purchased, a.heat_exported, net,
            ),
        )

    # ---------- 范围三：废纸回收减排（不计入国标边界） ----------
    def recycle_credit(self) -> Dict[str, object]:
        """废纸回收替代原生浆的减排量——范围三演示，单列不并入总量。"""
        tonnage = self.activity.wastepaper_recycled_wan_ton * 10000.0  # 万吨→吨
        credit = tonnage * model.RECYCLE_AVOID_COEF
        return {
            "wastepaper_ton": round(tonnage, 1),
            "coef": model.RECYCLE_AVOID_COEF,
            "coef_unit": "tCO2e/t废纸",
            "credit_tco2e": round(credit, 1),
            "scope": "范围三（不计入国标核算边界）",
            "source": model.RECYCLE_COEF_SOURCE,
            "note": "减排量为方法演示，不可用于碳交易或正式披露。",
        }

    # ---------- 汇总 ----------
    def calculate(self) -> Dict[str, object]:
        """按国标公式1汇总，返回完整核算结果。"""
        fuel = self.fuel_items()
        items = fuel + [
            self.process_item(),
            self.wastewater_item(),
            self.electricity_item(),
            self.heat_item(),
        ]
        # 电力因子未配置 → 该项 None → 总量不完整
        incomplete = any(it.emission is None for it in items)
        total = None if incomplete else round(
            sum(float(it.emission) for it in items), 3  # type: ignore[arg-type]
        )
        by_source: Dict[str, Optional[float]] = {}
        for it in items:
            prev = by_source.get(it.key)
            if prev is None:
                by_source[it.key] = it.emission
            elif it.emission is not None:
                by_source[it.key] = prev + it.emission

        output = self.activity.paper_output_wan_ton
        # 碳强度 = 总排放(tCO2e) ÷ 产量(万吨 × 10000 = 吨) → tCO2e/吨纸
        intensity = None if (total is None or output <= 0) else round(
            total / (output * 10000.0), 4
        )

        return {
            "factory": self.activity.factory_name,
            "year": self.activity.year,
            "provenance": self.activity.provenance,
            "items": [it.public() for it in items],
            "by_source": {
                k: (None if v is None else round(v, 3)) for k, v in by_source.items()
            },
            "total_tco2e": total,
            "output_wan_ton": output,
            "intensity_tco2e_per_ton": intensity,
            "intensity_unit": "tCO2e/吨纸",
            "incomplete": incomplete,
            "electric_configured": self.activity.electric_ef is not None,
            "recycle_credit": self.recycle_credit(),
            "formula": "E总 = 燃烧 + 过程 + 废水CH4 + 购入电/热 − 输出电/热（国标公式1）",
            "boundary_note": (
                "本结果为仿真演示：活动数据为示例输入，排放因子取国标附录B缺省值。"
                "电力因子需按主管部门最新年份配置。不含范围三排放。"
            ),
        }

    def scenario(self, changes: Dict[str, float]) -> Dict[str, object]:
        """情景模拟：改若干活动数据，对比基准与情景的排放变化。

        changes 的 key 形如 'limit:bituminous'（燃料用量）、'electricity_purchased'、'heat_purchased' 等。
        返回基准与情景两套结果及差额。
        """
        import copy

        base = self.calculate()
        alt_activity = copy.deepcopy(self.activity)
        for key, value in changes.items():
            if key.startswith("fuel:"):
                fk = key.split(":", 1)[1]
                found = False
                for fuel_use in alt_activity.fuels:
                    if fuel_use.key == fk:
                        fuel_use.quantity = float(value)
                        found = True
                        break
                if not found:
                    alt_activity.fuels.append(FuelUse(fk, float(value)))
            elif hasattr(alt_activity, key):
                setattr(alt_activity, key, float(value))
        alt = CarbonAccounting(alt_activity).calculate()

        b_total, a_total = base["total_tco2e"], alt["total_tco2e"]
        delta = None if (b_total is None or a_total is None) else round(a_total - b_total, 3)
        return {
            "changes": changes,
            "baseline": base,
            "scenario": alt,
            "delta_tco2e": delta,
            "interpretation": (
                "数据不完整，无法计算差额" if delta is None else
                ("排放下降 %.1f tCO2e（%.2f%%）" % (
                    -delta, (-delta / b_total * 100) if b_total else 0.0,
                ) if delta < 0 else "排放上升 %.1f tCO2e" % delta)
            ),
        }
