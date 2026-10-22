# 使用说明

## 安装

```bash
# 方式一：什么都不装，直接跑（Python 3.7+）
PYTHONPATH=src python -m paper_recycle_agent.cli history

# 方式二：装成命令（核心仍零依赖）
pip install -e .

# 需要 Excel 导出
pip install -e ".[excel]"

# 需要图形界面
pip install -e ".[web]"

# 仅跑测试
pip install pytest
PYTHONPATH=src pytest -q
```

> 运行时**无第三方依赖**，纯 Python 标准库即可，**最低 Python 3.7**。
>
> 版本分档：
>
> | 能力 | 最低 Python | 额外依赖 |
> | --- | --- | --- |
> | 命令行 / 统计 / 分类估价 | 3.7 | 无 |
> | 离线单文件版 | 3.7 | 无 |
> | 导出 `.xlsx` | 3.7 | `openpyxl` |
> | 图形界面 | 3.8 | `fastapi` / `uvicorn` |
>
> 仓库自带校验器，可随时验证代码没有越界用到 3.8+ 的语法或 API：
>
> ```bash
> python tools/check_compat.py
> ```

## 命令行

```bash
# 交互式对话
paper-recycle-agent chat

# 直接分类查询
paper-recycle-agent classify "快递纸箱"

# 估价（重量单位 kg）
paper-recycle-agent price "办公用纸" 10

# 列出全部类别
paper-recycle-agent categories
```

交互示例：

```
你: 纸箱 2kg
助手: 【纸箱/纸板】2.0 kg，预计回收价值约 1.8 元。
你: 纸巾能回收吗
助手: 识别为【纸巾/卫生纸】，暂不可回收。已被污染且纤维过短……
```

## 作为库调用

```python
from paper_recycle_agent import respond, classify, pricing

print(respond("报纸"))                       # 自然语言回复
print(classify("热敏小票"))                   # 结构化结果
print(pricing.estimate("办公用纸", 5))        # 估价
```

## 可选：HTTP 对话服务

```bash
pip install fastapi uvicorn
uvicorn app.server:app --reload
```

- `POST /chat`  body `{"message": "纸箱 2kg"}` → `{"reply": "..."}`
- `GET /health` → `{"status": "ok"}`

## 历年数据与分类数据（v1.3.0 新增）

### 命令行

```bash
# 历年回收量 / 回收率 / 利用率 / 废纸进口量
PYTHONPATH=src python -m paper_recycle_agent.cli history

# 按八大类拆分回收量（可指定年份）
PYTHONPATH=src python -m paper_recycle_agent.cli catstats 2024
PYTHONPATH=src python -m paper_recycle_agent.cli catstats 2020

# 区域统计（只支持全国与省级）
PYTHONPATH=src python -m paper_recycle_agent.cli region 全国
PYTHONPATH=src python -m paper_recycle_agent.cli region 山东

# 导出多表 Excel
PYTHONPATH=src python -m paper_recycle_agent.cli export 全国 --year 2024 --out 全国.xlsx
PYTHONPATH=src python -m paper_recycle_agent.cli export 山东 --year 2020 --out 山东2020.xlsx
```

### 对话里可以这么问

| 想查什么 | 输入示例 |
| --- | --- |
| 历年趋势 | 「历年数据」「近五年趋势」「以前年份回收量」 |
| 按类别看回收量 | 「分类回收数据」「八大类占比」「2020 年分类数据」 |
| 某省回收量 | 「山东省回收量」「广东排名」 |
| 全国统计 | 「全国统计」「回收率多少」 |
| 分类标准（技术要求） | 「废纸分类」 |

### 图形界面三个标签页

1. **区域统计**：省级回收量排名（带条形图），点击任意行查看该省明细，可返回全国。
   表中「数据」列标 `报道` 或 `测算`，一眼看出哪条能引用。
2. **历年数据**：年份选择器 + 回收量走势 + 明细表 + 废纸进口量条形图。
3. **分类结构**：八大类占比条形图 + 回收量/货值表；页面底部折叠区是 GB/T 20811-2018 分类技术要求。

### 导出的 Excel 长什么样

一个 `.xlsx`，五张工作表：

| 工作表 | 内容 |
| --- | --- |
| 省级统计 | 34 个省级行政区排名、回收量、占比、回收率、利用率、数据性质 + 合计行 |
| 分类回收 | 八大类占比、回收量、参考价、估算货值、主要去向 + 合计行 |
| 历年回收 | 2014—2025 年回收量、消费量、同比、回收率、利用率、纸及纸板产量 |
| 废纸进口 | 2017—2025 年进口量 |
| 数据说明 | 来源、口径区分、已知差异、如何替换真实数据 |

选中的是某个省时，「省级统计」表只导出该省一行；完整对照请选「全国」再导出。

### 注意

- 本工具只提供**全国**与**省级**两级统计，市级、县级数据已下线（无公开权威来源）。
- 分类回收量是「结构占比 × 官方回收量」的**估算值**，不是官方分项统计。

## 企业维度（v1.4.0 新增）

### 命令行

```bash
# 全国企业概览（按类型、按大类汇总）
PYTHONPATH=src python -m paper_recycle_agent.cli enterprises

# 某省企业概览（含名录覆盖率）
PYTHONPATH=src python -m paper_recycle_agent.cli enterprises --province 山东

# 按类型筛选
PYTHONPATH=src python -m paper_recycle_agent.cli enterprises --province 广东 --type 造纸企业
```

### 对话里可以这么问

| 想查什么 | 输入示例 |
| --- | --- |
| 全国企业概览 | 「企业名录」「有哪些回收企业」 |
| 某省企业 | 「山东有哪些回收企业」「广东的打包厂」 |
| 单个企业 | 「鲁清再生」「青岛海岳」 |
| 按类型 | 「分拣中心」「造纸厂」「贸易商」 |

### 图形界面「企业分布」标签页

- 三个筛选器：省份 / 大类 / 类型，任意组合
- 地理分布示意图：点大小 = 年回收量，颜色 = 企业类型，悬停看详情
- 类型分布条形图 + 企业明细表（按年回收量降序）

### 换成你自己的企业名录

```bash
cp data/enterprises.csv.example data/enterprises.csv
# 按表头填写真实企业，重启服务即可
```

字段说明见 [DATA_SOURCES.md](DATA_SOURCES.md) 第八节。填好后页面顶部的「示例」提示会自动消失，
导出 Excel 的「企业名录」表也会标注为真实数据。

## 语音输入用不了怎么办

页面输入框下方会直接显示原因，对照处理即可：

| 提示 | 原因 | 处理 |
| --- | --- | --- |
| 麦克风权限被拒绝 | 浏览器拒绝了麦克风 | 点地址栏左侧图标 → 允许麦克风 → 刷新 |
| 页面嵌在预览框里 | iframe 被 Permissions Policy 限制 | 在新标签页打开页面 |
| 要求 HTTPS 或 localhost | 非安全上下文 | 用 https 或本机地址访问 |
| 语音识别服务连接失败 | Chrome 识别服务在部分网络不可用 | 改用文字输入 |
| 当前浏览器不支持 | Firefox / 部分 Safari 无此 API | 用 Chrome / Edge |

## 打不开网站怎么办（三种打开方式）

### ① 离线单文件（推荐先用这个）

双击 `dist/paper-recycle-offline.html`，浏览器直接打开。

- 全部数据内联在文件里，**不联网、不起服务**
- 保留：对话问答、区域统计、历年数据、分类结构、企业分布、CSV 导出
- 不含：xlsx 多表导出（需要 openpyxl）、语音输入（依赖浏览器服务）

重新生成（数据更新后）：

```bash
PYTHONPATH=src python tools/build_offline.py
```

### ② 本地服务（要 xlsx 就用这个）

双击 `启动本地版.bat`（Windows），等窗口出现提示后用浏览器打开 `http://localhost:8000`。

脚本会自动探测 Python 并分流：

| 探测结果 | 脚本行为 |
| --- | --- |
| Python 3.8+ | 装依赖 → 起服务 |
| Python 3.7 | 提示图形界面需要 3.8+ → 自动打开离线版 |
| 找不到可用的 Python | 提示下载地址 + 离线版路径，并说明"商店跳转桩"陷阱 |

只看检测结果、不启动服务：

```bat
启动本地版.bat --check
```

输出示例：

```
[ok] interpreter: python   version: 3.13.14
--------------------------------------------
[result] full support: web UI can start.
```

> **为什么脚本里全是英文**：`.bat` 由 cmd.exe 按控制台代码页逐行解析，UTF-8 中文会把逻辑切断（首行加 BOM 还会让 `@echo off` 直接失效）。纯 ASCII 才能在任何 Windows 语言环境下都正常执行。中文说明放在本文档里。

命令行方式：

```bash
pip install -r requirements.txt
PYTHONPATH=src PORT=8000 python run.py
```

没装 openpyxl 时服务仍能启动，只是点「导出 Excel」会返回 503 并在按钮下方提示 `pip install openpyxl`，不会抛 500。

### ③ 在线版

需要能访问外网。如果浏览器提示"无法访问此网站"，通常是本机代理/DNS 问题：
换一个网络、关掉代理，或直接改用 ① ②。

### 排障顺序

1. 先打开 ①，确认页面能渲染 → 说明代码没问题
2. 再试 ②，确认本机 Python 环境正常 → 能拿到 xlsx
3. 最后试 ③ → 只有这一步才涉及网络
