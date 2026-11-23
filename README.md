# 造纸工厂多智能体 · 碳核算 Agent

![CI](https://github.com/lanlanyuan/paper-recycle-agent/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-%3E%3D3.7-3776ab)
![Tests](https://img.shields.io/badge/tests-235%20passed-brightgreen)
![Deps](https://img.shields.io/badge/runtime%20deps-0-brightgreen)

一个**造纸工厂多智能体系统**，核心是**碳核算 Agent**：按国标《温室气体排放核算与报告要求 造纸和纸制品生产企业》的方法核算工厂温室气体排放，排放因子取自附录B（逐条带出处），活动数据为示例工厂仿真输入。

```
                    ┌─────────────────────────────┐
                    │   碳核算 Agent（核心）       │  按国标核算五类排放源
                    └──────────────┬──────────────┘
                                   │ 回收量 → 范围三减排
   ┌─────────────────┐   ┌────────┴────────┐   ┌─────────────────┐
   │ 智能工厂 (mill/) │   │ 废纸回收子 Agent │   │ 产业大脑 (brain/)│
   │ 制浆/抄纸/干燥/质检│   │ 分类/估价/统计   │   │ 五链贯通 simulated│
   │ 车间层           │   │ 全功能保留       │   │ 经营管理层       │
   └─────────────────┘   └─────────────────┘   └─────────────────┘
```

三个子 Agent 各司其职，互不干扰；投入产出表的方法论抽出来作为供应链碳足迹（EEIOA）参考。

## 快速开始

```bash
# 双击启动（推荐）：启动本地版.bat → 浏览器打开 http://localhost:8000
# 碳核算 Agent 是默认首页：改活动数据即时重算、填电力因子、情景模拟

# 或命令行（Python 3.7+，零依赖）
PYTHONPATH=src python -m paper_recycle_agent.cli info

# Web 服务
pip install -r requirements.txt
PYTHONPATH=src python -m uvicorn app.server:app --reload
```

**离线单文件**（双击即开、零依赖、不用装 Python）：

| 文件 | 内容 |
| --- | --- |
| `dist/paper-mill-offline.html` | **造纸工艺仿真**：四工序 + 调度 + 异常注入，可投批次/单步/自动跑完 |
| `dist/paper-recycle-offline.html` | 废纸回收统计五个标签页（不含碳核算/地图/模型配置） |

运行环境：核心包**零依赖、Python 3.7 起**；Web 界面需 3.8+。`python tools/check_compat.py` 可验证 3.7 兼容性。

## 运行造纸工艺模型（智能工厂仿真）

四道工序——制浆 → 抄纸 → 干燥 → 质检——各由一个子智能体负责，总调度器编排任务、派 AGV / 机器狗 / PLC 作业。工况为仿真生成，设备为内存模拟对象，**不连接任何真实产线**。

### 方式 A：网页界面（推荐）

```bash
# 1. 启动服务
双击「启动本地版.bat」 → 浏览器打开 http://localhost:8000
# 或命令行：
PYTHONPATH=src python -m uvicorn app.server:app --reload

# 2. 点顶部「智能工厂」标签页
```

面板上按顺序点四个按钮：

| 按钮 | 作用 |
| --- | --- |
| 投批次 | 生成一个新批次，四道工序依次启动 |
| 单步 | 每次推进一个仿真步，观察工况变化 |
| 自动跑完 | 一直跑到流水线空闲（约 13 步，上限 80） |
| 重置 | 清空批次、日志与异常 |

跑起来后看三块：**工序流水线**（各工序实时工况，绿点正常 / 黄点越界）、**智能体决策**（配了 API Key 走大模型，否则回落规则引擎）、**设备任务与调度日志**。

试试**异常注入**：选工序、指标、填越界值（例如「干燥 / steam_pressure / 0.9」，超出正常区间 0.3~0.6 MPa），点「注入异常」，能看到智能体挂起批次、给处置建议、再恢复的全过程。

### 方式 B：命令行（零依赖，Python 3.7+）

```bash
PYTHONPATH=src python -c "from paper_recycle_agent.mill import Orchestrator; o=Orchestrator(); o.start_batch(); r=o.run_until_idle(max_steps=80); print('仿真步:', r['sim']['step'], '| 四道工序:', [(s['key'], s['state']) for s in r['sim']['stages']])"
```

### 方式 C：HTTP API（自己写前端 / 对接用）

服务启动后可调这些接口：

| 接口 | 方法 | 作用 |
| --- | --- | --- |
| `/api/mill/processes` | GET | 四道工序定义与指标区间 |
| `/api/mill/state` | GET | 当前仿真快照 |
| `/api/mill/start` | POST | 投新批次 |
| `/api/mill/step` | POST | 推进 N 步（`{"steps":1}`，上限 60） |
| `/api/mill/run` | POST | 自动跑到空闲 |
| `/api/mill/anomaly` | POST | 注入异常（`{"process":"drying","metric":"steam_pressure","value":0.9}`） |
| `/api/mill/reset` | POST | 重置仿真 |

```bash
curl -X POST http://localhost:8000/api/mill/start
curl -X POST http://localhost:8000/api/mill/run
curl http://localhost:8000/api/mill/state
```

## 功能一览

| 模块 | 作用 | 文档 |
| --- | --- | --- |
| **碳核算 Agent**（核心） | 国标五类排放源核算、排放因子带出处、情景模拟、范围三减排演示 | [CARBON_AGENT.md](docs/CARBON_AGENT.md) |
| 智能工厂 | 四道工序多智能体 + 总调度 + AGV/机器狗/PLC 仿真；不连真实产线 | [MILL_AGENTS.md](docs/MILL_AGENTS.md) |
| 废纸回收子 Agent | 分类、估价、区域/历年/分类统计、企业分布、Excel 导出、地图、模型配置 | [RECYCLE_AGENT.md](docs/RECYCLE_AGENT.md) · [USAGE.md](docs/USAGE.md) |
| 产业大脑 | 采购/生产/销售/物流/财务五链贯通仿真，12 条跨域联动 | [INDUSTRY_BRAIN.md](docs/INDUSTRY_BRAIN.md) |

## 项目结构

```
src/paper_recycle_agent/     核心包（纯标准库，Python 3.7+）
├── carbon/                  【核心】碳核算：factors/model/accounting/recycle_agent
├── mill/                    造纸工艺四工序多智能体（车间层）
├── brain/                   产业大脑五链贯通（经营管理层）
├── knowledge/data/stats/    废纸知识库、年鉴数据、历年序列
├── regions/enterprises/     区域统计、企业名录
├── io_table.py              投入产出（消耗金额、Leontief 逆），亦作 EEIOA 方法参考
├── llm.py                   模型配置（OpenAI 兼容，密钥脱敏）
├── exporter.py              多表 Excel 导出（openpyxl 按需导入）
└── agent.py/cli.py          对话引擎、命令行
app/server.py                FastAPI 服务（界面 + 全部接口）
app/static/index.html        界面（十个标签页，碳核算为首页）
tests/                       pytest 单元测试（235 项）
tools/                       兼容校验 / 历史自洽 / LOC 统计 / 代码清单 / 构建
```

## 验证

```bash
PYTHONPATH=src python -m pytest -q   # 235 passed
python tools/check_compat.py          # Python 3.7 兼容
python tools/count_loc.py --check     # 有效代码 8672 行（core 3478 / Web 2497 / 测试 1462 / 工具 1235）
python tools/check_history.py         # 连续开发历史自洽（6 项）
```

详细数据口径见 [DATA_SOURCES.md](docs/DATA_SOURCES.md)，有效代码 LOC 口径见 [EFFECTIVE_LOC.md](docs/EFFECTIVE_LOC.md)。

## 文档

- [碳核算 Agent：国标依据与架构](docs/CARBON_AGENT.md)　←　核心
- [智能工厂多智能体](docs/MILL_AGENTS.md)
- [废纸回收子 Agent：使用与口径](docs/RECYCLE_AGENT.md)
- [产业大脑五链贯通](docs/INDUSTRY_BRAIN.md)
- [使用说明](docs/USAGE.md)
- [数据来源与口径](docs/DATA_SOURCES.md)
- [代码清单](docs/CODE_LISTING.md) · [有效代码 LOC](docs/EFFECTIVE_LOC.md)
- [更新日志](docs/CHANGELOG.md) · [开发日志](docs/DEVLOG.md)
- [仓库历史说明](docs/REPO_PROVENANCE.md) · [上传到 GitHub](docs/UPLOAD_TO_GITHUB.md)
- [贡献指南](docs/CONTRIBUTING.md)

**Repo**：<https://github.com/lanlanyuan/paper-recycle-agent>

## License
MIT © 梁湘瑶 / 阿岩
