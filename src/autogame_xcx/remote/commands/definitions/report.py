"""#report [task_id]：查询执行报告。

阶段 2.3 简化实现：忽略 task_id 参数，直接返回 executor 最近一次 execution_report。
阶段 2.4+ 接入持久化任务历史后，task_id 才真正生效。
"""
from __future__ import annotations

from autogame_xcx.remote.commands.base import Command, CommandContext, CommandResult


class ReportCommand(Command):
    name = "REPORT"
    aliases = ["report", "报告", "结果"]
    description = "查询最近一次执行报告"
    usage = "#report [task_id]"

    def execute(self, ctx: CommandContext, args: str) -> CommandResult:
        # args 可能含 task_id，阶段 2.3 忽略
        executor = ctx.executor
        report = getattr(executor, "execution_report", None)
        if not report or not report.get("end_time"):
            return CommandResult(success=True, message="（暂无已完成的执行记录）")

        template_path = report.get("template_path", "?")
        start = report.get("start_time", "?")
        end = report.get("end_time", "?")
        summary = report.get("summary", {}) or {}
        tasks = report.get("tasks", []) or []

        lines = [
            "最近执行报告：",
            f"  模板：{template_path}",
            f"  开始：{start}",
            f"  结束：{end}",
            f"  总任务：{summary.get('total_tasks', '?')}",
            f"  成功：{summary.get('completed', '?')}",
            f"  失败：{summary.get('failed', '?')}",
            f"  成功率：{summary.get('success_rate', '?')}",
        ]

        # 任务级摘要（最多 5 条）
        if tasks:
            lines.append("")
            lines.append("任务详情：")
            for task in tasks[:5]:
                name = task.get("task_name", "?")
                status = task.get("status", "?")
                retry = task.get("retry_count", 0)
                mark = "✓" if status == "completed" else "✗"
                lines.append(f"  {mark} {name}  ({status}, 重试 {retry})")
            if len(tasks) > 5:
                lines.append(f"  ... 共 {len(tasks)} 个任务（仅显示前 5 个）")

        return CommandResult(success=True, message="\n".join(lines))
