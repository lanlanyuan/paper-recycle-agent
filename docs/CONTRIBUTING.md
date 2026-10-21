# 贡献指南

欢迎以 Issue / PR 的方式参与。本仓库刻意保留了一条**连续的开发历史**，
用以展示「真实 Repo 的连续开发」过程，提交时请遵循以下约定。

## 分支模型

- `main`：稳定主线，只允许合并（merge）进来的提交。
- `feature/<名称>`：功能开发分支，从 `main` 切出，完成后以 **--no-ff** 合并，
  保留合并提交，让 GitHub 网络图呈现真实的 PR 轨迹。

```bash
git switch -c feature/my-feature
# ... 开发、自测 ...
git switch main
git merge --no-ff feature/my-feature -m "Merge PR #N: 一句话说明"
```

## 提交信息规范

```
类型: 简短描述 (closes #N)
```

类型取值：`feat` / `fix` / `docs` / `refactor` / `test` / `chore`。
在描述末尾用 `closes #N` / `ref #N` 关联 Issue。

## 自测

每次 PR 前确保：

```bash
PYTHONPATH=src pytest -q
```

并在 CLI 中手动验证核心路径（分类、估价、对话）。

## Issue 与里程碑

- 需求 / Bug 用 Issue 跟踪，见 `docs/ISSUES.md` 的编号约定。
- 版本节点用里程碑（Milestone）划分：`v0.1` 核心引擎、`v0.2` 对话+CLI、
  `v1.0` 测试+CI+文档。
