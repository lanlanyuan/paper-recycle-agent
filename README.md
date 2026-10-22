# 废纸回收 Agent 对话助手

![CI](https://github.com/your-name/paper-recycle-agent/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-%3E%3D3.9-3776ab)

一个轻量级、纯标准库实现的废纸回收助手：识别废纸类型、判断是否可回收、按重量估算回收价值，并接入《中国造纸年鉴》/行业报告的废纸分类与行业数据，提供命令行与 Web 图形界面。

## 特性
- 9 类废纸知识库（可回收 / 不可回收及缘由）
- 关键词分类引擎，多命中智能排序
- 重量 × 单价回收估价，支持「斤」折算
- 自然语言对话（问候 / 帮助 / 估价 / 分类）
- 命令行 `chat` / `classify` / `price` / `categories` / `info`
- **接入《中国造纸年鉴》废纸分类（GB/T 20811-2018，8 大类 42 小类）与 2024 行业数据**
- **国家 → 省 → 市 → 县区四级区域统计**，界面可逐级下钻
- **一键导出 Excel**（供统计局人员直接使用）
- **对话支持语音输入**（浏览器 Web Speech API，无需第三方 ASR）
- **Web 图形界面**：FastAPI 聊天页 + 区域统计面板
- GitHub Actions 多版本 CI

## 快速开始
```bash
pip install -r requirements.txt   # 含 fastapi / uvicorn
# 命令行
PYTHONPATH=src python -m paper_recycle_agent.cli chat
# 图形界面（浏览器打开 http://localhost:8000）
uvicorn app.server:app --reload
```

## 项目结构
```
paper-recycle-agent/
├── src/paper_recycle_agent/   # 核心包（纯标准库）
│   ├── knowledge.py           # 知识库（9 类实用回收指引）
│   ├── data.py                # 年鉴/行业数据（GB/T 20811-2018 + 2024 报告）
│   ├── regions.py             # 国家→省→市→县区四级统计（含 Excel 导出）
│   ├── classifier.py          # 分类引擎
│   ├── pricing.py             # 估价
│   ├── agent.py               # 对话引擎
│   └── cli.py                 # 命令行
├── tests/                     # pytest 单元测试
├── app/server.py              # FastAPI 服务（图形界面 + 区域统计 + 导出）
├── app/static/index.html      # 聊天界面（区域下钻 / 导出 / 语音输入）
├── run.py                     # 读取 PORT 的统一启动入口
├── docs/                      # 使用/贡献/开发日志/代码清单
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
