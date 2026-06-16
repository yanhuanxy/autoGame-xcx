"""LLM 配置（provider / api_key / model / base_url）+ JSON 持久化。

阶段 2.6 配套：远程驱动 GUI 的"LLM 配置"段会读写这个对象。

JSON 路径约定：`data/config/remote_llm.json`
字段：
    {
        "enabled": true,
        "provider": "anthropic" | "openai",
        "api_key": "sk-...",
        "model": "...",
        "base_url": "..."  # openai 兼容端点；anthropic 忽略
    }
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_OPENAI = "openai"
_VALID_PROVIDERS = (PROVIDER_ANTHROPIC, PROVIDER_OPENAI)


@dataclass
class LlmConfig:
    """LLM 配置（可空字段表示未配置）。

    enabled=False 时，RemoteDriver 不会构造 orchestrator（自然语言消息被忽略）。
    """

    enabled: bool = False
    provider: str = PROVIDER_OPENAI  # 默认 openai（多兼容端点）
    api_key: str = ""
    model: str = ""                  # 用户必须填，无默认猜测
    base_url: str = ""               # 仅 openai 兼容端点用
    extra: dict = field(default_factory=dict)  # 预留扩展字段

    def validate(self) -> str | None:
        """返回 None 表示配置可用；否则返回错误描述。"""
        if not self.enabled:
            return None
        if self.provider not in _VALID_PROVIDERS:
            return f"provider 必须是 {_VALID_PROVIDERS} 之一，当前：{self.provider}"
        if not self.api_key.strip():
            return "api_key 不能为空"
        if not self.model.strip():
            return "model 不能为空"
        return None


def load_llm_config(path: Path) -> LlmConfig:
    """从 JSON 加载；文件不存在或解析失败返回默认空配置（不抛异常）。"""
    if not path.exists():
        logger.info("LLM config not found, using default: %s", path)
        return LlmConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load LLM config %s: %s", path, e)
        return LlmConfig()
    return LlmConfig(
        enabled=bool(data.get("enabled", False)),
        provider=str(data.get("provider", PROVIDER_OPENAI)),
        api_key=str(data.get("api_key", "")),
        model=str(data.get("model", "")),
        base_url=str(data.get("base_url", "")),
        extra=dict(data.get("extra", {})) if isinstance(data.get("extra"), dict) else {},
    )


def save_llm_config(config: LlmConfig, path: Path) -> None:
    """持久化到 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "enabled": config.enabled,
        "provider": config.provider,
        "api_key": config.api_key,
        "model": config.model,
        "base_url": config.base_url,
        "extra": config.extra,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("LLM config saved to %s", path)
