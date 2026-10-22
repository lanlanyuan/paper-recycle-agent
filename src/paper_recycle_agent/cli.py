"""命令行交互入口。"""

import argparse
import sys

from . import agent, classifier, data, pricing, regions
from . import stats as stats_mod


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
    sub.add_parser("history", help="历年回收量 / 回收率 / 利用率")
    cs = sub.add_parser("catstats", help="按八大类拆分回收量")
    cs.add_argument("year", type=int, nargs="?", default=stats_mod.LATEST_YEAR)
    rg = sub.add_parser("region", help="区域统计（全国 / 省级）")
    rg.add_argument("name", nargs="?", default="全国")
    ex = sub.add_parser("export", help="导出 Excel")
    ex.add_argument("name", nargs="?", default="全国")
    ex.add_argument("--year", type=int, default=regions.NATIONAL_YEAR)
    ex.add_argument("--out", default="废纸回收统计.xlsx")
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
    elif args.cmd == "history":
        print(stats_mod.history_summary())
    elif args.cmd == "catstats":
        print(stats_mod.category_summary(args.year))
    elif args.cmd == "region":
        node = regions.find(args.name)
        print(regions.summary(str(node["code"]) if node else "CN"))
    elif args.cmd == "export":
        from . import exporter

        node = regions.find(args.name) or regions.ROOT
        content = exporter.build_workbook(str(node["code"]), args.year)
        with open(args.out, "wb") as fh:
            fh.write(content)
        print(f"已导出：{args.out}（{len(content)} 字节，5 张工作表）")
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
