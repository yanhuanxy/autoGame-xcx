"""LLM 提供方抽象 + 测试用 Mock 实现。

生产实现（按需 import，依赖 optional 包）：
    anthropic_provider.AnthropicProvider  —— 依赖 anthropic
    openai_provider.OpenAIProvider        —— 依赖 openai

测试用：
    MockLlmProvider                       —— 按预设队列出固定响应
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class LlmProvider(Protocol):
    """LLM 提供方的最小接口。

    实现方只需支持 chat(messages) -> str。messages 是 OpenAI/Anthropic
    通用的 [{"role": ..., "content": ...}] 列表，返回模型生成的文本。
    orchestrator 把响应当作 JSON 字符串解析。
    """

    def chat(self, messages: Sequence[dict]) -> str: ...


class MockLlmProvider:
    """测试桩：按入参顺序返回预设响应；同时记录每次调用便于断言。

    用法：
        provider = MockLlmProvider(responses=['[{"action":"run","args":"签到"}]'])
        assert provider.chat([{"role":"user","content":"..."}]).startswith("[")
        assert len(provider.calls) == 1

    responses 耗尽后再调用返回空字符串 ""（避免 IndexError 让用例更稳）。
    """

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses: list[str] = list(responses or [])
        self._calls: list[list[dict]] = []

    def chat(self, messages: Sequence[dict]) -> str:
        self._calls.append([dict(m) for m in messages])
        if not self._responses:
            return ""
        return self._responses.pop(0)

    @property
    def calls(self) -> list[list[dict]]:
        """历史调用（每次 chat 的 messages 副本）。"""
        return self._calls

    @property
    def remaining_responses(self) -> int:
        return len(self._responses)
