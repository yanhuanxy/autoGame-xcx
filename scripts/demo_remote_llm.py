"""阶段 2.5 验证脚本：LLM 编排完整链路（用 MockLlmProvider，不调真实 API）。

验证目标（PLAN_02 §6 阶段 2.5）：
  1. 自然语言 → orchestrator → MockLlmProvider 返回 JSON
  2. JSON 解析 + 白名单校验 → 入队
  3. 用户收到"已为您规划 N 个指令"回执
  4. action 不在白名单时拒绝（安全防线）
  5. JSON 格式异常时拒绝
  6. router 集成：非 # 消息转给 orchestrator
  7. router # 消息仍走指令系统，不打扰 LLM

不调 anthropic / openai 真实 API——单元测试 + 演示用 Mock 即可，
真实 LLM 链路由用户配置 API key 后手动验证。

运行：
    uv run python scripts/demo_remote_llm.py
"""
from __future__ import annotations

from autogame_xcx.remote.commands import (
    CommandDispatcher,
    CommandParser,
    build_default_registry,
)
from autogame_xcx.remote.llm import LLMOrchestrator, MockLlmProvider
from autogame_xcx.remote.router import MessageRouter
from autogame_xcx.remote.scheduler.queue import CommandQueue
from autogame_xcx.remote.session import SessionManager

CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(cond), detail))
    mark = "OK " if cond else "FAIL"
    line = f"  [{mark}] {name}"
    if detail:
        line += f" — {detail}"
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", errors="replace").decode("ascii"))


def step(msg: str) -> None:
    print(f"\n>>> {msg}")


# -------------------- 共享 mock 工具（与 demo_remote_scheduler 同风格）--------------------


class MockSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_text(self, user_id: str, text: str) -> None:
        self.sent.append((user_id, text))

    def last_text(self) -> str | None:
        return self.sent[-1][1] if self.sent else None


class MockScheduler:
    """不异步消费，只记录入队请求。"""

    def __init__(self) -> None:
        self.enqueued: list[tuple[str, object]] = []

    def enqueue(self, user_id: str, parsed: object) -> int:
        self.enqueued.append((user_id, parsed))
        return len(self.enqueued)


# -------------------- 场景 1：自然语言 → 两个 #run 指令 --------------------


def scenario_happy_path() -> None:
    step("场景 1：'帮我把签到和领体力都做了' → 2 个 #run 入队")
    response = (
        '[{"action": "run", "args": "签到"}, {"action": "run", "args": "领体力"}]'
    )
    provider = MockLlmProvider(responses=[response])
    sender = MockSender()
    sched = MockScheduler()
    registry = build_default_registry()
    orch = LLMOrchestrator(
        provider=provider, registry=registry, scheduler=sched, sender=sender
    )

    result = orch.handle_natural_language("wxid_alice", "帮我把签到和领体力都做了")

    check("orchestrator 报告 success", result.success)
    check("解析出 2 条指令", len(result.commands) == 2, f"actual={len(result.commands)}")
    check("首条指令名是 RUN_TEMPLATE", result.commands[0].name == "RUN_TEMPLATE")
    check(
        "首条 args=签到",
        result.commands[0].args == "签到",
        f"actual={result.commands[0].args!r}",
    )
    check("2 条都入队", len(sched.enqueued) == 2)
    check(
        "回执含'已为您规划 2 个指令'",
        "已为您规划 2 个指令" in (sender.last_text() or ""),
    )
    check(
        "prompt 含 system + user",
        len(provider.calls) == 1 and provider.calls[0][0]["role"] == "system",
    )


# -------------------- 场景 2：LLM 越权指令 → 拒绝 --------------------


def scenario_unknown_action_rejected() -> None:
    step("场景 2：LLM 输出 #delete_database → 拒绝、不入队")
    response = '[{"action": "delete_database", "args": "all"}]'
    provider = MockLlmProvider(responses=[response])
    sender = MockSender()
    sched = MockScheduler()
    orch = LLMOrchestrator(
        provider=provider,
        registry=build_default_registry(),
        scheduler=sched,
        sender=sender,
    )

    result = orch.handle_natural_language("wxid_alice", "清空所有数据")

    check("orchestrator 报告 failure", not result.success)
    check("没有任何指令入队", len(sched.enqueued) == 0)
    reply = sender.last_text() or ""
    check("回执含'白名单'或动作名", ("白名单" in reply) or ("delete_database" in reply))


# -------------------- 场景 3：LLM 输出乱码 → 拒绝 --------------------


def scenario_malformed_json_rejected() -> None:
    step("场景 3：LLM 输出非 JSON → 拒绝")
    provider = MockLlmProvider(responses=["对不起，我无法处理这个请求。"])
    sender = MockSender()
    sched = MockScheduler()
    orch = LLMOrchestrator(
        provider=provider,
        registry=build_default_registry(),
        scheduler=sched,
        sender=sender,
    )

    result = orch.handle_natural_language("wxid_alice", "随便说说")

    check("orchestrator 报告 failure", not result.success)
    check("没有任何指令入队", len(sched.enqueued) == 0)
    check("回执含'格式异常'", "格式异常" in (sender.last_text() or ""))


# -------------------- 场景 4：Markdown 围栏容错 --------------------


def scenario_markdown_fence_tolerated() -> None:
    step("场景 4：LLM 输出包了 ```json 围栏 → 仍能解析")
    response = '```json\n[{"action": "status", "args": ""}]\n```'
    provider = MockLlmProvider(responses=[response])
    sender = MockSender()
    sched = MockScheduler()
    orch = LLMOrchestrator(
        provider=provider,
        registry=build_default_registry(),
        scheduler=sched,
        sender=sender,
    )

    result = orch.handle_natural_language("wxid_alice", "现在情况怎么样")

    check("orchestrator 报告 success", result.success)
    check("解析出 1 条指令", len(result.commands) == 1)
    check("指令名是 STATUS", result.commands[0].name == "STATUS")


# -------------------- 场景 5：router 集成 --------------------


def scenario_router_integration() -> None:
    step("场景 5：非 # 消息经 router → orchestrator；# 消息不打扰 LLM")
    response = '[{"action": "list", "args": ""}]'
    provider = MockLlmProvider(responses=[response])
    sender = MockSender()

    # 用真实 CommandQueue 但不 start（不消费，仅验证入队）
    sched = CommandQueue(consumer=lambda *_: None)
    sched.start()
    try:
        registry = build_default_registry()
        orch = LLMOrchestrator(
            provider=provider,
            registry=registry,
            scheduler=sched,
            sender=sender,
        )
        parser = CommandParser(registry)
        dispatcher = CommandDispatcher(registry)
        session = SessionManager(allowed={"wxid_alice"})
        router = MessageRouter(
            parser=parser,
            dispatcher=dispatcher,
            session=session,
            executor=None,  # 本次路由不走 #run
            template_manager=None,
            sender=sender,
            scheduler=None,  # router 同步路径（#list 用同步）
            llm_orchestrator=orch,
        )

        # 非 # 消息 → orchestrator
        sender.sent.clear()
        router.route("wxid_alice", "列出所有模板")
        check(
            "orchestrator 被调用 1 次",
            len(provider.calls) == 1,
            f"actual={len(provider.calls)}",
        )
        check(
            "回执含'已规划'",
            "已为您规划" in (sender.last_text() or ""),
        )

        # # 消息不打扰 LLM
        calls_before = len(provider.calls)
        sender.sent.clear()
        router.route("wxid_alice", "#help")
        check(
            "LLM 调用次数未增加",
            len(provider.calls) == calls_before,
            f"actual={len(provider.calls)}",
        )
        check(
            "#help 走指令系统",
            "可用指令" in (sender.last_text() or ""),
        )

        # 非白名单用户被忽略
        sender.sent.clear()
        provider.calls.clear()
        router.route("wxid_stranger", "列出所有模板")
        check(
            "非白名单用户消息被忽略",
            len(provider.calls) == 0 and len(sender.sent) == 0,
        )
    finally:
        sched.stop()


# -------------------- 场景 6：provider 异常隔离 --------------------


def scenario_provider_exception_isolated() -> None:
    step("场景 6：provider.chat 抛异常 → 回执 'AI 调用失败'")
    provider = MockLlmProvider(responses=[])

    def _boom(_messages: list[dict]) -> str:
        raise RuntimeError("network down")

    provider.chat = _boom  # type: ignore[method-assign]
    sender = MockSender()
    sched = MockScheduler()
    orch = LLMOrchestrator(
        provider=provider,
        registry=build_default_registry(),
        scheduler=sched,
        sender=sender,
    )

    result = orch.handle_natural_language("wxid_alice", "做签到")

    check("orchestrator 报告 failure", not result.success)
    check("没有任何指令入队", len(sched.enqueued) == 0)
    check("回执含 'AI 调用失败'", "AI 调用失败" in (sender.last_text() or ""))


# -------------------- 主入口 --------------------


def main() -> int:
    print("=" * 60)
    print("阶段 2.5 LLM 编排验证（MockLlmProvider）")
    print("=" * 60)

    scenario_happy_path()
    scenario_unknown_action_rejected()
    scenario_malformed_json_rejected()
    scenario_markdown_fence_tolerated()
    scenario_router_integration()
    scenario_provider_exception_isolated()

    total = len(CHECKS)
    passed = sum(1 for _, ok, _ in CHECKS if ok)
    print("\n" + "=" * 60)
    print(f"Result: {passed}/{total} checks passed")
    if passed != total:
        print("FAILURES:")
        for name, ok, detail in CHECKS:
            if not ok:
                print(f"  - {name} — {detail}")
        return 1

    try:
        print("\n[OK] stage 2.5 verification passed")
    except UnicodeEncodeError:
        print("\n[OK] stage 2.5 verification passed".encode("ascii", "replace").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
