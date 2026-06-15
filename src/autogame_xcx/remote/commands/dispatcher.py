"""指令分发：ParsedCommand → Command.execute → CommandResult。

异常隔离：Command.execute 抛任何异常都被捕获，转为 success=False 的 CommandResult。
这样单个指令崩溃不会拖垮整个消息处理流程。
"""
from __future__ import annotations

import logging

from autogame_xcx.remote.commands.base import CommandContext, CommandResult
from autogame_xcx.remote.commands.parser import ParsedCommand
from autogame_xcx.remote.commands.registry import CommandRegistry

logger = logging.getLogger(__name__)

# 内置"伪指令名"：别名未注册时 parser 返回这个
UNKNOWN_NAME = "UNKNOWN"


class CommandDispatcher:
    """分发指令到具体 Command 实现。

    - UNKNOWN：别名未注册，回提示并附 #help 链接
    - 其他：从 registry 取 Command.execute；异常被捕获转为失败结果
    """

    def __init__(self, registry: CommandRegistry) -> None:
        self.registry = registry

    def dispatch(self, ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
        if parsed.name == UNKNOWN_NAME:
            unknown_token = parsed.args.split(maxsplit=1)[0] if parsed.args else ""
            hint = (
                f"未知指令：#{unknown_token}\n\n"
                "输入 #help 查看可用指令"
            )
            return CommandResult(success=False, message=hint)

        command = self.registry.find(parsed.name)
        if command is None:
            logger.warning("Parsed name %s not in registry", parsed.name)
            return CommandResult(success=False, message=f"指令未注册：{parsed.name}")

        try:
            result = command.execute(ctx, parsed.args)
            if result is None:
                logger.warning("%s.execute returned None", type(command).__name__)
                return CommandResult(success=False, message="指令未返回结果")
            return result
        except Exception as e:
            logger.exception("Command %s crashed", parsed.name)
            return CommandResult(success=False, message=f"内部错误：{e}")
