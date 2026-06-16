"""消息路由：白名单 → #指令 or 自然语言分发。

阶段 2.3：仅处理 # 指令，同步 dispatch。
阶段 2.4：可选接入 scheduler，# 指令入队由 worker 线程串行消费。
         未接入 scheduler 时保持 2.3 的同步行为（向后兼容）。
阶段 2.5：非 # 消息走 LLM orchestrator（hook 已预留）。

线程模型：
- PythonMessageListener.onMessages 在 JVM 线程被调用，emit 到主线程后
  router.route() 在主线程被调用（通过 Qt 信号槽）
- 接入 scheduler 后：route() 入队即返回（不阻塞主线程），
  worker 线程顺序消费（保证同一时刻只有一个 execute_template 在跑）
"""
from __future__ import annotations

import logging

from autogame_xcx.remote.commands.base import CommandContext
from autogame_xcx.remote.commands.dispatcher import CommandDispatcher
from autogame_xcx.remote.commands.parser import CommandParser
from autogame_xcx.remote.scheduler.queue import CommandQueue
from autogame_xcx.remote.session import SessionManager

logger = logging.getLogger(__name__)


class MessageRouter:
    """消息路由。

    route() 接收 (user_id, text)，根据内容：
    - 非白名单用户 → 忽略
    - 非 # 开头 → LLM 编排（阶段 2.5 才有，当前忽略并提示）
    - # 指令 → parser + dispatcher 执行（经 scheduler 异步 或 直接同步）

    回执通过 sender.send_text 发回用户。
    """

    def __init__(
        self,
        parser: CommandParser,
        dispatcher: CommandDispatcher,
        session: SessionManager,
        executor,
        template_manager,
        sender,
        scheduler: CommandQueue | None = None,
        llm_orchestrator=None,
    ) -> None:
        self.parser = parser
        self.dispatcher = dispatcher
        self.session = session
        self.executor = executor
        self.template_manager = template_manager
        self.sender = sender
        self.scheduler = scheduler
        self.llm_orchestrator = llm_orchestrator

        # 接入 scheduler 时，注入 consumer（dispatcher.dispatch + send_text 组合）
        if scheduler is not None:
            scheduler._consumer = self._dispatch_and_reply  # type: ignore[attr-defined]

    def route(self, user_id: str, text: str) -> None:
        """处理一条消息。"""
        text = (text or "").strip()
        if not text:
            return

        if not self.session.is_allowed(user_id):
            logger.info("Ignored message from non-whitelisted user: %s", user_id)
            return

        if not self.parser.is_command(text):
            self._handle_natural_language(user_id, text)
            return

        parsed = self.parser.parse(text)
        if parsed is None:
            # 以 # 开头但 body 为空（如 "# "），忽略
            return

        if self.scheduler is not None:
            # 阶段 2.4：默认入队；但控制类指令（#status/#stop/#help/#list/#report）
            # 通过 queued_dispatch=False 标记为"立即同步 dispatch"，避免被 #run 阻塞
            command = self.parser.registry.find(parsed.name)
            if command is not None and command.queued_dispatch:
                self.scheduler.enqueue(user_id, parsed)
                return
            # 控制类指令：直接 dispatch（读状态/取消队列，本身就是线程安全且瞬时）
            self._dispatch_and_reply(user_id, parsed)
            return

        # 阶段 2.3：同步执行（向后兼容，便于单元测试）
        self._dispatch_and_reply(user_id, parsed)

    def _dispatch_and_reply(self, user_id: str, parsed) -> None:
        """构造 context + dispatch + 回执。

        被两个路径调用：
        - 同步路径：route() 直接调用
        - 异步路径：scheduler worker 线程调用
        """
        # 把 scheduler 注入到 ctx.state，让 #status / #stop 能访问
        state = {"scheduler": self.scheduler} if self.scheduler is not None else {}

        ctx = CommandContext(
            user_id=user_id,
            raw_text=parsed.raw,
            executor=self.executor,
            template_manager=self.template_manager,
            sender=self.sender,
            state=state,
        )
        result = self.dispatcher.dispatch(ctx, parsed)

        # 始终回执（即使是失败结果，让用户知道指令被处理了）
        try:
            self.sender.send_text(user_id, result.message)
        except Exception as e:
            logger.exception("Failed to send reply to %s: %s", user_id, e)

    def _handle_natural_language(self, user_id: str, text: str) -> None:
        """非 # 消息的处理（阶段 2.5 LLM 接入后实现）。"""
        if self.llm_orchestrator is None:
            logger.info("Non-command message from %s ignored (LLM not configured)", user_id)
            return
        self.llm_orchestrator.handle_natural_language(user_id, text)
