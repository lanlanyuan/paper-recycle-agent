# 废纸回收 Agent 对话助手

![CI](https://github.com/your-name/paper-recycle-agent/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-%3E%3D3.9-3776ab)

一个轻量级、纯标准库实现的废纸回收助手：识别废纸类型、判断是否可回收、按重量估算回收价值，并支持命令行对话与可选 HTTP 服务。

## 特性
- 9 类废纸知识库（可回收 / 不可回收及缘由）
- 关键词分类引擎，多命中智能排序
- 重量 × 单价回收估价，支持「斤」折算
- 自然语言对话（问候 / 帮助 / 估价 / 分类）
- 命令行 `chat` / `classify` / `price` / `categories`
- 可选 FastAPI 对话服务
- GitHub Actions 多版本 CI

## 快速开始
```bash
pip install -e .
paper-recycle-agent chat
```

## 项目结构
```
paper-recycle-agent/
├── src/paper_recycle_agent/   # 核心包
│   ├── knowledge.py           # 知识库
│   ├── classifier.py          # 分类引擎
│   ├── pricing.py             # 估价
│   ├── agent.py               # 对话引擎
│   └── cli.py                 # 命令行
├── tests/                     # pytest 单元测试
├── app/server.py              # 可选 FastAPI 服务
├── docs/                      # 使用/贡献/开发日志
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

## License
MIT © 梁湘瑶 / 阿岩
