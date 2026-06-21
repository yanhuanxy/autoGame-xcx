"""RemoteDriver：ilink 远程驱动的 GUI 集成控制器。

把 ILinkClient / MessageRouter / CommandQueue / SessionManager / 可选 LLMOrchestrator
组合成一个 QObject，提供 GUI 友好的信号 + 简单方法。

状态机：
    DISCONNECTED → CONNECTING → CONNECTED
                            ↘ ERROR
    任意状态 → DISCONNECTED（stop）

线程模型：
    - client.start() 阻塞（JVM 启动 ~1-2s + executeLogin）
    - 用 QThread + worker QObject 包装，避免冻结 GUI
    - listener 信号在 worker 线程 connect（Qt 跨线程连接安全），
      slot 在 driver 所属线程（主线程）执行
    - router.route 也在主线程被调用（信号槽自动转线程）

使用：
    driver = RemoteDriver(client=my_client)
    driver.state_changed.connect(ui.on_state)
    driver.qr_ready.connect(ui.show_qr)
    driver.start()         # 触发 worker
    ...
    driver.stop()          # 断开 client（保留 JVM）
    driver.shutdown()      # app 退出前：client.stop + jvm.shutdown

测试时传 mock client（见 tests/unit/test_remote_driver.py）。
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from autogame_xcx.remote.commands import (
    CommandDispatcher,
    CommandParser,
    build_default_registry,
)
from autogame_xcx.remote.llm import LLMOrchestrator
from autogame_xcx.remote.llm_config import LlmConfig, save_llm_config
from autogame_xcx.remote.router import MessageRouter
from autogame_xcx.remote.scheduler.queue import CommandQueue
from autogame_xcx.remote.session import SessionManager

logger = logging.getLogger(__name__)

STATE_DISCONNECTED = "DISCONNECTED"
STATE_CONNECTING = "CONNECTING"
STATE_CONNECTED = "CONNECTED"
STATE_ERROR = "ERROR"


class _StartWorker(QObject):
    """在 worker 线程跑 client 工厂（可选）+ prepare() + listener 连接 + client.start()。

    关键：listener 信号必须在 executeLogin 之前 connect——
    SDK 在 executeLogin 返回后立刻开始轮询扫码，可能在 ms 级内 fire login_success。
    """

    qr_ready = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, driver: RemoteDriver) -> None:
        super().__init__()
        self._driver = driver

    @pyqtSlot()
    def run(self) -> None:
        try:
            client = self._driver._ensure_client()  # noqa: SLF001 — 受控调用
            client.prepare()
            self._driver._wire_listeners()  # noqa: SLF001 — 受控调用
            qr = client.start()
            self.qr_ready.emit(str(qr))
        except Exception as e:
            logger.exception("RemoteDriver start worker failed")
            self.failed.emit(str(e))


class RemoteDriver(QObject):
    """远程驱动控制器（GUI 集成层）。

    信号：
        state_changed(str)  —— DISCONNECTED / CONNECTING / CONNECTED / ERROR
        qr_ready(str)       —— client.start() 返回的二维码内容（URL 或 base64）
        log_message(str)    —— 给用户看的人话日志（一行一条）
        error(str)          —— 错误描述（同时记日志）
    """

    state_changed = pyqtSignal(str)
    qr_ready = pyqtSignal(str)
    log_message = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        client: Any = None,
        *,
        client_factory: Callable[[], Any] | None = None,
        executor: Any = None,
        template_manager: Any = None,
        session: SessionManager | None = None,
        llm_config: LlmConfig | None = None,
        llm_config_path: Path | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent=parent)
        if client is None and client_factory is None:
            raise ValueError("必须提供 client 或 client_factory")
        self._client = client
        self._client_factory = client_factory
        self._executor = executor
        self._template_manager = template_manager
        self._session = session or SessionManager()
        self._llm_config = llm_config or LlmConfig()
        # 若提供 path，update_llm_config 会自动落盘；测试场景可不传，仅在内存生效。
        self._llm_config_path = llm_config_path
        self._state = STATE_DISCONNECTED
        self._wired = False

        # Scheduler：真实运行时强制接入（避免 execute_template 阻塞 GUI 主线程）
        self._scheduler = CommandQueue(consumer=lambda *_: None)
        self._router = self._build_router()
        # router 注入 consumer
        self._scheduler._consumer = self._router._dispatch_and_reply  # noqa: SLF001
        self._scheduler.start()

        self._thread: QThread | None = None
        self._worker: _StartWorker | None = None

    # -------------------- 公共属性 --------------------

    @property
    def state(self) -> str:
        return self._state

    @property
    def session(self) -> SessionManager:
        return self._session

    @property
    def router(self) -> MessageRouter:
        return self._router

    @property
    def scheduler(self) -> CommandQueue:
        return self._scheduler

    @property
    def llm_config(self) -> LlmConfig:
        return self._llm_config

    # -------------------- 生命周期 --------------------

    def start(self) -> None:
        """触发后台连接。幂等：CONNECTING/CONNECTED 时直接返回。"""
        if self._state in (STATE_CONNECTING, STATE_CONNECTED):
            logger.info("start() ignored; state=%s", self._state)
            return
        self._set_state(STATE_CONNECTING)
        self.log_message.emit("正在启动远程驱动...")

        self._thread = QThread(self)
        self._worker = _StartWorker(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.qr_ready.connect(self._on_qr_ready)
        self._worker.failed.connect(self._on_start_failed)
        # 资源清理：worker 完成后退出线程
        self._worker.qr_ready.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.start()

    def stop(self) -> None:
        """断开 client（保留 JVM，便于后续重启）。app 退出前用 shutdown()。"""
        if self._state == STATE_DISCONNECTED:
            return
        try:
            self._client.stop()
        except Exception as e:
            logger.warning("client.stop() raised: %s", e)
        self._set_state(STATE_DISCONNECTED)
        self.log_message.emit("远程驱动已断开")

    def shutdown(self) -> None:
        """app 退出前的彻底清理：stop client + 停 scheduler + shutdown JVM。

        幂等。安全地从 aboutToQuit 信号调用。
        """
        self.stop()
        try:
            self._scheduler.stop()
        except Exception as e:
            logger.warning("scheduler.stop() raised: %s", e)
        try:
            from autogame_xcx.remote.ilink.jvm import JVMManager

            jvm = JVMManager.get()
            jvm.shutdown()
        except Exception as e:
            logger.warning("JVM shutdown raised: %s", e)

    # -------------------- 白名单 --------------------

    def add_user(self, wxid: str) -> None:
        self._session.add_user(wxid)

    def remove_user(self, wxid: str) -> None:
        self._session.remove_user(wxid)

    def save_whitelist(self) -> None:
        self._session.save()

    def list_users(self) -> dict[str, list[str]]:
        return self._session.all_users()

    # -------------------- LLM 配置 --------------------

    def update_llm_config(self, config: LlmConfig) -> str | None:
        """更新 LLM 配置并重建 orchestrator。

        若构造时传了 llm_config_path，配置应用成功后会自动落盘。

        Returns:
            None — 配置已生效（落盘成功 或 不需要落盘）；
            str  — 配置不可用（validate 失败），保持原配置不变；或落盘失败（此时内存
                   已更新，但下次启动会回到旧配置）。
        """
        err = config.validate()
        if err is not None:
            return err
        self._llm_config = config
        # 重建 router（orchestrator 可能从无→有 或 有→无 切换）
        self._router = self._build_router()
        self._scheduler._consumer = self._router._dispatch_and_reply  # noqa: SLF001
        if self._llm_config_path is not None:
            try:
                save_llm_config(config, self._llm_config_path)
            except (OSError, ValueError) as e:
                logger.warning("Failed to persist LLM config: %s", e)
                return f"配置已应用但保存失败：{e}"
        return None

    # -------------------- 发消息（作为 router 的 sender）--------------------

    def send_text(self, user_id: str, text: str) -> None:
        """router 通过这个回执用户。未连接时丢弃消息（记日志）。"""
        if self._state != STATE_CONNECTED:
            logger.warning(
                "send_text while not connected; dropping message to %s", user_id
            )
            return
        try:
            self._client.send_text(user_id, text)
        except Exception as e:
            logger.exception("send_text failed")
            self.error.emit(f"发送失败：{e}")

    # -------------------- 内部 --------------------

    def _build_router(self) -> MessageRouter:
        registry = build_default_registry()
        parser = CommandParser(registry)
        dispatcher = CommandDispatcher(registry)
        router = MessageRouter(
            parser=parser,
            dispatcher=dispatcher,
            session=self._session,
            executor=self._executor,
            template_manager=self._template_manager,
            sender=self,
            scheduler=self._scheduler,
            llm_orchestrator=self._build_orchestrator(registry),
        )
        return router

    def _build_orchestrator(self, registry):
        """根据 _llm_config 决定是否构造 orchestrator。配置不可用返回 None。"""
        if not self._llm_config.enabled:
            return None
        if self._llm_config.validate() is not None:
            return None
        provider = self._make_provider(self._llm_config)
        if provider is None:
            return None
        return LLMOrchestrator(
            provider=provider,
            registry=registry,
            scheduler=self._scheduler,
            sender=self,
        )

    @staticmethod
    def _make_provider(config: LlmConfig):
        """按 provider 字段实例化对应 Provider；import 失败时返回 None。"""
        try:
            if config.provider == "anthropic":
                from autogame_xcx.remote.llm.anthropic_provider import AnthropicProvider

                return AnthropicProvider(api_key=config.api_key, model=config.model)
            if config.provider == "openai":
                from autogame_xcx.remote.llm.openai_provider import OpenAIProvider

                return OpenAIProvider(
                    api_key=config.api_key,
                    model=config.model,
                    base_url=config.base_url or None,
                )
        except ImportError as e:
            logger.warning("LLM provider import failed: %s", e)
            return None
        return None

    def _ensure_client(self) -> Any:
        """首次调用时按 client_factory 创建 client；之后返回缓存。"""
        if self._client is None:
            if self._client_factory is None:
                raise RuntimeError("client 和 client_factory 都未提供")
            self._client = self._client_factory()
        return self._client

    def _wire_listeners(self) -> None:
        """把 client 的 listener 信号接到 driver slot。幂等。

        在 worker 线程被调用（_StartWorker.run 内），Qt 跨线程 connect 安全。
        """
        if self._wired:
            return
        try:
            self._client.message_listener.message_received.connect(
                self._on_message_received
            )
            self._client.login_listener.login_success.connect(self._on_login_success)
            self._client.login_listener.login_failure.connect(self._on_login_failure)
            self._wired = True
        except Exception as e:
            logger.exception("Failed to wire listeners")
            self.error.emit(f"信号连接失败：{e}")

    def _set_state(self, state: str) -> None:
        if self._state == state:
            return
        self._state = state
        self.state_changed.emit(state)

    # -------------------- 信号 slot --------------------

    @pyqtSlot(str)
    def _on_qr_ready(self, qr_content: str) -> None:
        self.qr_ready.emit(qr_content)
        self.log_message.emit("二维码已就绪，等待微信扫码")

    @pyqtSlot(str)
    def _on_start_failed(self, reason: str) -> None:
        self._set_state(STATE_ERROR)
        self.error.emit(f"启动失败：{reason}")

    @pyqtSlot(dict)
    def _on_message_received(self, msg: dict) -> None:
        """SDK 消息到达。提取文本后转交 router。"""
        text = _extract_text(msg)
        user_id = msg.get("from_user_id", "") or ""
        if text:
            self.log_message.emit(f"收到：{text} from {user_id}")
        if user_id and text:
            try:
                self._router.route(user_id, text)
            except Exception as e:
                logger.exception("router.route crashed")
                self.error.emit(f"路由失败：{e}")

    @pyqtSlot(object)
    def _on_login_success(self, _ctx: object) -> None:
        self._set_state(STATE_CONNECTED)
        self.log_message.emit("登录成功，远程驱动就绪")

    @pyqtSlot(str)
    def _on_login_failure(self, reason: str) -> None:
        self._set_state(STATE_ERROR)
        self.error.emit(f"登录失败：{reason}")


def _extract_text(msg: dict) -> str:
    """从 SDK 的 message dict 中取第一条文本。"""
    items = msg.get("items") or []
    for item in items:
        if isinstance(item, dict) and item.get("text"):
            return str(item["text"])
    return ""
