"""指令系统：解析微信消息中的 `#指令`，分发给具体 Command 执行。

组件：
    Command / CommandContext / CommandResult — 抽象基类与数据类（base.py）
    CommandRegistry                          — 注册表 + 别名解析（registry.py）
    CommandParser / ParsedCommand            — 文本解析（parser.py）
    CommandDispatcher                        — 分发与异常隔离（dispatcher.py）
    definitions/                             — 5 个具体指令实现
"""
from autogame_xcx.remote.commands.base import Command, CommandContext, CommandResult
from autogame_xcx.remote.commands.dispatcher import CommandDispatcher
from autogame_xcx.remote.commands.parser import CommandParser, ParsedCommand
from autogame_xcx.remote.commands.registry import CommandRegistry, build_default_registry

__all__ = [
    "Command",
    "CommandContext",
    "CommandResult",
    "CommandRegistry",
    "build_default_registry",
    "CommandParser",
    "ParsedCommand",
    "CommandDispatcher",
]
