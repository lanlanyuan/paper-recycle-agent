#!/usr/bin/env bash
# 把 docs/ISSUES.md 里的 Issue 与里程碑真实建到 GitHub。
#
# 背景：本仓库的 commit message 里写了 `closes #26`、`Merge PR #19`，但仓库长期没有远端，
# GitHub 上并不存在这些对象。这个脚本用 gh CLI 把它们补建出来，让编号真正指向东西。
#
# 用法：
#   bash tools/publish_to_github.sh            # 预演，只打印将要创建什么
#   bash tools/publish_to_github.sh --apply    # 真的创建
#
# 前置：
#   1. 已 push 到 GitHub：git remote add origin git@github.com:OWNER/REPO.git && git push -u origin main --tags
#   2. 装了 gh 并登录：gh auth login
#
# 重要：Issue 编号是仓库级序列（与 PR 共享）。脚本要求仓库里还没有任何 Issue/PR，
# 这样按 #1→#30 顺序创建才能与 commit message 里的编号对上。

set -euo pipefail

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

red()  { printf '\033[31m%s\033[0m\n' "$*"; }
green(){ printf '\033[32m%s\033[0m\n' "$*"; }
dim()  { printf '\033[2m%s\033[0m\n' "$*"; }

# ---------------------------------------------------------------- 前置检查

if ! command -v gh >/dev/null 2>&1; then
  red "未找到 gh CLI。安装：https://cli.github.com/  然后 gh auth login"
  exit 2
fi

if ! gh auth status >/dev/null 2>&1; then
  red "gh 未登录。先执行：gh auth login"
  exit 2
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  red "还没有远端。先执行："
  dim "  git remote add origin git@github.com:OWNER/REPO.git"
  dim "  git push -u origin main --tags"
  exit 2
fi

REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
if [[ -z "$REPO" ]]; then
  red "无法确定 GitHub 仓库（gh repo view 失败）"
  exit 2
fi

echo "目标仓库：$REPO"
echo

existing_issues=$(gh issue list --state all --limit 100 --json number -q 'length' 2>/dev/null || echo 0)
existing_prs=$(gh pr list --state all --limit 100 --json number -q 'length' 2>/dev/null || echo 0)
if [[ "$existing_issues" != "0" || "$existing_prs" != "0" ]]; then
  red "仓库里已有 $existing_issues 个 Issue、$existing_prs 个 PR。"
  echo "Issue 编号是仓库级序列，已有编号会让 #1→#30 对不上 commit message 里的引用。"
  echo "建议：新建一个空仓库，或手工核对后再建。脚本中止。"
  exit 3
fi

# ---------------------------------------------------------------- 解析 ISSUES.md

ISSUES_MD="$ROOT/docs/ISSUES.md"
if [[ ! -f "$ISSUES_MD" ]]; then
  red "找不到 docs/ISSUES.md"
  exit 2
fi

# 表格行：| #1 | 项目初始化与知识库定义 | 新功能 | — | ✅ |
mapfile -t issue_rows < <(
  grep -E '^\| #[0-9]+ ' "$ISSUES_MD" | sed -E 's/^\| *//; s/ *\|$//'
)

if [[ ${#issue_rows[@]} -eq 0 ]]; then
  red "从 docs/ISSUES.md 没解析出任何 Issue 行"
  exit 2
fi

echo "解析到 ${#issue_rows[@]} 个 Issue"
echo

# 里程碑：| v1.0 首个正式版 | #6 #7 #8 | ✅ |
declare -A MS_OF_ISSUE=()
mapfile -t ms_rows < <(
  grep -E '^\| v[0-9]' "$ISSUES_MD" | sed -E 's/^\| *//; s/ *\|$//'
)
for row in "${ms_rows[@]}"; do
  IFS='|' read -r ms_name nums _status <<<"$row"
  ms_name="$(echo "$ms_name" | sed -E 's/ +$//')"
  for n in $nums; do
    n="${n#\#}"
    [[ "$n" =~ ^[0-9]+$ ]] && MS_OF_ISSUE["$n"]="$ms_name"
  done
done

# 里程碑去重并按出现顺序排列
milestones=()
for row in "${ms_rows[@]}"; do
  IFS='|' read -r ms_name _ _ <<<"$row"
  ms_name="$(echo "$ms_name" | sed -E 's/^ +//; s/ +$//')"
  [[ -n "$ms_name" ]] && milestones+=("$ms_name")
done

echo "里程碑（${#milestones[@]} 个）："
for m in "${milestones[@]}"; do echo "  · $m"; done
echo

# ---------------------------------------------------------------- 预演

print_plan() {
  local num title kind
  for row in "${issue_rows[@]}"; do
    IFS='|' read -r num title kind _ _ <<<"$row"
    num="$(echo "$num" | tr -d ' #')"
    title="$(echo "$title" | sed -E 's/^ +//; s/ +$//')"
    kind="$(echo "$kind" | sed -E 's/^ +//; s/ +$//')"
    printf '  #%-3s %-46s %s\n' "$num" "$title" "${MS_OF_ISSUE[$num]:-（无里程碑）}"
  done
}

if [[ "$APPLY" -eq 0 ]]; then
  echo "将创建以下 Issue（预演模式，未写入 GitHub）："
  print_plan
  echo
  dim "确认无误后执行：bash tools/publish_to_github.sh --apply"
  exit 0
fi

# ---------------------------------------------------------------- 创建里程碑

echo "== 创建里程碑 =="
declare -A MS_NUMBER=()
for m in "${milestones[@]}"; do
  if gh api "repos/$REPO/milestones" --jq '.[].title' 2>/dev/null | grep -qxF "$m"; then
    echo "  已存在：$m"
  else
    gh api -X POST "repos/$REPO/milestones" -f title="$m" >/dev/null
    echo "  已创建：$m"
  fi
done
echo

# ---------------------------------------------------------------- 创建标签

echo "== 确保标签存在 =="
for label in "bug:d73a4a" "enhancement:a2eeef" "docs:0075ca" "refactor:cfd3d7"; do
  name="${label%%:*}"; color="${label##*:}"
  gh label create "$name" --color "$color" --force >/dev/null 2>&1 || true
done
echo "  ok"
echo

# ---------------------------------------------------------------- 创建 Issue

echo "== 创建 Issue（顺序即编号）=="
for row in "${issue_rows[@]}"; do
  IFS='|' read -r num title kind _status <<<"$row"
  num="$(echo "$num" | tr -d ' #')"
  title="$(echo "$title" | sed -E 's/^ +//; s/ +$//')"
  kind="$(echo "$kind" | sed -E 's/^ +//; s/ +$//')"
  ms="${MS_OF_ISSUE[$num]:-}"

  # 找实现这条 Issue 的提交，写进正文，形成双向可追溯
  commit_line="$(git log --all --pretty='%h %s' | grep -E "#${num}([^0-9]|$)" | head -1 || true)"

  case "$kind" in
    Bug|修复) label="bug" ;;
    文档)     label="docs" ;;
    重构)     label="refactor" ;;
    *)        label="enhancement" ;;
  esac

  body="## 类型
$kind

## 说明
见 docs/ISSUES.md 与 docs/DEVLOG.md 中关于 #$num 的记录。
"
  if [[ -n "$commit_line" ]]; then
    body="$body
## 关联提交
\`$commit_line\`
"
  fi

  args=(issue create --title "$title" --body "$body" --label "$label")
  [[ -n "$ms" ]] && args+=(--milestone "$ms")

  if url=$(gh "${args[@]}" 2>&1); then
    echo "  #$num  $title"
  else
    red "  #$num 创建失败：$url"
  fi
done

echo
green "完成。检查一下编号是否对得上："
dim "  gh issue list --limit 40"
dim "  git log --oneline | grep -o 'closes #[0-9]*'"
