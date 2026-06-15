"""阶段 2.3 验证脚本：指令系统完整链路。

不调 ilink SDK，用 mock sender + mock executor/template_manager 跑通：
    parser → dispatcher → command.execute → mock_sender.send_text

覆盖：
    1. registry 装载 6 个指令（help/list/run/status/stop/report）
    2. parser 解析（# 前缀、别名、空 body、未知指令）
    3. dispatcher 异常隔离（command 抛异常不影响后续）
    4. router 白名单 + 指令分发
    5. session 持久化（JSON 读写）

运行：
    uv run python scripts/demo_commands.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from autogame_xcx.remote.commands import (
    CommandDispatcher,
    CommandParser,
    build_default_registry,
)
from autogame_xcx.remote.router import MessageRouter
from autogame_xcx.remote.session import SessionManager

CHECKS = []


def check(name: str, cond: bool, detail: str = "") -> None:
    CHECKS.append((name, bool(cond), detail))
    mark = "OK " if cond else "FAIL"
    line = f"  [{mark}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)


def step(msg: str) -> None:
    print(f"\n>>> {msg}")


# -------------------- 测试 fixtures --------------------

class MockSender:
    """收集 send_text 调用，便于断言。"""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_text(self, user_id: str, text: str) -> None:
        self.sent.append((user_id, text))

    def last_text(self) -> str | None:
        return self.sent[-1][1] if self.sent else None


class MockTemplateManager:
    """模拟 list_templates 返回值。"""

    def __init__(self, templates: list[dict]) -> None:
        self._templates = templates

    def list_templates(self) -> list[dict]:
        return list(self._templates)


class MockExecutor:
    """模拟 GameExecutor 的最小行为。"""

    def __init__(self, *, succeed: bool = True, report: dict | None = None) -> None:
        self.succeed = succeed
        self.execution_report = report or {}
        self.current_template = None
        self.calls: list[str] = []

    def execute_template(self, filepath: str) -> bool:
        self.calls.append(filepath)
        # 模拟执行后 current_template 与 report 都被填充
        self.current_template = {"template_info": {"name": "from_exec"}}
        self.execution_report = {
            "start_time": "2026-06-15 10:00:00",
            "end_time": "2026-06-15 10:01:30",
            "template_path": filepath,
            "tasks": [
                {"task_name": "签到", "status": "completed", "retry_count": 0},
                {"task_name": "领体力", "status": "completed", "retry_count": 0},
            ],
            "summary": {"total_tasks": 2, "completed": 2, "failed": 0, "success_rate": "100.0%"},
        }
        return self.succeed


def make_router(
    *,
    templates: list[dict] | None = None,
    executor_succeed: bool = True,
    allowed: set[str] | None = None,
) -> tuple[MessageRouter, MockSender, MockExecutor]:
    sender = MockSender()
    executor = MockExecutor(succeed=executor_succeed)
    tm = MockTemplateManager(templates or [])
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
    )
    return router, sender, executor


# -------------------- 测试用例 --------------------

def test_registry_loading() -> None:
    step("registry 装载与别名解析")
    registry = build_default_registry()
    check("注册了 6 个指令", len(registry) == 6, detail=f"actual={len(registry)}")
    check("HELP 已注册", "HELP" in registry)
    check("RUN_TEMPLATE 已注册", "RUN_TEMPLATE" in registry)
    check("别名 'run' 解析到 RUN_TEMPLATE", registry.resolve_alias("run") == "RUN_TEMPLATE")
    check("别名 '执行' 解析到 RUN_TEMPLATE", registry.resolve_alias("执行") == "RUN_TEMPLATE")
    check("大小写不敏感（'LIST' → LIST_TEMPLATES）",
          registry.resolve_alias("LIST") == "LIST_TEMPLATES")
    check("未知别名返回 None", registry.resolve_alias("nonexistent") is None)


def test_parser() -> None:
    step("parser 解析")
    registry = build_default_registry()
    parser = CommandParser(registry)

    parsed = parser.parse("#run 签到模板")
    check("解析 #run 签到模板",
          parsed is not None and parsed.name == "RUN_TEMPLATE" and parsed.args == "签到模板",
          detail=str(parsed))

    parsed = parser.parse("#list")
    check("解析无参数指令 #list",
          parsed is not None and parsed.name == "LIST_TEMPLATES" and parsed.args == "",
          detail=str(parsed))

    parsed = parser.parse("#help")
    check("解析 #help",
          parsed is not None and parsed.name == "HELP",
          detail=str(parsed))

    parsed = parser.parse("hello world")
    check("非 # 消息返回 None", parsed is None)

    parsed = parser.parse("#")
    check("空 body 返回 None", parsed is None)

    parsed = parser.parse("#nonexistent arg1")
    check("未知指令 → UNKNOWN",
          parsed is not None and parsed.name == "UNKNOWN",
          detail=str(parsed))


def test_help_command() -> None:
    step("#help 渲染")
    router, sender, _ = make_router()
    router.route("wxid_alice", "#help")
    reply = sender.last_text()
    check("#help 有回复", reply is not None and len(reply) > 0)
    check("回复含所有指令",
          reply is not None and "可用指令" in reply and "#run" in reply and "#list" in reply,
          detail=reply[:200] if reply else "")


def test_list_command() -> None:
    step("#list 列模板")
    templates = [
        {"name": "签到", "filepath": "a.json", "game_name": "小游戏A"},
        {"name": "领体力", "filepath": "b.json", "game_name": "小游戏B"},
    ]
    router, sender, _ = make_router(templates=templates)
    router.route("wxid_alice", "#list")
    reply = sender.last_text()
    check("#list 返回非空", reply is not None and len(reply) > 0)
    check("#list 含模板名", reply is not None and "签到" in reply and "领体力" in reply)

    # 空模板
    router2, sender2, _ = make_router(templates=[])
    router2.route("wxid_alice", "#list")
    check("空模板时提示", sender2.last_text() is not None and "无" in sender2.last_text())


def test_run_command() -> None:
    step("#run 执行模板")
    templates = [{"name": "签到", "filepath": "/tmp/sign.json", "game_name": ""}]
    router, sender, executor = make_router(templates=templates)

    router.route("wxid_alice", "#run 签到")
    # 应该收到 2 条消息：开始 + 完成
    check("收到 ≥2 条消息（开始+完成）", len(sender.sent) >= 2,
          detail=f"actual={len(sender.sent)}")
    check("第一条是'开始执行'", "开始执行" in sender.sent[0][1])
    check("最后一条含'完成'", "完成" in sender.sent[-1][1])
    check("executor 收到 filepath 调用", len(executor.calls) == 1 and executor.calls[0] == "/tmp/sign.json")

    # 模板不存在
    sender.sent.clear()
    router.route("wxid_alice", "#run 不存在的模板")
    check("不存在模板时回复提示", "不存在" in (sender.last_text() or ""))

    # 空参数
    sender.sent.clear()
    router.route("wxid_alice", "#run")
    check("空参数提示用法", "用法" in (sender.last_text() or ""))


def test_unknown_command() -> None:
    step("未知指令")
    router, sender, _ = make_router()
    router.route("wxid_alice", "#invalid args")
    reply = sender.last_text()
    check("未知指令回复提示", reply is not None and "未知指令" in reply)
    check("回复含 #help 引导", reply is not None and "#help" in reply)


def test_whitelist() -> None:
    step("白名单过滤")
    router, sender, _ = make_router(allowed={"wxid_alice"})

    # 白名单用户消息被处理
    sender.sent.clear()
    router.route("wxid_alice", "#help")
    check("白名单用户收到回复", len(sender.sent) == 1)

    # 非白名单用户被忽略
    sender.sent.clear()
    router.route("wxid_stranger", "#help")
    check("非白名单用户无回复", len(sender.sent) == 0)


def test_natural_language_ignored() -> None:
    step("非 # 消息（LLM 未接入时忽略）")
    router, sender, _ = make_router()
    router.route("wxid_alice", "帮我把签到做了")
    check("非 # 消息无回复（阶段 2.5 LLM 接入后才处理）", len(sender.sent) == 0)


def test_status_command() -> None:
    step("#status 占位实现")
    router, sender, _ = make_router()
    router.route("wxid_alice", "#status")
    reply = sender.last_text()
    check("#status 有回复", reply is not None and "当前状态" in reply)
    check("提示调度器未启用（阶段 2.4 接入）",
          reply is not None and "调度器" in reply)


def test_stop_command_placeholder() -> None:
    step("#stop 占位（阶段 2.4 接入 scheduler）")
    router, sender, _ = make_router()
    router.route("wxid_alice", "#stop")
    reply = sender.last_text()
    check("#stop 回复调度器未启用", reply is not None and "调度器" in reply)


def test_report_command() -> None:
    step("#report 查询执行报告")
    templates = [{"name": "签到", "filepath": "/tmp/sign.json", "game_name": ""}]
    router, sender, _ = make_router(templates=templates)

    # 未执行任何模板
    router.route("wxid_alice", "#report")
    check("未执行时提示暂无记录", "暂无" in (sender.last_text() or ""))

    # 执行后查询
    router.route("wxid_alice", "#run 签到")
    sender.sent.clear()
    router.route("wxid_alice", "#report")
    reply = sender.last_text()
    check("#执行后 #report 有详情", reply is not None and "签到" in reply and "100.0%" in reply,
          detail=(reply[:200] if reply else ""))


def test_session_persistence() -> None:
    step("SessionManager JSON 持久化")
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "whitelist.json"
        session = SessionManager(allowed={"wxid_a"}, admins={"wxid_admin"}, whitelist_path=path)
        session.add_user("wxid_b")
        session.save()
        check("文件已创建", path.exists())

        # 重新加载
        loaded = SessionManager.from_json(path)
        check("重载后白名单含 wxid_a", loaded.is_allowed("wxid_a"))
        check("重载后白名单含 wxid_b", loaded.is_allowed("wxid_b"))
        check("重载后 admin 含 wxid_admin", loaded.is_admin("wxid_admin"))
        check("重载后陌生人被拒", not loaded.is_allowed("wxid_stranger"))


def test_dispatcher_exception_isolation() -> None:
    step("dispatcher 异常隔离")
    # 注册一个会抛异常的指令
    from autogame_xcx.remote.commands.base import Command, CommandContext, CommandResult

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

    from autogame_xcx.remote.router import MessageRouter
    router = MessageRouter(
        parser=parser, dispatcher=dispatcher, session=session,
        executor=executor, template_manager=tm, sender=sender,
    )

    router.route("wxid_alice", "#crash")
    reply = sender.last_text()
    check("crash 后仍回复（异常隔离）", reply is not None and "内部错误" in reply)

    # 后续指令仍然正常
    sender.sent.clear()
    router.route("wxid_alice", "#help")
    check("crash 后 #help 仍正常", "可用指令" in (sender.last_text() or ""))


# -------------------- main --------------------

def main() -> int:
    tests = [
        test_registry_loading,
        test_parser,
        test_help_command,
        test_list_command,
        test_run_command,
        test_unknown_command,
        test_whitelist,
        test_natural_language_ignored,
        test_status_command,
        test_stop_command_placeholder,
        test_report_command,
        test_session_persistence,
        test_dispatcher_exception_isolation,
    ]
    for t in tests:
        t()

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok, _ in CHECKS if ok)
    total = len(CHECKS)
    print(f"阶段 2.3 验证：通过 {passed}/{total} 项检查")
    failed = [(n, d) for n, ok, d in CHECKS if not ok]
    if failed:
        print("\n失败项：")
        for name, detail in failed:
            print(f"  - {name}" + (f" — {detail}" if detail else ""))
        return 1
    print("\n✓ 阶段 2.3 指令系统验证 PASSED")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
