"""阶段 2.6 RemoteDriver 测试。

覆盖：
- 初始状态 = DISCONNECTED
- start() → CONNECTING → qr_ready 信号
- _on_login_success → CONNECTED
- _on_login_failure → ERROR + error 信号
- stop() → DISCONNECTED
- 白名单 ops（add / remove / save）
- LLM 配置校验（validate 失败时拒绝更新）
- 消息路由：mock client emit message_received → router.route 被 invoke

用 Mock client（不依赖 JVM），pytest-qt qtbot fixture 处理 QApplication。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PyQt6.QtCore import QObject, pyqtSignal

from autogame_xcx.remote.driver import (
    STATE_CONNECTED,
    STATE_CONNECTING,
    STATE_DISCONNECTED,
    STATE_ERROR,
    RemoteDriver,
)
from autogame_xcx.remote.llm_config import PROVIDER_OPENAI, LlmConfig, load_llm_config
from autogame_xcx.remote.session import SessionManager

# -------------------- mock 工具 --------------------


class MockMessageListener(QObject):
    message_received = pyqtSignal(dict)
    message_error = pyqtSignal(str)


class MockLoginListener(QObject):
    login_success = pyqtSignal(object)
    login_failure = pyqtSignal(str)


class MockILinkClient:
    """最小 ilink client 桩：暴露 RemoteDriver 需要的接口。

    - prepare() / start() / stop() 记录调用
    - send_text() 记录到 calls
    - listeners 是真 QObject，可以 emit 信号
    """

    def __init__(self, *, qr_content: str = "http://example/qr", fail_start: bool = False) -> None:
        self.qr_content = qr_content
        self.fail_start = fail_start
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
        if self.fail_start:
            raise RuntimeError("mock start failure")
        return self.qr_content

    def stop(self) -> None:
        self.stopped = True

    def send_text(self, user_id: str, text: str) -> None:
        self.calls.append((user_id, text))


class MockExecutor:
    """记录 execute_template 调用。"""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.execution_report: dict[str, Any] = {}
        self.current_template = None

    def execute_template(self, filepath: str) -> bool:
        self.calls.append(filepath)
        return True


class MockTemplateManager:
    def __init__(self, templates: list[dict] | None = None) -> None:
        self._t = templates or []

    def list_templates(self) -> list[dict]:
        return list(self._t)


# -------------------- fixtures --------------------


@pytest.fixture
def make_driver(qtbot):  # type: ignore[no-untyped-def]
    """工厂：构造 (driver, mock_client, mock_executor)。

    用法：
        def test_xxx(make_driver):
            driver, client, executor = make_driver()
    """

    def _factory(
        *,
        templates: list[dict] | None = None,
        allowed: set[str] | None = None,
        qr_content: str = "http://example/qr",
        fail_start: bool = False,
        llm_config: LlmConfig | None = None,
        whitelist_path: Path | None = None,
    ) -> tuple[RemoteDriver, MockILinkClient, MockExecutor]:
        client = MockILinkClient(qr_content=qr_content, fail_start=fail_start)
        executor = MockExecutor()
        tm = MockTemplateManager(templates)
        session = SessionManager(allowed=allowed or {"wxid_alice"}, whitelist_path=whitelist_path)
        driver = RemoteDriver(
            client=client,
            executor=executor,
            template_manager=tm,
            session=session,
            llm_config=llm_config or LlmConfig(),
        )
        return driver, client, executor

    return _factory


# -------------------- 状态机 --------------------


def test_initial_state_is_disconnected(make_driver) -> None:  # type: ignore[no-untyped-def]
    driver, _, _ = make_driver()
    assert driver.state == STATE_DISCONNECTED


def test_start_emits_connecting_then_qr(make_driver, qtbot) -> None:  # type: ignore[no-untyped-def]
    driver, client, _ = make_driver()
    states: list[str] = []
    qrs: list[str] = []

    driver.state_changed.connect(states.append)
    driver.qr_ready.connect(qrs.append)

    with qtbot.waitSignal(driver.qr_ready, timeout=2000):
        driver.start()

    assert STATE_CONNECTING in states
    assert qrs == ["http://example/qr"]
    assert client.prepared
    assert client.started


def test_login_success_transitions_to_connected(make_driver, qtbot) -> None:  # type: ignore[no-untyped-def]
    driver, client, _ = make_driver()
    with qtbot.waitSignal(driver.qr_ready, timeout=2000):
        driver.start()
    # 模拟用户扫码成功
    client.login_listener.login_success.emit(None)
    assert driver.state == STATE_CONNECTED


def test_login_failure_transitions_to_error(make_driver, qtbot) -> None:  # type: ignore[no-untyped-def]
    driver, client, _ = make_driver()
    errors: list[str] = []
    driver.error.connect(errors.append)

    with qtbot.waitSignal(driver.qr_ready, timeout=2000):
        driver.start()
    client.login_listener.login_failure.emit("扫码超时")

    assert driver.state == STATE_ERROR
    assert any("扫码超时" in e for e in errors)


def test_start_failure_emits_error(make_driver, qtbot) -> None:  # type: ignore[no-untyped-def]
    driver, _, _ = make_driver(fail_start=True)
    errors: list[str] = []
    driver.error.connect(errors.append)

    with qtbot.waitSignal(driver.error, timeout=2000):
        driver.start()

    assert driver.state == STATE_ERROR
    assert any("mock start failure" in e for e in errors)


def test_start_idempotent_when_connecting(make_driver, qtbot) -> None:  # type: ignore[no-untyped-def]
    """start() 在 CONNECTING/CONNECTED 状态再次调用应被忽略。"""
    driver, client, _ = make_driver()
    with qtbot.waitSignal(driver.qr_ready, timeout=2000):
        driver.start()
    client.login_listener.login_success.emit(None)  # CONNECTED
    # 第二次 start 不应触发额外 worker
    driver.start()
    # 没有崩溃 + 状态保持 CONNECTED
    assert driver.state == STATE_CONNECTED


def test_stop_transitions_to_disconnected(make_driver, qtbot) -> None:  # type: ignore[no-untyped-def]
    driver, client, _ = make_driver()
    with qtbot.waitSignal(driver.qr_ready, timeout=2000):
        driver.start()
    client.login_listener.login_success.emit(None)
    driver.stop()
    assert driver.state == STATE_DISCONNECTED
    assert client.stopped


def test_stop_idempotent_when_already_disconnected(make_driver) -> None:  # type: ignore[no-untyped-def]
    driver, _, _ = make_driver()
    driver.stop()  # 不抛异常
    assert driver.state == STATE_DISCONNECTED


# -------------------- 白名单 --------------------


def test_add_remove_user_roundtrip(make_driver, tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "whitelist.json"
    driver, _, _ = make_driver(allowed={"wxid_alice"}, whitelist_path=path)
    driver.add_user("wxid_bob")
    assert "wxid_bob" in driver.list_users()["allowed"]

    driver.remove_user("wxid_bob")
    assert "wxid_bob" not in driver.list_users()["allowed"]


def test_save_whitelist_writes_json(make_driver, tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "whitelist.json"
    driver, _, _ = make_driver(allowed={"wxid_alice"}, whitelist_path=path)
    driver.add_user("wxid_bob")
    driver.save_whitelist()
    assert path.exists()
    # 重新加载，应包含 alice + bob
    loaded = SessionManager.from_json(path)
    assert loaded.is_allowed("wxid_alice")
    assert loaded.is_allowed("wxid_bob")


# -------------------- LLM 配置 --------------------


def test_update_llm_config_rejects_invalid(make_driver) -> None:  # type: ignore[no-untyped-def]
    """validate 失败时拒绝更新；保持原配置。"""
    driver, _, _ = make_driver()
    bad = LlmConfig(enabled=True, provider="weird", api_key="", model="")
    err = driver.update_llm_config(bad)
    assert err is not None
    assert "provider" in err
    # 原 config（disabled）保持
    assert driver.llm_config.enabled is False


def test_update_llm_config_disabled_is_valid(make_driver) -> None:  # type: ignore[no-untyped-def]
    driver, _, _ = make_driver()
    err = driver.update_llm_config(LlmConfig(enabled=False))
    assert err is None


def test_update_llm_config_valid_openai_no_import(make_driver) -> None:  # type: ignore[no-untyped-def]
    """openai 包未装时，配置本身有效但 orchestrator 不会构造（None）。"""
    driver, _, _ = make_driver()
    cfg = LlmConfig(
        enabled=True,
        provider=PROVIDER_OPENAI,
        api_key="sk-test",
        model="gpt-4o",
    )
    err = driver.update_llm_config(cfg)
    assert err is None
    # router.llm_orchestrator 仍是 None（import 失败回退）
    assert driver.router.llm_orchestrator is None


def test_load_llm_config_nonexistent_returns_default(tmp_path) -> None:
    cfg = load_llm_config(tmp_path / "missing.json")
    assert cfg.enabled is False
    assert cfg.api_key == ""


def test_load_save_llm_config_roundtrip(tmp_path) -> None:
    path = tmp_path / "llm.json"
    cfg = LlmConfig(
        enabled=True,
        provider=PROVIDER_OPENAI,
        api_key="sk-test",
        model="gpt-4o",
        base_url="https://api.deepseek.com/v1",
    )
    from autogame_xcx.remote.llm_config import save_llm_config

    save_llm_config(cfg, path)
    loaded = load_llm_config(path)
    assert loaded.enabled is True
    assert loaded.provider == PROVIDER_OPENAI
    assert loaded.api_key == "sk-test"
    assert loaded.base_url == "https://api.deepseek.com/v1"


# -------------------- 消息路由 --------------------


def test_message_received_routes_to_router(make_driver, qtbot) -> None:  # type: ignore[no-untyped-def]
    """SDK emit message_received → driver 调 router.route → 用户收到回复。"""
    driver, client, _ = make_driver(allowed={"wxid_alice"})
    with qtbot.waitSignal(driver.qr_ready, timeout=2000):
        driver.start()
    client.login_listener.login_success.emit(None)

    # 模拟 SDK 投递一条 #help 消息
    msg = {
        "from_user_id": "wxid_alice",
        "items": [{"text": "#help"}],
    }
    client.message_listener.message_received.emit(msg)

    # 客户端应收到回复（router 走 #help 同步路径）
    assert any("可用指令" in text for _, text in client.calls)


def test_message_received_ignores_non_whitelisted(make_driver, qtbot) -> None:  # type: ignore[no-untyped-def]
    driver, client, _ = make_driver(allowed={"wxid_alice"})
    with qtbot.waitSignal(driver.qr_ready, timeout=2000):
        driver.start()
    client.login_listener.login_success.emit(None)

    msg = {"from_user_id": "wxid_stranger", "items": [{"text": "#help"}]}
    client.message_listener.message_received.emit(msg)
    # 非白名单用户：没有回复
    assert all(u != "wxid_stranger" for u, _ in client.calls)


def test_send_text_drops_message_when_disconnected(make_driver) -> None:  # type: ignore[no-untyped-def]
    """未连接时 send_text 不抛异常，静默丢弃。"""
    driver, client, _ = make_driver()
    driver.send_text("wxid_alice", "hello")
    assert client.calls == []  # 没真发出去


def test_shutdown_calls_jvm_shutdown_safe(make_driver) -> None:  # type: ignore[no-untyped-def]
    """shutdown 路径在没启动 JVM 时也不应抛异常。"""
    driver, client, _ = make_driver()
    driver.shutdown()  # JVMManager.get 会因为没初始化抛错，被 driver 捕获
    assert driver.state == STATE_DISCONNECTED
