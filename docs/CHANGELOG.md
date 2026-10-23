# 更新日志（CHANGELOG）

## v1.6.5 (2026-10-23)
**修徽章替换在 Windows 上必然失败的问题（两个坑叠加）。**

用户推送成功后收尾报「替换脚本异常」，README 的 CI 徽章没换掉。查下去是两个独立问题：

- **坑一：`python` 执行失败**。Windows 上 `python` 可能是微软商店的
  App Execution Alias 桩，`command -v` 找得到、执行却返回 9009，
  被 shell 截断成 49，正好落进 `*)` 分支，用户只看到一句「替换脚本异常」。
- **坑二：换行符不匹配**。README 在工作区是 CRLF，而脚本把待匹配的多行文本
  硬编码成 `\n`，`old not in t` 永远成立——即使 python 能跑，也只会静默「跳过」。

- **重写替换逻辑**：改用 `awk`，不依赖任何 Python 环境；用 `index()` 做字面匹配
  而不是正则（避免 `\/` 这类转义在不同 awk 实现里行为不一）；顺带合并连续空行
- **修正 `gh` 安装提示**：原来写 `npm install -g gh`——npm 上那个 `gh` 是无关的
  Node 库，不是 GitHub CLI。改为 `winget install --id GitHub.cli` / `brew install gh`
- **README**：CI 徽章直接指向真实仓库（`lanlanyuan/paper-recycle-agent`），
  删掉占位说明块，清理两处连续空行

验证：把 `python` 换成必失败的商店桩，在本地裸仓库模拟完整推送流程，
五项检查全部通过（占位符清零 / 说明块删除 / 徽章地址正确 / 纯 LF 入库 / 无连续空行）。

## v1.6.4 (2026-10-23)
**修 Token 权限说明：含 workflow 文件的仓库必须多勾一个 `workflow`。**

用户实际推送时被拒：

```
! [remote rejected] main -> main (refusing to allow a Personal Access Token
  to create or update workflow `.github/workflows/ci.yml` without `workflow` scope)
```

根因是本文档和 README 都写着「Token 只勾 `repo` 这一个」——**这句是错的**。
本仓库含 `.github/workflows/ci.yml`，GitHub 要求写工作流文件单独授权，
只有 `repo` 的 Token 连改 README 都推不上去。

- **文档改正**
  - `docs/UPLOAD_TO_GITHUB.md` 第 3 步：`Select scopes` 改为勾 `repo` + `workflow`，
    新增「为什么必须多勾一个 workflow」小节，含完整报错原文与 fine-grained token 的对应设置
  - 报错对照表新增该错误条目：说明它不是密码错（重输 Token 无效），
    给出「给现有 Token 补权限」（Token 字符串不变、凭据不用清）与「重新生成」两条路径
  - README 认证小节同步改正，并链到对照表
- **脚本加固**
  - `push_to_github.sh` 体检阶段检测 `.github/workflows/`，命中就提前提示需要两个权限
  - 推送失败时捕获完整输出并识别该错误，直接打印修法，退出码 3（与普通失败的 2 区分）
  - 新增 `warn` / `yellow` 输出函数

## v1.6.3 (2026-10-23)
**推送范围补全，并把「连续开发」从自述改成逐项对照。**

- `push_to_github.sh` 补 `git push origin --all`——原来只推 `main` + tags，
  16 个 `feature/*`、`fix/*` 分支全留在本地，GitHub 上 `/branches` 与 `/network`
  看不到分支开发的过程，等于把证据丢了一半
- README 与 `docs/REPO_PROVENANCE.md` 新增「对照五项要素」表：
  连续 commit ✅ / feature 分支 ✅ / PR ⚠️ 形似 / CI ❌ / Issue ❌，
  并写明 PR 一项**永远补不了**（GitHub 不允许事后创建 PR）
- 提交数改为区间表述，避免每提交一次就要改文档

## v1.6.2 (2026-10-23)
**准备上传 GitHub：修 README 破图、模板结构、一键推送脚本。**

- **README 修复**
  - CI 徽章原本指向 `your-name/paper-recycle-agent`，真实仓库里是 404 破图。
    改为注释形式并写明替换方法，补 Tests / Deps 两个不需要仓库地址的徽章
  - 「六表 Excel」→「七表」，「四个标签页」→「七个标签页」
  - 项目结构树中文注释宽度不一导致竖线错位，统一对齐
  - 「③ 在线版」改成「③ 自行部署」——没有线上链接就不该写有
  - 新增「上传到 GitHub」章节：建空仓库 → 一键脚本 → 认证说明 → 补建 Issue
- **`.github` 模板结构**
  - `.github/ISSUE_TEMPLATE.yml` 是单文件写法，GitHub 只认
    `.github/ISSUE_TEMPLATE/` 目录下的 `bug_report.yml` / `feature_request.yml` / `config.yml`，
    原来那个文件根本不会被加载。已改成目录结构
- **新增 `tools/push_to_github.sh`**
  - 体检（git 仓库 / 工作区干净 / 无敏感文件 / git 身份已配）→ 配远端 → 推 main + tags
    → 把 README 的 CI 徽章换成真实地址并推一版
  - 不带参数只打印指引，不碰任何东西
- **新增 `tools/check_history.py`**：校验时间线单调、分支有 `--no-ff` 合并、
  标签可达、提交信息规范。CI 每次都会跑
- **新增 `tools/publish_to_github.sh`**：用 `gh` 把 `docs/ISSUES.md` 的 #1–#30
  与里程碑真实建到 GitHub，让 commit message 里的 `closes #26` 不再悬空
- **新增 `.gitattributes`**：全部按 LF 入库，只有 `.bat` 保留 CRLF；
  构建产物标记为 generated
- **修复推送脚本的静默失败**：徽章替换后 `git commit` 因「Author identity unknown」
  失败，但错误被 `2>/dev/null` 吞掉，脚本仍打印成功。现改为体检阶段先查 git 身份，
  去掉 `2>/dev/null`，Python 侧用退出码区分「已替换 / 无需替换 / 出错」
- 测试 159 → 169 项（新增 `tests/test_history.py`）

## v1.6.1 (2026-10-23)
**修复：省级「消耗金额」被错标为官方数据。**

- `province_spend()` 原本在 `quality == "reported"` 时把金额的 `provenance` 设为「官方」，
  但 `reported` 说的是**回收量**来自公开报道，金额本身是「全国金额 × 该省占比」分摊出来的。
  结果是山东 68.4 亿元、广东 65.6 亿元被标成官方——正是本项目一直在防的误读。
  - 金额一律标「估算（分摊）」；回收量口径单独放进 `recovery_provenance`
  - Excel「投入产出」表拆成「金额性质 / 回收量性质」两列，现在读起来是「估算（分摊） | 官方」
  - 界面表头改为「金额口径」，提示语补上「省级虽有官方投入产出表，但本表金额是分摊的」
- 修复命令行摘要里直接消耗系数漏百分号（`4.28` → `4.28%`），并补「属下限」
- 测试同步修正：原来那条「山东的 provenance 必须是官方」的断言本身就写错了，已改写并注明原因
- 测试 158 → 159 项

## v1.6.0 (2026-10-23)
**新增四个模块：投入产出、消耗地图、模型配置、麦克风自检。**

- 新增 `io_table.py`：投入产出视角的消耗金额
  - 全国：官方口径（国家统计局 42 部门投入产出表 + 中国造纸协会 2024 年报营收 1.46 万亿元）
  - 省级：官方表存在，但分省金额按回收量占比分摊，明确标注「非实际采购分布」
  - 地级市：国家统计局明确「地级市暂不编制投入产出表」，按企业名录城市分布分摊
  - 企业：不存在「企业投入产出表」，金额 = 年经手量 × 市场均价，标注「示例」
  - 金额按回收参考价计价，标注为**纸厂废纸成本下限**（不含分拣打包运输），不额外加价推算
  - 实现 `leontief_inverse()` / `influence_coefficients()` / `response_coefficients()`
    （纯标准库高斯消元），并**不内置任何投入产出矩阵**——编假矩阵比不提供更糟
- 新增 `llm.py`：模型配置模块
  - OpenAI 兼容协议，`urllib` 实现，保持零第三方依赖
  - 支持 OpenAI / DeepSeek / 通义 / 智谱 / Kimi / 本地 Ollama 预设
  - 密钥只返回脱敏值（`sk-…3f9a`），报错信息先脱敏再返回
  - 配置优先级：环境变量 > `config/llm.json` > 默认；未配置时自动回落规则引擎
- 新增地图接口 `/api/map/config`、`/api/map/data`
  - 只用腾讯位置服务正版底图，**不内置任何可用密钥**，用显式占位符
  - 无密钥时降级为省份排行，**不自行绘制任何国界**
- 界面新增三个标签页：投入产出 / 消耗地图 / 设置
  - 设置页含模型配置表单与**麦克风自检**（真实读取音频流算 RMS，判断能否收音，
    而不只是判断有没有权限），含设备列表、权限状态、识别实测
- Excel 增加「投入产出」表（共 7 张）
- 对话新增投入产出意图：「废纸消耗金额」「直接消耗系数」「山东废纸消耗金额」
- 离线单文件版增加「投入产出」标签页（地图与模型配置需本地服务版）
- `.gitignore` 增加 `config/llm.json`、`data/io_matrix.csv`、`data/enterprises.csv`
- 测试从 111 项增至 158 项

## v1.5.0 (2026-10-23)
**运行环境门槛下调：Python 下限从 3.9 降到 3.7，核心包彻底零依赖。**

- `requires-python` 改为 `>=3.7`。全仓库唯一的版本门槛是 `dataclasses`（3.7 引入），
  没有使用 walrus / `match` / `removeprefix` / `zoneinfo` 等更高版本的语法与 API
- `openpyxl` 改为**按需导入**：以前它在模块顶层 import，导致没装 openpyxl 的机器
  连 `import paper_recycle_agent` 都会失败；现在只有真正写工作簿时才加载
  - 新增 `exporter.available()`，`build_workbook()` 在缺依赖时抛 `RuntimeError` 并附安装指引
  - `/export.xlsx` 缺 openpyxl 时返回 **503 + JSON 说明**，不再是 500 堆栈
  - 前端新增导出状态行：缺依赖时提前说明，导出失败不再静默下载一个 JSON 文件
- `pyproject.toml` 拆分可选依赖：`[web]` / `[excel]` / `[test]` / `[all]`，核心 `dependencies = []`
- 新增 `tools/check_compat.py`：用 3.7 语法树解析全部源码，并扫描 3.8/3.9 专有 API
  与未启用 `from __future__ import annotations` 时的内置泛型注解，可接入 CI
- `启动本地版.bat` 重写：
  - 实测候选解释器能否执行 Python 代码，识破 Windows「微软商店跳转桩」（`python.exe` 只是跳转器）
  - 按版本分流：3.8+ 起服务；3.7 打开零依赖离线版；无 Python 给出下载地址与离线版路径
  - 离线版缺失时自动构建，不再只报错
  - 新增 `--check` 只报告检测结果，便于排障
  - 内容改为**纯 ASCII**：cmd.exe 按控制台代码页解析 `.bat`，UTF-8 中文会切断逻辑，
    UTF-8 BOM 还会让 `@echo off` 失效（已实测）
- `dist/paper-recycle-offline.html` 纳入版本库：它的卖点是「不装任何东西也能打开」，
  若还需先装 Python 来生成就自相矛盾了
- CI 改为 3.8 / 3.11 / 3.13 跑全量 + 独立 3.7 job 跑零依赖核心，并执行兼容性校验
- `tests/test_exporter.py` 改用 `importorskip`，没装 openpyxl 时跳过而不是让整个套件崩掉
- 测试从 101 项增至 111 项

## v1.4.0 (2026-10-22)
- 新增 `enterprises.py`：企业维度（名称 / 城市 / 经纬度 / 类型 / 主营大类 / 年回收量）
  - 内置 30 家示例企业，覆盖 15 个省级行政区、4 种企业类型
  - 支持按省 / 大类 / 类型筛选，按省、按类、按类型汇总
  - 放 `data/enterprises.csv` 即自动切换为真实名录（`is_demo` 变为 False）
  - 提供名录覆盖率（企业合计 ÷ 该省官方回收量），避免把样本当全量
- 新增 `/api/enterprises` 接口；Excel 增加「企业名录」表（共 6 张）
- 图形界面新增「企业分布」标签页：筛选器 + 经纬度散点示意图 + 类型分布 + 明细表
- 对话引擎新增企业意图：企业名直查、某省企业概览、按类型查企业
- 语音输入重做：每个失败原因都有中文提示（权限拒绝 / 无麦克风 / 网络 / 无语音 / iframe 受限 / 非 HTTPS），
  并实时回显临时识别结果，不再是「按了没反应」
- `regions.find` 支持简称与自然语言（「山东有哪些企业」→ 山东省）
- CLI 新增 `enterprises` 子命令
- 测试从 77 项增至 101 项

## v1.3.1 (2026-10-22)
- 修复 `HEAD /` 返回 405、未知页面路径返回 404（托管环境与预览面板会显示 Not Found）
- 新增兜底路由：未匹配页面回落首页，接口与静态资源仍如实 404
- 新增 `tests/test_server.py`（17 项）与 `conftest.py`

## v1.3.0 (2026-10-22)
**破坏性变更**：移除市级、县级统计，只保留全国 + 省级两级。

- 新增 `stats.py`：2014—2025 年回收量 / 消费量 / 回收率 / 利用率 / 废纸进口量序列
- 新增八大类回收量拆分（GB/T 20811-2018），占比按 2015/2020/2025 三锚点线性插值
- 新增 `exporter.py`：五表 Excel（省级 / 分类 / 历年 / 进口 / 数据说明），支持按省份与年份导出
- `regions.py` 重写：34 个省级行政区，山东 763 万吨、广东 733 万吨为公开报道值，
  其余按行业梯队测算并归一化到全国 6971 万吨（合计严格相等）
- 省级节点新增 `tier` / `tier_label` / `quality` / `rank` / `占全国比重(%)` 字段
- 对话引擎新增「历年趋势」「按类别看回收量」意图，支持从问句里提取年份
- 图形界面重做：区域 / 历年 / 分类三个标签页 + 年份切换 + 条形图
- 接口调整：`/api/stats` 增加 `history`、`categories`、`import_series`、`share_of_national`；
  `/export.xlsx` 支持 `year` 参数，文件名改为 UTF-8 编码
- CLI 新增 `history` / `catstats` / `region` / `export` 子命令
- 测试从 25 项增至 60 项

## v1.2.1 (2026-10-22)
- 修复 `/index.html` 未注册导致预览面板 404（`/` 与 `/index.html` 同时注册）
- 修复 Excel 导出在嵌入式预览中被拦截：改为 `fetch` + Blob 下载，附新窗口兜底
- 页面加 `Cache-Control: no-store`，避免旧版本 HTML 被缓存

## v1.2.0 (2026-10-22)
- 新增 `regions.py`：区域分层统计，支持下钻与汇总
- 新增 `/api/stats`、`/api/regions`、`/export.xlsx`（openpyxl 导出 Excel）
- 图形界面重做：区域统计面板、面包屑、返回上一级、导出按钮；行业标准收进「内部参考」
- 聊天框新增语音输入（浏览器 Web Speech API）
- 测试增至 25 项；CI 改为安装 `requirements.txt`

## v1.1.0 (2026-10-22)
- 新增 `data.py`：GB/T 20811-2018 废纸分类（8 大类 42 小类）+ 2024 行业数据
- 对话引擎支持「年鉴 / 行业数据 / 回收量 / 分类标准」查询；CLI 新增 `info`
- 新增 Web 图形界面：FastAPI + `app/static/index.html` 聊天页（含分类与数据面板）
- 新增 `docs/CODE_LISTING.md` 代码清单文档

## v1.0.0 (2026-10-22)
- 补全使用文档与贡献指南
- 新增 GitHub Actions CI（Python 3.9 / 3.11 矩阵）
- 新增可选 FastAPI 对话服务 `app/server.py`
- 发布正式版本，打 tag `v1.0.0`

## v0.2.0 (2026-10-14)
- 新增对话引擎 `agent.py`（问候 / 帮助 / 估价 / 分类意图）
- 新增命令行 `cli.py`：`chat` / `classify` / `price` / `categories`
- 支持「斤」自动折算为 kg

## v0.1.0 (2026-10-09)
- 建立废纸回收知识库（9 类）
- 实现分类引擎 `classifier.py`
- 实现回收估价 `pricing.py`
