# 更新日志（CHANGELOG）

## v1.2.0 (2026-10-22)
- 新增 `regions.py`：国家 → 省 → 市 → 县区四级区域统计，支持下钻与汇总
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
