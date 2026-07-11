"""ExecutorBridge：MCP tool 与 GameExecutor/TemplateManager 之间的桥接。

职责：
1. 串行化 GameExecutor.execute_template 调用（避免并发触发多个游戏脚本），
   多个调用方并发请求时按 FIFO 排队，排队位置经 get_status 可见。
2. 提供 tool 友好的同步 API（run_template / get_status / stop_execution / get_report / list_templates）
3. 不持有任何远程通信状态（MCP server / bot 端的状态都不在这里）

线程模型：
    MCP tool handler（asyncio loop 内）
        ↓ asyncio.to_thread(...)
    ExecutorBridge.run_template(...)（在线程池里阻塞）
        ↓ self._cv 守护的 FIFO 队列（保证真正执行严格串行）
    self._exec_pool（唯一 worker 线程）
        ↓
    GameExecutor.execute_template(..., cancel_event=...)（可被真取消）
        ↓
    Windows API / GUI 自动化（必须串行）

GUI 触发的执行也应通过本 bridge，确保和远程触发共享同一个队列。
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from autogame_xcx.core.game_executor import ExecutionCancelledError

if TYPE_CHECKING:
    from autogame_xcx.core.game_executor import GameExecutor
    from autogame_xcx.core.template_manager import TemplateManager

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_CAPACITY = 2
DEFAULT_QUEUE_WAIT_TIMEOUT_SECONDS = 300.0
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 480.0


class QueueFullError(RuntimeError):
    """队列已达容量上限，拒绝新请求。"""

    def __init__(self, queue_length: int, queue_capacity: int) -> None:
        self.queue_length = queue_length
        self.queue_capacity = queue_capacity
        super().__init__(f"排队已满（{queue_length}/{queue_capacity}），请稍后重试")


class DuplicateCallerError(RuntimeError):
    """同一 caller 已有在途（排队中或执行中）请求。"""

    def __init__(self, caller: str) -> None:
        self.caller = caller
        super().__init__(f"调用方 {caller} 已有任务在排队或执行中，请等待其完成后再发起")


class QueueWaitTimeoutError(RuntimeError):
    """排队等待超过配置的超时时间，已从队列摘除。"""


class EntryCancelledError(RuntimeError):
    """排队中的任务被 stop_execution 取消。"""


class ExecutionOverdueError(RuntimeError):
    """执行耗时超过配置的超时时间，已发送取消信号（不代表已停止，见 get_status.overdue）。"""


@dataclass(eq=False)
class _QueueEntry:
    """队列里的一项排队/执行记录。用对象identity区分，不做值比较。"""

    caller: str | None
    template: str
    enqueued_at: float
    running: bool = False
    overdue: bool = False
    cancel_event: threading.Event = field(default_factory=threading.Event)


class ExecutorBridge:
    """FIFO 排队 + 严格串行访问 GameExecutor 的桥接层。

    无 lifecycle（不需要 start/stop），构造时注入 executor + template_manager 即可。
    """

    def __init__(
        self,
        executor: GameExecutor,
        template_manager: TemplateManager,
        queue_capacity: int = DEFAULT_QUEUE_CAPACITY,
        queue_wait_timeout_seconds: float | None = DEFAULT_QUEUE_WAIT_TIMEOUT_SECONDS,
        execution_timeout_seconds: float | None = DEFAULT_EXECUTION_TIMEOUT_SECONDS,
    ) -> None:
        self._executor = executor
        self._template_manager = template_manager
        self._queue_capacity = (
            queue_capacity if queue_capacity and queue_capacity > 0 else DEFAULT_QUEUE_CAPACITY
        )
        self._queue_wait_timeout_seconds = queue_wait_timeout_seconds
        self._execution_timeout_seconds = execution_timeout_seconds
        self._cv = threading.Condition()
        self._queue: deque[_QueueEntry] = deque()
        self._exec_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="autogame-exec")
        self._last_report: dict | None = None

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
        """按 name 排队执行模板，阻塞到完成（或被取消/超时）。

        Args:
            caller: 发起方标识（bot 账号名）。同一 caller 同时只能有一个在途
                （排队中或执行中）请求；`caller=None` 不做去重。

        Returns:
            {template, filepath, success, summary: {...}}（被取消时 summary={"cancelled": True}）
        Raises:
            ValueError: 模板不存在。
            DuplicateCallerError: caller 已有在途请求。
            QueueFullError: 队列已满。
            QueueWaitTimeoutError: 排队等待超时，已从队列摘除。
            EntryCancelledError: 排队中被 stop_execution 摘除。
            ExecutionOverdueError: 执行耗时超过配置阈值，已发送取消信号（RPC 不再等待）。
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

        entry = self._enqueue(name, caller)
        self._await_turn(entry)

        logger.info("MCP run_template: %s (%s), caller=%s", name, filepath, caller)
        future = self._exec_pool.submit(self._run_and_cleanup, entry, filepath)
        try:
            return future.result(timeout=self._execution_timeout_seconds)
        except TimeoutError as e:
            entry.overdue = True
            entry.cancel_event.set()
            logger.warning(
                "run_template 执行超时（>%ss），已发送取消信号：caller=%s, template=%s",
                self._execution_timeout_seconds,
                caller,
                name,
            )
            raise ExecutionOverdueError(
                f"执行超过 {self._execution_timeout_seconds}s 未完成，已发送取消信号"
            ) from e

    def _run_and_cleanup(self, entry: _QueueEntry, filepath: str) -> dict:
        """在唯一的 worker 线程里真正执行；无论结果如何都会清理队列（finally）。"""
        try:
            try:
                success = bool(
                    self._executor.execute_template(filepath, cancel_event=entry.cancel_event)
                )
            except ExecutionCancelledError:
                logger.warning("execute_template cancelled: caller=%s", entry.caller)
                return {
                    "template": entry.template,
                    "filepath": filepath,
                    "success": False,
                    "summary": {"cancelled": True},
                }
            except Exception as e:
                logger.exception("execute_template crashed")
                raise RuntimeError(f"模板执行异常：{e}") from e

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
                "template": entry.template,
                "filepath": filepath,
                "success": success,
                "summary": summary,
            }
        finally:
            with self._cv:
                if entry in self._queue:
                    self._queue.remove(entry)
                self._cv.notify_all()

    def _enqueue(self, name: str, caller: str | None) -> _QueueEntry:
        with self._cv:
            if caller is not None and any(e.caller == caller for e in self._queue):
                raise DuplicateCallerError(caller)
            if len(self._queue) >= self._queue_capacity:
                raise QueueFullError(len(self._queue), self._queue_capacity)
            entry = _QueueEntry(caller=caller, template=name, enqueued_at=time.monotonic())
            self._queue.append(entry)
            self._cv.notify_all()
            return entry

    def _await_turn(self, entry: _QueueEntry) -> None:
        deadline = (
            entry.enqueued_at + self._queue_wait_timeout_seconds
            if self._queue_wait_timeout_seconds and self._queue_wait_timeout_seconds > 0
            else None
        )
        with self._cv:
            while True:
                if entry not in self._queue:
                    raise EntryCancelledError("排队中的任务已被取消")
                if self._queue[0] is entry:
                    entry.running = True
                    return
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self._queue.remove(entry)
                        self._cv.notify_all()
                        raise QueueWaitTimeoutError(
                            f"排队等待超过 {self._queue_wait_timeout_seconds}s，已取消"
                        )
                    self._cv.wait(timeout=remaining)
                else:
                    self._cv.wait()

    def get_status(self, caller: str | None = None) -> dict:
        """返回当前执行状态。

        running=True 时 current_template/caller 给出正在跑的模板/发起方（队头）；
        overdue 表示队头任务已越过执行超时阈值仍在物理运行；
        queue_length 是队列总长度（含正在执行的一项）；
        queue_position 传入 caller 时给出其排队位置（1 表示正在执行或即将执行）。
        """
        with self._cv:
            head = self._queue[0] if self._queue else None
            running = head is not None and head.running
            queue_position = None
            if caller is not None:
                for i, e in enumerate(self._queue):
                    if e.caller == caller:
                        queue_position = i + 1
                        break
            return {
                "running": running,
                "current_template": head.template if running else None,
                "caller": head.caller if running else None,
                "overdue": bool(head.overdue) if running else False,
                "queue_length": len(self._queue),
                "queue_position": queue_position,
                "last_template": (self._last_report or {}).get("template_info", {}).get("name"),
            }

    def stop_execution(self, caller: str | None = None) -> dict:
        """请求停止 caller 对应的任务。

        - 排队中（未开始执行）：直接摘除，真取消。
        - 执行中且是本人：发送取消信号（下一个安全检查点生效，不会立即打断当前动作）。
        - 执行中但不是本人：越权拒绝，说明当前运行方。
        - 没有任何排队/执行中的任务：如实说明。
        """
        with self._cv:
            my_entry = None
            my_index = None
            if caller is not None:
                for i, e in enumerate(self._queue):
                    if e.caller == caller:
                        my_entry = e
                        my_index = i
                        break

            if my_entry is not None and not my_entry.running:
                del self._queue[my_index]
                my_entry.cancel_event.set()
                self._cv.notify_all()
                logger.info("stop_execution：取消排队中的任务，caller=%s", caller)
                return {"stopped": True, "reason": "已取消排队中的任务，未开始执行"}

            if my_entry is not None and my_entry.running:
                my_entry.cancel_event.set()
                logger.info("stop_execution：已发送取消信号，caller=%s", caller)
                return {
                    "stopped": True,
                    "reason": "已发送取消信号，任务将在下一个安全检查点停止（不会立即打断当前动作）",
                }

            owner = self._queue[0].caller if (self._queue and self._queue[0].running) else None
            if owner is not None:
                logger.warning("stop_execution 越权：caller=%s，当前 owner=%s", caller, owner)
                return {
                    "stopped": False,
                    "reason": f"无权停止：当前运行方是 {owner}，且您没有排队或执行中的任务",
                }

            return {"stopped": False, "reason": "当前没有正在执行或排队中的任务"}

    def get_report(self) -> dict:
        """返回最近一次执行的完整报告（无则空 dict）。"""
        return self._last_report or {}
