"""Excel 导出：面向统计局/行业协会的多表工作簿。

工作表结构：
1. 省级统计   —— 34 个省级行政区的回收量、比重、回收率、利用率等（2024 年）
2. 分类回收   —— 按 GB/T 20811-2018 八大类拆分的回收量与估算货值（可选年份/区域）
3. 历年回收   —— 2014—2025 年回收量、消费量、回收率、利用率
4. 废纸进口   —— 2017—2025 年废纸进口量（体现禁废令效果）
5. 企业名录   —— 企业名称、城市、类型、主营大类、年回收量、经纬度
6. 数据说明   —— 数据来源、口径与「官方 / 测算 / 示例」区分，供复核
"""

from io import BytesIO
from typing import Dict, List, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from . import enterprises, regions
from . import stats as stats_mod

HEADER_FILL = PatternFill("solid", fgColor="2F7D4F")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
TITLE_FONT = Font(bold=True, size=13, color="1F2329")
NOTE_FONT = Font(size=10, color="6B7280")
THIN = Side(style="thin", color="D9D9D9")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _style_header(ws, row: int, ncols: int) -> None:
    for col in range(1, ncols + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER


def _autofit(ws, widths: List[int]) -> None:
    for i, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width


def _write_sheet(ws, title: str, headers: List[str], rows: List[List[object]],
                 widths: List[int], note: Optional[str] = None) -> None:
    """统一的「标题 + 表头 + 数据 + 备注」写入。"""
    ws.append([title])
    ws.cell(row=1, column=1).font = TITLE_FONT
    if note:
        ws.append([note])
        ws.cell(row=2, column=1).font = NOTE_FONT
        header_row = 3
    else:
        header_row = 2
    ws.append(headers)
    _style_header(ws, header_row, len(headers))
    for row in rows:
        ws.append(row)
    for r in range(header_row + 1, ws.max_row + 1):
        for c in range(1, len(headers) + 1):
            ws.cell(row=r, column=c).border = BORDER
    ws.freeze_panes = ws.cell(row=header_row + 1, column=1)
    _autofit(ws, widths)


def _province_rows() -> List[List[object]]:
    rows: List[List[object]] = []
    for p in regions.get_children("CN"):
        s = p["stats"]  # type: ignore[index]
        rows.append([
            p["rank"], p["name"], p["tier_label"],
            s["回收量(万吨)"], s["占全国比重(%)"],
            s["回收率(%)"], s["利用率(%)"], s["纸及纸板产量(万吨)"],
            s["回收企业数(家)"], s["从业人员(人)"],
            "公开报道" if p["quality"] == "reported" else "梯队测算",
        ])
    total = sum(float(p["stats"]["回收量(万吨)"]) for p in regions.get_children("CN"))  # type: ignore[index]
    rows.append(["合计", "全国", "—", round(total, 1), 100.0,
                 regions.NATIONAL_STATS["回收率(%)"], regions.NATIONAL_STATS["利用率(%)"],
                 regions.NATIONAL_STATS["纸及纸板产量(万吨)"],
                 regions.NATIONAL_STATS["回收企业数(家)"],
                 regions.NATIONAL_STATS["从业人员(人)"], "官方"])
    return rows


def build_workbook(code: str = "CN", year: int = regions.NATIONAL_YEAR) -> bytes:
    """生成多表工作簿，返回 .xlsx 字节流。"""
    node = regions.get_node(code) or regions.ROOT
    node_code = str(node["code"])
    is_national = node["level"] == "national"
    scope_name = str(node["name"])

    wb = Workbook()

    # ---- 1. 省级统计 ----
    ws1 = wb.active
    ws1.title = "省级统计"
    if is_national:
        rows1 = _province_rows()
        note1 = ("数据年度：2024 年。全国合计为中国造纸协会官方值；"
                 "山东、广东为公开报道值；其余省份为梯队测算，仅供结构参考。")
    else:
        s = node["stats"]  # type: ignore[index]
        rows1 = [[
            node.get("rank", "—"), node["name"], node["tier_label"],
            s["回收量(万吨)"], s["占全国比重(%)"],
            s["回收率(%)"], s["利用率(%)"], s["纸及纸板产量(万吨)"],
            s["回收企业数(家)"], s["从业人员(人)"],
            "公开报道" if node["quality"] == "reported" else "梯队测算",
        ]]
        note1 = f"仅导出「{scope_name}」。完整省级对照请选择「全国」后再导出。"
    _write_sheet(
        ws1, f"{scope_name} 废纸回收统计（2024 年）",
        ["排名", "区域", "梯队", "回收量(万吨)", "占全国比重(%)", "回收率(%)",
         "利用率(%)", "纸及纸板产量(万吨)", "回收企业数(家)", "从业人员(人)", "数据性质"],
        rows1,
        [8, 20, 22, 15, 14, 12, 12, 20, 16, 14, 12],
        note1,
    )

    # ---- 2. 分类回收 ----
    ws2 = wb.create_sheet("分类回收")
    share = regions.share_of_national(node_code)
    year_total = stats_mod.get_recovery(year)
    base = (year_total or 0.0) * share
    cat_rows = []
    for r in stats_mod.category_breakdown(year, total=base):
        cat_rows.append([
            r["code"], r["name"], r["share"], r["tonnage"],
            r["price"], r["value"], r["use"],
        ])
    cat_rows.append([
        "合计", "八大类", round(sum(float(r["share"]) for r in stats_mod.category_breakdown(year, total=base)), 2),
        round(sum(float(r["tonnage"]) for r in stats_mod.category_breakdown(year, total=base)), 1),
        "—",
        round(sum(float(r["value"]) for r in stats_mod.category_breakdown(year, total=base)), 1),
        "",
    ])
    _write_sheet(
        ws2, f"{scope_name} {year} 年废纸回收量分类拆分（GB/T 20811-2018）",
        ["类别代码", "类别名称", "占比(%)", "回收量(万吨)", "参考价(元/公斤)",
         "估算货值(亿元)", "主要去向"],
        cat_rows,
        [10, 20, 10, 14, 16, 16, 52],
        "占比为行业结构估算（2015/2020/2025 三锚点插值），回收量 = 占比 × 当年回收量；"
        "货值为「回收量 × 参考价」估算，非实际成交额。",
    )

    # ---- 3. 历年回收 ----
    ws3 = wb.create_sheet("历年回收")
    hist_rows = []
    for r in stats_mod.get_history():
        hist_rows.append([
            r["year"], r["recovery"],
            "—" if r["consumption"] is None else r["consumption"],
            "—" if r["yoy"] is None else r["yoy"],
            r["recovery_rate"],
            "—" if r["utilization"] is None else r["utilization"],
            "—" if r["paper_output"] is None else r["paper_output"],
            r["note"],
        ])
    _write_sheet(
        ws3, "历年废纸回收利用情况（全国）",
        ["年份", "回收量(万吨)", "废纸消费量(万吨)", "回收量同比(%)",
         "回收率(%)", "利用率(%)", "纸及纸板产量(万吨)", "数据性质"],
        hist_rows,
        [10, 15, 18, 14, 12, 12, 20, 14],
        "回收率 = 回收量 ÷ 纸及纸板消费量；利用率 = 废纸消费量 ÷ 纸及纸板产量。",
    )

    # ---- 4. 废纸进口 ----
    ws4 = wb.create_sheet("废纸进口")
    imp_rows = [[r["year"], r["value"]] for r in stats_mod.get_import_series()]
    _write_sheet(
        ws4, "废纸进口量（万吨）",
        ["年份", "进口量(万吨)"],
        imp_rows,
        [10, 16],
        "2021-01-01《关于全面禁止进口固体废物有关事项的公告》施行后，废纸进口清零。",
    )

    # ---- 5. 企业名录 ----
    ws5 = wb.create_sheet("企业名录")
    prov = None if is_national else node_code
    ent_rows = []
    for e in enterprises.list_enterprises(prov):
        ent_rows.append([
            e["name"], e["city"], e["type"],
            "、".join(e["category_names"]),
            e["volume"], e["lat"], e["lon"], e["note"],
            "示例" if e["is_demo"] else "真实",
        ])
    ent_rows.append([
        "合计", "", "", "",
        round(sum(float(e["volume"]) for e in enterprises.list_enterprises(prov)), 1),
        "", "", "", "",
    ])
    _write_sheet(
        ws5, f"{scope_name} 回收企业名录",
        ["企业名称", "城市", "类型", "主营大类", "年回收量(万吨)",
         "纬度", "经度", "备注", "数据性质"],
        ent_rows,
        [30, 12, 16, 34, 16, 10, 10, 34, 10],
        "企业维度用于回答「某个地方的量由谁在做、分布在哪些城市、各品类由哪类企业消化」。"
        "内置名录为示例数据（虚构名称），可在项目根目录放 data/enterprises.csv 覆盖。",
    )

    # ---- 6. 数据说明 ----
    ws6 = wb.create_sheet("数据说明")
    ws6.append(["数据来源与口径说明"])
    ws6.cell(row=1, column=1).font = TITLE_FONT
    lines = [
        "一、数据来源",
        *[f"  · {s}" for s in stats_mod.SOURCES],
        "",
        "二、口径区分",
        "  · 官方：中国造纸协会年度报告公布值，可直接引用。",
        "  · 公开报道：省级回收量来自行业研究机构公开报道。",
        "  · 梯队测算 / 估算：按行业分区梯队或结构占比推算，仅供结构参考，不可作为统计公报数据。",
        "  · 示例：企业名录为演示用虚构数据，需替换为真实名录后使用。",
        "",
        "三、已知口径差异",
        "  · 2024 年全国废纸回收量：中国造纸协会年度报告 6971 万吨；"
        "部分行业机构按 6797 万吨统计（同比 +9.1%）。本工具采用协会口径。",
        "  · 部分年份（2015、2017、2018）废纸消费量/利用率未在公开年报中单列，故留空。",
        "",
        "四、层级范围",
        "  · 本工具提供全国与省级两级统计；市级、县级无公开权威数据，故不提供，避免误导。",
        "  · 企业名录带城市与经纬度，可在省级以下提供更细的空间视角，但企业样本不代表全量。",
        "",
        "五、替换为真实数据",
        "  · 省级：修改 src/paper_recycle_agent/regions.py 的 SEEDS，为省份填入 reported 值。",
        "  · 历年：修改 src/paper_recycle_agent/stats.py 的 HISTORY。",
        "  · 分类占比：修改 CATEGORY_SHARES 的锚点年份数值。",
        "  · 企业名录：在项目根目录放 data/enterprises.csv（表头见 enterprises.CSV_FIELDS）。",
    ]
    for line in lines:
        ws6.append([line])
    ws6.column_dimensions["A"].width = 110
    for r in range(2, ws6.max_row + 1):
        ws6.cell(row=r, column=1).alignment = Alignment(wrap_text=False, vertical="center")

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def filename(code: str = "CN", year: int = regions.NATIONAL_YEAR) -> str:
    node = regions.get_node(code) or regions.ROOT
    return f"废纸回收统计_{node['name']}_{year}.xlsx"
