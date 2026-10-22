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
