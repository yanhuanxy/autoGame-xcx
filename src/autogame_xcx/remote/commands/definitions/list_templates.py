"""#list：列出可用模板。

对接 core/template_manager.py 的真实 API：
    manager.list_templates() → list[dict{filename, filepath, name, version, game_name, ...}]
"""
from __future__ import annotations

from autogame_xcx.remote.commands.base import Command, CommandContext, CommandResult


class ListTemplatesCommand(Command):
    name = "LIST_TEMPLATES"
    aliases = ["list", "ls", "列表", "模板"]
    description = "列出可用模板"
    usage = "#list"

    def execute(self, ctx: CommandContext, args: str) -> CommandResult:
        try:
            templates = ctx.template_manager.list_templates()
        except Exception as e:
            return CommandResult(success=False, message=f"读取模板列表失败：{e}")

        if not templates:
            return CommandResult(success=True, message="（暂无模板）")

        lines = [f"可用模板（共 {len(templates)} 个）："]
        for t in templates:
            name = t.get("name", "?")
            game = t.get("game_name", "")
            suffix = f"  [{game}]" if game else ""
            lines.append(f"  #run {name}{suffix}")
        lines.append("")
        lines.append("提示：用 #run <模板名> 触发执行")
        return CommandResult(success=True, message="\n".join(lines))
