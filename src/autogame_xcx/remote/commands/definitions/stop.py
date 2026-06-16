"""#stop：停止当前任务（取消队列中等待的）。

阶段 2.4 完整实现：
- 调用 scheduler.cancel_pending(user_id) 取消该用户在队列中尚未开始的指令
- 正在执行的指令（execute_template）无法立即中断（底层不检查停止信号），
  但取消队列可防止"连发 3 个 #run 时全跑掉"
- 若取消数为 0 且无正在执行的任务，明确告知用户
"""
from __future__ import annotations

import logging

from autogame_xcx.remote.commands.base import Command, CommandContext, CommandResult

logger = logging.getLogger(__name__)


class StopCommand(Command):
    name = "STOP"
    aliases = ["stop", "停止", "取消"]
    description = "取消队列中等待的指令（正在执行中的无法立即中断）"
    usage = "#stop"

    def execute(self, ctx: CommandContext, args: str) -> CommandResult:
        scheduler = ctx.state.get("scheduler")
        if scheduler is None:
            return CommandResult(
                success=False,
                message="调度器未启用；当前指令同步执行无法取消",
            )

        try:
            cancelled = scheduler.cancel_pending(user_id=ctx.user_id)
            current = scheduler.current_running
            current_is_self = current is not None and current[0] == ctx.user_id

            parts = []
            if cancelled > 0:
                parts.append(f"已取消 {cancelled} 个排队中的指令")
            if current_is_self:
                parts.append("正在执行的指令无法立即中断（底层执行器不响应取消信号），将在完成后退出")
            if not parts:
                if current is None:
                    return CommandResult(success=True, message="无任务可取消（队列空、空闲中）")
                # 队列空但别的用户在执行
                return CommandResult(
                    success=True,
                    message="无任务可取消（您当前没有排队或执行的指令）",
                )

            logger.info(
                "User %s stopped: cancelled=%d, current_is_self=%s",
                ctx.user_id, cancelled, current_is_self,
            )
            return CommandResult(success=True, message="；".join(parts))
        except Exception as e:
            logger.exception("stop failed")
            return CommandResult(success=False, message=f"停止失败：{e}")
