"""LLM 编排提示词构造。

把用户的自然语言 + 可用指令清单组装成 OpenAI/Anthropic 通用的 messages 数组，
约束 LLM 输出 JSON 数组：[{"action": "<别名>", "args": "<参数>"}]
"""
from __future__ import annotations

from collections.abc import Iterable

from autogame_xcx.remote.commands.base import Command


def build_orchestration_prompt(
    user_text: str,
    commands: Iterable[Command],
) -> list[dict]:
    """构造 messages 数组。

    Returns:
        [{"role": "system", "content": ...}, {"role": "user", "content": ...}]

    System 段落注入可用指令清单 + JSON 输出格式约束 + 示例，约束 LLM 行为。
    User 段落保留用户原文（去首尾空白）。
    """
    return [
        {"role": "system", "content": _system_prompt(commands)},
        {"role": "user", "content": (user_text or "").strip()},
    ]


def _system_prompt(commands: Iterable[Command]) -> str:
    cmds = list(commands)
    lines = [
        "你是微信小游戏自动化助手的指令编排器。",
        "用户用自然语言描述需求，你把它拆解为一个或多个可执行指令。",
        "",
        "可用指令：",
    ]
    for cmd in cmds:
        aliases = (
            ", ".join("#" + a for a in cmd.aliases)
            if cmd.aliases
            else f"#{cmd.name.lower()}"
        )
        desc = cmd.description or "(无说明)"
        line = f"  - {aliases}：{desc}"
        if cmd.usage:
            line += f"（用法：{cmd.usage}）"
        lines.append(line)

    lines += [
        "",
        "输出要求：",
        "- 只输出 JSON 数组，不要任何解释、前后缀或 Markdown 围栏。",
        '- 每个元素形如：{"action": "<指令别名>", "args": "<参数字符串>"}。',
        "- action 必须是上面列出的别名之一（大小写不敏感）。",
        "- 无法映射到指令时输出空数组 []。",
        "- 多个指令按执行先后顺序排列。",
        "",
        "示例：",
        "用户：帮我把签到和领体力都做了",
        '输出：[{"action": "run", "args": "签到"}, {"action": "run", "args": "领体力"}]',
        "",
        "用户：现在情况怎么样",
        '输出：[{"action": "status", "args": ""}]',
    ]
    return "\n".join(lines)
