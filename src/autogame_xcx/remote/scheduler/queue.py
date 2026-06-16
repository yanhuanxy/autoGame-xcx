"""单线程消费的指令队列。

设计要点：
1. 同一时刻只消费一个指令（避免窗口冲突）
2. consumer 由调用方注入（router 注入"dispatcher.dispatch + send_text"组合）
3. cancel_pending 支持"按 user_id 取消队列中尚未开始的指令"
   ——不能中断正在执行的指令（execute_template 不检查停止信号），
     但至少让排队中的 #run 不会全部跑掉
4. worker 是 daemon 线程，主进程退出时自动结束
5. enqueue 后立即返回，不阻塞调用线程（router 在主线程被调用）

线程模型：
    JVM 线程 → listener.emit → 主线程 router.route → enqueue（不阻塞）
                                                       ↓
                                          worker 线程 ← (单线程消费)
                                                       ↓
                                              consumer(user_id, parsed)
                                                       ↓
                                          executor.execute_template(...)  ← 长任务
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from collections.abc import Callable

logger = logging.getLogger(__name__)


class CommandQueue:
    """单线程消费的指令队列。

    用法：
        queue = CommandQueue(consumer=my_consumer)
        queue.start()                          # 启动 worker
        queue.enqueue(user_id, parsed_cmd)     # 非阻塞入队
        ...
        queue.stop()                           # 优雅停止

    consumer 签名：consumer(user_id: str, parsed: ParsedCommand) -> None
    """

    def __init__(self, consumer: Callable[[str, object], None]) -> None:
        self._consumer = consumer
        self._q: deque[tuple[str, object]] = deque()
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._running = False              # worker 是否在跑
        self._current: tuple[str, object] | None = None  # (user_id, parsed) of currently executing
        self._worker: threading.Thread | None = None
        self._processed = 0                # 已完成总数（统计用）

    def start(self) -> None:
        """启动 worker 线程（重复调用幂等）。"""
        with self._cv:
            if self._worker is not None and self._worker.is_alive():
                return
            self._running = True
            self._worker = threading.Thread(
                target=self._loop,
                name="ilink-cmd-queue",
                daemon=True,
            )
            self._worker.start()
            logger.info("CommandQueue worker started")

    def enqueue(self, user_id: str, parsed: object) -> int:
        """入队，返回当前队列长度（不含正在执行的）。

        Raises:
            RuntimeError: worker 未启动（避免指令永远不被消费）。
        """
        if not self._running:
            raise RuntimeError("CommandQueue 未启动；先调用 start()")

        with self._cv:
            self._q.append((user_id, parsed))
            length = len(self._q)
            self._cv.notify()
        logger.info("Enqueued from user=%s, queue_length=%d", user_id, length)
        return length

    def cancel_pending(self, user_id: str | None = None) -> int:
        """取消队列中尚未开始的指令。

        Args:
            user_id: 仅取消该用户的；None 取消所有。

        Returns:
            被取消的数量。

        注意：不能中断正在执行的指令（current_running 不变）。
        """
        with self._cv:
            if user_id is None:
                n = len(self._q)
                self._q.clear()
            else:
                keep = [(u, p) for u, p in self._q if u != user_id]
                n = len(self._q) - len(keep)
                self._q.clear()
                self._q.extend(keep)
        if n > 0:
            logger.info("Cancelled %d pending commands (user_filter=%s)", n, user_id)
        return n

    def stop(self) -> None:
        """优雅停止 worker（等待当前指令完成）。"""
        with self._cv:
            self._running = False
            self._cv.notify_all()
        if self._worker is not None and self._worker.is_alive():
            # 不强行 join（consumer 可能长任务），让 daemon 线程随主进程退出
            self._worker = None
        logger.info("CommandQueue stopped")

    @property
    def queue_length(self) -> int:
        """队列中等待的指令数（不含正在执行的）。"""
        with self._lock:
            return len(self._q)

    @property
    def current_running(self) -> tuple[str, object] | None:
        """正在执行的 (user_id, parsed)；空闲时为 None。"""
        # 不需要锁：Python 的引用读写是原子的，且只有 worker 会写
        return self._current

    @property
    def is_running(self) -> bool:
        """worker 是否在运行。"""
        return self._running

    @property
    def processed_count(self) -> int:
        """累计已完成的指令数（含失败）。"""
        return self._processed

    def _loop(self) -> None:
        """worker 主循环。"""
        logger.info("CommandQueue worker loop started")
        while self._running:
            with self._cv:
                while self._running and not self._q:
                    self._cv.wait()
                if not self._running:
                    break
                self._current = self._q.popleft()
            user_id, parsed = self._current
            try:
                self._consumer(user_id, parsed)
            except Exception:
                logger.exception("Consumer crashed on parsed=%s", parsed)
            finally:
                self._current = None
                with self._lock:
                    self._processed += 1
        logger.info("CommandQueue worker loop exited")
