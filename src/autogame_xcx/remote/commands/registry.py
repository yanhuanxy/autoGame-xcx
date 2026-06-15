"""指令注册表 + 别名解析。

注册的指令供 parser/dispatcher 查找；build_default_registry() 装载本阶段 5 个指令。
"""
from __future__ import annotations

from autogame_xcx.remote.commands.base import Command


class CommandRegistry:
    """指令注册表。

    - 按 canonical name 注册 Command 实例
    - 别名（含 canonical name 的小写形式）映射到 canonical name
    - resolve_alias() 大小写不敏感
    """

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self._alias_to_name: dict[str, str] = {}

    def register(self, command: Command) -> Command:
        if not command.name:
            raise ValueError(
                f"{type(command).__name__}.name 必须设置（不能为空字符串）"
            )
        if command.name in self._commands:
            raise ValueError(f"指令已注册：{command.name}")
        self._commands[command.name] = command
        # canonical name 自身的小写形式也作为别名
        self._alias_to_name[command.name.lower()] = command.name
        for alias in command.aliases:
            key = alias.lower()
            if key in self._alias_to_name and self._alias_to_name[key] != command.name:
                raise ValueError(
                    f"别名冲突：'{alias}' 已绑定到 {self._alias_to_name[key]}"
                )
            self._alias_to_name[key] = command.name
        return command

    def resolve_alias(self, alias: str) -> str | None:
        """返回 canonical name；未注册返回 None。"""
        return self._alias_to_name.get(alias.lower())

    def find(self, canonical_name: str) -> Command | None:
        """按 canonical name 取指令；不存在返回 None。"""
        return self._commands.get(canonical_name)

    def all_commands(self) -> list[Command]:
        """所有已注册指令（按注册顺序）。"""
        return list(self._commands.values())

    def __len__(self) -> int:
        return len(self._commands)

    def __contains__(self, canonical_name: str) -> bool:
        return canonical_name in self._commands


def build_default_registry() -> CommandRegistry:
    """装载阶段 2.3 的 5 个基础指令 + HelpCommand。

    顺序即列出 #help 时的显示顺序。HelpCommand 需要访问 registry 渲染指令列表，
    通过后绑定避免构造期循环引用。
    """
    from autogame_xcx.remote.commands.definitions.help import HelpCommand
    from autogame_xcx.remote.commands.definitions.list_templates import ListTemplatesCommand
    from autogame_xcx.remote.commands.definitions.report import ReportCommand
    from autogame_xcx.remote.commands.definitions.run_template import RunTemplateCommand
    from autogame_xcx.remote.commands.definitions.status import StatusCommand
    from autogame_xcx.remote.commands.definitions.stop import StopCommand

    registry = CommandRegistry()
    registry.register(HelpCommand())
    registry.register(ListTemplatesCommand())
    registry.register(RunTemplateCommand())
    registry.register(StatusCommand())
    registry.register(StopCommand())
    registry.register(ReportCommand())

    # HelpCommand 后绑定 registry（注册完成后才能引用它）
    help_cmd = registry.find("HELP")
    if help_cmd is not None:
        help_cmd.bind_registry(registry)
    return registry
