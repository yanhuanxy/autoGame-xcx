"""大模型编排：自然语言 → 指令队列。

组件（按 PLAN_02 §5.11）：
    LlmProvider                — 抽象协议（provider.py）
    MockLlmProvider            — 测试用桩，按预设队列出响应（provider.py）
    AnthropicProvider          — Claude 实现（可选依赖 anthropic，anthropic_provider.py）
    OpenAIProvider             — OpenAI 兼容实现（可选依赖 openai，openai_provider.py）
    build_orchestration_prompt — 提示词构造（prompt_templates.py）
    LLMOrchestrator            — 编排器（orchestrator.py）

注意：AnthropicProvider / OpenAIProvider 不在 __all__ 中——
import 它们需要安装 optional 依赖。需要时显式写：
    from autogame_xcx.remote.llm.anthropic_provider import AnthropicProvider
"""
from autogame_xcx.remote.llm.orchestrator import LLMOrchestrator, OrchestrationResult
from autogame_xcx.remote.llm.prompt_templates import build_orchestration_prompt
from autogame_xcx.remote.llm.provider import LlmProvider, MockLlmProvider

__all__ = [
    "LlmProvider",
    "MockLlmProvider",
    "LLMOrchestrator",
    "OrchestrationResult",
    "build_orchestration_prompt",
]
