# 更新日志（CHANGELOG）

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
