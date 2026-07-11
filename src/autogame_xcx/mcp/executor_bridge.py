"""ExecutorBridge：MCP tool 与 GameExecutor/TemplateManager 之间的桥接。

职责：
1. 串行化 GameExecutor.execute_template 调用（避免并发触发多个游戏脚本）
2. 提供 tool 友好的同步 API（run_template / get_status / stop_execution / get_report / list_templates）
3. 不持有任何远程通信状态（MCP server / bot 端的状态都不在这里）

线程模型：
    MCP tool handler（asyncio loop 内）
        ↓ asyncio.to_thread(...)
    ExecutorBridge.run_template(...)（在线程池里阻塞）
        ↓ self._lock（保证串行）
    GameExecutor.execute_template(...)
        ↓
    Windows API / GUI 自动化（必须串行）

GUI 触发的执行也应通过本 bridge，确保和远程触发共享同一个锁。
"""
from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autogame_xcx.core.game_executor import GameExecutor
    from autogame_xcx.core.template_manager import TemplateManager

logger = logging.getLogger(__name__)


class ExecutorBridge:
    """串行化 GameExecutor 访问的桥接层。

    无 lifecycle（不需要 start/stop），构造时注入 executor + template_manager 即可。
    """

    def __init__(self, executor: GameExecutor, template_manager: TemplateManager) -> None:
        self._executor = executor
        self._template_manager = template_manager
        self._lock = threading.Lock()
        self._last_report: dict | None = None
        self._current_template: str | None = None
        # 迭代C：发起当前执行的调用方标识（bot 账号名），用于 get_status 归属 / stop_execution 越权校验
        self._current_caller: str | None = None

    def list_templates(self) -> list[dict]:
        """列出所有本地模板。

        Returns:
            list of {filename, filepath, name, version, game_name, created_time}
        Raises:
            RuntimeError: 读取失败。
        """
        try:
            return list(self._template_manager.list_templates())
        except Exception as e:
            logger.exception("list_templates failed")
            raise RuntimeError(f"读取模板列表失败：{e}") from e

    def run_template(self, name: str, caller: str | None = None) -> dict:
        """按 name 执行模板，阻塞到完成。

        Args:
            caller: 发起方标识（bot 账号名），记录为当前执行的 owner，供 get_status/stop_execution 使用。

        Returns:
            {template, filepath, success, summary: {completed, total_tasks, success_rate, ...}}
        Raises:
            ValueError: 模板不存在。
            RuntimeError: 执行异常。
        """
        templates = self.list_templates()
        match = next((t for t in templates if t.get("name") == name), None)
        if match is None:
            available = [t.get("name", "?") for t in templates]
            raise ValueError(f"模板不存在：{name}；可用：{available}")

        filepath = match.get("filepath")
        if not filepath:
            raise RuntimeError(f"模板缺少 filepath 字段：{match}")

        with self._lock:
            self._current_template = name
            self._current_caller = caller
            logger.info("MCP run_template: %s (%s), caller=%s", name, filepath, caller)
            try:
                success = bool(self._executor.execute_template(filepath))
            except Exception as e:
                logger.exception("execute_template crashed")
                raise RuntimeError(f"模板执行异常：{e}") from e
            finally:
                self._current_template = None
                self._current_caller = None

            summary: dict = {}
            try:
                summary = self._executor.execution_report.get("summary", {}) or {}
            except Exception:
                logger.warning("Failed to read summary from execution_report")

            try:
                self._last_report = dict(self._executor.execution_report or {})
            except Exception:
                pass

            return {
                "template": name,
                "filepath": filepath,
                "success": success,
                "summary": summary,
            }

    def get_status(self) -> dict:
        """返回当前执行状态。

        running=True 时 current_template 给出正在跑的模板名，caller 给出发起方（迭代C）。
        """
        # _current_template 仅在持锁时非 None；不持锁即视为空闲
        return {
            "running": self._current_template is not None,
            "current_template": self._current_template,
            "caller": self._current_caller,
            "last_template": (self._last_report or {})
            .get("template_info", {})
            .get("name"),
        }

    def stop_execution(self, caller: str | None = None) -> dict:
        """请求停止当前执行。

        越权校验（迭代C）：仅发起方本人可请求停止；caller 不匹配当前 owner 时直接拒绝，
        不触碰 GameExecutor（越权判断先于"是否支持中断"判断）。
        GameExecutor 当前不检查停止信号，即便 owner 校验通过也只是占位（返回原因）。
        """
        owner = self._current_caller
        if owner is not None and caller != owner:
            logger.warning("stop_execution 越权：caller=%s，当前 owner=%s", caller, owner)
            return {
                "stopped": False,
                "reason": f"无权停止其他调用方发起的任务（当前运行方：{owner}）",
            }
        logger.warning("stop_execution requested (GameExecutor does not support interrupt)")
        return {
            "stopped": False,
            "reason": "GameExecutor 当前不支持中断正在执行的指令",
        }

    def get_report(self) -> dict:
        """返回最近一次执行的完整报告（无则空 dict）。"""
        return self._last_report or {}
