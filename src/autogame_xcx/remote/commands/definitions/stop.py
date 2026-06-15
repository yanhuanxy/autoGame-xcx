"""#stop：停止当前任务。

阶段 2.3 是占位实现——scheduler 还没接入（阶段 2.4 才有）。
若 ctx.state["scheduler"] 存在则调用其 stop()；否则提示未启用。
"""
from __future__ import annotations

import logging

from autogame_xcx.remote.commands.base import Command, CommandContext, CommandResult

logger = logging.getLogger(__name__)


class StopCommand(Command):
    name = "STOP"
    aliases = ["stop", "停止", "取消"]
    description = "停止当前正在执行的任务"
    usage = "#stop"

    def execute(self, ctx: CommandContext, args: str) -> CommandResult:
        scheduler = ctx.state.get("scheduler")
        if scheduler is None:
            return CommandResult(
                success=False,
                message="调度器未启用（阶段 2.4 实现后可用）；当前指令同步执行无法中断",
            )

        try:
            current = scheduler.current_running
            if current is None:
                return CommandResult(success=True, message="当前没有正在执行的任务")
            scheduler.stop_current()
            logger.info("User %s stopped current task", ctx.user_id)
            return CommandResult(success=True, message="已请求停止当前任务")
        except Exception as e:
            logger.exception("stop failed")
            return CommandResult(success=False, message=f"停止失败：{e}")
