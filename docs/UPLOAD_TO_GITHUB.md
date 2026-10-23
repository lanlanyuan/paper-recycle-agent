# 把本项目上传到 GitHub：手把手

> 目标：在 10 分钟内拿到一个能打开的地址，形如
> `https://github.com/你的用户名/paper-recycle-agent`
>
> 本文按「Windows + 本机已装 Git 2.55」写的，每一步都写了**你会看到什么**，
> 以及**报错时怎么办**。卡在某一步就直接跳到最后的「常见报错对照表」。

---

## 第 0 步：确认你已经有的东西

打开「Git Bash」（开始菜单搜 `Git Bash`），执行：

```bash
git --version
```

看到 `git version 2.55.0.windows.3` 这类输出就对了。

| 需要的东西 | 你有吗 | 说明 |
| --- | --- | --- |
| Git | ✅ 2.55.0 | 已确认 |
| GitHub 账号 | ❓ 需要自己确认 | 没有就去 https://github.com/signup 注册，5 分钟 |
| 仓库本身 | ✅ | 83 个提交、7 个标签，已就绪 |
| 全局 git 身份 | ❌ **没配** | 第 1 步补上 |
| SSH 密钥 | ❌ 没有 | 不影响，本文用 HTTPS |
| gh CLI | ❌ 没装 | 不影响，只影响后面「补建 Issue」 |

---

## 第 1 步：配置 git 身份（2 分钟）

你的仓库里已经有身份（`liang-xiangyao <dev@example.com>`），但**只在这个仓库生效**，
换一个目录就没了。配成全局的，以后不用再管：

```bash
git config --global user.name "liang-xiangyao"
git config --global user.email "你的邮箱"
```

**邮箱填哪个很重要**，它决定 GitHub 上那些提交显不显示你的头像：

| 填什么 | 结果 |
| --- | --- |
| GitHub 账号的已验证邮箱 | ✅ 提交关联到你，贡献图会亮 |
| `dev@example.com`（现在的值） | ⚠️ 提交归属不到任何账号，显示成一个灰色默认头像 |
| `12345678+liang-xiangyao@users.noreply.github.com` | ✅ 也能关联，且不暴露真实邮箱 |

不知道 GitHub 给的那个 noreply 地址？登录 GitHub →
右上头像 → Settings → Emails → 勾选 `Keep my email addresses private`，
页面上会显示 `xxxxx+你的用户名@users.noreply.github.com`。

> **关于已有的 83 个提交**：它们用的是 `dev@example.com`。想让它们也关联到你的账号，
> 需要在推之前改写历史（见本文末尾「可选：让 83 个提交都关联到你的账号」）。
> 不改也能正常推送，只是头像不对。

验证：

```bash
git config --global user.name
git config --global user.email
```

两行都输出你的值就成功了。

---

## 第 2 步：在 GitHub 建一个**空**仓库（3 分钟）

浏览器打开 **https://github.com/new**

按下面填，**一个字都别多勾**：

| 页面上叫什么 | 填什么 |
| --- | --- |
| `Repository name` | `paper-recycle-agent` |
| `Description` | 可留空，或写「废纸回收 Agent 对话助手」 |
| `Public` / `Private` | 作品集展示选 **Public**；只想自己看选 Private |
| `Add a README file` | ☐ **不要勾** |
| `Add .gitignore` | ☐ **不要勾** |
| `Choose a license` | ☐ **不要勾** |

点绿色按钮 **`Create repository`**。

### 为什么三个都不能勾

勾了任何一个，GitHub 会先在远端建一个提交（比如自动生成的 README）。
你本地也有一份 README，两边历史不相干，`git push` 会直接被拒：

```
! [rejected]  main -> main (fetch first)
error: failed to push some refs to 'https://github.com/...'
hint: Updates were rejected because the remote contains work that you do not have locally.
```

这是第一次上传**最常见的失败**。真遇到了也别慌，补救方法在最后的报错表里。

建完之后你会看到一个空仓库页面，中间显示「Quick setup」和一段
`git remote add origin ...` 的命令。**先别照着它敲**，第 4 步有更省事的办法。

---

## 第 3 步：生成 Personal Access Token（3 分钟）

GitHub 从 2021 年起**不接受账号密码**。`git push` 弹出密码框时，
密码位置必须填 Token，否则你会看到：

```
remote: Support for password authentication was removed on August 13, 2021.
fatal: Authentication failed for 'https://github.com/...'
```

生成步骤，一步别漏：

1. 登录 GitHub，点右上角头像 → **`Settings`**
2. 左侧栏拉到最底 → **`Developer settings`**
3. 左侧 → **`Personal access tokens`** → **`Tokens (classic)`**
4. 右上 → **`Generate new token`** → **`Generate new token (classic)`**
5. 填写：
   - `Note`：随便写，比如 `paper-recycle-agent push`
   - `Expiration`：选 `90 days`（别选 No expiration）
   - `Select scopes`：**只勾 `repo` 这一个**（它包含下面所有子项）
6. 拉到最底 → **`Generate token`**
7. 页面顶部出现一串 `ghp_xxxxxxxx...` —— **只显示这一次，立刻复制到记事本**

> 这串东西等于你的账号权限，别贴到聊天窗口、别提交进仓库。
> 本项目已经把 `config/llm.json` 之类加进 `.gitignore`，但 Token 你自己要收好。

---

## 第 4 步：推送（1 分钟）

### 推荐：用仓库里的脚本

在 Git Bash 里 `cd` 到项目目录：

```bash
cd "C:/Users/liang/WorkBuddy AI/2026-10-22-20-36-39/paper-recycle-agent"
bash tools/push_to_github.sh 你的GitHub用户名
```

脚本会依次做四件事，每步都会打印结果：

```
[1/4] 体检
  是 git 仓库
  工作区干净
  无敏感文件入库（config/llm.json、data/*.csv 均未跟踪）
  提交 83 个，标签 7 个
  git 身份已配置

[2/4] 远端配置
  目标：https://github.com/你的用户名/paper-recycle-agent.git

[3/4] 推送 main 与全部 tag
  ← 这里会弹出登录框，见下方说明
```

**弹出登录窗口时**：

| 框里要什么 | 填什么 |
| --- | --- |
| `Username` | 你的 GitHub 用户名（不是邮箱） |
| `Password` / `Token` | **粘贴第 3 步的 `ghp_...`** |

看到 `分支与标签均已推送` 就成功了。

### 手动方式（想自己敲）

```bash
git remote add origin https://github.com/你的用户名/paper-recycle-agent.git
git push -u origin main
git push origin --all      # 16 个 feature/fix 分支，别漏
git push origin --tags     # 7 个版本标签
```

**`--all` 这一行不能省**。只推 `main` 的话，GitHub 上只有一个线性历史，
别人看不到「开分支 → 分主题提交 → 合并」的过程，连续开发的证据就丢了一半。
推上去之后 `/branches` 页面应该能看到 16 个分支。

> 如果 `git remote add` 报 `remote origin already exists`，说明之前配过，
> 用 `git remote set-url origin https://github.com/你的用户名/paper-recycle-agent.git` 改地址。

---

## 第 5 步：验证真的成功了（1 分钟）

浏览器打开：

```
https://github.com/你的用户名/paper-recycle-agent
```

逐项对照，**每一项都能查到才算真的成了**：

| 检查 | 应该看到 |
| --- | --- |
| 文件列表 | `README.md`、`src/`、`app/`、`docs/`、`tools/` 等 60 个文件 |
| README 渲染 | 中文正常显示，徽章不是裂图，有「上传到 GitHub」这一节 |
| 提交数 | 文件列表右上方显示 `80+ Commits` |
| **分支数** | `/branches` 页面能看到 16 个 `feature/*` 或 `fix/*` 分支（**这是「连续开发」最直观的证据**） |
| 标签 | `/tags` 页面能看到 v1.0.0 ~ v1.6.2 共 7 个 |
| 合并轨迹 | `/network` 页面能看到分支线汇入 main，不是一条直线 |
| 默认分支 | 左上角显示 `main` |

再看一眼 Actions（可选）：

```
https://github.com/你的用户名/paper-recycle-agent/actions
```

第一次推送会自动触发 CI，跑 Python 3.8 / 3.11 / 3.13 三个版本 + 3.7 零依赖 job。
绿勾表示全部通过；红叉点进去看日志（通常是 openpyxl 没装，不影响核心功能）。

---

## 常见报错对照表

按报错信息查，找到对应的原因和处理。

### `Updates were rejected because the remote contains work that you do not have locally`

**原因**：建仓库时勾了 README / .gitignore / license，远端已有提交。

**处理**（保留本地版本，覆盖远端那个自动生成的提交）：

```bash
git pull --rebase origin main --allow-unrelated-histories
# 如果提示冲突，解决后：
git add -A && git rebase --continue
git push -u origin main
```

**或者更干脆**——删掉远端仓库重建，这次三个勾都别勾。

### `Support for password authentication was removed`

**原因**：密码框里填了账号密码。

**处理**：重新推一次，密码位置改填 `ghp_...` 的 Token。

Windows 会把错的凭据记住，先清掉：

```
控制面板 → 用户账户 → 凭据管理器 → Windows 凭据
找到 git:https://github.com，删除
```

### `Permission denied (publickey)`

**原因**：用了 SSH 地址 `git@github.com:...`，但没配密钥。

**处理**：要么换回 HTTPS：

```bash
git remote set-url origin https://github.com/你的用户名/paper-recycle-agent.git
```

要么配 SSH（见下方「可选：用 SSH 免密」）。

### `remote: Repository not found`

**原因**：仓库名或用户名拼错，或者仓库是 Private 但 Token 没勾 `repo` 权限。

**处理**：打开 `https://github.com/你的用户名/paper-recycle-agent` 确认这个页面存在。
不存在就是拼错了，用 `git remote set-url` 改成正确的。

### `fatal: not a git repository`

**原因**：当前目录不对。

**处理**：

```bash
cd "C:/Users/liang/WorkBuddy AI/2026-10-22-20-36-39/paper-recycle-agent"
```

### `src refspec main does not match any`

**原因**：本地分支不叫 `main`。

**处理**：

```bash
git branch --show-current     # 看当前叫什么
git push -u origin HEAD:main  # 强制推到远端 main
```

### `RPC failed; curl 56 ...` 或推一半断掉

**原因**：网络不稳，或者仓库超过 100MB（本项目 1.5MB，不太可能）。

**处理**：把单次推送的缓冲区调大，再重试：

```bash
git config --global http.postBuffer 524288000
git push -u origin main
```

---

## 可选：用 SSH 免密（配一次，以后不用输 Token）

```bash
ssh-keygen -t ed25519 -C "你的邮箱"        # 连按三次回车，不设密码
cat ~/.ssh/id_ed25519.pub                  # 复制输出的整行
```

复制后：GitHub → 右上头像 → `Settings` → `SSH and GPG keys` →
`New SSH key` → `Title` 随便写 → `Key` 粘贴 → `Add SSH key`。

改远端地址：

```bash
git remote set-url origin git@github.com:你的用户名/paper-recycle-agent.git
ssh -T git@github.com     # 看到 "Hi 你的用户名!" 就成了
git push -u origin main
git push origin --all --tags
```

---

## 可选：让全部历史提交都关联到你的账号

现在的提交邮箱是 `dev@example.com`（占位符），推到 GitHub 后归属不到你。
如果这个仓库要当作品集展示，改一下更专业。

**前提**：第 1 步已经把全局 `user.email` 配成你的 GitHub 邮箱。

**先备份**（重要，改写历史不可逆）：

```bash
cd "C:/Users/liang/WorkBuddy AI/2026-10-22-20-36-39/paper-recycle-agent"
git bundle create ../paper-recycle-backup.bundle --all
```

**再改写**：

```bash
NEW_EMAIL="你的GitHub邮箱"
git filter-branch -f --env-filter "
  export GIT_AUTHOR_EMAIL='$NEW_EMAIL'
  export GIT_COMMITTER_EMAIL='$NEW_EMAIL'
" --tag-name-filter cat -- --all
```

**验证**：

```bash
git log --pretty="%an <%ae>" | sort -u
# 应该只剩一行，邮箱是你的
```

**清理**：

```bash
git for-each-ref --format='%(refname)' refs/original | xargs -n1 git update-ref -d
git reflog expire --expire=now --all
git gc --prune=now
```

> ⚠️ 改写会让所有 commit 的哈希值变掉。如果**已经推过**，改完必须
> `git push --force`，而 force push 会覆盖远端历史。所以：**要在第一次推送之前改**。

---

## 可选：把 Issue 和里程碑真实建出来

commit message 里写了 `closes #26`、`Merge PR #19`，但 GitHub 上还没有这些东西。
补建需要 gh CLI：

1. 装：https://cli.github.com/ （Windows 下 `winget install GitHub.cli`）
2. 登录：`gh auth login`，选 `GitHub.com` → `HTTPS` → `Y` → 浏览器授权
3. 预演：`bash tools/publish_to_github.sh`（只打印，不创建）
4. 执行：`bash tools/publish_to_github.sh --apply`

**必须在仓库还没有任何 Issue / PR 时跑**。Issue 编号是仓库级序列（和 PR 共享），
一旦有别的对象占了号，`closes #26` 就对不上了。

---

## 上传之后可以做的事

| 想做什么 | 怎么做 |
| --- | --- |
| 让仓库更好搜 | Settings → 加 `Description` 和 `Topics`（`paper-recycling`、`agent`、`fastapi`、`china`） |
| 挂个在线预览 | 用 GitHub Pages 托管 `dist/paper-recycle-offline.html`（Settings → Pages） |
| 让别人能装 | `pip install git+https://github.com/你的用户名/paper-recycle-agent.git` |
| 保护主分支 | Settings → Branches → 加规则，要求 PR + CI 通过才能合 |
| 发个 Release | 右侧 `Releases` → `Draft a new release` → 选 `v1.6.2` 标签 |

---

## 一页速查

```bash
# 1. 配身份
git config --global user.name "liang-xiangyao"
git config --global user.email "你的GitHub邮箱"

# 2. 网页建空仓库（三个勾都别勾）
#    https://github.com/new

# 3. 生成 Token（只勾 repo 权限）
#    https://github.com/settings/tokens

# 4. 推送
cd "C:/Users/liang/WorkBuddy AI/2026-10-22-20-36-39/paper-recycle-agent"
bash tools/push_to_github.sh 你的用户名
#    Username: 你的用户名
#    Password: ghp_...（Token）

# 5. 验证
#    https://github.com/你的用户名/paper-recycle-agent
```
