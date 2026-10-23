# 有效代码 LOC（Effective Lines of Code）

> 本文件由 `tools/count_loc.py` 自动生成，请勿手工编辑。
> 复现：`python tools/count_loc.py`

## 一、口径定义

```
有效代码行 = 物理行 - 空行 - 注释行 - 文档字符串 - 内嵌模板/数据
```

| 项 | 判定方式 |
| --- | --- |
| 物理行 | 文件按行切分后的总行数 |
| 空行 | `line.strip()` 为空 |
| 注释行 | Python 用 `tokenize` 取 `COMMENT` token；JS/CSS 识别 `//` 与 `/* */`（含跨行块注释）；HTML 识别 `<!-- -->`；Shell 识别行首 `#` |
| 文档字符串 | Python 中独立成句的字符串字面量（模块/类/函数首个语句），用 `tokenize` 判定前一个有效 token |
| 内嵌模板/数据 | **任何跨行数 >= 30 的字符串字面量**。这类内容是要输出的产物或夹具数据，不是逻辑 |

统计范围**只包含 git 跟踪的文件**（`git ls-files`），因此 `__pycache__`、
`.pytest_cache`、本地生成的 `config/llm.json` 等天然不在内。

## 二、分层汇总

| 层级 | 文件数 | 物理行 | 空行 | 注释 | 文档字符串 | 内嵌模板 | **有效代码行** |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 核心领域逻辑（`core`） | 13 | 2741 | 376 | 92 | 272 | 0 | **2043** |
| Web 层（`web`） | 3 | 1952 | 180 | 56 | 39 | 0 | **1680** |
| 测试（`tests`） | 14 | 1490 | 434 | 27 | 69 | 0 | **969** |
| 工具脚本（`tools`） | 6 | 1726 | 203 | 74 | 54 | 641 | **790** |
| **合计** | **36** | **7909** | **1193** | **249** | **434** | **641** | **5482** |

有效代码行占物理行的 **69.3%**，其余为空白、注释、文档字符串与内嵌模板。

## 三、逐文件明细（仅计入的层级）

| 文件 | 语言 | 层级 | 物理行 | 空行 | 注释 | 文档串 | 模板 | 有效代码行 |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `app/static/index.html` | HTML | Web 层 | 1519 | 102 | 45 | 0 | 0 | 1372 |
| `src/paper_recycle_agent/io_table.py` | Python | 核心领域逻辑 | 487 | 69 | 30 | 76 | 0 | 327 |
| `app/server.py` | Python | Web 层 | 412 | 71 | 10 | 34 | 0 | 299 |
| `src/paper_recycle_agent/exporter.py` | Python | 核心领域逻辑 | 363 | 42 | 8 | 25 | 0 | 291 |
| `src/paper_recycle_agent/llm.py` | Python | 核心领域逻辑 | 360 | 43 | 2 | 39 | 0 | 281 |
| `src/paper_recycle_agent/enterprises.py` | Python | 核心领域逻辑 | 326 | 47 | 3 | 29 | 0 | 251 |
| `src/paper_recycle_agent/regions.py` | Python | 核心领域逻辑 | 326 | 57 | 11 | 31 | 0 | 231 |
| `tools/check_history.py` | Python | 工具脚本 | 239 | 50 | 3 | 20 | 0 | 170 |
| `tools/push_to_github.sh` | Shell | 工具脚本 | 236 | 28 | 39 | 0 | 0 | 169 |
| `src/paper_recycle_agent/stats.py` | Python | 核心领域逻辑 | 239 | 30 | 17 | 32 | 0 | 166 |
| `tests/test_history.py` | Python | 测试 | 216 | 52 | 8 | 10 | 0 | 147 |
| `tools/publish_to_github.sh` | Shell | 工具脚本 | 205 | 35 | 27 | 0 | 0 | 143 |
| `tools/check_compat.py` | Python | 工具脚本 | 174 | 25 | 4 | 14 | 0 | 134 |
| `tests/test_io_table.py` | Python | 测试 | 231 | 73 | 8 | 21 | 0 | 131 |
| `tests/test_llm.py` | Python | 测试 | 197 | 58 | 4 | 7 | 0 | 129 |
| `tests/test_compat.py` | Python | 测试 | 171 | 40 | 2 | 12 | 0 | 119 |
| `src/paper_recycle_agent/agent.py` | Python | 核心领域逻辑 | 154 | 25 | 15 | 5 | 0 | 109 |
| `tools/gen_code_listing.py` | Python | 工具脚本 | 135 | 25 | 1 | 8 | 0 | 103 |
| `src/paper_recycle_agent/cli.py` | Python | 核心领域逻辑 | 105 | 13 | 0 | 1 | 0 | 91 |
| `src/paper_recycle_agent/data.py` | Python | 核心领域逻辑 | 114 | 12 | 3 | 11 | 0 | 89 |
| `src/paper_recycle_agent/knowledge.py` | Python | 核心领域逻辑 | 99 | 8 | 2 | 5 | 0 | 85 |
| `tools/build_offline.py` | Python | 工具脚本 | 737 | 40 | 0 | 12 | 641 | 71 |
| `tests/test_exporter.py` | Python | 测试 | 102 | 30 | 3 | 0 | 0 | 69 |
| `tests/test_server.py` | Python | 测试 | 113 | 36 | 2 | 9 | 0 | 68 |
| `tests/test_enterprises.py` | Python | 测试 | 99 | 31 | 0 | 2 | 0 | 66 |
| `tests/test_agent.py` | Python | 测试 | 100 | 36 | 0 | 1 | 0 | 63 |
| `src/paper_recycle_agent/classifier.py` | Python | 核心领域逻辑 | 86 | 17 | 1 | 8 | 0 | 61 |
| `tests/test_regions.py` | Python | 测试 | 86 | 24 | 0 | 1 | 0 | 61 |
| `tests/test_stats.py` | Python | 测试 | 84 | 24 | 0 | 1 | 0 | 59 |
| `src/paper_recycle_agent/pricing.py` | Python | 核心领域逻辑 | 47 | 7 | 0 | 5 | 0 | 36 |
| `src/paper_recycle_agent/__init__.py` | Python | 核心领域逻辑 | 35 | 6 | 0 | 5 | 0 | 25 |
| `tests/test_classifier.py` | Python | 测试 | 29 | 10 | 0 | 0 | 0 | 19 |
| `tests/test_data.py` | Python | 测试 | 24 | 8 | 0 | 0 | 0 | 16 |
| `tests/test_pricing.py` | Python | 测试 | 23 | 8 | 0 | 0 | 0 | 15 |
| `run.py` | Python | Web 层 | 21 | 7 | 1 | 5 | 0 | 9 |
| `conftest.py` | Python | 测试 | 15 | 4 | 0 | 5 | 0 | 7 |

### 前端文件的分段构成

`app/static/index.html` 是单文件前端，混在一起统计会掩盖真实构成，故拆开：

| 分段 | 物理行 | 空行 | 注释 | 有效代码行 |
| --- | ---: | ---: | ---: | ---: |
| HTML 结构 | 296 | 10 | 7 | 279 |
| CSS 样式 | 152 | 15 | 7 | 130 |
| JavaScript 逻辑 | 1071 | 77 | 31 | 963 |

## 四、不计入的文件及理由

| 类别 | 文件 | 为什么不计入 |
| --- | --- | --- |
| 配置 / 模板数据 | `.gitattributes` | 配置 / 模板数据，不含应用逻辑 |
| 配置 / 模板数据 | `.github/ISSUE_TEMPLATE/bug_report.yml` | 配置 / 模板数据，不含应用逻辑 |
| 配置 / 模板数据 | `.github/ISSUE_TEMPLATE/config.yml` | 配置 / 模板数据，不含应用逻辑 |
| 配置 / 模板数据 | `.github/ISSUE_TEMPLATE/feature_request.yml` | 配置 / 模板数据，不含应用逻辑 |
| 文档 | `.github/PULL_REQUEST_TEMPLATE.md` | 文档，不是可执行逻辑 |
| 配置 / 模板数据 | `.github/workflows/ci.yml` | 配置 / 模板数据，不含应用逻辑 |
| 配置 / 模板数据 | `.gitignore` | 配置 / 模板数据，不含应用逻辑 |
| 文档 | `LICENSE` | 文档，不是可执行逻辑 |
| 文档 | `README.md` | 文档，不是可执行逻辑 |
| 配置 / 模板数据 | `config/llm.json.example` | 配置 / 模板数据，不含应用逻辑 |
| 配置 / 模板数据 | `data/enterprises.csv.example` | 配置 / 模板数据，不含应用逻辑 |
| 配置 / 模板数据 | `data/io_matrix.csv.example` | 配置 / 模板数据，不含应用逻辑 |
| 生成物 | `dist/paper-recycle-offline.html` | 构建产物，内容由源码生成，计入即重复计数 |
| 文档 | `docs/CHANGELOG.md` | 文档，不是可执行逻辑 |
| 生成物 | `docs/CODE_LISTING.md` | 构建产物，内容由源码生成，计入即重复计数 |
| 文档 | `docs/CONTRIBUTING.md` | 文档，不是可执行逻辑 |
| 文档 | `docs/DATA_SOURCES.md` | 文档，不是可执行逻辑 |
| 文档 | `docs/DEVLOG.md` | 文档，不是可执行逻辑 |
| 文档 | `docs/ISSUES.md` | 文档，不是可执行逻辑 |
| 文档 | `docs/REPO_PROVENANCE.md` | 文档，不是可执行逻辑 |
| 文档 | `docs/UPLOAD_TO_GITHUB.md` | 文档，不是可执行逻辑 |
| 文档 | `docs/USAGE.md` | 文档，不是可执行逻辑 |
| 配置 / 模板数据 | `pyproject.toml` | 配置 / 模板数据，不含应用逻辑 |
| 配置 / 模板数据 | `requirements.txt` | 配置 / 模板数据，不含应用逻辑 |
| 配置 / 模板数据 | `启动本地版.bat` | 配置 / 模板数据，不含应用逻辑 |

## 五、卫生检查（确认没有虚增）

| 检查项 | 结果 | 说明 |
| --- | --- | --- |
| 无第三方 vendor 目录 | 通过 | 0 个 |
| 无压缩代码 | 通过 | 0 个 |
| 无超长行（>2000 字符） | 通过 | 0 处 |
| 内嵌模板已单独归类 | 通过 | 641 行（不计入 SLOC） |

这几项对应评审最关心的四类虚增：**生成物**、**第三方复制代码**、
**压缩代码**、**大块测试夹具数据**。逐项检查结果如上。

## 六、怎么自行复核

```bash
# 1. 重新统计（数字应完全一致）
python tools/count_loc.py

# 2. 看某个文件的行数分布
python tools/count_loc.py --json | python -m json.tool | less

# 3. 抽查一个文件：注释与 docstring 的判定是否合理
sed -n '1,40p' src/paper_recycle_agent/data.py

# 4. 确认生成物确实由脚本产出
grep -n 'dist/paper-recycle-offline.html' tools/build_offline.py
grep -n 'docs/CODE_LISTING.md' tools/gen_code_listing.py
```

