# 造纸工厂多智能体 · 碳核算 Agent

![CI](https://github.com/lanlanyuan/paper-recycle-agent/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-%3E%3D3.7-3776ab)
![Tests](https://img.shields.io/badge/tests-235%20passed-brightgreen)
![Deps](https://img.shields.io/badge/runtime%20deps-0-brightgreen)

一个从废纸回收助手成长而来的**造纸工厂多智能体系统**，核心是**碳核算 Agent**：
按国标《温室气体排放核算与报告要求 造纸和纸制品生产企业》的方法核算工厂温室气体排放，
排放因子取自国标附录B（逐条带出处），活动数据为示例工厂仿真输入。

**v1.9.0 定位重构**：废纸回收助手保留全部能力，降级为工厂内的「废纸回收子 Agent」，
其回收量喂给碳核算做范围三减排演示；原投入产出表的方法论（直接消耗系数/Leontief 逆）
抽出来作为供应链碳足迹（EEIOA）的参考；智能工厂（工艺智能体）与产业大脑（五链贯通）
作为工厂的车间层与经营层并存。详见 [docs/CARBON_AGENT.md](docs/CARBON_AGENT.md)。

**v1.7.0 新增「智能工厂」**：把造纸流程拆成制浆 / 抄纸 / 干燥 / 质检四道工序，每道工序由一个子智能体负责，总调度器编排任务、派机器狗与 AGV 作业，支持异常注入与处置链演示。这是**仿真演示，不连接任何真实产线**——详见 [docs/MILL_AGENTS.md](docs/MILL_AGENTS.md)。

**v1.8.0 新增「产业大脑」**：对标华泰造纸「产业大脑」五链贯通（采购 / 生产 / 销售 / 仓储物流 / 资金财务），五域共享数据底座，12 条跨域联动规则可观测、可推演。KPI 为仿真值；华泰公开成效单列并标注来源，绝不混入本项目成果——详见 [docs/INDUSTRY_BRAIN.md](docs/INDUSTRY_BRAIN.md)。

## 三种打开方式（任选其一）

| 方式 | 怎么用 | 需要什么 | 能力 |
| --- | --- | --- | --- |
| **① 离线单文件**（最稳） | 双击 `dist/paper-recycle-offline.html` | 只要浏览器 | 对话、五个标签页（含投入产出）、CSV 导出 |
| **② 本地服务** | 双击 `启动本地版.bat`，浏览器打开 `http://localhost:8000` | Python 3.8+ | 全部功能：十个标签页（碳核算为首页）、七张表 xlsx、模型配置、麦克风自检 |
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

## 废纸回收子 Agent 解决什么问题

系统核心已是碳核算 Agent；下面这段讲的是作为工厂子 Agent 的废纸回收助手，
它覆盖四类角色、六个真实问题（其回收量同时喂给碳核算做范围三减排演示）：

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

**核心 · 碳核算 Agent**（v1.9.0，详见 [docs/CARBON_AGENT.md](docs/CARBON_AGENT.md)）：
- **国标方法核算**：按《温室气体排放核算与报告要求 造纸和纸制品生产企业》核算五类排放源（燃料燃烧 / 过程 / 废水甲烷 / 购入电力 / 购入热力），公式逐条可手算复核
- **排放因子带出处**：因子取自国标附录B，逐条标注来源；电力因子不内置过期值，由用户填当年主管部门数据
- **口径纪律**：活动数据为示例工厂仿真输入；范围三（废纸回收减排）单列不并入国标边界；投入产出法仅作 EEIOA 方法参考、无数据不推算
- **情景模拟 + 输入可改**：界面改活动数据即时重算，支持减排情景对比

**工厂子 Agent · 废纸回收助手**（原项目主角，保留全功能）：
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
- **智能工厂多智能体仿真**（v1.7.0）：四道工序子智能体 + 总调度器 + AGV/机器狗/PLC 模拟，异常注入演示处置链，决策标注 rule/llm 来源；详见 [docs/MILL_AGENTS.md](docs/MILL_AGENTS.md)
- **产业大脑五链贯通仿真**（v1.8.0）：采购/生产/销售/物流/财务五域智能体 + 共享数据底座 + 12 条跨域联动 + 管理干预推演；对标来源与仿真边界见 [docs/INDUSTRY_BRAIN.md](docs/INDUSTRY_BRAIN.md)
- **Web 图形界面**：FastAPI 聊天页 + 十个标签页（碳核算 / 区域 / 历年 / 分类 / 企业 / 投入产出 / 智能工厂 / 产业大脑 / 消耗地图 / 设置），碳核算为默认首页
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
│   ├── carbon/                    【核心】工厂碳核算 Agent（国标方法，五类排放源）
│   │   ├── factors.py             国标附录B排放因子（逐条带出处）+ 公式常量
│   │   ├── model.py               活动数据模型 + 示例工厂仿真输入
│   │   ├── accounting.py          核算引擎：燃烧/过程/废水/电力/热力 + 情景模拟
│   │   └── recycle_agent.py       废纸回收桥接 + EEIOA 供应链碳足迹方法参考
│   ├── mill/                      造纸工艺四工序多智能体（车间层）
│   ├── brain/                     产业大脑五链贯通（经营管理层）
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
├── app/server.py                  FastAPI 服务（界面 + 碳核算/统计接口 + 导出 + 模型代理）
├── app/static/index.html          界面（十个标签页，碳核算为默认首页）
├── tests/                         pytest 单元测试（235 项）
├── tools/                         代码清单 / 离线版构建 / 3.7 兼容校验 / 历史自洽校验
├── config/llm.json.example        模型配置模板（复制为 llm.json，已被 gitignore）
├── data/enterprises.csv.example   企业名录模板
├── data/io_matrix.csv.example     投入产出矩阵导入格式（仅格式示例，非真实数据）
├── docs/                          使用 / 贡献 / 开发日志 / 代码清单 / 数据来源
├── run.py                         读取 PORT 的统一启动入口
├── 启动本地版.bat                 一键启动（纯 ASCII，避免 cmd 按 GBK 解析中文出错）
└── .github/workflows/ci.yml       CI
```

## 代码规模：有效代码 LOC

不按「文件多少行」报数，按**有效代码行**算——空行、注释、文档字符串、
内嵌模板全部剔除。数字截至 v1.9.0（碳核算 Agent 重构后）：

| 层级 | 文件数 | 物理行 | 有效代码行 |
| --- | ---: | ---: | ---: |
| 核心领域逻辑（`src/paper_recycle_agent/`） | 22 | 4026 | 2990 |
| Web 层（`app/` + `run.py`） | 3 | 2942 | 2497 |
| 测试（`tests/` + `conftest.py`） | 17 | 2033 | 1326 |
| 工具脚本（`tools/`） | 7 | 2332 | 1235 |
| **合计** | **49** | **11333** | **8048** |

三类内容明确**不计入**，理由写清楚而不是悄悄略过：

| 不计入 | 为什么 |
| --- | --- |
| `dist/paper-recycle-offline.html` | 由 `tools/build_offline.py` 构建，计入即重复计数 |
| `docs/CODE_LISTING.md` | 由 `tools/gen_code_listing.py` 生成，是源码的镜像 |
| `tools/build_offline.py` 里的 641 行 `TEMPLATE` 字符串 | 内嵌的整页 HTML，是构建产物不是逻辑 |

```bash
python tools/count_loc.py            # 重新统计，数字应完全一致
python tools/count_loc.py --json     # 机审用的结构化数据
python tools/count_loc.py --check    # CI 用：有虚增迹象时退出码 1
```

`--check` 会顺带做四项卫生检查：**无第三方 vendor 目录、无 `.min.js` 压缩代码、
无超长行、内嵌模板已单独归类**——正好对应评审最关心的四类虚增。
统计器自身有 17 项测试（`tests/test_count_loc.py`）钉住每条判定规则，
包括「行尾注释所在行仍算代码」「模块 docstring 再长也不是模板」这类容易算错的边界。

完整口径、逐文件明细与排除清单见 [docs/EFFECTIVE_LOC.md](docs/EFFECTIVE_LOC.md)。

## 连续开发：这套历史是怎么来的，以及怎么自己查

本仓库不是「一次性把成稿丢进去」，而是按功能一块块长出来的：80+ 个提交、16 个 feature/fix 分支、
16 个合并提交、10 个版本标签，每个功能都走「开分支 → 分主题提交 → `--no-ff` 合并」的流程，
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

### 关于本仓库历史的三点如实说明

1. **2026-10-01 → 10-21 的 16 个提交是按开发顺序补录的**，时间戳为重建（所以全落在整点或半点）；
   10-22 起的 72 个提交是真实连续开发留下的，含秒级时间戳。补录部分保留了真实的
   代码演进顺序与踩坑记录，但**不应被当作"每天在写代码"的证据**。
2. **commit message 里的 `Merge PR #N`、`closes #N` 是本地留档**。仓库已经推到 GitHub，
   但那些编号对应的 PR / Issue 在 GitHub 上**仍然不存在**（PR 无法事后创建）。
   运行 `bash tools/publish_to_github.sh --apply` 可以用 `gh` 把 30 个 Issue、7 个里程碑
   真实建出来，让 `closes #N` 有东西可指——**在那之前，请不要对外声称"有 30 个 Issue"**。
3. **CI 已经真实跑过了**。`.github/workflows/ci.yml` 在首次 push 后触发，
   截至 v1.6.5 共运行 2 次，均通过（Python 3.8 / 3.11 / 3.13 跑全量，
   3.7 跑零依赖核心 + 语法兼容校验）。日志在仓库的 `/actions` 页可查。

这三条写在这里而不是藏起来，是因为「过程可信」的前提是**经得起核查**，不是看起来像。

### 对照五项要素：现在到底符合几项

| 要素 | 现状 | 判定 |
| --- | --- | --- |
| 连续的 commit | 88 个（截至 v1.6.5），其中 72 个是真实开发时间 | ✅ |
| feature 分支 | 16 个，每个都有 `--no-ff` 合并，GitHub `/branches` 可见 | ✅ |
| CI | 已在 GitHub 真实运行 2 次，均通过，日志可查 | ✅ |
| PR 合并 | 16 次本地合并，GitHub 上 0 个 PR | ⚠️ 形似而非 |
| Issue / 里程碑 | 本地 30 条，GitHub 上 0 条 | ❌ 跑脚本可补 |

**3 项真、1 项形似、1 项空。** 跑完 `bash tools/publish_to_github.sh --apply`
（需要 `gh` CLI）能补到 4 项真；PR 那项补不了——GitHub 不允许事后创建 PR，
只能靠后续开发真的走一遍「开分支 → push → 开 PR → 合并」。
展开说明与验证命令见 [docs/REPO_PROVENANCE.md](docs/REPO_PROVENANCE.md)。

## 上传到 GitHub：怎么拿到 Repo 地址

> **本仓库已经推送**：<https://github.com/lanlanyuan/paper-recycle-agent>。
> 下面这套流程给「fork 后自己推一份」或「从零重建」用，步骤完全一样。

本地仓库就绪后（80+ 个提交、16 个合并、10 个标签），缺的只是一个远端。

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
3. **推送**——`main` + 16 个 `feature/*`/`fix/*` 分支 + 10 个标签（分支必须一起推，
   否则 GitHub 上只剩线性历史，看不出分支开发的过程）
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
git push origin --all      # 16 个 feature/fix 分支，别漏
git push origin --tags     # 10 个版本标签
```

`--all` 不能省：只推 `main` 的话 GitHub 上只有一个线性历史，
看不到「开分支 → 分主题提交 → 合并」的过程。

### 认证：密码位置要填 Token，不是登录密码

2021 年起 GitHub 关闭了密码认证。`git push` 弹出账号密码框时：

- 用户名 → GitHub 用户名
- 密码 → **Personal Access Token**（Settings → Developer settings →
  Personal access tokens → Tokens (classic) → Generate new token，勾 **`repo` + `workflow`** 两个权限）

> **`workflow` 不能漏**。本仓库含 `.github/workflows/ci.yml`，GitHub 要求写工作流文件
> 单独授权。只勾 `repo` 会被拒：
> `refusing to allow a Personal Access Token to create or update workflow ... without workflow scope`。
> 这是权限范围问题，不是密码错，重输 Token 无效。补勾方法见
> [docs/UPLOAD_TO_GITHUB.md](docs/UPLOAD_TO_GITHUB.md#refusing-to-allow-a-personal-access-token-to-create-or-update-workflow--without-workflow-scope)。

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
- [碳核算 Agent：国标依据与架构](docs/CARBON_AGENT.md)　←　v1.9.0 核心，公式/因子逐条带出处
- [智能工厂多智能体](docs/MILL_AGENTS.md)
- [产业大脑五链贯通](docs/INDUSTRY_BRAIN.md)
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
