"""文本解析：# 前缀 + 别名 → ParsedCommand。

纯文本解析，不依赖 Java SDK；可单独单元测试。
"""
from __future__ import annotations

from dataclasses import dataclass

from autogame_xcx.remote.commands.registry import CommandRegistry

PREFIX = "#"


@dataclass(frozen=True)
class ParsedCommand:
    """解析结果。

    name: 规范指令名（如 RUN_TEMPLATE）；未注册的别名 → "UNKNOWN"
    args: 指令参数（已 strip；无参数为 ""）
    raw:  原始文本（含 # 前缀）
    """

    name: str
    args: str
    raw: str


class CommandParser:
    """文本 → ParsedCommand。

    用法：
        parser = CommandParser(registry)
        parsed = parser.parse("#run 签到")
        if parsed is None: ...  # 不是指令
        else: dispatcher.dispatch(ctx, parsed)
    """

    def __init__(self, registry: CommandRegistry, prefix: str = PREFIX) -> None:
        self.registry = registry
        self.prefix = prefix

    def is_command(self, text: str) -> bool:
        """文本是否以指令前缀开头（不校验别名是否注册）。"""
        return bool(text) and text.startswith(self.prefix)

    def parse(self, text: str) -> ParsedCommand | None:
        """解析文本。

        Returns:
            ParsedCommand — 是指令（含 UNKNOWN 别名情形）
            None          — 不是指令（不以 # 开头，或 # 后空白）
        """
        if not text or not text.startswith(self.prefix):
            return None
        body = text[len(self.prefix):].strip()
        if not body:
            return None
        parts = body.split(maxsplit=1)
        command_alias = parts[0]
        args = parts[1].strip() if len(parts) > 1 else ""
        canonical = self.registry.resolve_alias(command_alias)
        name = canonical if canonical is not None else "UNKNOWN"
        return ParsedCommand(name=name, args=args, raw=text)


class HelpCommandText:
    """#help 文本生成（不注册为正式 Command，仅格式化）。"""

    @staticmethod
    def render(registry: CommandRegistry) -> str:
        cmds = registry.all_commands()
        if not cmds:
            return "（暂无可用指令）"
        lines = ["可用指令："]
        for cmd in cmds:
            aliases = "/".join("#" + a for a in cmd.aliases) if cmd.aliases else f"#{cmd.name.lower()}"
            lines.append(f"  {aliases}  — {cmd.description}")
        return "\n".join(lines)
