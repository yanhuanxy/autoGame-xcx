"""LLM 编排器：自然语言 → 指令队列。

工作流：
    1. build_orchestration_prompt 拼装 system+user prompt（含指令清单 + 格式约束）
    2. provider.chat 拿 JSON 字符串
    3. _parse_and_validate 解析 JSON，对每个 action 走 registry.resolve_alias 校验
    4. 校验通过：逐条入 scheduler 队列；回执"已规划 N 个"
       校验失败：整批拒绝 + 回执错误描述（不入队任何指令）

安全防线（PLAN_02 §7 风险表"LLM 拆解指令失败/越界"对策）：
    - JSON 解析失败 / 字段缺失 / 类型错误 → 拒绝
    - action 不在 registry 别名表 → 拒绝（防 LLM 幻觉 #delete_database 之类）
    - 单条失败导致整批拒绝（避免半执行状态难以回滚）
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from autogame_xcx.remote.commands.parser import ParsedCommand
from autogame_xcx.remote.commands.registry import CommandRegistry
from autogame_xcx.remote.llm.prompt_templates import build_orchestration_prompt
from autogame_xcx.remote.llm.provider import LlmProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrchestrationResult:
    """编排结果（用于测试断言；同时通过 sender 回执用户）。"""

    success: bool
    message: str               # 回执文本
    commands: list[ParsedCommand]  # 通过校验的指令（success=False 时为空）


class LLMOrchestrator:
    """自然语言 → 指令队列编排器。

    用法：
        orchestrator = LLMOrchestrator(
            provider=AnthropicProvider(api_key=...),
            registry=build_default_registry(),
            scheduler=queue,
            sender=ilink_client,
        )
        router = MessageRouter(..., llm_orchestrator=orchestrator)
    """

    def __init__(
        self,
        provider: LlmProvider,
        registry: CommandRegistry,
        scheduler,
        sender,
    ) -> None:
        self.provider = provider
        self.registry = registry
        self.scheduler = scheduler
        self.sender = sender

    def handle_natural_language(
        self, user_id: str, text: str
    ) -> OrchestrationResult:
        """处理一条自然语言消息。

        1. 调 LLM
        2. 解析 + 白名单校验
        3. 入队 / 回执
        """
        messages = build_orchestration_prompt(text, self.registry.all_commands())
        try:
            raw_response = self.provider.chat(messages)
        except Exception as e:
            logger.exception("LLM provider.chat crashed")
            return self._fail(user_id, f"AI 调用失败：{e}", [])

        commands, parse_error = self._parse_and_validate(raw_response)
        if parse_error is not None:
            logger.warning(
                "LLM response rejected: %s; raw_head=%r",
                parse_error,
                raw_response[:200],
            )
            return self._fail(user_id, parse_error, [])

        if not commands:
            return self._fail(
                user_id, "未能理解您的请求；输入 #help 查看可用指令", []
            )

        for cmd in commands:
            try:
                self.scheduler.enqueue(user_id, cmd)
            except Exception as e:
                logger.exception("scheduler.enqueue crashed")
                return self._fail(user_id, f"指令入队失败：{e}", [])

        msg = f"已为您规划 {len(commands)} 个指令，正在顺序执行..."
        self._reply(user_id, msg)
        return OrchestrationResult(success=True, message=msg, commands=list(commands))

    def _parse_and_validate(
        self, raw_response: str
    ) -> tuple[list[ParsedCommand], str | None]:
        """解析 + 白名单校验 LLM 输出。

        Returns:
            (commands, None)  — 全部通过
            ([], error_msg)   — 任一项失败（解析或校验）
        """
        json_str = _extract_json_array(raw_response)
        if json_str is None:
            return [], "AI 输出格式异常（未找到 JSON 数组），请改用 # 指令"

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return [], f"AI 输出 JSON 解析失败：{e}"

        if not isinstance(data, list):
            return [], "AI 输出应为 JSON 数组"

        commands: list[ParsedCommand] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                return [], f"AI 输出第 {i + 1} 项不是对象"

            action = item.get("action")
            args = item.get("args", "")

            if not isinstance(action, str) or not action.strip():
                return [], f"AI 输出第 {i + 1} 项缺少 action 字段"
            if not isinstance(args, str):
                return [], f"AI 输出第 {i + 1} 项 args 必须是字符串"

            canonical = self.registry.resolve_alias(action)
            if canonical is None:
                return [], f"AI 输出指令不在白名单：#{action}"

            commands.append(
                ParsedCommand(
                    name=canonical,
                    args=args,
                    raw=f"#{action} {args}".strip(),
                )
            )
        return commands, None

    def _fail(self, user_id: str, message: str, commands: list[ParsedCommand]) -> OrchestrationResult:
        self._reply(user_id, message)
        return OrchestrationResult(success=False, message=message, commands=commands)

    def _reply(self, user_id: str, text: str) -> None:
        try:
            self.sender.send_text(user_id, text)
        except Exception:
            logger.exception("Failed to send reply to %s", user_id)


def _extract_json_array(text: str) -> str | None:
    """从 LLM 文本中抽取第一个 JSON 数组片段。

    容错策略（LLM 经常无视"只输出 JSON"约束）：
    - 先剥离 ```json ... ``` / ``` ... ``` 围栏
    - 取第一个 '[' 到最后一个 ']' 之间的内容
    - 找不到括号返回 None
    """
    text = (text or "").strip()
    if not text:
        return None

    # 剥离 Markdown 围栏
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]
