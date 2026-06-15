"""#help：查看可用指令。

通过 bind_registry() 在 build_default_registry() 完成后注入 registry 引用，
避免构造期循环引用。
"""
from __future__ import annotations

from autogame_xcx.remote.commands.base import Command, CommandContext, CommandResult
from autogame_xcx.remote.commands.parser import HelpCommandText


class HelpCommand(Command):
    name = "HELP"
    aliases = ["help", "?", "帮助"]
    description = "查看可用指令"
    usage = "#help"

    def __init__(self) -> None:
        self._registry = None

    def bind_registry(self, registry) -> None:
        """由 build_default_registry() 在注册完成后调用。"""
        self._registry = registry

    def execute(self, ctx: CommandContext, args: str) -> CommandResult:
        if self._registry is None:
            return CommandResult(success=False, message="help 未初始化")
        return CommandResult(success=True, message=HelpCommandText.render(self._registry))
