# 使用说明

## 安装

```bash
# 克隆后进入目录
pip install -e .

# 仅跑测试
pip install pytest
PYTHONPATH=src pytest -q
```

> 运行时**无第三方依赖**，纯 Python 标准库即可。Python ≥ 3.9。

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
