"""阶段 2.3 / 2.5 共享 pytest fixtures。

MockSender / MockTemplateManager / MockExecutor 模拟 core API，
让指令测试不依赖 ilink SDK 或真实窗口。
"""
from __future__ import annotations

from collections.abc import Callable

import pytest

from autogame_xcx.remote.commands import (
    CommandDispatcher,
    CommandParser,
    build_default_registry,
)
from autogame_xcx.remote.llm import LLMOrchestrator, MockLlmProvider
from autogame_xcx.remote.router import MessageRouter
from autogame_xcx.remote.session import SessionManager


class MockSender:
    """收集 send_text 调用，便于断言。"""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_text(self, user_id: str, text: str) -> None:
        self.sent.append((user_id, text))

    def last_text(self) -> str | None:
        return self.sent[-1][1] if self.sent else None

    def messages_for(self, user_id: str) -> list[str]:
        return [t for u, t in self.sent if u == user_id]

    def clear(self) -> None:
        self.sent.clear()


class MockTemplateManager:
    """模拟 list_templates 返回值。"""

    def __init__(self, templates: list[dict] | None = None) -> None:
        self._templates = templates or []

    def list_templates(self) -> list[dict]:
        return list(self._templates)


class MockExecutor:
    """模拟 GameExecutor 的最小行为。"""

    def __init__(
        self,
        *,
        succeed: bool = True,
        report: dict | None = None,
    ) -> None:
        self.succeed = succeed
        self.execution_report = report or {}
        self.current_template = None
        self.calls: list[str] = []

    def execute_template(self, filepath: str) -> bool:
        self.calls.append(filepath)
        self.current_template = {"template_info": {"name": "from_exec"}}
        self.execution_report = {
            "start_time": "2026-06-15 10:00:00",
            "end_time": "2026-06-15 10:01:30",
            "template_path": filepath,
            "tasks": [
                {"task_name": "签到", "status": "completed", "retry_count": 0},
                {"task_name": "领体力", "status": "completed", "retry_count": 0},
            ],
            "summary": {
                "total_tasks": 2,
                "completed": 2,
                "failed": 0,
                "success_rate": "100.0%",
            },
        }
        return self.succeed


@pytest.fixture
def make_router() -> Callable[..., tuple[MessageRouter, MockSender, MockExecutor]]:
    """工厂：按需构造 (router, sender, executor) 三元组。

    用法：
        def test_xxx(make_router):
            router, sender, executor = make_router(templates=[...])
    """

    def _factory(
        *,
        templates: list[dict] | None = None,
        executor_succeed: bool = True,
        allowed: set[str] | None = None,
        scheduler=None,
        llm_orchestrator=None,
    ) -> tuple[MessageRouter, MockSender, MockExecutor]:
        sender = MockSender()
        executor = MockExecutor(succeed=executor_succeed)
        tm = MockTemplateManager(templates)
        registry = build_default_registry()
        parser = CommandParser(registry)
        dispatcher = CommandDispatcher(registry)
        session = SessionManager(allowed=allowed or {"wxid_alice"})
        router = MessageRouter(
            parser=parser,
            dispatcher=dispatcher,
            session=session,
            executor=executor,
            template_manager=tm,
            sender=sender,
            scheduler=scheduler,
            llm_orchestrator=llm_orchestrator,
        )
        return router, sender, executor

    return _factory


class MockScheduler:
    """轻量调度器桩：不消费队列，只记录 enqueue 调用便于断言。

    真实的 CommandQueue 会异步消费，编排器单元测试不需要异步行为，
    用这个桩更易断言"被入队了 N 次 / 第 i 次入队是什么指令"。
    """

    def __init__(self) -> None:
        self.enqueued: list[tuple[str, object]] = []

    def enqueue(self, user_id: str, parsed: object) -> int:
        self.enqueued.append((user_id, parsed))
        return len(self.enqueued)


@pytest.fixture
def make_orchestrator() -> Callable[..., tuple[LLMOrchestrator, MockLlmProvider, MockSender, MockScheduler]]:
    """工厂：构造 (orchestrator, mock_provider, sender, mock_scheduler)。

    用法：
        def test_xxx(make_orchestrator):
            orch, provider, sender, sched = make_orchestrator(
                responses=['[{"action":"run","args":"签到"}]'],
            )
            orch.handle_natural_language("wxid_alice", "帮我把签到做了")
            assert len(sched.enqueued) == 1
    """

    def _factory(
        *,
        responses: list[str] | None = None,
        sender: MockSender | None = None,
    ) -> tuple[LLMOrchestrator, MockLlmProvider, MockSender, MockScheduler]:
        provider = MockLlmProvider(responses=responses)
        if sender is None:
            sender = MockSender()
        scheduler = MockScheduler()
        registry = build_default_registry()
        orchestrator = LLMOrchestrator(
            provider=provider,
            registry=registry,
            scheduler=scheduler,
            sender=sender,
        )
        return orchestrator, provider, sender, scheduler

    return _factory
