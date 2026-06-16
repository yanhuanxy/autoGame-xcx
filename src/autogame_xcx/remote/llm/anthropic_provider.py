"""Anthropic Claude 提供方（optional 依赖）。

依赖：`uv pip install anthropic`（或 `uv pip install autogame-xcx[llm]`）

注意：本模块在 anthropic 未安装时，仅在 import 时才报错——
让 orchestrator 测试可以不安装 anthropic 而走 MockLlmProvider。
"""
from __future__ import annotations

from collections.abc import Sequence


class AnthropicProvider:
    """Claude API 实现。

    用法：
        provider = AnthropicProvider(
            api_key="sk-ant-...",
            model="claude-sonnet-4-6",
        )
        text = provider.chat([
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
        ])
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 1024,
    ) -> None:
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as e:
            raise ImportError(
                "anthropic 包未安装；请运行 `uv pip install anthropic`"
                " 或 `uv pip install autogame-xcx[llm]`"
            ) from e
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def chat(self, messages: Sequence[dict]) -> str:
        # Anthropic SDK 把 system 段落单独传，这里做一次拆分兼容 OpenAI 风格 messages
        system_parts = [
            str(m["content"])
            for m in messages
            if m.get("role") == "system"
        ]
        conv = [
            {"role": m["role"], "content": str(m["content"])}
            for m in messages
            if m.get("role") in ("user", "assistant")
        ]
        kwargs: dict = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": conv,
        }
        if system_parts:
            kwargs["system"] = "\n\n".join(system_parts)

        resp = self._client.messages.create(**kwargs)
        # resp.content 是 list[ContentBlock]，取第一个 text block
        if resp.content and hasattr(resp.content[0], "text"):
            return resp.content[0].text or ""
        return ""
