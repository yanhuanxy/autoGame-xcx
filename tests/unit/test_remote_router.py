"""router 测试（阶段 2.3 + 2.4）。

覆盖：
- 白名单过滤
- 非 # 消息（LLM 未接入时）忽略
- 控制类指令（#status/#stop）即使接入 scheduler 也走 inline dispatch
- #run 接入 scheduler 时入队、未接入时同步
"""
from __future__ import annotations

from autogame_xcx.remote.scheduler import CommandQueue


def test_whitelisted_user_receives_reply(make_router) -> None:  # type: ignore[no-untyped-def]
    router, sender, _ = make_router(allowed={"wxid_alice"})
    router.route("wxid_alice", "#help")
    assert len(sender.sent) == 1


def test_non_whitelisted_user_ignored(make_router) -> None:  # type: ignore[no-untyped-def]
    router, sender, _ = make_router(allowed={"wxid_alice"})
    router.route("wxid_stranger", "#help")
    assert len(sender.sent) == 0


def test_non_command_ignored_when_llm_not_configured(make_router) -> None:  # type: ignore[no-untyped-def]
    router, sender, _ = make_router()
    router.route("wxid_alice", "帮我把签到做了")
    assert len(sender.sent) == 0


def test_empty_text_ignored(make_router) -> None:  # type: ignore[no-untyped-def]
    router, sender, _ = make_router()
    router.route("wxid_alice", "")
    router.route("wxid_alice", "   ")
    assert len(sender.sent) == 0


def test_control_command_dispatches_inline_with_scheduler(make_router) -> None:  # type: ignore[no-untyped-def]
    """接入 scheduler 后，#status 这类控制指令应立即返回（不入队）。"""
    scheduler = CommandQueue(consumer=lambda *_: None)
    scheduler.start()
    try:
        templates = [
            {"name": "t1", "filepath": "/1.json", "game_name": ""},
            {"name": "t2", "filepath": "/2.json", "game_name": ""},
        ]
        router, sender, _ = make_router(templates=templates, scheduler=scheduler)

        # 入队一个 #run（worker 会消费，但本测试只关注 #status 是否立即返回）
        router.route("wxid_alice", "#run t1")
        # 立即查 #status —— 不应被 #run 阻塞
        sender.clear()
        router.route("wxid_alice", "#status")
        reply = sender.last_text()
        assert reply is not None
        assert "当前状态" in reply
        # 接入 scheduler 后 #status 应反映队列信息（"队列等待" 或 "正在执行" 或 "累计完成"）
        assert (
            "正在执行" in reply or "队列等待" in reply or "累计完成" in reply
        ), f"reply missing scheduler info: {reply[:200]}"
    finally:
        scheduler.stop()


def test_stop_cancels_pending_with_scheduler(make_router) -> None:  # type: ignore[no-untyped-def]
    """接入 scheduler 后，#stop 取消该用户队列中的待执行指令。"""
    import time

    scheduler = CommandQueue(consumer=lambda *_: None)
    scheduler.start()
    try:
        templates = [
            {"name": "t1", "filepath": "/1.json", "game_name": ""},
            {"name": "t2", "filepath": "/2.json", "game_name": ""},
            {"name": "t3", "filepath": "/3.json", "game_name": ""},
        ]
        router, sender, _ = make_router(templates=templates, scheduler=scheduler)

        # 入队 3 个 #run，第一个会立即被消费
        router.route("wxid_alice", "#run t1")
        router.route("wxid_alice", "#run t2")
        router.route("wxid_alice", "#run t3")
        time.sleep(0.05)  # 让 worker pop 出第一个

        # 调 #stop，应取消 t2/t3（在队列里）
        sender.clear()
        router.route("wxid_alice", "#stop")
        reply = sender.last_text()
        assert reply is not None
        assert "取消" in reply

        # 检查队列长度：t1 已 pop，t2/t3 应被取消，队列应为 0
        # 给一点时间让 cancel 生效
        time.sleep(0.05)
        assert scheduler.queue_length == 0, (
            f"expected queue empty after stop, got {scheduler.queue_length}"
        )
    finally:
        scheduler.stop()
