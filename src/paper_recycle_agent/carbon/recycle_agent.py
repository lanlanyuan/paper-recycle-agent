"""废纸回收 Agent（工厂内子智能体）：把回收数据喂给碳核算。

定位变化
--------
原「废纸回收对话助手」在本系统里降级为工厂的一个子 Agent：
它继续负责分类 / 估价 / 区域统计等原有能力，同时把「回收量」
作为活动数据提供给碳核算 Agent，折算成范围三的原料替代减排量。

本模块只做**桥接**：从已有的 stats / regions / io_table 取数，
转换成碳核算需要的输入，不重复实现回收助手的业务逻辑。

投入产出表的角色
----------------
按用户要求，「投入产出表的思考剥离出来当成参考」——
这里用 io_table.leontief_inverse / influence_coefficients 做供应链
碳足迹的**方法演示**（环境扩展投入产出 EEIOA 的思路），
明确标注为方法演示、非真实核算，不并入国标核算边界。
"""

from typing import Dict, List, Optional

from .. import io_table, stats as stats_mod


def recovery_from_stats(year: int = 2024, code: Optional[str] = None) -> Dict[str, object]:
    """从现有回收统计取回收量，作为碳核算的原料输入。

    code=None 取全国；给定省级代码则按占全国比重分摊（沿用 io_table 口径）。
    """
    row = None
    for r in stats_mod.get_history():
        if int(r["year"]) == year:
            row = r
            break
    if row is None:
        return {"ok": False, "error": "无该年数据", "year": year}

    national = float(row.get("recovery") or 0.0)
    share = 1.0
    scope = "全国"
    if code and code != "CN":
        from .. import regions
        node = regions.get_node(code)
        if node is not None and node["level"] == "province":
            share = float(node["stats"]["占全国比重(%)"]) / 100.0  # type: ignore[index]
            scope = str(node["name"])

    return {
        "ok": True,
        "year": year,
        "scope": scope,
        "recovery_wan_ton": round(national * share, 1),
        "national_wan_ton": round(national, 1),
        "share": round(share, 4),
        "provenance": "全国为行业年报数据；分省按回收量占比分摊（估算）",
        "note": "这是行业/区域统计口径，非单厂实际回收量；用于碳核算演示时请按需替换为工厂实测值。",
    }


def bridge_to_activity(recovery_wan_ton: float,
                       activity: object,
                       overwrite: bool = True) -> Dict[str, object]:
    """把回收量写进碳核算活动数据的 wastepaper 字段。

    返回桥接说明。不直接修改调用方之外的数据，由调用方决定是否采用。
    """
    from .model import ActivityData
    if not isinstance(activity, ActivityData):
        return {"ok": False, "error": "活动数据类型不符"}
    written = bool(overwrite or activity.wastepaper_recycled_wan_ton <= 0)
    if written:
        activity.wastepaper_recycled_wan_ton = float(recovery_wan_ton)
    return {
        "ok": True,
        "written": written,
        "wastepaper_recycled_wan_ton": activity.wastepaper_recycled_wan_ton,
        "source": "废纸回收 Agent（stats 回收量）",
        "note": "该值仅用于范围三减排演示，不进入国标核算边界。",
    }


def supply_chain_carbon_demo(matrix: Optional[List[List[float]]] = None) -> Dict[str, object]:
    """环境扩展投入产出（EEIOA）方法演示。

    思路：把直接消耗系数矩阵 A 换成「单位产值的碳排放强度向量」后，
    完全需求（Leontief 逆）可用于估算供应链累积碳足迹：
        C_total = c × (I − A)^-1 × y
    这里 c 为各部门直接碳强度，y 为最终需求。

    本演示**不内置任何碳强度向量或最终需求**（那会是编数据），
    只提供算法骨架：传入矩阵与向量才算得出结果。
    """
    if matrix is None:
        return {
            "ok": False,
            "available": False,
            "method": "环境扩展投入产出（EEIOA）",
            "formula": "C_total = c × (I−A)^-1 × y",
            "reason": "未提供投入产出矩阵与部门碳强度向量，不做无数据推算。",
            "reuse": "io_table.leontief_inverse / influence_coefficients / response_coefficients",
            "boundary": "方法演示，非国标核算边界，不并入碳核算总量。",
        }
    try:
        inv = io_table.leontief_inverse(matrix)
        return {
            "ok": True,
            "available": True,
            "method": "环境扩展投入产出（EEIOA）",
            "formula": "C_total = c × (I−A)^-1 × y",
            "leontief_inverse": inv,
            "influence": io_table.influence_coefficients(matrix),
            "response": io_table.response_coefficients(matrix),
            "boundary": "方法演示；需另配部门碳强度 c 与最终需求 y 才能算碳足迹。",
        }
    except ValueError as exc:
        return {"ok": False, "error": "矩阵无法求逆：%s" % exc}


def agent_status() -> Dict[str, object]:
    """废纸回收 Agent 在系统里的状态说明（供界面展示）。"""
    return {
        "role": "工厂内的废纸回收子 Agent",
        "source_modules": ["stats", "regions", "io_table", "classifier", "pricing"],
        "capabilities": [
            "废纸分类与可回收判定（原有）",
            "按重量估价（原有）",
            "区域 / 历年 / 分类统计（原有）",
            "回收量 → 碳核算原料输入（新增桥接）",
            "范围三原料替代减排演示（新增）",
        ],
        "carbon_link": "回收量经 model.RECYCLE_AVOID_COEF 折算为减排量，单列展示",
        "io_reference": "投入产出系数与 Leontief 逆作为供应链碳足迹方法参考",
    }
