"""阶段 2.6 验证脚本：RemoteDriver + GUI 集成完整链路。

不调真实 ilink SDK / JVM（用 MockILinkClient 桩），
不弹真实 GUI（offscreen QPA），仅验证：

  1. RemoteDriver 状态机正确（DISCONNECTED → CONNECTING → CONNECTED → DISCONNECTED）
  2. listener 信号能从 client 传到 driver（消息路由打通）
  3. 白名单 add/remove/save 持久化到 JSON
  4. LLM 配置 validate 失败时拒绝更新
  5. shutdown 路径安全（未启动 JVM 时不抛异常）
  6. MainGUI 实例化成功 + 远程驱动 sidebar 页加载
  7. aboutToQuit hook 不抛异常

运行：
    uv run python scripts/demo_remote_driver.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Offscreen QPA —— 让脚本在无显示器的 CI / 终端也能跑
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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


# -------------------- Mock 工具（与 tests/unit/test_remote_driver.py 同款）--------------------


from PyQt6.QtCore import QObject, pyqtSignal  # noqa: E402


class MockMessageListener(QObject):
    message_received = pyqtSignal(dict)
    message_error = pyqtSignal(str)


class MockLoginListener(QObject):
    login_success = pyqtSignal(object)
    login_failure = pyqtSignal(str)


class MockILinkClient:
    def __init__(self, *, qr_content: str = "http://example/qr") -> None:
        self.qr_content = qr_content
        self.message_listener = MockMessageListener()
        self.login_listener = MockLoginListener()
        self.calls: list[tuple[str, str]] = []
        self.prepared = False
        self.started = False
        self.stopped = False

    def prepare(self) -> None:
        self.prepared = True

    def start(self) -> str:
        self.started = True
        return self.qr_content

    def stop(self) -> None:
        self.stopped = True

    def send_text(self, user_id: str, text: str) -> None:
        self.calls.append((user_id, text))


class MockExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.execution_report: dict[str, Any] = {}
        self.current_template = None

    def execute_template(self, filepath: str) -> bool:
        self.calls.append(filepath)
        return True


# -------------------- 场景 1：状态机 --------------------


def scenario_state_machine(app) -> None:  # type: ignore[no-untyped-def]
    step("场景 1：RemoteDriver 状态机 + QR 信号")
    from autogame_xcx.remote.driver import (
        STATE_CONNECTED,
        STATE_CONNECTING,
        STATE_DISCONNECTED,
        RemoteDriver,
    )
    from autogame_xcx.remote.session import SessionManager

    client = MockILinkClient(qr_content="http://example/qr/abc")
    driver = RemoteDriver(
        client=client,
        executor=MockExecutor(),
        session=SessionManager(allowed={"wxid_alice"}),
    )
    check("初始状态 DISCONNECTED", driver.state == STATE_DISCONNECTED)

    # 用 QSignalSpy 等 qr_ready
    from PyQt6.QtCore import QEventLoop, QTimer

    qr_captured: list[str] = []
    driver.qr_ready.connect(qr_captured.append)
    state_changes: list[str] = []
    driver.state_changed.connect(state_changes.append)

    loop = QEventLoop()
    driver.qr_ready.connect(loop.quit)
    driver.start()
    QTimer.singleShot(2000, loop.quit)  # 兜底超时
    loop.exec()

    check("qr_ready 信号收到", len(qr_captured) == 1, f"qr_captured={qr_captured}")
    check("QR 内容 = 期望 URL", qr_captured == ["http://example/qr/abc"])
    check("client.prepare 被调用", client.prepared)
    check("client.start 被调用", client.started)
    check(
        "state 经过 CONNECTING",
        STATE_CONNECTING in state_changes,
        f"states={state_changes}",
    )

    # 模拟扫码成功
    client.login_listener.login_success.emit(None)
    check("login_success 后状态 CONNECTED", driver.state == STATE_CONNECTED)

    # stop
    driver.stop()
    check("stop 后状态 DISCONNECTED", driver.state == STATE_DISCONNECTED)
    check("client.stop 被调用", client.stopped)


# -------------------- 场景 2：消息路由 --------------------


def scenario_message_routing(app) -> None:  # type: ignore[no-untyped-def]
    step("场景 2：SDK 消息 → router → 发回微信")
    from PyQt6.QtCore import QEventLoop, QTimer

    from autogame_xcx.remote.driver import RemoteDriver
    from autogame_xcx.remote.session import SessionManager

    client = MockILinkClient()
    driver = RemoteDriver(
        client=client,
        executor=MockExecutor(),
        session=SessionManager(allowed={"wxid_alice"}),
    )
    loop = QEventLoop()
    driver.qr_ready.connect(loop.quit)
    driver.start()
    QTimer.singleShot(2000, loop.quit)
    loop.exec()
    client.login_listener.login_success.emit(None)

    # 投递一条 #help 消息
    client.message_listener.message_received.emit({
        "from_user_id": "wxid_alice",
        "items": [{"text": "#help"}],
    })

    # 让信号槽走完
    loop2 = QEventLoop()
    QTimer.singleShot(100, loop2.quit)
    loop2.exec()

    check(
        "router 走完，client 收到回复",
        len(client.calls) > 0,
        f"calls={client.calls}",
    )
    check(
        "回复含 'help'",
        any("help" in text.lower() or "可用指令" in text for _, text in client.calls),
        f"calls={client.calls}",
    )


# -------------------- 场景 3：白名单持久化 --------------------


def scenario_whitelist_persistence() -> None:
    step("场景 3：白名单 add/save 持久化")
    import tempfile

    from autogame_xcx.remote.driver import RemoteDriver
    from autogame_xcx.remote.session import SessionManager

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "whitelist.json"
        client = MockILinkClient()
        driver = RemoteDriver(
            client=client,
            session=SessionManager(allowed={"wxid_alice"}, whitelist_path=path),
        )
        driver.add_user("wxid_bob")
        driver.add_user("wxid_carol")
        driver.save_whitelist()

        check("whitelist.json 已生成", path.exists())
        loaded = SessionManager.from_json(path)
        check(
            "重新加载后 alice + bob + carol 都在",
            loaded.is_allowed("wxid_alice")
            and loaded.is_allowed("wxid_bob")
            and loaded.is_allowed("wxid_carol"),
        )
        driver.remove_user("wxid_bob")
        driver.save_whitelist()
        reloaded = SessionManager.from_json(path)
        check("删除 bob 后重新加载，bob 不在", not reloaded.is_allowed("wxid_bob"))


# -------------------- 场景 4：LLM 配置 --------------------


def scenario_llm_config() -> None:
    step("场景 4：LLM 配置 validate 失败拒绝更新")
    from autogame_xcx.remote.driver import RemoteDriver
    from autogame_xcx.remote.llm_config import PROVIDER_OPENAI, LlmConfig

    client = MockILinkClient()
    driver = RemoteDriver(client=client)

    bad = LlmConfig(enabled=True, provider="weird", api_key="", model="")
    err = driver.update_llm_config(bad)
    check("validate 失败时返回错误", err is not None, f"err={err}")
    check(
        "原配置保持 disabled",
        driver.llm_config.enabled is False,
    )

    # provider=openai 但 api_key 给定 → validate 通过，但 import openai 失败时 orchestrator=None
    ok = LlmConfig(
        enabled=True,
        provider=PROVIDER_OPENAI,
        api_key="sk-test",
        model="gpt-4o",
    )
    err = driver.update_llm_config(ok)
    check("validate 通过返回 None", err is None)
    check(
        "router.llm_orchestrator 仍是 None（openai 未装）",
        driver.router.llm_orchestrator is None,
    )


# -------------------- 场景 5：shutdown 安全 --------------------


def scenario_shutdown_safe() -> None:
    step("场景 5：shutdown 路径在未启动 JVM 时不抛异常")
    from autogame_xcx.remote.driver import RemoteDriver

    client = MockILinkClient()
    driver = RemoteDriver(client=client)
    try:
        driver.shutdown()
        check("shutdown 无异常", True)
    except Exception as e:
        check("shutdown 无异常", False, f"raised: {e}")


# -------------------- 场景 6：MainGUI 集成 --------------------


def scenario_main_gui_integration(app) -> None:  # type: ignore[no-untyped-def]
    step("场景 6：MainGUI 实例化 + 远程驱动 sidebar 页加载")
    from autogame_xcx.ui.main_window import MainGUI

    gui = MainGUI()
    check("MainGUI 实例化成功", gui is not None)
    check("remote_driver 存在", gui.remote_driver is not None)
    check(
        "remote_driver 初始状态 DISCONNECTED",
        gui.remote_driver.state == "DISCONNECTED",
    )
    check("content_stack 有 5 个页面", gui.content_stack.count() == 5)
    check("remote_page 存在", gui.remote_page is not None)
    check(
        "remote_page 索引 = 4",
        gui.content_stack.indexOf(gui.remote_page) == 4,
    )
    gui.show_remote_driver()
    check(
        "show_remote_driver 切换到 index 4",
        gui.content_stack.currentIndex() == 4,
    )

    # 模拟 aboutToQuit 信号触发 shutdown（不抛异常即可）
    try:
        gui.remote_driver.shutdown()
        check("aboutToQuit → shutdown 不抛异常", True)
    except Exception as e:
        check("aboutToQuit → shutdown 不抛异常", False, f"raised: {e}")


# -------------------- 主入口 --------------------


def main() -> int:
    print("=" * 60)
    print("阶段 2.6 GUI 集成验证（MockILinkClient + offscreen QPA）")
    print("=" * 60)

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    scenario_state_machine(app)
    scenario_message_routing(app)
    scenario_whitelist_persistence()
    scenario_llm_config()
    scenario_shutdown_safe()
    scenario_main_gui_integration(app)

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
        print("\n[OK] stage 2.6 verification passed")
    except UnicodeEncodeError:
        print("\n[OK] stage 2.6 verification passed".encode("ascii", "replace").decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
