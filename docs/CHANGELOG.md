# 更新日志（CHANGELOG）

## v1.5.0 (2026-10-23)
**运行环境门槛下调：Python 下限从 3.9 降到 3.7，核心包彻底零依赖。**

- `requires-python` 改为 `>=3.7`。全仓库唯一的版本门槛是 `dataclasses`（3.7 引入），
  没有使用 walrus / `match` / `removeprefix` / `zoneinfo` 等更高版本的语法与 API
- `openpyxl` 改为**按需导入**：以前它在模块顶层 import，导致没装 openpyxl 的机器
  连 `import paper_recycle_agent` 都会失败；现在只有真正写工作簿时才加载
  - 新增 `exporter.available()`，`build_workbook()` 在缺依赖时抛 `RuntimeError` 并附安装指引
  - `/export.xlsx` 缺 openpyxl 时返回 **503 + JSON 说明**，不再是 500 堆栈
  - 前端新增导出状态行：缺依赖时提前说明，导出失败不再静默下载一个 JSON 文件
- `pyproject.toml` 拆分可选依赖：`[web]` / `[excel]` / `[test]` / `[all]`，核心 `dependencies = []`
- 新增 `tools/check_compat.py`：用 3.7 语法树解析全部源码，并扫描 3.8/3.9 专有 API
  与未启用 `from __future__ import annotations` 时的内置泛型注解，可接入 CI
- `启动本地版.bat` 重写：
  - 实测候选解释器能否执行 Python 代码，识破 Windows「微软商店跳转桩」（`python.exe` 只是跳转器）
  - 按版本分流：3.8+ 起服务；3.7 打开零依赖离线版；无 Python 给出下载地址与离线版路径
  - 离线版缺失时自动构建，不再只报错
  - 新增 `--check` 只报告检测结果，便于排障
  - 内容改为**纯 ASCII**：cmd.exe 按控制台代码页解析 `.bat`，UTF-8 中文会切断逻辑，
    UTF-8 BOM 还会让 `@echo off` 失效（已实测）
- `dist/paper-recycle-offline.html` 纳入版本库：它的卖点是「不装任何东西也能打开」，
  若还需先装 Python 来生成就自相矛盾了
- CI 改为 3.8 / 3.11 / 3.13 跑全量 + 独立 3.7 job 跑零依赖核心，并执行兼容性校验
- `tests/test_exporter.py` 改用 `importorskip`，没装 openpyxl 时跳过而不是让整个套件崩掉
- 测试从 101 项增至 111 项

## v1.4.0 (2026-10-22)
- 新增 `enterprises.py`：企业维度（名称 / 城市 / 经纬度 / 类型 / 主营大类 / 年回收量）
  - 内置 30 家示例企业，覆盖 15 个省级行政区、4 种企业类型
  - 支持按省 / 大类 / 类型筛选，按省、按类、按类型汇总
  - 放 `data/enterprises.csv` 即自动切换为真实名录（`is_demo` 变为 False）
  - 提供名录覆盖率（企业合计 ÷ 该省官方回收量），避免把样本当全量
- 新增 `/api/enterprises` 接口；Excel 增加「企业名录」表（共 6 张）
- 图形界面新增「企业分布」标签页：筛选器 + 经纬度散点示意图 + 类型分布 + 明细表
- 对话引擎新增企业意图：企业名直查、某省企业概览、按类型查企业
- 语音输入重做：每个失败原因都有中文提示（权限拒绝 / 无麦克风 / 网络 / 无语音 / iframe 受限 / 非 HTTPS），
  并实时回显临时识别结果，不再是「按了没反应」
- `regions.find` 支持简称与自然语言（「山东有哪些企业」→ 山东省）
- CLI 新增 `enterprises` 子命令
- 测试从 77 项增至 101 项

## v1.3.1 (2026-10-22)
- 修复 `HEAD /` 返回 405、未知页面路径返回 404（托管环境与预览面板会显示 Not Found）
- 新增兜底路由：未匹配页面回落首页，接口与静态资源仍如实 404
- 新增 `tests/test_server.py`（17 项）与 `conftest.py`

## v1.3.0 (2026-10-22)
**破坏性变更**：移除市级、县级统计，只保留全国 + 省级两级。

- 新增 `stats.py`：2014—2025 年回收量 / 消费量 / 回收率 / 利用率 / 废纸进口量序列
- 新增八大类回收量拆分（GB/T 20811-2018），占比按 2015/2020/2025 三锚点线性插值
- 新增 `exporter.py`：五表 Excel（省级 / 分类 / 历年 / 进口 / 数据说明），支持按省份与年份导出
- `regions.py` 重写：34 个省级行政区，山东 763 万吨、广东 733 万吨为公开报道值，
  其余按行业梯队测算并归一化到全国 6971 万吨（合计严格相等）
- 省级节点新增 `tier` / `tier_label` / `quality` / `rank` / `占全国比重(%)` 字段
- 对话引擎新增「历年趋势」「按类别看回收量」意图，支持从问句里提取年份
- 图形界面重做：区域 / 历年 / 分类三个标签页 + 年份切换 + 条形图
- 接口调整：`/api/stats` 增加 `history`、`categories`、`import_series`、`share_of_national`；
  `/export.xlsx` 支持 `year` 参数，文件名改为 UTF-8 编码
- CLI 新增 `history` / `catstats` / `region` / `export` 子命令
- 测试从 25 项增至 60 项

## v1.2.1 (2026-10-22)
- 修复 `/index.html` 未注册导致预览面板 404（`/` 与 `/index.html` 同时注册）
- 修复 Excel 导出在嵌入式预览中被拦截：改为 `fetch` + Blob 下载，附新窗口兜底
- 页面加 `Cache-Control: no-store`，避免旧版本 HTML 被缓存

## v1.2.0 (2026-10-22)
- 新增 `regions.py`：区域分层统计，支持下钻与汇总
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
