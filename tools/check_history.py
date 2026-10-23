"""历史自洽校验器：把「连续开发」从自述变成可证伪的检查。

用法：
    python tools/check_history.py
    python tools/check_history.py --quiet     # 只输出结论

检查项（任一不通过即以退出码 1 结束）：

1. 父子提交时间严格递增 —— 发布提交不可能早于它要发布的内容；
2. author date 与 committer date 一致 —— 不一致通常意味着历史被事后改过；
3. 提交时间不在未来 —— 防止为了"看起来开发了很久"把时间戳往前挪；
4. 每个 feature/* 分支都有对应的 --no-ff 合并提交 —— 证明是分支开发 + 合并，
   而不是直接往 main 上堆；
5. 标签都指向存在且可达的提交 —— 防止出现空标签；
6. 提交信息带规范前缀（feat/fix/docs/test/chore/refactor/build/ci/Merge…）。

纯标准库，兼容 Python 3.7。
"""

import subprocess
import sys
import time
from typing import Dict, List, Optional, Sequence, Tuple

ROOT = None  # 由 git 命令自行定位，避免依赖 cwd

PREFIXES = (
    "feat", "fix", "docs", "test", "tests", "chore", "refactor",
    "build", "ci", "perf", "style", "revert", "Merge", "merge",
)

# 未来时间的容忍度（秒）：时钟漂移不该被判为作弊
FUTURE_TOLERANCE = 300


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.stdout


def _git_ok(*args: str) -> bool:
    proc = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode == 0


def _is_shallow() -> bool:
    return _git("rev-parse", "--is-shallow-repository").strip() == "true"


def _commits() -> List[Dict[str, object]]:
    """返回全部提交的元数据（按 git 默认顺序）。"""
    out = _git("log", "--all", "--pretty=%H|%at|%ct|%aI|%cI|%s")
    rows = []
    for line in out.strip().splitlines():
        parts = line.split("|", 5)
        if len(parts) < 6:
            continue
        h, at, ct, ai, ci, subject = parts
        rows.append({
            "hash": h,
            "author_ts": int(at),
            "commit_ts": int(ct),
            "author_iso": ai,
            "commit_iso": ci,
            "subject": subject,
        })
    return rows


def _parents() -> Dict[str, List[str]]:
    out = _git("rev-list", "--parents", "--all")
    table = {}
    for line in out.strip().splitlines():
        parts = line.split()
        if parts:
            table[parts[0]] = parts[1:]
    return table


def check_time_order(commits: Sequence[Dict[str, object]],
                     parents: Dict[str, List[str]]) -> List[str]:
    problems = []
    for c in commits:
        for p in parents.get(c["hash"], []):  # type: ignore[arg-type]
            pc = next((x for x in commits if x["hash"] == p), None)
            if pc is None:
                continue
            if int(pc["author_ts"]) >= int(c["author_ts"]):  # type: ignore[arg-type]
                problems.append(
                    "时间倒挂：%s（%s）不晚于父提交 %s（%s）"
                    % (c["hash"][:7], c["author_iso"], p[:7], pc["author_iso"])
                )
    return problems


def check_author_equals_committer(commits: Sequence[Dict[str, object]]) -> List[str]:
    problems = []
    for c in commits:
        if c["author_iso"] != c["commit_iso"]:
            problems.append(
                "author/committer 时间不一致：%s（A=%s, C=%s）"
                % (c["hash"][:7], c["author_iso"], c["commit_iso"])
            )
    return problems


def check_no_future(commits: Sequence[Dict[str, object]]) -> List[str]:
    now = int(time.time())
    problems = []
    for c in commits:
        if int(c["author_ts"]) > now + FUTURE_TOLERANCE:  # type: ignore[arg-type]
            problems.append(
                "提交时间在未来：%s（%s）" % (c["hash"][:7], c["author_iso"])
            )
    return problems


def _branches(prefix: str) -> List[str]:
    out = _git("for-each-ref", "--format=%(refname:short)", "refs/heads/" + prefix)
    return [b for b in out.strip().splitlines() if b]


def check_merge_commits(parents: Dict[str, List[str]]) -> Tuple[List[str], int]:
    """每个 feature/fix 分支都应被某个合并提交当作父提交引用过。"""
    problems = []
    merged_tips = set()
    merge_count = 0
    for h, ps in parents.items():
        if len(ps) >= 2:
            merge_count += 1
            for p in ps:
                merged_tips.add(p)

    branches = _branches("feature/") + _branches("fix/")
    for b in branches:
        tip = _git("rev-parse", b).strip()
        if tip and tip not in merged_tips:
            problems.append("分支 %s 没有对应的合并提交（可能被快进合并或未合并）" % b)
    return problems, merge_count


def check_tags(commits: Sequence[Dict[str, object]]) -> List[str]:
    problems = []
    out = _git("for-each-ref", "--format=%(refname:short)", "refs/tags")
    known = {c["hash"] for c in commits}
    for tag in [t for t in out.strip().splitlines() if t]:
        if not _git_ok("rev-parse", "--verify", tag + "^{commit}"):
            problems.append("标签 %s 指向的提交不存在" % tag)
            continue
        commit = _git("rev-parse", tag + "^{commit}").strip()
        if commit not in known:
            problems.append("标签 %s 指向的提交不在任何分支历史中" % tag)
    return problems


def check_subject_prefix(commits: Sequence[Dict[str, object]]) -> List[str]:
    problems = []
    for c in commits:
        subject = str(c["subject"])
        # 合并提交由 git 自动生成 "Merge branch 'x'" 或手写 "Merge PR #N: …"，
        # 不套用 feat/fix 前缀规范。
        if subject.startswith(("Merge ", "merge ")):
            continue
        head = subject.split(":", 1)[0].split("(", 1)[0].strip()
        if head not in PREFIXES:
            problems.append(
                "提交信息缺少规范前缀：%s「%s」" % (c["hash"][:7], subject[:50])
            )
    return problems


def main(argv: Sequence[str]) -> int:
    quiet = "--quiet" in argv

    if not _git_ok("rev-parse", "--git-dir"):
        print("错误：当前目录不是 Git 仓库")
        return 2

    commits = _commits()
    if not commits:
        print("错误：读不到任何提交")
        return 2

    parents = _parents()
    if not quiet:
        print("历史自洽校验")
        print("-" * 46)
        print("提交数：%d" % len(commits))

    results = []

    p1 = check_time_order(commits, parents)
    results.append(("父子提交时间严格递增", p1))

    p2 = check_author_equals_committer(commits)
    results.append(("author 与 committer 时间一致", p2))

    p3 = check_no_future(commits)
    results.append(("提交时间不在未来", p3))

    p4, merge_count = check_merge_commits(parents)
    results.append(("每个 feature/fix 分支都有合并提交", p4))

    p5 = check_tags(commits)
    results.append(("标签指向存在且可达的提交", p5))

    p6 = check_subject_prefix(commits)
    results.append(("提交信息带规范前缀", p6))

    failed = 0
    for name, problems in results:
        if problems:
            failed += 1
            print("[x] %s：%d 处问题" % (name, len(problems)))
            for p in problems[:8]:
                print("      · %s" % p)
            if len(problems) > 8:
                print("      · …另有 %d 处" % (len(problems) - 8))
        elif not quiet:
            print("[ok] %s" % name)

    if not quiet:
        print("-" * 46)
        print("合并提交（--no-ff）：%d 个" % merge_count)
        if _is_shallow():
            print("注意：这是浅克隆，历史检查结果不可信，请先 git fetch --unshallow")
        print("结果：%s" % ("通过" if failed == 0 else "不通过（%d 项）" % failed))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
