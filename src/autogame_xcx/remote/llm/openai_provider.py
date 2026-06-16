"""OpenAI 兼容 API 提供方（optional 依赖）。

依赖：`uv pip install openai`（或 `uv pip install autogame-xcx[llm]`）

兼容端点：OpenAI 官方、Azure OpenAI、DeepSeek、Moonshot 等所有
"OpenAI-compatible" 接口——通过 base_url 切换。
"""
from __future__ import annotations

from collections.abc import Sequence


class OpenAIProvider:
    """OpenAI 兼容 LLM 实现。

    用法：
        provider = OpenAIProvider(
            api_key="sk-...",
            model="gpt-4o",
            base_url="https://api.openai.com/v1",  # 留空走默认
        )
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        max_tokens: int = 1024,
    ) -> None:
        try:
            import openai  # type: ignore[import-not-found]
        except ImportError as e:
            raise ImportError(
                "openai 包未安装；请运行 `uv pip install openai`"
                " 或 `uv pip install autogame-xcx[llm]`"
            ) from e
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai.OpenAI(**kwargs)
        self._model = model
        self._max_tokens = max_tokens

    def chat(self, messages: Sequence[dict]) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=list(messages),
        )
        return resp.choices[0].message.content or ""
