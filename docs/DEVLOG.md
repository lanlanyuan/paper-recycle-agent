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

## v1.2 四级区域统计 + Excel 导出 + 语音输入（2026-10-22）

针对「只能看全国一个数」的问题，按统计局工作场景扩展（Issue #12 / #13 / #14）：

- **Issue #12 四级区域统计**：新增 `regions.py`，覆盖全国 → 34 个省级行政区 → 市 → 县区，
  支持逐级下钻、面包屑与区域汇总。国家级为官方口径，省市县为可替换的分层测算数据（带 provenance）。
- **Issue #12 Excel 导出**：`/export.xlsx?code=...` 用 openpyxl 生成 .xlsx（含表头、合计行、列宽），
  统计局人员可直接下载使用；同时提供 `/api/stats`、`/api/regions` 接口。
- **Issue #13 图形界面**：重做 `app/static/index.html`，右侧为区域统计面板（下钻表格、返回上一级、导出按钮），
  行业标准收进「内部参考」折叠区；聊天框加入 🎤 语音输入（浏览器 Web Speech API）。
- **Issue #14 文档与测试**：补 `tests/test_regions.py`，CI 改为安装 `requirements.txt`（含 openpyxl），
  重新生成 `docs/CODE_LISTING.md`。

你会看到 `main` 上每隔几天一次提交，外加 6 个 `--no-ff` 合并节点，
每个合并都对应一个 `feature/*` 分支——这就是「连续开发」在 Git 上的样子。

## v1.3 两级 + 历年 + 分类（2026-10-22）

这一版做了一次「减法 + 加法」：**减掉市县数据，加上时间维度和类别维度**（Issue #15 / #16 / #17 / #18）。

### 减法：下线市、县两级（#15）

v1.2 的区域树是「全国 → 省 → 市 → 县区」，其中市县两级是按权重分摊生成的。
问题在于：界面看起来是完整的四级统计，但只有全国那一个数是真的。
用户拿到 Excel 无法分辨哪一列能写进公报——这比没有数据更危险。

决策：只保留**全国 + 省级**两级，把 34 个省级行政区的数据性质拆成三档：
- `reported`：山东 763 万吨、广东 733 万吨，公开报道值；
- `estimated`：其余 32 个按行业梯队（>500 / 200–500 / 100–200 / <100 万吨）测算；
- 全部归一化，使 34 省合计**严格等于** 6971 万吨（有测试守着）。

省级的回收率、利用率、企业数、从业人员也明确标注为测算值，不再假装精确。

### 加法一：历年序列（#16）

新增 `stats.py`，收录 2014—2025 年的回收量 / 消费量 / 回收率 / 利用率 / 废纸进口量。
2015、2017、2018 三年公开年报未单列消费量与利用率，**留空而不插值**——
插值出来的曲线很漂亮，但那是我们自己造的趋势，不是行业趋势。

废纸进口单独成表：2017 年 2572 万吨 → 2021 年 54 万吨 → 2022 年起 0，
一根斜线就把「禁废令」讲清楚了，比任何文字都有说服力。

### 加法二：八大类分类回收量（#16）

GB/T 20811-2018 的 8 大类此前只以「分类技术要求」的形式存在，没有量。
这次补上「结构占比 × 官方回收量」：

- 占比在 2015 / 2020 / 2025 三个锚点定义，其余年份线性插值；
- 结构变化有行业逻辑支撑：电商快递拉动废瓦楞纸箱类从 52% → 58%，
  报纸发行量萎缩使废新闻纸类从 13% → 3.5%，垃圾分类后混合废纸类从 5% → 12.5%；
- 每个字段带 `provenance = "估算（行业结构占比 × 官方回收量）"`，界面直接显示。

这样「必须分清楚类别」这条需求才算真的落地：既能按年看，也能按类看，还能按省看。

### 加法三：多表 Excel（#17）

`exporter.py` 生成五张表：省级统计 / 分类回收 / 历年回收 / 废纸进口 / 数据说明。
「数据说明」表专门写清口径、已知差异（6971 vs 6797）、以及如何替换真实数据——
把免责声明放进文件里，而不是只放在网页上。

### 界面重做（#18）

右侧面板改成三个标签页：

- **区域统计**：省级排名表（带条形图）、点击行看该省明细、返回全国；
- **历年数据**：年份选择器 + 回收量走势 + 明细表 + 进口量条形图；
- **分类结构**：八大类占比条形图 + 回收量/货值表 + 行业标准折叠区。

年份选择器是全局的：切到 2020 年，分类回收量和历年明细一起变；
选中某个省时，该省的历史序列与分类量都按「该省占全国比重」折算，保持量级自洽。

### 测试

从 25 项增至 60 项，新增 `test_stats.py`（11 项）与 `test_exporter.py`（10 项），
其中几条是「反造假」测试：
- `test_province_sum_equals_national_total`：34 省合计必须等于全国官方值；
- `test_category_tonnage_sums_to_recovery`：八大类合计必须等于当年回收量；
- `test_category_newsprint_declining`：废新闻纸占比必须逐年下降（结构逻辑不能写反）。

## v1.4 企业维度与语音可诊断（2026-10-22）

### 起因

用户问了两件事：一是「说话无法输入文字」，二是「这个 agent 到底能解决什么问题，
不只帮统计局吧？我想看各企业不同地理位置的回收量和分类」。

第二个问题点到了要害：前四个模块（分类、区域、历年、八大类）都是**宏观口径**，
而真实的统计工作最后一定要落到**企业**身上——某个省的量是谁在做、分布在哪些城市、
各品类分别由哪类企业消化。没有这一层，工具只能看趋势，不能核查。

### 语音为什么"按了没反应"

排查后确认，不是麦克风坏了，而是**错误被吞掉了**。原实现只有一个：

```js
recog.onerror = () => micBtn.classList.remove("listening");
```

Web Speech API 的失败方式很多，全都走这一个回调：
`not-allowed`（用户拒绝权限）、`audio-capture`（没麦克风）、`network`（识别服务连不上）、
`no-speech`（没听到）、`aborted`、`language-not-supported`，以及在 iframe 里被
Permissions Policy 直接拦截。原代码把它们全部无视，用户只会看到按钮闪一下。

重做后：
- 每个 error code 对应一句中文原因 + 该怎么做；
- 启动前做体检（iframe / 非 HTTPS / 浏览器不支持），把注定失败的情况提前说清楚；
- `interimResults = true`，边说边回显，让用户看到"确实在识别"；
- 再点一次按钮 = 停止；`InvalidStateError` 单独提示。

### 企业维度怎么做的

新增 `enterprises.py`，每条记录：名称、省、城市、经纬度、类型、主营大类、年回收量。
四个类型（回收站点 / 分拣打包中心 / 造纸企业 / 贸易商）覆盖了废纸从社区到纸厂的链条。

关键设计是**不假装它是全量**：
- 内置 30 家是示例数据，`is_demo = True`，界面和 Excel 都标「示例」；
- 放 `data/enterprises.csv` 即自动切换为真实名录；
- 摘要里给出「名录覆盖率」= 企业合计 ÷ 该省官方回收量（如山东 4 家 88.9 万吨 = 11.7%），
  让使用者一眼知道这是样本而不是总量。

界面加了「企业分布」标签页：筛选器 + 经纬度散点示意图（点大小 = 年回收量，
颜色 = 企业类型）+ 类型分布 + 明细表。散点没有底图，标题就写明「示意图」——
宁可不画地图，也不画一张看起来精确、实际会误导的假地图。

### 顺带修的

`regions.find("山东有哪些回收企业")` 之前返回 None，因为匹配逻辑要求「山东省」整串出现。
改成建立「全称 + 简称」别名表（山东/广西/内蒙古/香港…），按别名长度倒序匹配，
自然语言里的省名就能命中。

### 测试

77 → 101 项。新增 `test_enterprises.py`（16 项），其中一条是防呆的：
`test_province_volume_not_exceed_official` —— 任何省份的企业合计都不得超过该省官方回收量，
否则说明示例数据编得不合理。

---

### 2026-10-23 · 把运行环境门槛降下来（PR #18, closes #23 #24 #25）

起因是一句话：「我有 python，你不要用 3.9 版本那么高」。

先做体检而不是先改代码：全仓库 grep 了 walrus、`match`、`removeprefix`、`zoneinfo`、
PEP 604 联合类型、f-string 自文档等特性，结果是**一个都没有**。唯一的版本门槛是
`dataclasses`（3.7 引入）。也就是说「需要 3.9」这个声明本身就没有依据——它大概是写
`pyproject.toml` 时随手填的默认值。

#### 真正的拦路石不是语法，是 openpyxl

`exporter.py` 顶层 `from openpyxl import Workbook`，而 `__init__.py` import 了 exporter。
于是「没装 openpyxl」的机器连 `import paper_recycle_agent` 都会失败——命令行、离线版全废。
这跟 Python 版本无关，但它是「换个环境就跑不起来」的主要原因，顺手一起解决：

- 样式对象（`PatternFill` / `Font` / `Border`）改成 `_styles()` 惰性构造并缓存；
- `_require_openpyxl()` 负责导入并抛带安装指引的 `RuntimeError`；
- 新增 `available()`，`/export.xlsx` 缺依赖时返回 503 + JSON 说明；
- 前端加一行状态提示，缺依赖时提前说，失败时显示原因而不是静默下载一个 JSON。

#### 让「支持 3.7」变成可验证的约束

新增 `tools/check_compat.py`：用 `ast.parse(..., feature_version=(3, 7))` 解析每个 `.py`，
再扫 3.8/3.9 专有 API，以及未开 `from __future__ import annotations` 时的内置泛型注解。
写完先拿一个故意违规的文件试了一遍——必须确认它会红，否则这个校验器只是装饰品：

```
· tools/_probe_bad.py:5: `.removeprefix` 需要 Python 3.9，本仓库下限为 3.7
· tools/_probe_bad.py:4: 注解 `list[...]` 需要 Python 3.9，请改用 typing.List ...
结果：不通过
```

#### 启动脚本：两种编码都试过，都不行

第一版按惯例写 UTF-8 + `chcp 65001`，跑起来直接崩：

```
'e' 不是内部或外部命令
'exe' 不是内部或外部命令
```

cmd.exe 按控制台代码页逐行解析 `.bat`，UTF-8 中文把 `!PYEXE!` 切断成了碎片。
接着试 UTF-8 加 BOM，首行变成带 BOM 的 `@echo off`，`@echo off` 失效、每行都回显。
GBK 在中文系统上能用，但系统一旦开了「Beta: 使用 Unicode UTF-8」又会崩。

结论：**启动脚本必须纯 ASCII**。中文说明挪进 README / USAGE。同时补了两件事：
- `:probe` 实测候选解释器能否执行 `import sys`，识破 Windows 的微软商店跳转桩
  （`python.exe` 只是跳转器，双击只会打开商店）；
- `--check` 参数只报告检测结果，方便排障和写进文档。

实测输出：

```
[ok] interpreter: python   version: 3.13.14
--------------------------------------------
[result] full support: web UI can start.
```

#### 顺带补的一个坑

`dist/` 原本被 `.gitignore` 排除，意味着新克隆下来既没有离线版 HTML、也不一定装了 Python，
而 README 第一条路径就是「双击 dist/...」。改成只忽略 `dist/*` 并放行那一个 HTML：
离线版的全部价值就是「零依赖打开」，让它依赖 Python 来生成是自相矛盾的。

#### 测试

101 → 111 项。新增 `tests/test_compat.py`：校验器通过 + 校验器能报错（防止它变成摆设）、
`requires-python` 与版本号一致、屏蔽 openpyxl 后核心包仍可导入、CLI 仍可用、
导出接口返回 503 且带 `pip install openpyxl` 提示。

顺带把 `test_exporter.py` 改成 `importorskip`——没装 openpyxl 的机器上应该跳过这组测试，
而不是让整个套件在 collection 阶段就崩掉。

---

### 2026-10-23 · 投入产出、地图、模型配置、麦克风自检（PR #19, closes #26 #27 #28 #29）

需求原话是：「依据中国投入产出表、各省份投入产出表和各企业投入产出表去统计全国各省各城市
各造纸企业的消耗金额量情况，并且引入正版的中国地图做显示。你需要做一个模型配置模块可以
接入 API 进行思考，并且检查好麦克风是否能收音输入文字。」

四件事，其中第一件在动手前就撞上了事实问题。

#### 一、「各企业投入产出表」这个东西不存在

先查证，再写代码。投入产出表（Input-Output Table）是**国民经济核算工具**，编制主体是国家
或地区统计局，用于刻画产业部门之间的中间投入与最终使用关系。企业的法定报表是资产负债表、
利润表、现金流量表，**没有任何一家企业会编制投入产出表**，也不存在这样的公开数据集。

同样地，国家统计局在公开咨询答复中明确：**目前地级市暂不编制投入产出表**，投入产出表只到
国家与省级两个层级。

所以原始需求里的四级（国 / 省 / 市 / 企业）在「投入产出」这个口径下，实际可得的只有两级。
如果硬凑四级，唯一的做法是编数字。这和 v1.3.0 下线市县数据是同一道题——那次选择了「减法」，
这次也一样：

```python
LEVELS = [
    {"key": "national",   "io_available": True,  "provenance": "官方", ...},
    {"key": "province",   "io_available": True,  "provenance": "官方（表）+ 估算（分摊）", ...},
    {"key": "city",       "io_available": False, "provenance": "估算",
     "note": "国家统计局：地级市暂不编制投入产出表。按企业名录城市分布分摊"},
    {"key": "enterprise", "io_available": False, "provenance": "示例",
     "note": "企业无投入产出表（只有财务报表）。按年经手量 × 市场均价估算采购金额"},
]
```

`io_available` 这个布尔字段是给前端和 Excel 用的：**能查到官方表就标官方，查不到就明说查不到**，
而不是含糊地给一个数字。

#### 二、金额是「下限」，所以字段名带 is_lower_bound

废纸消耗金额 = 消耗量 × 加权参考价。难点在价格：知识库里的 888.5 元/吨是**居民/回收站口径**
的回收参考价，纸厂到厂价还要加上分拣、打包、运输，通常更高。

最省事的做法是乘一个「加价系数 1.2」之类的，但那是一个没有任何出处的假设，比不给更糟。
最终选择：**不乘系数**，把结果标成下限。

```python
return {
    "amount": round(t * p / 10000, 1),   # 亿元
    "is_lower_bound": True,
    "note": "按回收参考价计价，是纸厂废纸成本的下限（不含分拣打包运输）",
}
```

界面、Excel「投入产出」表、文档三处都写同一句话。测试里专门有一条守着它：
`test_spend_is_labelled_lower_bound`。

#### 三、不内置投入产出矩阵，但把算法做对

`data/io_matrix.csv` 是空的，`.gitignore` 也把它排除了。理由写在代码注释里：

> 本仓库不内置任何投入产出矩阵：编一张看起来权威的假矩阵，比不提供更糟。

但算法要真能用。`leontief_inverse()` 用**纯标准库**实现带部分主元的高斯-约当消元求
`(I - A)^-1`，不引入 numpy——这个仓库的基调就是零运行时依赖：

```python
# 构造 [I - A | I]，逐列选主元、归一化、消元
for col in range(n):
    pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
    if abs(aug[pivot][col]) < 1e-12:
        raise ValueError("矩阵奇异：第 %d 列无法消元…" % (col + 1))
    ...
```

正确性用教科书例子验证：`A = [[0.2, 0.3], [0.4, 0.1]]` → `(I-A)^-1 = [[1.5, 0.5], [2/3, 4/3]]`。
另有 `test_leontief_inverse_rejects_singular` 确认奇异矩阵会报错而不是返回垃圾。
影响力系数与感应度系数的均值都应为 1，也各有一条测试。

用户要做的只有一步：把国家统计局 42 部门表导成 CSV，放到 `data/io_matrix.csv`。
`data/io_matrix.csv.example` 给了格式样例。

#### 四、地图：只用正版底图，而且不内置 key

这一块有合规红线：中国地图的国界线、台湾岛、南海诸岛画法有明确规定，**不能自己用 SVG
画一个「大致形状」**。可用的只有持牌地图服务商（腾讯 / 高德 / 百度 / 天地图）。

于是 `/api/map/config` 从环境变量 `TMAP_KEY` 读 key，代码里不写任何可用 key，
只留一句显式占位符：

```python
key_placeholder = "Please apply for your own key at the Tencent Map Open Platform and replace this placeholder"
```

没 key 的时候前端**降级而不是报错**：不画地图，改成省份排行条形榜，并给出申请链接。

```
未配置地图密钥，已降级为下方的省份排行…
```

这个降级路径有测试盯着（`test_map_config_without_key_degrades`），因为「没配置就白屏」
是最容易被忽略的体验缺陷。

气泡大小按金额等比缩放（`bubbleIcon()`），坐标用 GCJ-02——腾讯地图的坐标系，
用 WGS-84 会整体偏移几百米，虽然在全国尺度看不出来，但这是个不该犯的错。

#### 五、模型配置：让 agent 真能「思考」，但没配置时不能瘫

`llm.py` 走 OpenAI 兼容协议 `/chat/completions`，用 `urllib.request` 实现，零第三方依赖。
支持 6 个预设：OpenAI / DeepSeek / 通义千问 / 智谱 GLM / Kimi / 本地 Ollama。

两个细节值得记：

**1. 密钥永远不出现在响应里。** `public()` 只返回 `mask_key()` 后的 `sk-…3f9a`。
`save_config(api_key=None)` 表示「不改密钥」，避免用户只想改模型名却把密钥清空。
报错信息也要脱敏——`_scrub()` 会在抛出前把文本里出现的密钥替换掉，否则某些服务端
会把 key 回显在错误体里，直接泄露到前端。

**2. 没配置时必须回落，而不是报错。** `/api/llm/chat` 在 `configured() == False` 时
直接走原来的规则引擎 `respond()`，并在响应里带一句 `llm_error` 说明原因：

```json
{"engine": "rule", "llm_error": "未配置模型 API：请在「设置」里填写…"}
```

这样「装了就能用大模型，不装也能用」——而不是装完发现不填 key 连话都不能说。

系统提示词里明确写了「以下数据口径以此为准，不要自行编造数字」，并把全国回收量、
回收率、货值一起塞进上下文。测试 `test_system_prompt_forbids_fabrication` 守着这句话。

#### 六、麦克风：不能只看权限，要看波形

之前 v1.4 的语音输入只判断了 `getUserMedia` 是否抛异常，于是出现「权限给了、按钮亮了、
说话没反应」的情况——设备存在但录不到声音（静音、选错设备、系统级禁用）。

这次改成**真读音频流算能量**：

```javascript
const tick = () => {
  analyser.getByteTimeDomainData(buf);
  let sum = 0;
  for (let i = 0; i < buf.length; i++) { const v = (buf[i]-128)/128; sum += v*v; }
  const rms = Math.sqrt(sum / buf.length);
  if (rms > peak) peak = rms;
  meter.style.width = Math.min(100, rms * 400).toFixed(0) + "%";
  if (Date.now() - started < 3000) micRAF = requestAnimationFrame(tick); else finish();
};
```

录 3 秒，取 RMS 峰值，分三档给结论：**<1% 几乎无声**（提示检查静音/换设备）、
**1–5% 声音太弱**（提示靠近麦克风）、**>5% 正常**。同时列出所有输入设备让用户自己选，
并检查 `window.isSecureContext`——`http://` 非 localhost 环境下浏览器根本不给麦克风权限，
这是最常见的「点了没反应」原因，直接在界面上写出来。

#### 七、踩到的坑

- **`%` 格式化被中文全角逗号打断**：`"…货值约 %.1f 亿元（按回收参考价，属下限）。"` 直接抛
  `ValueError: unsupported format character '?' (0xff0c)`——全角逗号被当成格式符。
  改用 `.format()`，且数字全部从模块取，不写死。
- **`enterprise_spend()` 引用了不存在的字段**：企业记录只有 `province_code`，没有
  `province_name`。改成 `regions.get_node(str(e["province_code"]))["name"]`。
- **浮点断言过严**：`direct_coefficient` 实现里 `round(..., 4)` 得 0.0428，未 round 是
  0.04278082…，断言 1e-6 必挂。改成拿 `round()` 后的值直接比。
- **前端假 DOM 缺全局**：补了 `URLSearchParams`，以及 `/api/stats`、`/api/enterprises`、
  `/api/info` 三个桩，否则测试里 `Cannot read properties of undefined`。

#### 七点五、上线前自查抓到的一处口径错误

导出 Excel 逐行核对时发现：山东那一行「数据性质」写的是**官方**，但它的金额
68.4 亿元 = 624.6 × 10.95%，明明是分摊出来的。原因在 `province_spend()`：

```python
"provenance": PROVENANCE_OFFICIAL if node["quality"] == "reported" else ...
```

`quality == "reported"` 说的是**回收量**来自公开报道，不是**金额**。金额永远是分摊值。
这正是本项目一直在防的那类错误——标签一错，读表的人就会把它当统计公报数据引用。

改法是把两个口径拆开：

```python
"provenance": PROVENANCE_ESTIMATED,          # 金额：永远是分摊
"recovery_provenance": PROVENANCE_OFFICIAL if node["quality"] == "reported" else ...
```

Excel 的「投入产出」表相应拆成「金额性质 / 回收量性质」两列，现在读起来是
「估算（分摊） | 官方」，一眼能看出哪部分是查来的、哪部分是算出来的。
原来那条断言「山东的 provenance 必须是官方」的测试本身也写错了，一并改写并注明原因。

顺带修了命令行摘要里「直接消耗系数　4.28」漏百分号的问题（读起来像 4.28 元）。

#### 八、验证方式

不只看 pytest 绿灯：

| 检查 | 手段 | 结果 |
| --- | --- | --- |
| 单元测试 | `pytest -q` | 111 → **158 passed** |
| 版本兼容 | `tools/check_compat.py` | 语法 / 运行时 API / 注解三项 OK |
| JS 语法 | `node --check` | 通过 |
| 前端逻辑 | 假 DOM + `node:vm` | 11 项检查全通过 |
| 离线版 | 假 DOM 跑 7 项 | 全通过 |
| Excel 结构 | 实际导出后读表名与单元格 | 7 张表，数值逐项核对 |
| 无 key 降级 | 直接请求接口 | 返回 `engine=rule` + 可读原因 |

Excel 导出实测：

```
['省级统计', '分类回收', '历年回收', '废纸进口', '企业名录', '投入产出', '数据说明']
投入产出表 78 行 · 消耗量 7030 万吨 · 加权价 888.5 元/吨 · 货值 624.6 亿元
直接消耗系数 4.28% · 单位产值消耗 0.482 吨/万元
```

#### 测试

111 → 158 项。新增 `tests/test_io_table.py`（30 项）与 `tests/test_llm.py`（17 项）。
几条防呆的：

- `test_no_builtin_matrix_shipped` —— 断言 `data/io_matrix.csv` 不存在，防止哪天有人
  「顺手」塞一张假矩阵进仓库；
- `test_public_config_never_leaks_key` —— 遍历 `public()` 的所有字段，确认没有明文密钥；
- `test_chat_http_error_is_readable_and_scrubbed` —— 401 的报错文本里不能出现 key；
- `test_spend_matches_category_sum` —— 两条算金额的路径（总量 × 均价 / 分类加总）必须一致。
