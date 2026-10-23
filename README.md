# 废纸回收 Agent 对话助手

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-%3E%3D3.7-3776ab)
![Tests](https://img.shields.io/badge/tests-169%20passed-brightgreen)
![Deps](https://img.shields.io/badge/runtime%20deps-0-brightgreen)

> CI 徽章需要仓库地址：把下面这行里的 `OWNER/REPO` 换成你的 GitHub 用户名与仓库名后取消注释。
> 在此之前不放，是为了避免 README 上出现一个 404 的破图。
>
> `![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)`

一个轻量级、纯标准库实现的废纸回收助手：识别废纸类型、判断是否可回收、按重量估算回收价值，并接入《中国造纸年鉴》/行业报告的废纸分类与行业数据，提供命令行与 Web 图形界面。

## 三种打开方式（任选其一）

| 方式 | 怎么用 | 需要什么 | 能力 |
| --- | --- | --- | --- |
| **① 离线单文件**（最稳） | 双击 `dist/paper-recycle-offline.html` | 只要浏览器 | 对话、五个标签页（含投入产出）、CSV 导出 |
| **② 本地服务** | 双击 `启动本地版.bat`，浏览器打开 `http://localhost:8000` | Python 3.8+ | 全部功能：七张表 xlsx、消耗地图、模型配置、麦克风自检 |
| **③ 自行部署**（可选） | `uvicorn app.server:app` 后挂到任意容器 / 平台 | Python 3.8+ | 同 ② |

> 打不开线上链接时，先用 ① —— 它是单个 HTML 文件，数据全部内联，不联网、不起服务、双击即开。

## 运行环境：分三档，别被 3.9 吓到

核心包**零依赖**，只用 Python 标准库（唯一的版本门槛是 `dataclasses`，Python 3.7 引入）：

| 能力 | 最低 Python | 需要装什么 |
| --- | --- | --- |
| 命令行对话 / 统计 / 分类估价 | **3.7** | 什么都不用装 |
| 离线单文件版（已随仓库提供） | **3.7** | 什么都不用装 |
| 导出 `.xlsx` 工作簿 | 3.7 | `pip install openpyxl` |
| Web 图形界面（FastAPI） | 3.8 | `pip install -r requirements.txt` |

`启动本地版.bat` 会自动探测版本并分流：3.8+ 起服务；只有 3.7 时直接打开离线版；没装 Python 会明确告知（Windows 自带的 `python.exe` 常常只是微软商店的跳转桩，双击只会打开商店，并不代表装好了）。

仓库带一个可执行的兼容性校验器，把「支持 3.7」变成可验证的约束而不是口头承诺：

```bash
python tools/check_compat.py     # 用 3.7 语法树解析全部源码 + 扫描 3.8/3.9 专有 API
```


## 这个 Agent 解决什么问题

很多人第一反应是「给统计局做报表」。其实它覆盖四类角色、六个真实问题：

| 角色 | 他们要回答的问题 | 本工具对应的能力 |
| --- | --- | --- |
| **统计 / 协会** | 全国和各省回收量、回收率是多少？这些年怎么变的？ | 全国+省级统计、2014—2025 历年序列、多表 Excel 导出 |
| **行业研究 / 投资** | 八大类各占多少？哪一类在萎缩？进口清零后缺口谁补？ | 八大类拆分、结构插值、废纸进口序列 |
| **回收企业 / 贸易商** | 某个省的货由谁在做？同城有哪些打包厂、纸厂？我能卖给谁？ | 企业名录 + 城市 + 经纬度 + 类型 + 主营品类 |
| **产废单位 / 物业** | 这堆纸能不能回收？大概值多少钱？涉密文件怎么处理？ | 9 类知识库、分类引擎、估价、语音提问 |

### 它到底"新"在哪

1. **把宏观数据和微观主体接上了。** 区域统计回答「一个地方有多少量」，企业维度回答「这些量由谁在做、分布在哪些城市、各品类由哪类企业消化」。两者用「名录覆盖率」串起来（企业合计 ÷ 该省官方回收量），一眼看出样本占全量的比例。
2. **敢说"没有"。** 市县数据、逐类回收量、逐家企业回收量都没有公开权威来源，工具明确标注「测算 / 估算 / 示例」三档，而不是编一个看起来精确的数字。
3. **一个入口覆盖"查—算—导"。** 对话问、界面看、Excel 导，同一套数据口径，不用在三个系统之间对数。

### 典型使用场景

- 统计局：拉某省分类回收量底表 → 导出七表 Excel → 直接进公报核对流程
- 协会：看八大类结构五年变化，判断废新闻纸类萎缩速度
- 回收企业：在「企业分布」里筛「山东 + 造纸企业」，找下游直供对象
- 产废单位：语音问「纸箱 20 斤能卖多少」，或问「涉密文件怎么处理」

## 特性
- 9 类废纸知识库（可回收 / 不可回收及缘由）
- 关键词分类引擎，多命中智能排序
- 重量 × 单价回收估价，支持「斤」折算
- 自然语言对话（问候 / 帮助 / 估价 / 分类）
- 命令行 `chat` / `classify` / `price` / `categories` / `info` / `history` / `catstats` / `io` / `region` / `enterprises` / `export`
- **接入《中国造纸年鉴》废纸分类（GB/T 20811-2018，8 大类 42 小类）与 2024 行业数据**
- **全国 + 省级两级区域统计**（不再提供市/县数据，见下方「数据口径」）
- **历年数据 2014—2025**：回收量、回收率、利用率、废纸进口量
- **按八大类拆分的分类回收量**（占比 × 回收量，含参考价与估算货值）
- **企业维度：企业名录 + 地理位置 + 主营品类 + 年回收量**（可按省 / 大类 / 类型筛选，含地理分布示意图）
- **投入产出视角：废纸消耗金额、直接消耗系数、单位产值消耗**（全国 / 省 / 市 / 企业四级，每级标注口径）
- **正版底图消耗地图**（腾讯位置服务 GL JS，按省级消耗金额打点；无密钥时降级为排行，不画任何边界）
- **模型配置模块**：接入任意 OpenAI 兼容 API（OpenAI / DeepSeek / 通义 / 智谱 / Kimi / 本地 Ollama），未配置时自动回落规则引擎
- **麦克风自检**：真实读取音频流算 RMS，判断「能不能收音」而不只是「有没有权限」
- **一键导出多表 Excel**（省级 / 分类 / 历年 / 进口 / 企业 / 投入产出 / 数据说明 七张表）
- **对话支持语音输入**（浏览器 Web Speech API，失败时在输入框下方显示具体原因）
- **Web 图形界面**：FastAPI 聊天页 + 七个标签页（区域 / 历年 / 分类 / 企业 / 投入产出 / 消耗地图 / 设置）
- **核心零依赖、Python 3.7 起可用**；openpyxl 为可选依赖，缺失时导出接口返回 503 并给出安装提示
- GitHub Actions 多版本 CI（3.8 / 3.11 / 3.13 跑全量，3.7 跑零依赖核心）

## 数据口径（重要）

| 维度 | 数据性质 | 说明 |
|---|---|---|
| 全国 2024 | 官方 | 中国造纸协会《中国造纸工业2024年度报告》 |
| 省级回收量 | 报道 + 测算 | 山东 763、广东 733 为公开报道值；其余 32 个省级行政区为梯队测算并归一化到全国总量 |
| 历年 2014—2025 | 官方 | 中国造纸协会年度报告、《中国造纸》统计表；2025 为初步核算 |
| 八大类占比 | 估算 | 官方未逐类公布回收量，按 2015/2020/2025 三锚点插值 |
| 企业名录 | 示例 | 内置 30 家示例企业（虚构名称），放 `data/enterprises.csv` 即切换为真实名录 |
| 投入产出（全国） | 官方 | 国家统计局全国投入产出表（42 部门）+ 中国造纸协会 2024 年报（营收 1.46 万亿元） |
| 投入产出（省级） | 官方表 + 估算分摊 | 各省均编制本地区投入产出表；本工具的分省金额按回收量占比分摊，**非实际采购分布** |
| 投入产出（地级市） | 估算 | 国家统计局明确「地级市暂不编制投入产出表」，按企业名录城市分布分摊 |
| 投入产出（企业） | 示例 | **不存在「企业投入产出表」**，只有财务报表；金额 = 年经手量 × 市场均价 |

### 投入产出的金额是怎么算的

```
消耗金额(亿元) = Σ(分类消耗量(万吨) × 回收参考价(元/公斤) × 0.1)
直接消耗系数   = 消耗金额 ÷ 造纸和纸制品业营业收入
单位产值消耗   = 消耗量(万吨) ÷ 营业收入(亿元) = 吨/万元
```

参考价是**居民 / 回收站口径**，不含分拣、打包、运输，所以这个金额是**纸厂废纸成本的下限**，
不是到厂采购额。本工具不额外乘一个加价系数——那会引入没有依据的假设，宁可给下限并写明。

`io_table.py` 里实现了 Leontief 逆矩阵、影响力系数、感应度系数（纯标准库高斯消元），
但**仓库不内置任何投入产出矩阵**：编一张看起来权威的假矩阵比不提供更糟。
要用完整模型，请从国家统计局 42 部门表导出 CSV，格式见 `data/io_matrix.csv.example`。

**为什么不提供市、县数据**：市级、县级废纸回收量没有公开的权威逐级统计。早期版本用权重分摊"造"出了市县数据，容易让使用者误以为是真实统计，v1.3.0 起已下线，只保留可核验的两级。替换真实数据的方法见 [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)。

> 投入产出的层级与这个逻辑一致：国家统计局在咨询公开里明确「**目前地级市暂不编制投入产出表**」，
> 企业更是只有财务报表、没有投入产出表。所以这两级的金额一律标「估算 / 示例」，不当官方数据用。

## 地图：为什么默认没有底图

地图只能使用**具备测绘资质的正版底图**（腾讯位置服务 / 高德 / 百度 / 天地图）。
本仓库**不内置任何可用密钥**——内置的 key 一旦推到 GitHub 就等于泄露。

所以默认行为是：

| 情况 | 表现 |
| --- | --- |
| 没配置地图 key | 地图页降级为「省份消耗金额排行」，**不绘制任何边界** |
| 在「设置 → 地图 Key」填了 key | 加载腾讯地图 GL JS 正版底图，按省级金额打点（点大小 = 金额量级） |
| key 无效 / Referer 不匹配 | 提示具体原因并降级为排行 |

申请免费 key：<https://lbs.qq.com/dev/console/application/mine>（选 Web 端，配置 Referer 白名单）。

> 为什么不用开源 GeoJSON 自己画中国地图：自行绘制国界极易出错，而国界、台湾、南海诸岛
> 的绘制有明确的合规红线。用正版底图，边界由持牌方负责；我们只叠加统计数据。

## 模型配置：怎么接 API 思考

「设置」页可以填 Base URL / 模型名 / API Key，保存到服务端 `config/llm.json`（已 gitignore）。
接口只返回脱敏密钥（`sk-…3f9a`），报错信息也会先把密钥替换掉。

```bash
# 或者用环境变量（优先级高于配置文件，适合 CI / 服务器）
export PAPER_LLM_BASE_URL=https://api.deepseek.com/v1
export PAPER_LLM_API_KEY=sk-xxx
export PAPER_LLM_MODEL=deepseek-chat
```

内置预设：OpenAI / DeepSeek / 通义千问（DashScope 兼容模式）/ 智谱 GLM / Kimi / 本地 Ollama。
**没配置也能用**：对话自动回落到 `agent.py` 的规则引擎，工具不会因为缺 key 而不可用。

安全提醒：`config/llm.json` 是明文密钥。本机自用没问题；若把服务暴露到公网，请自行加鉴权，
或改用只读环境变量方式。

## 快速开始
```bash
# 只想用命令行：什么都不用装（Python 3.7+）
PYTHONPATH=src python -m paper_recycle_agent.cli history
PYTHONPATH=src python -m paper_recycle_agent.cli catstats 2024
PYTHONPATH=src python -m paper_recycle_agent.cli region 山东
PYTHONPATH=src python -m paper_recycle_agent.cli io 2024      # 消耗金额 + 直接消耗系数

# 需要 xlsx 导出 / 图形界面
pip install -r requirements.txt   # fastapi + uvicorn + openpyxl + pytest
PYTHONPATH=src python -m paper_recycle_agent.cli export 山东 --year 2024 --out 山东.xlsx
uvicorn app.server:app --reload    # 浏览器打开 http://localhost:8000
```

## 项目结构
```
paper-recycle-agent/
├── src/paper_recycle_agent/       核心包（业务逻辑纯标准库）
│   ├── knowledge.py               知识库（9 类实用回收指引 + 参考价）
│   ├── data.py                    年鉴/行业数据（GB/T 20811-2018 + 2024 报告）
│   ├── stats.py                   历年序列 + 八大类占比与分类回收量
│   ├── regions.py                 全国 + 省级两级统计
│   ├── enterprises.py             企业名录（地理坐标 / 类型 / 主营品类 / 年回收量）
│   ├── io_table.py                投入产出：消耗金额、直接消耗系数、Leontief 逆矩阵
│   ├── llm.py                     模型配置：OpenAI 兼容 API、密钥脱敏、连通性探测
│   ├── exporter.py                多表 Excel 导出（openpyxl，按需导入）
│   ├── classifier.py              分类引擎
│   ├── pricing.py                 估价
│   ├── agent.py                   对话引擎
│   └── cli.py                     命令行
├── app/server.py                  FastAPI 服务（界面 + 统计接口 + 导出 + 模型代理）
├── app/static/index.html          界面（七个标签页）
├── tests/                         pytest 单元测试（169 项）
├── tools/                         代码清单 / 离线版构建 / 3.7 兼容校验 / 历史自洽校验
├── config/llm.json.example        模型配置模板（复制为 llm.json，已被 gitignore）
├── data/enterprises.csv.example   企业名录模板
├── data/io_matrix.csv.example     投入产出矩阵导入格式（仅格式示例，非真实数据）
├── docs/                          使用 / 贡献 / 开发日志 / 代码清单 / 数据来源
├── run.py                         读取 PORT 的统一启动入口
├── 启动本地版.bat                 一键启动（纯 ASCII，避免 cmd 按 GBK 解析中文出错）
└── .github/workflows/ci.yml       CI
```

## 连续开发：这套历史是怎么来的，以及怎么自己查

本仓库不是「一次性把成稿丢进去」，而是按功能一块块长出来的：83 个提交、16 个 feature/fix 分支、
16 个合并提交、7 个版本标签，每个功能都走「开分支 → 分主题提交 → `--no-ff` 合并」的流程，
合并提交里带 `closes #N` 与 PR 编号。

但**光说"我是连续开发的"没有意义**，得能被核查。所以：

```bash
# 1. 时间线自洽：父子提交时间必须严格递增，author 与 committer 必须一致
python tools/check_history.py

# 2. 看分支与合并轨迹
git log --graph --oneline --all --date-order

# 3. 看某个版本是怎么一步步做出来的
git log --oneline v1.4.0..v1.5.0
git show --stat <commit>
```

`tools/check_history.py` 会逐条检查下面这些**可证伪**的约束，任一条不满足就以非零码退出，
CI 每次都会跑：

| 检查项 | 为什么重要 |
| --- | --- |
| 父子提交时间严格递增 | 发布提交不可能早于它要发布的内容 |
| `author date == committer date` | 两者不一致通常意味着历史被事后改过 |
| 每个 feature 分支都有对应 merge commit | 证明是「分支开发 + 合并」，不是直接往 main 上堆 |
| 合并提交使用 `--no-ff`（有两个父提交） | 快进合并会抹掉分支存在过的痕迹 |
| 标签都指向已存在的提交且可达 | 防止出现指向丢失对象的空标签 |
| 提交信息符合 `类型: 描述` 前缀 | 保证变更可分类、可追溯 |

### 关于本仓库历史的两点如实说明

1. **2026-10-01 → 10-21 的 19 个提交是按开发顺序补录的**，时间戳为重建（所以都落在整点）；
   10-22 起的 56 个提交是真实连续开发留下的，含秒级时间戳。补录部分保留了真实的
   代码演进顺序与踩坑记录，但**不应被当作"每天在写代码"的证据**。
2. **commit message 里的 `Merge PR #N`、`closes #N` 是本地留档**。把仓库推上去之前，
   GitHub 上并不存在这些 PR / Issue。推送后运行 `bash tools/publish_to_github.sh --apply`，
   用 `gh` 把 30 个 Issue、7 个里程碑真实建出来，编号才会指向对象——
   **在那之前，请不要对外声称"有 30 个 Issue"**。

这两条写在这里而不是藏起来，是因为「过程可信」的前提是**经得起核查**，不是看起来像。

## 上传到 GitHub：怎么拿到 Repo 地址

本地仓库已经就绪（83 个提交、16 个合并、7 个标签），缺的只是一个远端。

> 需要**一步不落的手把手版本**（含每个报错怎么处理）？
> 见 [docs/UPLOAD_TO_GITHUB.md](docs/UPLOAD_TO_GITHUB.md)。下面是精简版。

### 第一步：建一个**空**仓库

打开 https://github.com/new ，只填两样：

| 字段 | 填什么 |
| --- | --- |
| Repository name | `paper-recycle-agent` |
| Visibility | Public（作品集展示）/ Private 都行 |

**下面三个勾选框全部不要勾**：`Add a README file`、`Add .gitignore`、`Choose a license`。
勾了任何一个，远端就会先有一个提交，`git push` 会被 `non-fast-forward` 拒绝——
这是新手第一次上传最常见的失败原因。

### 第二步：一键推送

```bash
bash tools/push_to_github.sh 你的GitHub用户名
```

脚本按顺序做四件事，任一步失败就停下并说清原因：

1. **体检**——是不是 git 仓库、工作区有没有未提交改动、有没有把 `config/llm.json`
   或 `data/enterprises.csv` 这类含密钥/私有数据的文件误提交（这条是硬拦截）
2. **配远端**——`origin` 已存在就 `set-url`，不会因为重复 `add` 而中断
3. **推送**——`main` 分支 + 全部 7 个标签
4. **收尾**——把 README 顶部的 CI 徽章从注释占位符换成真实地址并推一版

不带参数先跑一次可以只看指引，不碰任何东西：

```bash
bash tools/push_to_github.sh          # 只打印步骤
```

推送成功后，你的 Repo 地址就是：

```
https://github.com/你的GitHub用户名/paper-recycle-agent
```

### 手动方式（不想用脚本）

```bash
git remote add origin https://github.com/你的用户名/paper-recycle-agent.git
git push -u origin main
git push origin --tags
```

### 认证：密码位置要填 Token，不是登录密码

2021 年起 GitHub 关闭了密码认证。`git push` 弹出账号密码框时：

- 用户名 → GitHub 用户名
- 密码 → **Personal Access Token**（Settings → Developer settings →
  Personal access tokens → Tokens (classic) → Generate new token，勾 `repo` 权限）

想免掉每次输入，用 SSH 更省事：

```bash
ssh-keygen -t ed25519 -C "你的邮箱"      # 一路回车
cat ~/.ssh/id_ed25519.pub                # 复制内容到 GitHub → Settings → SSH keys
git remote set-url origin git@github.com:你的用户名/paper-recycle-agent.git
```

### 第三步：让 `closes #26` 真的有东西可指（可选）

需要 [gh CLI](https://cli.github.com/)：

```bash
gh auth login
bash tools/publish_to_github.sh          # 预演，看会建哪些 Issue
bash tools/publish_to_github.sh --apply  # 真的创建
```

脚本会按 `docs/ISSUES.md` 里的顺序建 #1–#30 与 7 个里程碑。**必须在仓库还没有
任何 Issue/PR 时跑**——Issue 编号是仓库级序列，与 PR 共享，一旦有别的对象占号就对不上了。


## 文档
- [使用说明](docs/USAGE.md)
- [上传到 GitHub（手把手）](docs/UPLOAD_TO_GITHUB.md)　←　含 7 种常见报错的处理方法
- [贡献指南](docs/CONTRIBUTING.md)
- [开发日志](docs/DEVLOG.md)
- [更新日志](docs/CHANGELOG.md)
- [代码清单](docs/CODE_LISTING.md)
- [数据来源与口径](docs/DATA_SOURCES.md)
- [仓库历史说明](docs/REPO_PROVENANCE.md)　←　这套"连续开发"里哪些是真的、怎么核查

## License
MIT © 梁湘瑶 / 阿岩
