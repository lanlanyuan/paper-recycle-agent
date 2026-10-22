"""模型配置模块：接入任意 OpenAI 兼容的大模型 API。

设计要点
--------
1. **零第三方依赖**：用标准库 `urllib.request` 发请求，不引入 requests / openai SDK。
   这样「Python 3.7 + 什么都不装」的承诺不会因为接了大模型而破功。
2. **密钥不出现在任何输出里**：`public_config()` 只返回脱敏值（`sk-…3f9a`），
   报错信息也会先把密钥替换掉再返回。日志、接口响应、异常里都不会带明文。
3. **没配置也能用**：`chat()` 在未配置时返回 `configured=False`，
   上层自动回落到 `agent.py` 的规则引擎。整个工具不会因为「没填 API Key」而不可用。
4. **配置来源优先级**：环境变量 > config/llm.json > 默认值。
   环境变量适合 CI / 服务器；JSON 适合本地图形界面里填。

安全提醒（README 里也写了）
--------------------------
前端明文保存的密钥可被同机程序读取。本模块把配置存在服务端文件
（`config/llm.json`，已加入 .gitignore），接口只回脱敏值。
如果要把服务暴露到公网，请自行加鉴权，或改用只读环境变量方式。
"""

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

ENV_BASE_URL = "PAPER_LLM_BASE_URL"
ENV_API_KEY = "PAPER_LLM_API_KEY"
ENV_MODEL = "PAPER_LLM_MODEL"

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT = 30.0

# 仓库根目录下的 config/llm.json（不纳入版本库）
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "llm.json"

DEFAULT_SYSTEM_PROMPT = (
    "你是废纸回收领域的助手，服务对象包括回收企业、造纸厂、行业协会和统计部门。"
    "回答要求：\n"
    "1. 涉及数据时，先说明口径（官方 / 测算 / 估算 / 示例），不确定就直说不确定；\n"
    "2. 不要编造具体省份的回收量、企业采购量或价格；\n"
    "3. 回答简洁，能用一两句说清就不要展开；\n"
    "4. 中文回答。"
)

# 常见服务商的默认地址，供界面下拉选择
PRESETS: List[Dict[str, str]] = [
    {"name": "OpenAI", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    {"name": "DeepSeek", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    {"name": "通义千问（DashScope 兼容模式）",
     "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
     "model": "qwen-plus"},
    {"name": "智谱 GLM", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash"},
    {"name": "Kimi（Moonshot）", "base_url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"},
    {"name": "本地 Ollama", "base_url": "http://127.0.0.1:11434/v1", "model": "qwen2.5"},
]


def mask_key(key: Optional[str]) -> str:
    """把密钥脱敏成 sk-…3f9a 形式；空值返回空串。"""
    if not key:
        return ""
    text = str(key)
    if len(text) <= 8:
        return "…" + text[-2:] if len(text) > 2 else "…"
    return text[:3] + "…" + text[-4:]


@dataclass
class LLMConfig:
    base_url: str = DEFAULT_BASE_URL
    api_key: str = ""
    model: str = DEFAULT_MODEL
    temperature: float = 0.3
    max_tokens: int = 600
    timeout: float = DEFAULT_TIMEOUT
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    source: str = field(default="default", compare=False)

    def endpoint(self) -> str:
        """补全为 …/chat/completions。兼容用户填 /v1 或填完整路径。"""
        base = self.base_url.strip().rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"

    def configured(self) -> bool:
        return bool(self.api_key.strip())

    def public(self) -> Dict[str, object]:
        """对外暴露的配置：绝不含明文密钥。"""
        return {
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
            "system_prompt": self.system_prompt,
            "api_key_masked": mask_key(self.api_key),
            "has_api_key": bool(self.api_key),
            "configured": self.configured(),
            "source": self.source,
        }


def _from_env() -> Optional[LLMConfig]:
    base = os.environ.get(ENV_BASE_URL, "").strip()
    key = os.environ.get(ENV_API_KEY, "").strip()
    model = os.environ.get(ENV_MODEL, "").strip()
    if not (base or key or model):
        return None
    return LLMConfig(
        base_url=base or DEFAULT_BASE_URL,
        api_key=key,
        model=model or DEFAULT_MODEL,
        source="env",
    )


def _from_file() -> Optional[LLMConfig]:
    if not CONFIG_PATH.exists():
        return None
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None
    return LLMConfig(
        base_url=str(raw.get("base_url") or DEFAULT_BASE_URL),
        api_key=str(raw.get("api_key") or ""),
        model=str(raw.get("model") or DEFAULT_MODEL),
        temperature=float(raw.get("temperature", 0.3)),
        max_tokens=int(raw.get("max_tokens", 600)),
        timeout=float(raw.get("timeout", DEFAULT_TIMEOUT)),
        system_prompt=str(raw.get("system_prompt") or DEFAULT_SYSTEM_PROMPT),
        source="file",
    )


def load_config() -> LLMConfig:
    """环境变量 > config/llm.json > 默认值。"""
    return _from_env() or _from_file() or LLMConfig()


def save_config(base_url: str, api_key: Optional[str], model: str,
                temperature: float = 0.3, max_tokens: int = 600,
                timeout: float = DEFAULT_TIMEOUT,
                system_prompt: Optional[str] = None) -> LLMConfig:
    """保存配置到 config/llm.json。

    `api_key` 传 None 或空串时，保留原有密钥（避免界面上只改模型却把密钥清掉）。
    """
    current = _from_file() or LLMConfig()
    key = current.api_key if not api_key else str(api_key)
    cfg = LLMConfig(
        base_url=(base_url or DEFAULT_BASE_URL).strip(),
        api_key=key.strip(),
        model=(model or DEFAULT_MODEL).strip(),
        temperature=float(temperature),
        max_tokens=int(max_tokens),
        timeout=float(timeout),
        system_prompt=(system_prompt or DEFAULT_SYSTEM_PROMPT),
        source="file",
    )
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(
            {
                "base_url": cfg.base_url,
                "api_key": cfg.api_key,
                "model": cfg.model,
                "temperature": cfg.temperature,
                "max_tokens": cfg.max_tokens,
                "timeout": cfg.timeout,
                "system_prompt": cfg.system_prompt,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    try:  # 尽量收紧权限（Windows 上 chmod 语义有限，失败不影响功能）
        os.chmod(str(CONFIG_PATH), 0o600)
    except OSError:
        pass
    return cfg


def clear_config() -> bool:
    """删除本地配置文件。环境变量方式不受影响。"""
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
        return True
    return False


def _scrub(text: str, key: str) -> str:
    """把可能出现在报错文本里的密钥替换掉。"""
    if key and key in text:
        return text.replace(key, mask_key(key))
    return text


def _post(url: str, payload: Dict[str, object], key: str, timeout: float):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + key,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def chat(messages: List[Dict[str, str]],
         config: Optional[LLMConfig] = None,
         use_system_prompt: bool = True) -> Dict[str, object]:
    """调用 /chat/completions。

    返回结构：
        {"ok": bool, "configured": bool, "reply": str, "error": str,
         "model": str, "latency_ms": int, "usage": {...}}

    未配置密钥时 `ok=False, configured=False`，调用方应回落到规则引擎。
    """
    cfg = config or load_config()
    if not cfg.configured():
        return {
            "ok": False,
            "configured": False,
            "reply": "",
            "error": "未配置模型 API：请在「设置」里填写 Base URL 与 API Key，"
                     "或设置环境变量 %s。" % ENV_API_KEY,
            "model": cfg.model,
            "latency_ms": 0,
            "usage": {},
        }

    payload_msgs: List[Dict[str, str]] = []
    if use_system_prompt and cfg.system_prompt:
        payload_msgs.append({"role": "system", "content": cfg.system_prompt})
    payload_msgs.extend(messages)

    payload = {
        "model": cfg.model,
        "messages": payload_msgs,
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
        "stream": False,
    }

    started = time.time()
    try:
        data = _post(cfg.endpoint(), payload, cfg.api_key, cfg.timeout)
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:400]
        except Exception:  # pragma: no cover - 读取失败时忽略
            detail = ""
        hint = {
            401: "密钥无效或已过期",
            403: "密钥无权限访问该模型",
            404: "Base URL 或模型名不正确",
            429: "触发限流或余额不足",
        }.get(exc.code, "HTTP %d" % exc.code)
        return {
            "ok": False,
            "configured": True,
            "reply": "",
            "error": _scrub("%s（%s）%s" % (hint, exc.code, detail), cfg.api_key),
            "model": cfg.model,
            "latency_ms": int((time.time() - started) * 1000),
            "usage": {},
        }
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "configured": True,
            "reply": "",
            "error": _scrub("连接失败：%s（检查 Base URL 与网络）" % exc.reason, cfg.api_key),
            "model": cfg.model,
            "latency_ms": int((time.time() - started) * 1000),
            "usage": {},
        }
    except Exception as exc:  # pragma: no cover - 兜底，避免接口 500
        return {
            "ok": False,
            "configured": True,
            "reply": "",
            "error": _scrub("调用异常：%s" % exc, cfg.api_key),
            "model": cfg.model,
            "latency_ms": int((time.time() - started) * 1000),
            "usage": {},
        }

    latency = int((time.time() - started) * 1000)
    try:
        reply = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return {
            "ok": False,
            "configured": True,
            "reply": "",
            "error": "返回结构不符合 OpenAI 兼容格式（缺少 choices[0].message.content）",
            "model": cfg.model,
            "latency_ms": latency,
            "usage": {},
        }

    return {
        "ok": True,
        "configured": True,
        "reply": str(reply).strip(),
        "error": "",
        "model": cfg.model,
        "latency_ms": latency,
        "usage": data.get("usage") or {},
    }


def probe(config: Optional[LLMConfig] = None) -> Dict[str, object]:
    """连通性探测：发一句最短的请求，看能不能通。"""
    cfg = config or load_config()
    result = chat(
        [{"role": "user", "content": "回复两个字：可用"}],
        config=cfg,
        use_system_prompt=False,
    )
    return {
        "ok": result["ok"],
        "configured": result["configured"],
        "model": result["model"],
        "latency_ms": result["latency_ms"],
        "reply": result["reply"][:60],
        "error": result["error"],
        "endpoint": cfg.endpoint(),
        "api_key_masked": mask_key(cfg.api_key),
    }


def status() -> Dict[str, object]:
    """给界面用的状态：是否配置、当前来源、可选预设。"""
    cfg = load_config()
    return {
        "config": cfg.public(),
        "presets": PRESETS,
        "config_path": str(CONFIG_PATH),
        "env_vars": [ENV_BASE_URL, ENV_API_KEY, ENV_MODEL],
        "ready": cfg.configured(),
    }
