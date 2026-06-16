"""#status：查询当前执行状态。

阶段 2.3 是占位实现，从 executor.execution_report / current_template 推断。
阶段 2.4 接入 scheduler 后会有完整的"队列长度 / 正在执行"等信息。
"""
from __future__ import annotations

from autogame_xcx.remote.commands.base import Command, CommandContext, CommandResult


class StatusCommand(Command):
    name = "STATUS"
    aliases = ["status", "状态"]
    description = "查询当前执行状态"
    usage = "#status"

    def execute(self, ctx: CommandContext, args: str) -> CommandResult:
        executor = ctx.executor
        report = getattr(executor, "execution_report", None) or {}
        current = getattr(executor, "current_template", None)

        lines = ["当前状态："]

        # 正在执行 / 空闲（基于 current_template 与 report.end_time 推断）
        if current is not None and not report.get("end_time"):
            name = current.get("template_info", {}).get("name", "?")
            lines.append(f"  ▶ 正在执行：{name}")
        elif report.get("end_time"):
            lines.append("  ● 空闲（上次执行已结束）")
        else:
            lines.append("  ● 空闲（未执行过）")

        # 队列信息（阶段 2.4 接入 scheduler 后可用）
        scheduler = ctx.state.get("scheduler")
        if scheduler is not None:
            current_task = scheduler.current_running
            queue_len = scheduler.queue_length
            processed = scheduler.processed_count
            if current_task is not None:
                cur_user, cur_parsed = current_task
                lines.append(f"  ▶ 正在执行：#{cur_parsed.raw[1:] if cur_parsed.raw else '?'}（来自 {cur_user}）")
            if queue_len > 0:
                lines.append(f"  队列等待：{queue_len} 个指令")
            else:
                lines.append("  队列等待：0")
            lines.append(f"  累计完成：{processed} 个")
        else:
            lines.append("  （调度器未启用，指令同步执行）")

        # 最近一次执行摘要
        summary = report.get("summary")
        if summary:
            lines.append(
                f"  最近执行：{summary.get('completed', '?')}/{summary.get('total_tasks', '?')} "
                f"任务成功（{summary.get('success_rate', '?')}）"
            )

        return CommandResult(success=True, message="\n".join(lines))
