# 废纸回收 Agent 对话助手

![CI](https://github.com/your-name/paper-recycle-agent/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-%3E%3D3.9-3776ab)

一个轻量级、纯标准库实现的废纸回收助手：识别废纸类型、判断是否可回收、按重量估算回收价值，并接入《中国造纸年鉴》/行业报告的废纸分类与行业数据，提供命令行与 Web 图形界面。

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

- 统计局：拉某省分类回收量底表 → 导出六表 Excel → 直接进公报核对流程
- 协会：看八大类结构五年变化，判断废新闻纸类萎缩速度
- 回收企业：在「企业分布」里筛「山东 + 造纸企业」，找下游直供对象
- 产废单位：语音问「纸箱 20 斤能卖多少」，或问「涉密文件怎么处理」

## 特性
- 9 类废纸知识库（可回收 / 不可回收及缘由）
- 关键词分类引擎，多命中智能排序
- 重量 × 单价回收估价，支持「斤」折算
- 自然语言对话（问候 / 帮助 / 估价 / 分类）
- 命令行 `chat` / `classify` / `price` / `categories` / `info` / `history` / `catstats` / `region` / `enterprises` / `export`
- **接入《中国造纸年鉴》废纸分类（GB/T 20811-2018，8 大类 42 小类）与 2024 行业数据**
- **全国 + 省级两级区域统计**（不再提供市/县数据，见下方「数据口径」）
- **历年数据 2014—2025**：回收量、回收率、利用率、废纸进口量
- **按八大类拆分的分类回收量**（占比 × 回收量，含参考价与估算货值）
- **企业维度：企业名录 + 地理位置 + 主营品类 + 年回收量**（可按省 / 大类 / 类型筛选，含地理分布示意图）
- **一键导出多表 Excel**（省级 / 分类 / 历年 / 进口 / 企业 / 数据说明 六张表）
- **对话支持语音输入**（浏览器 Web Speech API，失败时在输入框下方显示具体原因）
- **Web 图形界面**：FastAPI 聊天页 + 区域/历年/分类/企业 四个标签页
- GitHub Actions 多版本 CI

## 数据口径（重要）

| 维度 | 数据性质 | 说明 |
|---|---|---|
| 全国 2024 | 官方 | 中国造纸协会《中国造纸工业2024年度报告》 |
| 省级回收量 | 报道 + 测算 | 山东 763、广东 733 为公开报道值；其余 32 个省级行政区为梯队测算并归一化到全国总量 |
| 历年 2014—2025 | 官方 | 中国造纸协会年度报告、《中国造纸》统计表；2025 为初步核算 |
| 八大类占比 | 估算 | 官方未逐类公布回收量，按 2015/2020/2025 三锚点插值 |
| 企业名录 | 示例 | 内置 30 家示例企业（虚构名称），放 `data/enterprises.csv` 即切换为真实名录 |

**为什么不提供市、县数据**：市级、县级废纸回收量没有公开的权威逐级统计。早期版本用权重分摊"造"出了市县数据，容易让使用者误以为是真实统计，v1.3.0 起已下线，只保留可核验的两级。替换真实数据的方法见 [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)。

## 快速开始
```bash
pip install -r requirements.txt   # 含 fastapi / uvicorn / openpyxl
# 命令行
PYTHONPATH=src python -m paper_recycle_agent.cli history
PYTHONPATH=src python -m paper_recycle_agent.cli catstats 2024
PYTHONPATH=src python -m paper_recycle_agent.cli export 山东 --year 2024 --out 山东.xlsx
# 图形界面（浏览器打开 http://localhost:8000）
uvicorn app.server:app --reload
```

## 项目结构
```
paper-recycle-agent/
├── src/paper_recycle_agent/   # 核心包（业务逻辑纯标准库）
│   ├── knowledge.py           # 知识库（9 类实用回收指引 + 参考价）
│   ├── data.py                # 年鉴/行业数据（GB/T 20811-2018 + 2024 报告）
│   ├── stats.py               # 历年序列 + 八大类占比与分类回收量
│   ├── regions.py             # 全国 + 省级两级统计
│   ├── enterprises.py         # 企业名录（地理坐标 / 类型 / 主营品类 / 年回收量）
│   ├── exporter.py            # 多表 Excel 导出（openpyxl）
│   ├── classifier.py          # 分类引擎
│   ├── pricing.py             # 估价
│   ├── agent.py               # 对话引擎
│   └── cli.py                 # 命令行
├── data/enterprises.csv.example  # 企业名录模板（复制为 enterprises.csv 即启用真实数据）
├── tests/                     # pytest 单元测试（101 项）
├── app/server.py              # FastAPI 服务（图形界面 + 统计接口 + 导出）
├── app/static/index.html      # 聊天界面（区域 / 历年 / 分类 / 企业 四标签页）
├── run.py                     # 读取 PORT 的统一启动入口
├── docs/                      # 使用/贡献/开发日志/代码清单/数据来源
└── .github/workflows/ci.yml   # CI
```

## 连续开发说明
本仓库保留了一条**真实的连续开发历史**：连续 commit + feature 分支 + --no-ff 合并（即 PR 轨迹）+ Issue/里程碑关联。详见 [docs/DEVLOG.md](docs/DEVLOG.md)。

```bash
git log --oneline --graph --all
```

## 文档
- [使用说明](docs/USAGE.md)
- [贡献指南](docs/CONTRIBUTING.md)
- [开发日志](docs/DEVLOG.md)
- [更新日志](docs/CHANGELOG.md)
- [代码清单](docs/CODE_LISTING.md)

## License
MIT © 梁湘瑶 / 阿岩
