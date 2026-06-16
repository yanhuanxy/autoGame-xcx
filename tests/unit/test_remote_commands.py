"""指令行为测试（阶段 2.3 + 2.4）。

覆盖：#help / #list / #run / #status / #stop / #report / 未知指令
"""
from __future__ import annotations

from autogame_xcx.remote.commands.base import Command, CommandContext, CommandResult


def test_help_lists_all_commands(make_router) -> None:  # type: ignore[no-untyped-def]
    router, sender, _ = make_router()
    router.route("wxid_alice", "#help")
    reply = sender.last_text()
    assert reply is not None
    assert "可用指令" in reply
    assert "#run" in reply
    assert "#list" in reply


def test_list_with_templates(make_router) -> None:  # type: ignore[no-untyped-def]
    templates = [
        {"name": "签到", "filepath": "a.json", "game_name": "小游戏A"},
        {"name": "领体力", "filepath": "b.json", "game_name": "小游戏B"},
    ]
    router, sender, _ = make_router(templates=templates)
    router.route("wxid_alice", "#list")
    reply = sender.last_text()
    assert reply is not None
    assert "签到" in reply
    assert "领体力" in reply


def test_list_empty_templates_hints(make_router) -> None:  # type: ignore[no-untyped-def]
    router, sender, _ = make_router(templates=[])
    router.route("wxid_alice", "#list")
    reply = sender.last_text()
    assert reply is not None
    assert "无" in reply


def test_run_happy_path(make_router) -> None:  # type: ignore[no-untyped-def]
    templates = [{"name": "签到", "filepath": "/tmp/sign.json", "game_name": ""}]
    router, sender, executor = make_router(templates=templates)
    router.route("wxid_alice", "#run 签到")
    # 应该至少 2 条消息：开始 + 完成
    assert len(sender.sent) >= 2
    assert "开始执行" in sender.sent[0][1]
    assert "完成" in sender.sent[-1][1]
    assert executor.calls == ["/tmp/sign.json"]


def test_run_template_not_found(make_router) -> None:  # type: ignore[no-untyped-def]
    templates = [{"name": "签到", "filepath": "/tmp/sign.json", "game_name": ""}]
    router, sender, _ = make_router(templates=templates)
    router.route("wxid_alice", "#run 不存在的模板")
    reply = sender.last_text()
    assert reply is not None
    assert "不存在" in reply
    assert "#list" in reply  # 引导用户查列表


def test_run_no_arg_shows_usage(make_router) -> None:  # type: ignore[no-untyped-def]
    router, sender, _ = make_router()
    router.route("wxid_alice", "#run")
    reply = sender.last_text()
    assert reply is not None
    assert "用法" in reply


def test_run_executor_failure(make_router) -> None:  # type: ignore[no-untyped-def]
    templates = [{"name": "签到", "filepath": "/tmp/sign.json", "game_name": ""}]
    router, sender, _ = make_router(templates=templates, executor_succeed=False)
    router.route("wxid_alice", "#run 签到")
    reply = sender.last_text()
    assert reply is not None
    assert "失败" in reply


def test_status_without_scheduler(make_router) -> None:  # type: ignore[no-untyped-def]
    """未接入 scheduler 时 #status 提示同步模式。"""
    router, sender, _ = make_router()
    router.route("wxid_alice", "#status")
    reply = sender.last_text()
    assert reply is not None
    assert "当前状态" in reply
    # 未接入 scheduler 时应明确告知
    assert "调度器" in reply


def test_stop_without_scheduler(make_router) -> None:  # type: ignore[no-untyped-def]
    """未接入 scheduler 时 #stop 提示同步模式无法取消。"""
    router, sender, _ = make_router()
    router.route("wxid_alice", "#stop")
    reply = sender.last_text()
    assert reply is not None
    assert "调度器" in reply


def test_report_no_history(make_router) -> None:  # type: ignore[no-untyped-def]
    router, sender, _ = make_router()
    router.route("wxid_alice", "#report")
    reply = sender.last_text()
    assert reply is not None
    assert "暂无" in reply


def test_report_after_run(make_router) -> None:  # type: ignore[no-untyped-def]
    templates = [{"name": "签到", "filepath": "/tmp/sign.json", "game_name": ""}]
    router, sender, _ = make_router(templates=templates)
    router.route("wxid_alice", "#run 签到")
    sender.clear()
    router.route("wxid_alice", "#report")
    reply = sender.last_text()
    assert reply is not None
    assert "签到" in reply
    assert "100.0%" in reply


def test_unknown_command_hint(make_router) -> None:  # type: ignore[no-untyped-def]
    router, sender, _ = make_router()
    router.route("wxid_alice", "#invalid args")
    reply = sender.last_text()
    assert reply is not None
    assert "未知指令" in reply
    assert "#help" in reply


def test_dispatcher_exception_isolation(make_router) -> None:  # type: ignore[no-untyped-def]
    """command.execute 抛异常不应影响 dispatcher 后续调用。"""
    from conftest import MockExecutor, MockSender, MockTemplateManager

    from autogame_xcx.remote.commands import (
        CommandDispatcher,
        CommandParser,
        build_default_registry,
    )
    from autogame_xcx.remote.router import MessageRouter
    from autogame_xcx.remote.session import SessionManager

    class CrashCommand(Command):
        name = "CRASH"
        aliases = ["crash"]
        description = "测试异常隔离"
        usage = "#crash"

        def execute(self, ctx: CommandContext, args: str) -> CommandResult:
            raise RuntimeError("intentional crash")

    registry = build_default_registry()
    registry.register(CrashCommand())
    parser = CommandParser(registry)
    dispatcher = CommandDispatcher(registry)
    sender = MockSender()
    executor = MockExecutor()
    tm = MockTemplateManager([])
    session = SessionManager(allowed={"wxid_alice"})
    router = MessageRouter(
        parser=parser,
        dispatcher=dispatcher,
        session=session,
        executor=executor,
        template_manager=tm,
        sender=sender,
    )

    router.route("wxid_alice", "#crash")
    reply = sender.last_text()
    assert reply is not None
    assert "内部错误" in reply

    # 后续指令仍正常
    sender.clear()
    router.route("wxid_alice", "#help")
    assert "可用指令" in (sender.last_text() or "")
