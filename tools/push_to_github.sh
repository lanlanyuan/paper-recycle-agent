#!/usr/bin/env bash
# 把本地仓库推到 GitHub，并拿到可访问的 Repo 地址。
#
# 用法：
#   bash tools/push_to_github.sh                      # 预演：只检查，不改任何东西
#   bash tools/push_to_github.sh YOURNAME             # 仓库名默认 paper-recycle-agent
#   bash tools/push_to_github.sh YOURNAME my-repo     # 自定义仓库名
#
# 它做四件事：
#   1. 体检：是不是 git 仓库、有没有未提交改动、有没有敏感文件混进来
#   2. 配远端：git remote add（已存在则 set-url，避免 add 报错）
#   3. 推送：main 分支 + 全部 tag
#   4. 收尾：把 README 里的 OWNER/REPO 占位符替换成真实地址
#
# 前置：已在 GitHub 网页上建好一个空仓库（不要勾选 README / .gitignore / license，
#       否则 push 会因为「远端已有提交」被拒）。建仓地址：https://github.com/new

set -uo pipefail

OWNER="${1:-}"
REPO_NAME="${2:-paper-recycle-agent}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2

red()  { printf '\033[31m%s\033[0m\n' "$*"; }
green(){ printf '\033[32m%s\033[0m\n' "$*"; }
dim()  { printf '\033[2m%s\033[0m\n' "$*"; }
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }

# ---------------------------------------------------------------- 1. 体检

step "[1/4] 体检"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  red "当前目录不是 git 仓库：$ROOT"
  exit 2
fi
green "  是 git 仓库"

if ! git remote get-url origin >/dev/null 2>&1; then
  dim "  尚未配置远端 origin"
  HAS_REMOTE=0
else
  dim "  已有远端 origin：$(git remote get-url origin)"
  HAS_REMOTE=1
fi

dirty="$(git status --porcelain)"
if [[ -n "$dirty" ]]; then
  red "  有未提交的改动，先提交再推："
  printf '%s\n' "$dirty" | sed 's/^/    /'
  exit 2
fi
green "  工作区干净"

# 敏感文件绝不能推上去
leaked="$(git ls-files | grep -E '(^|/)(llm\.json|io_matrix\.csv|enterprises\.csv)$' || true)"
if [[ -n "$leaked" ]]; then
  red "  以下文件被 git 跟踪了，里面有 API 密钥或私有数据，必须先移除："
  printf '%s\n' "$leaked" | sed 's/^/    /'
  dim "  处理：git rm --cached <文件> && git commit -m \"chore: 停止跟踪私有文件\""
  exit 2
fi
green "  无敏感文件入库（config/llm.json、data/*.csv 均未跟踪）"

commits="$(git rev-list --count HEAD)"
tags="$(git tag | wc -l | tr -d ' ')"
dim "  提交 $commits 个，标签 $tags 个"

# git 身份没配的话，后面替换徽章那步的 commit 会静默失败
if ! git config user.email >/dev/null 2>&1 || ! git config user.name >/dev/null 2>&1; then
  red "  未配置 git 身份（user.name / user.email），提交会失败："
  dim "    git config --global user.name \"你的名字\""
  dim "    git config --global user.email \"你的邮箱\""
  exit 2
fi
green "  git 身份已配置"

# ---------------------------------------------------------------- 2. 参数

if [[ -z "$OWNER" ]]; then
  step "用法"
  cat <<'USAGE'
  在 GitHub 网页上先建一个空仓库：https://github.com/new
    - Repository name 填 paper-recycle-agent
    - 不要勾 "Add a README file" / ".gitignore" / "license"
      （勾了远端就有提交，push 会被拒）

  然后执行：
    bash tools/push_to_github.sh 你的GitHub用户名

  推送完成后，Repo 地址就是：
    https://github.com/你的GitHub用户名/paper-recycle-agent
USAGE
  exit 0
fi

URL="https://github.com/${OWNER}/${REPO_NAME}.git"
step "[2/4] 远端配置"
dim "  目标：$URL"

if [[ "$HAS_REMOTE" == "1" ]]; then
  git remote set-url origin "$URL"
  green "  已更新 origin 指向"
else
  git remote add origin "$URL"
  green "  已添加 origin"
fi

# ---------------------------------------------------------------- 3. 推送

branch_count="$(git for-each-ref --format='%(refname:short)' refs/heads | wc -l | tr -d ' ')"
step "[3/4] 推送 ${branch_count} 个分支与全部 tag"
dim "  首次推送会要求输入 GitHub 用户名与 Personal Access Token（不是账号密码）"
dim "  没有 token 的话：GitHub → Settings → Developer settings → Personal access tokens → Generate new token (classic)，勾 repo 权限"

if ! git push -u origin main; then
  red "  push 失败。常见原因："
  dim "    - 远端仓库不是空的（建仓时勾了 README）→ 先 git pull --rebase origin main 再推"
  dim "    - 认证失败 → 密码位置要填 Personal Access Token，不是登录密码"
  dim "    - 仓库名拼错 → 检查 https://github.com/${OWNER}/${REPO_NAME} 是否存在"
  exit 2
fi

# feature/fix 分支必须一起推：只推 main 的话，GitHub 上只有一个线性历史，
# 看不出「开分支 → 分主题提交 → 合并」的过程，连续开发的证据就丢了一半。
if ! git push origin --all; then
  red "  分支推送失败（main 已推成功）。单独重试：git push origin --all"
  exit 2
fi

if ! git push origin --tags; then
  red "  标签推送失败（分支已推成功）。单独重试：git push origin --tags"
  exit 2
fi
green "  ${branch_count} 个分支与 $(git tag | wc -l | tr -d ' ') 个标签均已推送"

# ---------------------------------------------------------------- 4. 收尾

step "[4/4] 收尾"

# README 的 CI 徽章占位符换成真实地址
if grep -q "OWNER/REPO" README.md 2>/dev/null; then
  python_bin=""
  for c in python python3 py; do
    command -v "$c" >/dev/null 2>&1 && { python_bin="$c"; break; }
  done
  if [[ -n "$python_bin" ]]; then
    # 退出码：0=已替换  1=无需替换  2=出错
    "$python_bin" - "$OWNER" "$REPO_NAME" <<'PY'
import pathlib, sys
owner, repo = sys.argv[1], sys.argv[2]
p = pathlib.Path("README.md")
t = p.read_text(encoding="utf-8")
old = "> CI 徽章需要仓库地址：把下面这行里的 `OWNER/REPO` 换成你的 GitHub 用户名与仓库名后取消注释。\n> 在此之前不放，是为了避免 README 上出现一个 404 的破图。\n>\n> `![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)`"
new = "![CI](https://github.com/%s/%s/actions/workflows/ci.yml/badge.svg)" % (owner, repo)
if old not in t:
    print("  README 占位符格式已变，跳过自动替换（手动改第 5 行附近即可）")
    sys.exit(1)
p.write_text(t.replace(old, new), encoding="utf-8")
print("  已把 README 的 CI 徽章指向真实仓库")
sys.exit(0)
PY
    case $? in
      0)
        git add README.md
        if git commit -q -m "docs(readme): CI 徽章指向真实仓库地址"; then
          if git push -q origin main; then
            green "  徽章提交已推送"
          else
            red "  徽章提交已创建但推送失败，手动执行：git push origin main"
          fi
        else
          red "  徽章改动已写入 README.md，但提交失败（见上方 git 报错）"
          dim "  改动仍在工作区，可手动 git add README.md && git commit && git push"
        fi
        ;;
      1) dim "  跳过" ;;
      *) red "  替换脚本异常，手动改 README 第 5 行附近的徽章地址" ;;
    esac
  else
    dim "  未找到 python，跳过徽章自动替换（手动改 README 第 5 行）"
  fi
else
  dim "  README 里没有占位符，跳过"
fi

step "完成"
green "Repo 地址：https://github.com/${OWNER}/${REPO_NAME}"
echo
dim "接下来可选（让 commit message 里的 closes #26 真的指向东西）："
dim "  npm install -g gh  或  下载 https://cli.github.com/"
dim "  gh auth login"
dim "  bash tools/publish_to_github.sh --apply"
