"""阶段 2.4 验证脚本：指令调度器完整链路。

验证目标（PLAN_02 §6 阶段 2.4）：
  1. 接入 scheduler 后，连续 N 个 #run 顺序执行（同一时刻只有一个）
  2. #status 返回"正在执行 + 队列等待 + 累计完成"
  3. #stop 取消队列中尚未开始的指令（按 user_id）
  4. router.route() 入队即返回（不阻塞主线程）
  5. consumer 异常被吞掉（worker 不挂）

不调 ilink SDK，用 mock executor 模拟"长任务"（sleep）以验证并发与串行。

运行：
    uv run python scripts/demo_remote_scheduler.py
"""
from __future__ import annotations

import threading
import time

from autogame_xcx.remote.commands import (
    CommandDispatcher,
    CommandParser,
    build_default_registry,
)
from autogame_xcx.remote.router import MessageRouter
from autogame_xcx.remote.scheduler import CommandQueue
from autogame_xcx.remote.session import SessionManager

CHECKS = []


def check(name: str, cond: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(cond), detail))
    mark = "OK " if cond else "FAIL"
    line = f"  [{mark}] {name}"
    if detail:
        line += f" — {detail}"
    # Windows GBK 终端无法编码 ▶/✓ 等 Unicode 符号，安全降级为 ASCII
    try:
        print(line)
    except UnicodeEncodeError:
        safe = line.encode("ascii", errors="replace").decode("ascii")
        print(safe)


def step(msg: str) -> None:
    print(f"\n>>> {msg}")


# -------------------- 测试 fixtures --------------------

class MockSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []
        self._lock = threading.Lock()

    def send_text(self, user_id: str, text: str) -> None:
        with self._lock:
            self.sent.append((user_id, text))

    def messages_for(self, user_id: str) -> list[str]:
        with self._lock:
            return [t for u, t in self.sent if u == user_id]

    def clear(self) -> None:
        with self._lock:
            self.sent.clear()


class MockTemplateManager:
    def __init__(self, templates: list[dict]) -> None:
        self._templates = templates

    def list_templates(self) -> list[dict]:
        return list(self._templates)


class SlowExecutor:
    """模拟 execute_template 阻塞 delay 秒，记录调用顺序。

    用 start/end 时间戳验证"串行执行"：连续两个任务的 [end_i, start_{i+1}]
    不应重叠（start_{i+1} >= end_i）。
    """

    def __init__(self, delay: float = 0.3, succeed: bool = True) -> None:
        self.delay = delay
        self.succeed = succeed
        self.execution_report: dict = {}
        self.current_template = None
        self.call_log: list[dict] = []  # {filepath, start, end}
        self._lock = threading.Lock()

    def execute_template(self, filepath: str) -> bool:
        start = time.monotonic()
        # 模拟长任务（实际 execute_template 内部会操作窗口）
        time.sleep(self.delay)
        end = time.monotonic()
        with self._lock:
            self.call_log.append({"filepath": filepath, "start": start, "end": end})
            self.current_template = {"template_info": {"name": filepath}}
            self.execution_report = {
                "start_time": "2026-06-15 10:00:00",
                "end_time": "2026-06-15 10:00:01",
                "template_path": filepath,
                "tasks": [],
                "summary": {"total_tasks": 1, "completed": 1, "failed": 0, "success_rate": "100.0%"},
            }
        return self.succeed


def make_router(
    *,
    templates: list[dict] | None = None,
    delay: float = 0.3,
    allowed: set[str] | None = None,
    with_scheduler: bool = True,
) -> tuple[MessageRouter, MockSender, SlowExecutor, CommandQueue | None]:
    sender = MockSender()
    executor = SlowExecutor(delay=delay)
    tm = MockTemplateManager(templates or [])
    registry = build_default_registry()
    parser = CommandParser(registry)
    dispatcher = CommandDispatcher(registry)
    session = SessionManager(allowed=allowed or {"wxid_alice"})

    scheduler: CommandQueue | None = None
    if with_scheduler:
        scheduler = CommandQueue(consumer=lambda *_: None)  # router 会重写 consumer
        scheduler.start()

    router = MessageRouter(
        parser=parser, dispatcher=dispatcher, session=session,
        executor=executor, template_manager=tm, sender=sender,
        scheduler=scheduler,
    )
    return router, sender, executor, scheduler


def wait_for_processed(scheduler: CommandQueue, target: int, timeout: float = 10.0) -> bool:
    """等待 scheduler 累计处理数达到 target，超时返回 False。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if scheduler.processed_count >= target:
            return True
        time.sleep(0.02)
    return False


# -------------------- 测试用例 --------------------

def test_scheduler_starts_and_consumes() -> None:
    step("scheduler 启动并消费单条指令")
    router, sender, executor, scheduler = make_router(
        templates=[{"name": "签到", "filepath": "/a.json", "game_name": ""}],
    )
    assert scheduler is not None

    check("scheduler 启动后 is_running=True", scheduler.is_running is True)
    check("初始 queue_length=0", scheduler.queue_length == 0)
    check("初始 current_running=None", scheduler.current_running is None)
    check("初始 processed_count=0", scheduler.processed_count == 0)

    router.route("wxid_alice", "#run 签到")
    ok = wait_for_processed(scheduler, target=1)
    check("1 个指令被消费", ok and scheduler.processed_count == 1)
    check("executor 被 call 1 次", len(executor.call_log) == 1)
    check("用户收到 ≥2 条消息", len(sender.messages_for("wxid_alice")) >= 2)

    scheduler.stop()


def test_three_runs_are_serial() -> None:
    step("连续 3 个 #run 顺序执行（不并发）")
    templates = [
        {"name": "t1", "filepath": "/1.json", "game_name": ""},
        {"name": "t2", "filepath": "/2.json", "game_name": ""},
        {"name": "t3", "filepath": "/3.json", "game_name": ""},
    ]
    router, sender, executor, scheduler = make_router(templates=templates, delay=0.2)
    assert scheduler is not None

    # 连续入队 3 个
    router.route("wxid_alice", "#run t1")
    router.route("wxid_alice", "#run t2")
    router.route("wxid_alice", "#run t3")

    # 等所有完成
    ok = wait_for_processed(scheduler, target=3, timeout=10)
    check("3 个指令全部完成", ok and scheduler.processed_count == 3)
    check("executor 被 call 3 次", len(executor.call_log) == 3)

    # 关键：验证串行（start_{i+1} >= end_i）
    calls = executor.call_log
    serial = True
    for i in range(len(calls) - 1):
        if calls[i + 1]["start"] < calls[i]["end"]:
            serial = False
            break
    check("3 个任务串行（无时间重叠）", serial,
          detail=f"calls={[{k: round(v, 3) if isinstance(v, float) else v for k, v in c.items()} for c in calls]}")

    # 每个都收到了开始+完成消息（≥6 条）
    alice_msgs = sender.messages_for("wxid_alice")
    check("alice 收到 ≥6 条消息（3 个 × 2）", len(alice_msgs) >= 6)

    scheduler.stop()


def test_status_during_execution() -> None:
    step("#status 反映队列状态")
    templates = [
        {"name": "t1", "filepath": "/1.json", "game_name": ""},
        {"name": "t2", "filepath": "/2.json", "game_name": ""},
        {"name": "t3", "filepath": "/3.json", "game_name": ""},
    ]
    router, sender, executor, scheduler = make_router(templates=templates, delay=0.5)
    assert scheduler is not None

    # 用另一个用户的 #status 查询（避免 alice 自己排队影响）
    router.session.add_user("wxid_bob")

    # 入队 3 个 alice 的指令
    router.route("wxid_alice", "#run t1")
    router.route("wxid_alice", "#run t2")
    router.route("wxid_alice", "#run t3")

    # 立即查询 status（此时第一个可能在执行，2 个在队列）
    # 给 worker 一点时间 pop 第一个
    time.sleep(0.1)
    router.route("wxid_bob", "#status")

    bob_msgs = sender.messages_for("wxid_bob")
    check("#status 有回复", len(bob_msgs) >= 1)
    if bob_msgs:
        reply = bob_msgs[-1]
        check("#status 含'当前状态'", "当前状态" in reply)
        # 队列等待或正在执行至少出现一个
        has_activity = "正在执行" in reply or "队列等待" in reply or "累计完成" in reply
        check("#status 含调度信息", has_activity, detail=reply[:200])

    # 等所有完成
    wait_for_processed(scheduler, target=3, timeout=10)
    scheduler.stop()


def test_stop_cancels_pending() -> None:
    step("#stop 取消队列中尚未开始的指令")
    templates = [
        {"name": "t1", "filepath": "/1.json", "game_name": ""},
        {"name": "t2", "filepath": "/2.json", "game_name": ""},
        {"name": "t3", "filepath": "/3.json", "game_name": ""},
        {"name": "t4", "filepath": "/4.json", "game_name": ""},
    ]
    router, sender, executor, scheduler = make_router(templates=templates, delay=0.5)
    assert scheduler is not None

    # 入队 4 个，等 0.1s 让第一个开始执行
    router.route("wxid_alice", "#run t1")
    router.route("wxid_alice", "#run t2")
    router.route("wxid_alice", "#run t3")
    router.route("wxid_alice", "#run t4")
    time.sleep(0.1)

    # 调用 #stop
    sender.clear()
    router.route("wxid_alice", "#stop")
    time.sleep(0.1)
    stop_reply = sender.messages_for("wxid_alice")
    check("#stop 有回复", len(stop_reply) >= 1)
    if stop_reply:
        check("#stop 提示已取消", "取消" in stop_reply[-1], detail=stop_reply[-1][:200])

    # 等执行中的任务完成
    wait_for_processed(scheduler, target=2, timeout=10)  # t1 + stop 本身（不计入）
    # 等再多一点，看 t3/t4 是否真的被取消
    time.sleep(0.5)
    final_processed = scheduler.processed_count

    # 至少 t1 完成（+ t2 可能也，但 t3/t4 必须被取消）
    check("至少 1 个指令被执行（t1）", len(executor.call_log) >= 1)
    check("被取消的 t3/t4 没有执行", len(executor.call_log) <= 2,
          detail=f"实际执行 {len(executor.call_log)} 个")

    scheduler.stop()


def test_stop_no_pending() -> None:
    step("#stop 在无任务时合理回复")
    router, sender, _, scheduler = make_router()
    assert scheduler is not None

    router.route("wxid_alice", "#stop")
    reply = sender.messages_for("wxid_alice")
    check("#stop 空闲时回复", len(reply) >= 1 and ("无任务" in reply[-1] or "可取消" in reply[-1]))
    scheduler.stop()


def test_stop_only_affects_self() -> None:
    step("#stop 仅取消自己的指令（不影响其他用户队列）")
    templates = [
        {"name": "t1", "filepath": "/1.json", "game_name": ""},
        {"name": "t2", "filepath": "/2.json", "game_name": ""},
        {"name": "t3", "filepath": "/3.json", "game_name": ""},
        {"name": "t4", "filepath": "/4.json", "game_name": ""},
    ]
    router, sender, executor, scheduler = make_router(templates=templates, delay=0.4)
    assert scheduler is not None
    router.session.add_user("wxid_bob")

    # alice 和 bob 各入队 2 个
    router.route("wxid_alice", "#run t1")
    router.route("wxid_bob", "#run t2")
    router.route("wxid_alice", "#run t3")
    router.route("wxid_bob", "#run t4")
    time.sleep(0.1)

    # alice 调 #stop，应该只取消 alice 自己的 t3，不影响 bob 的 t4
    sender.clear()
    router.route("wxid_alice", "#stop")
    time.sleep(0.2)

    stop_reply = sender.messages_for("wxid_alice")
    check("alice 的 #stop 回复含取消", any("取消" in r for r in stop_reply))

    # 等所有可达任务完成（最多 t1+t2+t4 三个，t3 被取消）
    wait_for_processed(scheduler, target=3, timeout=15)
    time.sleep(0.3)
    check("bob 的指令未受 alice #stop 影响",
          scheduler.processed_count >= 3,
          detail=f"processed={scheduler.processed_count}")

    scheduler.stop()


def test_router_enqueue_returns_immediately() -> None:
    step("router.route() 入队即返回（不阻塞）")
    templates = [{"name": "t1", "filepath": "/1.json", "game_name": ""}]
    router, _, _, scheduler = make_router(templates=templates, delay=2.0)  # 2 秒长任务
    assert scheduler is not None

    # 即使 executor 要 2 秒，route() 应该几乎瞬间返回
    t0 = time.monotonic()
    router.route("wxid_alice", "#run t1")
    elapsed = time.monotonic() - t0

    check(f"route() 返回时间 <0.5s（实际 {elapsed:.3f}s）", elapsed < 0.5)

    # 清理：等任务完成再 stop
    wait_for_processed(scheduler, target=1, timeout=10)
    scheduler.stop()


def test_consumer_exception_does_not_kill_worker() -> None:
    step("consumer 抛异常不影响后续消费")
    # 注册一个会 crash 的指令
    from autogame_xcx.remote.commands.base import Command, CommandContext, CommandResult

    class CrashCommand(Command):
        name = "CRASH"
        aliases = ["crash"]
        description = "测试 consumer 异常隔离"
        usage = "#crash"
        queued_dispatch = True  # 走队列，验证 worker 在 consumer crash 后能继续消费

        def execute(self, ctx: CommandContext, args: str) -> CommandResult:
            raise RuntimeError("intentional")

    registry = build_default_registry()
    registry.register(CrashCommand())
    parser = CommandParser(registry)
    dispatcher = CommandDispatcher(registry)
    sender = MockSender()
    executor = SlowExecutor(delay=0.1)
    tm = MockTemplateManager([{"name": "t1", "filepath": "/1.json", "game_name": ""}])
    session = SessionManager(allowed={"wxid_alice"})

    scheduler = CommandQueue(consumer=lambda *_: None)
    scheduler.start()
    router = MessageRouter(
        parser=parser, dispatcher=dispatcher, session=session,
        executor=executor, template_manager=tm, sender=sender,
        scheduler=scheduler,
    )

    # crash 入队
    router.route("wxid_alice", "#crash")
    ok1 = wait_for_processed(scheduler, target=1, timeout=5)
    check("crash 指令被处理（worker 没挂）", ok1)

    # 后续 #run 应该仍然正常
    sender.clear()
    router.route("wxid_alice", "#run t1")
    ok2 = wait_for_processed(scheduler, target=2, timeout=5)
    check("crash 后 #run 仍被消费", ok2)
    check("crash 后 #run 用户收到回复", len(sender.messages_for("wxid_alice")) >= 2)

    scheduler.stop()


def test_backward_compat_without_scheduler() -> None:
    step("未接入 scheduler 时保持同步行为（阶段 2.3 兼容）")
    templates = [{"name": "签到", "filepath": "/a.json", "game_name": ""}]
    # with_scheduler=False
    router, sender, executor, scheduler = make_router(
        templates=templates, with_scheduler=False,
    )
    check("scheduler 为 None", scheduler is None)

    t0 = time.monotonic()
    router.route("wxid_alice", "#run 签到")
    elapsed = time.monotonic() - t0

    # 同步执行：route() 必须等到 execute_template 完成才返回
    check("同步模式下 route() 阻塞到执行完成", elapsed >= 0.2,
          detail=f"elapsed={elapsed:.3f}s")
    check("executor 已被调用", len(executor.call_log) == 1)
    check("用户收到回复", len(sender.messages_for("wxid_alice")) >= 2)


# -------------------- main --------------------

def main() -> int:
    tests = [
        test_scheduler_starts_and_consumes,
        test_three_runs_are_serial,
        test_status_during_execution,
        test_stop_cancels_pending,
        test_stop_no_pending,
        test_stop_only_affects_self,
        test_router_enqueue_returns_immediately,
        test_consumer_exception_does_not_kill_worker,
        test_backward_compat_without_scheduler,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            import traceback
            traceback.print_exc()
            check(f"{t.__name__} 未抛异常", False, detail=str(e))

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in CHECKS if ok)
    total = len(CHECKS)
    print(f"阶段 2.4 验证：通过 {passed}/{total} 项检查")
    failed = [(n, d) for n, ok, d in CHECKS if not ok]
    if failed:
        print("\n失败项：")
        for name, detail in failed:
            print(f"  - {name}" + (f" — {detail}" if detail else ""))
        return 1
    print("\n[OK] 阶段 2.4 指令调度器验证 PASSED")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
