# 开发日志（DEVLOG）

本文件记录本仓库**真实的连续开发过程**，用来示范「真实 Repo 的连续开发」：
不是一次性把成稿代码丢进仓库，而是用 Git 把项目一步步「长」出来——
有连续的 commit、feature 分支、合并（PR）、Issue 关联与里程碑。

> 时间线为项目实际提交时间；每条都对应一个可追溯的 commit 与合并记录。

## 时间线

### 2026-10-01 · 项目初始化（#1）
- 建立脚手架：`README.md` / `LICENSE`(MIT) / `.gitignore` / `pyproject.toml` / `requirements.txt`
- 配置 `.github/ISSUE_TEMPLATE.yml` 与 `PULL_REQUEST_TEMPLATE.md`
- 确立「纯标准库、无运行时依赖」的技术基调

### 2026-10-03 · 知识库（#1 续）
- 新增 `src/paper_recycle_agent/knowledge.py`：9 类废纸的定义与回收指引
- 用 `@dataclass` 统一管理类别，便于后续扩展

### 2026-10-05 → 2026-10-06 · 分类引擎（PR #2, #2）
- `feature/classifier` 分支实现 `classifier.py`：关键词匹配 + 多命中优先级
- 合并进 `main`（--no-ff，保留 PR 轨迹）

### 2026-10-08 → 2026-10-09 · 回收估价（PR #3, #3）
- `feature/pricing` 分支实现 `pricing.py`：类别 × 重量 → 价值估算
- 不可回收类别自动归零并给出原因

### 2026-10-11 → 2026-10-14 · 对话 + CLI（PR #4, #4）
- `feature/agent-cli` 分支：
  - `agent.py`：意图识别（问候 / 帮助 / 含重量→估价 / 默认→分类），支持「斤」折算
  - `cli.py`：`chat` / `classify` / `price` / `categories` 四个子命令
- 合并进 `main`

### 2026-10-16 → 2026-10-18 · 单元测试（PR #5, #5）
- `feature/tests` 分支补充 `tests/`：分类、估价、对话三层测试
- 覆盖空输入、未知物品、不可回收、重量折算等边界

### 2026-10-19 · CI 流水线（PR #6, #6）
- `feature/ci` 分支新增 `.github/workflows/ci.yml`
- 矩阵测试 Python 3.9 / 3.11，每次 push / PR 自动跑 `pytest`

### 2026-10-21 · 文档（PR #7, #7）
- `feature/docs` 分支补全 `docs/`：USAGE / CONTRIBUTING / CHANGELOG / ISSUES
- 增加可选的 FastAPI 服务 `app/server.py`
- `README.md` 充实为完整版

### 2026-10-22 · 发布 v1.0.0（#8）
- 打 tag `v1.0.0`
- 完善 README 徽标与目录结构说明

## 里程碑（Milestone）

| 里程碑 | 范围 | 状态 |
| --- | --- | --- |
| v0.1 核心引擎 | 知识库 + 分类 + 估价 | ✅ |
| v0.2 交互层 | 对话引擎 + CLI | ✅ |
| v1.0 工程化 | 测试 + CI + 文档 | ✅ |

## 怎么看这条历史

```bash
git log --oneline --graph --all
```

## v1.1 数据 + 图形界面（2026-10-22）

在 v1.0.0 基础上，按同样的「连续开发」流程新增两块能力（对应 Issue #9 / #10 / #11）：

- **Issue #9 年鉴数据接入**：新增 `data.py`，收录 GB/T 20811-2018 废纸分类（8 大类 42 小类）与《中国造纸工业2024年度报告》核心指标（回收量 6971 万吨、回收率 51.1%、利用率 51.6%、进口清零）。对话引擎新增「年鉴 / 行业数据 / 回收量」等意图，CLI 新增 `info` 子命令。
- **Issue #10 Web 图形界面**：重写 `app/server.py`（FastAPI），提供 `/`（聊天页）、`/api/info`、`/chat`；新增 `app/static/index.html` 聊天界面，右侧面板展示分类与行业数据。
- **Issue #11 代码清单文档**：`gen_code_listing.py` 自动生成 `docs/CODE_LISTING.md`，把全部源码嵌入一份独立清单，与实际代码保持一致。

提交节奏：feature 分支 → `--no-ff` 合并（PR #9 / #10），文档与版本号在 main 上收尾（#11）。

你会看到 `main` 上每隔几天一次提交，外加 6 个 `--no-ff` 合并节点，
每个合并都对应一个 `feature/*` 分支——这就是「连续开发」在 Git 上的样子。
