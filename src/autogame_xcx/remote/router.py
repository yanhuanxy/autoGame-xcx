"""消息路由：白名单 → #指令 or 自然语言分发。

阶段 2.3 仅处理 # 指令；自然语言分支预留 LLM orchestrator hook（阶段 2.5）。

线程模型：
- PythonMessageListener.onMessages 在 JVM 线程被调用，emit 到主线程后
  router.route() 在主线程被调用（通过 Qt 信号槽）
- dispatcher.dispatch 是同步的；对于 #run 这种长任务（execute_template 几分钟），
  实际使用时应该交给阶段 2.4 的 scheduler 异步执行
"""
from __future__ import annotations

import logging

from autogame_xcx.remote.commands.base import CommandContext
from autogame_xcx.remote.commands.dispatcher import CommandDispatcher
from autogame_xcx.remote.commands.parser import CommandParser
from autogame_xcx.remote.session import SessionManager

logger = logging.getLogger(__name__)


class MessageRouter:
    """消息路由。

    route() 接收 (user_id, text)，根据内容：
    - 非白名单用户 → 忽略
    - 非 # 开头 → LLM 编排（阶段 2.5 才有，当前忽略并提示）
    - # 指令 → parser + dispatcher 执行

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
        llm_orchestrator=None,
    ) -> None:
        self.parser = parser
        self.dispatcher = dispatcher
        self.session = session
        self.executor = executor
        self.template_manager = template_manager
        self.sender = sender
        self.llm_orchestrator = llm_orchestrator

    def route(self, user_id: str, text: str) -> None:
        """处理一条消息。"""
        text = (text or "").strip()
        if not text:
            return

        if not self.session.is_allowed(user_id):
            logger.info("Ignored message from non-whitelisted user: %s", user_id)
            return

        # 阶段 2.3：仅处理 # 指令
        if not self.parser.is_command(text):
            self._handle_natural_language(user_id, text)
            return

        parsed = self.parser.parse(text)
        if parsed is None:
            # 以 # 开头但 body 为空（如 "# "），忽略
            return

        ctx = CommandContext(
            user_id=user_id,
            raw_text=text,
            executor=self.executor,
            template_manager=self.template_manager,
            sender=self.sender,
            state={},
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
            # 当前阶段：不响应（避免给用户错觉），仅记日志
            logger.info("Non-command message from %s ignored (LLM not configured)", user_id)
            return
        # 阶段 2.5 后：self.llm_orchestrator.handle_natural_language(user_id, text)
        self.llm_orchestrator.handle_natural_language(user_id, text)
