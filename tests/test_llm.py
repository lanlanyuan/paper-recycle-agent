"""模型配置模块测试。

这里最要紧的一条是：**密钥绝不能出现在任何输出里**。
其余是配置读写、回落行为与错误提示的可读性。
"""

import json
import urllib.error

import pytest

from paper_recycle_agent import llm

SECRET = "sk-test-1234567890abcdefXYZ"


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    """把配置文件重定向到临时目录，避免污染真实 config/llm.json。"""
    monkeypatch.setattr(llm, "CONFIG_PATH", tmp_path / "config" / "llm.json")
    for name in (llm.ENV_BASE_URL, llm.ENV_API_KEY, llm.ENV_MODEL):
        monkeypatch.delenv(name, raising=False)
    yield


# ---------------------------------------------------------------- 脱敏


def test_mask_key():
    assert llm.mask_key(SECRET) == "sk-…" + SECRET[-4:]
    assert "1234567890" not in llm.mask_key(SECRET)


def test_mask_key_short_and_empty():
    assert llm.mask_key("") == ""
    assert llm.mask_key(None) == ""
    assert llm.mask_key("ab") == "…"
    assert llm.mask_key("abcdef") == "…ef"


def test_public_config_never_leaks_key():
    cfg = llm.LLMConfig(api_key=SECRET)
    pub = cfg.public()
    dumped = json.dumps(pub, ensure_ascii=False)
    assert SECRET not in dumped
    assert pub["has_api_key"] is True
    assert pub["api_key_masked"].endswith(SECRET[-4:])


# ---------------------------------------------------------------- 配置读写


def test_default_config_not_configured():
    cfg = llm.load_config()
    assert cfg.configured() is False
    assert cfg.base_url == llm.DEFAULT_BASE_URL


def test_save_and_load_roundtrip():
    llm.save_config("https://api.deepseek.com/v1", SECRET, "deepseek-chat",
                    temperature=0.5, max_tokens=800)
    cfg = llm.load_config()
    assert cfg.base_url == "https://api.deepseek.com/v1"
    assert cfg.api_key == SECRET
    assert cfg.model == "deepseek-chat"
    assert cfg.temperature == 0.5
    assert cfg.max_tokens == 800
    assert cfg.source == "file"


def test_save_without_key_keeps_previous_key():
    """界面上只改模型名时，不应该把已有密钥清掉。"""
    llm.save_config("https://api.deepseek.com/v1", SECRET, "deepseek-chat")
    llm.save_config("https://api.deepseek.com/v1", None, "deepseek-reasoner")
    cfg = llm.load_config()
    assert cfg.api_key == SECRET
    assert cfg.model == "deepseek-reasoner"


def test_env_overrides_file():
    llm.save_config("https://file.example/v1", "file-key", "file-model")
    import os

    os.environ[llm.ENV_BASE_URL] = "https://env.example/v1"
    os.environ[llm.ENV_API_KEY] = "env-key"
    try:
        cfg = llm.load_config()
        assert cfg.source == "env"
        assert cfg.base_url == "https://env.example/v1"
        assert cfg.api_key == "env-key"
    finally:
        os.environ.pop(llm.ENV_BASE_URL, None)
        os.environ.pop(llm.ENV_API_KEY, None)


def test_clear_config():
    llm.save_config("https://x/v1", SECRET, "m")
    assert llm.clear_config() is True
    assert llm.clear_config() is False
    assert llm.load_config().configured() is False


def test_config_file_is_valid_json():
    llm.save_config("https://x/v1", SECRET, "m")
    raw = json.loads(llm.CONFIG_PATH.read_text(encoding="utf-8"))
    assert raw["api_key"] == SECRET
    assert set(raw) >= {"base_url", "api_key", "model", "temperature", "max_tokens"}


# ---------------------------------------------------------------- endpoint


def test_endpoint_appends_path():
    cfg = llm.LLMConfig(base_url="https://api.deepseek.com/v1")
    assert cfg.endpoint() == "https://api.deepseek.com/v1/chat/completions"


def test_endpoint_tolerates_trailing_slash_and_full_path():
    assert llm.LLMConfig(base_url="https://x/v1/").endpoint() == "https://x/v1/chat/completions"
    assert llm.LLMConfig(
        base_url="https://x/v1/chat/completions"
    ).endpoint() == "https://x/v1/chat/completions"


# ---------------------------------------------------------------- 回落与报错


def test_chat_without_key_returns_not_configured():
    result = llm.chat([{"role": "user", "content": "hi"}])
    assert result["ok"] is False
    assert result["configured"] is False
    assert llm.ENV_API_KEY in result["error"]


def test_probe_without_key():
    result = llm.probe()
    assert result["ok"] is False
    assert result["configured"] is False


def test_chat_http_error_is_readable_and_scrubbed(monkeypatch):
    cfg = llm.LLMConfig(api_key=SECRET, model="m")

    def boom(url, payload, key, timeout):
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(llm, "_post", boom)
    result = llm.chat([{"role": "user", "content": "hi"}], config=cfg)
    assert result["ok"] is False
    assert "密钥无效" in result["error"]
    assert SECRET not in json.dumps(result, ensure_ascii=False)


def test_chat_network_error_is_readable(monkeypatch):
    cfg = llm.LLMConfig(api_key=SECRET, model="m")

    def boom(url, payload, key, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(llm, "_post", boom)
    result = llm.chat([{"role": "user", "content": "hi"}], config=cfg)
    assert result["ok"] is False
    assert "连接失败" in result["error"]


def test_chat_bad_payload_shape(monkeypatch):
    cfg = llm.LLMConfig(api_key=SECRET, model="m")
    monkeypatch.setattr(llm, "_post", lambda *a, **k: {"unexpected": True})
    result = llm.chat([{"role": "user", "content": "hi"}], config=cfg)
    assert result["ok"] is False
    assert "OpenAI 兼容" in result["error"]


def test_chat_success(monkeypatch):
    cfg = llm.LLMConfig(api_key=SECRET, model="m")
    monkeypatch.setattr(
        llm, "_post",
        lambda *a, **k: {
            "choices": [{"message": {"content": " 可用 "}}],
            "usage": {"total_tokens": 7},
        },
    )
    result = llm.chat([{"role": "user", "content": "hi"}], config=cfg)
    assert result["ok"] is True
    assert result["reply"] == "可用"
    assert result["usage"]["total_tokens"] == 7


def test_status_shape():
    s = llm.status()
    assert "config" in s and "presets" in s
    assert isinstance(s["presets"], list) and s["presets"]
    assert s["ready"] is False


def test_system_prompt_forbids_fabrication():
    assert "不要编造" in llm.DEFAULT_SYSTEM_PROMPT
