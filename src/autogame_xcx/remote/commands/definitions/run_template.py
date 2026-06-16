"""#run <模板名>：触发本地模板执行。

对接 core API：
    manager.list_templates() → 按 name 匹配（find_by_name 不存在）
    executor.execute_template(filepath) → bool
    executor.execution_report → dict（含 summary）
"""
from __future__ import annotations

import logging

from autogame_xcx.remote.commands.base import Command, CommandContext, CommandResult

logger = logging.getLogger(__name__)


class RunTemplateCommand(Command):
    name = "RUN_TEMPLATE"
    aliases = ["run", "执行", "运行"]
    description = "触发指定模板的自动化执行"
    usage = "#run <模板名>  例如：#run 签到"
    queued_dispatch = True  # 长任务，必须走 scheduler 串行队列

    def execute(self, ctx: CommandContext, args: str) -> CommandResult:
        template_name = args.strip()
        if not template_name:
            return CommandResult(success=False, message=f"用法：{self.usage}")

        try:
            templates = ctx.template_manager.list_templates()
        except Exception as e:
            return CommandResult(success=False, message=f"读取模板列表失败：{e}")

        match = next((t for t in templates if t.get("name") == template_name), None)
        if match is None:
            available = [t.get("name", "?") for t in templates]
            hint = ", ".join(available) if available else "(无)"
            return CommandResult(
                success=False,
                message=f"模板不存在：{template_name}\n可用模板：{hint}\n\n输入 #list 查看完整列表",
            )

        filepath = match.get("filepath")
        if not filepath:
            return CommandResult(
                success=False,
                message=f"模板缺少 filepath 字段：{match}",
            )

        # 提示用户开始执行
        ctx.sender.send_text(ctx.user_id, f"▶ 开始执行模板：{template_name}")
        logger.info("User %s triggered template %s (%s)", ctx.user_id, template_name, filepath)

        try:
            success = bool(ctx.executor.execute_template(filepath))
        except Exception as e:
            logger.exception("execute_template crashed")
            return CommandResult(success=False, message=f"模板执行异常：{e}")

        if not success:
            return CommandResult(success=False, message=f"模板执行失败：{template_name}")

        # 从 execution_report 取摘要（execution_report 可能不存在或异常，吞掉）
        import contextlib

        summary: dict = {}
        with contextlib.suppress(Exception):
            summary = ctx.executor.execution_report.get("summary", {}) or {}

        completed = summary.get("completed", "?")
        total = summary.get("total_tasks", "?")
        rate = summary.get("success_rate", "?")
        return CommandResult(
            success=True,
            message=(
                f"✓ 模板执行完成：{template_name}\n"
                f"任务 {completed}/{total} 成功（成功率 {rate}）\n"
                f"用 #report 查看详情"
            ),
            payload={"template": template_name, "filepath": filepath},
        )
