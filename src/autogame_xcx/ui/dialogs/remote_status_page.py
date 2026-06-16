"""远程驱动 sidebar 页（阶段 2.6 PLAN_02 §6.1+3+5）。

集成 RemoteDriver，提供：
- 连接状态指示灯 + Start/Stop 按钮
- 二维码显示（用 qrcode lib 渲染）
- LLM 配置段（provider / api_key / model / base_url）
- 白名单管理 + 日志控制台入口按钮

线程模型：所有 UI 更新在主线程；driver 的信号通过 Qt 信号槽自动跨线程。
"""
from __future__ import annotations

import logging
from io import BytesIO

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from autogame_xcx.remote.driver import (
    STATE_CONNECTED,
    STATE_CONNECTING,
    STATE_DISCONNECTED,
    STATE_ERROR,
)
from autogame_xcx.remote.llm_config import PROVIDER_ANTHROPIC, PROVIDER_OPENAI, LlmConfig

logger = logging.getLogger(__name__)

_STATE_LABELS = {
    STATE_DISCONNECTED: "○ 未连接",
    STATE_CONNECTING: "◐ 连接中...",
    STATE_CONNECTED: "● 已连接",
    STATE_ERROR: "✕ 错误",
}


class RemoteStatusPage(QWidget):
    """远程驱动 sidebar 页。"""

    def __init__(self, driver, parent: QWidget | None = None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent=parent)
        self._driver = driver

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(self._build_connection_group())
        layout.addWidget(self._build_qr_group())
        layout.addWidget(self._build_llm_group())
        layout.addStretch(1)
        layout.addLayout(self._build_footer_buttons())

        # 初始同步状态
        self._on_state_changed(driver.state)
        driver.state_changed.connect(self._on_state_changed)
        driver.qr_ready.connect(self._on_qr_ready)
        driver.error.connect(self._on_error)

    # -------------------- 构造子段 --------------------

    def _build_connection_group(self) -> QGroupBox:
        box = QGroupBox("连接状态", self)
        layout = QHBoxLayout(box)

        self._state_label = QLabel(_STATE_LABELS.get(self._driver.state, "?"), self)
        self._state_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self._state_label)
        layout.addStretch(1)

        self._start_btn = QPushButton("启动", self)
        self._start_btn.clicked.connect(self._on_start_clicked)
        layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton("停止", self)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self._stop_btn)
        return box

    def _build_qr_group(self) -> QGroupBox:
        box = QGroupBox("二维码", self)
        layout = QVBoxLayout(box)

        self._qr_label = QLabel("（未启动）", self)
        self._qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_label.setMinimumSize(220, 220)
        self._qr_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._qr_label)

        self._qr_hint = QLabel("", self)
        self._qr_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._qr_hint)
        return box

    def _build_llm_group(self) -> QGroupBox:
        box = QGroupBox("LLM 配置", self)
        layout = QVBoxLayout(box)

        self._llm_enabled = QCheckBox("启用 LLM 编排（自然语言 → 指令）", self)
        layout.addWidget(self._llm_enabled)

        form = QFormLayout()
        # Provider 单选
        provider_row = QHBoxLayout()
        self._provider_group = QButtonGroup(self)
        self._rb_anthropic = QRadioButton("Anthropic", self)
        self._rb_openai = QRadioButton("OpenAI 兼容", self)
        self._rb_openai.setChecked(True)
        self._provider_group.addButton(self._rb_anthropic)
        self._provider_group.addButton(self._rb_openai)
        provider_row.addWidget(self._rb_anthropic)
        provider_row.addWidget(self._rb_openai)
        provider_row.addStretch(1)
        provider_wrap = QWidget(self)
        provider_wrap.setLayout(provider_row)
        form.addRow("Provider:", provider_wrap)

        self._api_key_edit = QLineEdit(self)
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("sk-...")
        form.addRow("API Key:", self._api_key_edit)

        self._model_edit = QLineEdit(self)
        self._model_edit.setPlaceholderText("gpt-4o / claude-sonnet-4-6 / deepseek-chat")
        form.addRow("Model:", self._model_edit)

        self._base_url_edit = QLineEdit(self)
        self._base_url_edit.setPlaceholderText("仅 OpenAI 兼容端点（如 https://api.deepseek.com/v1）")
        form.addRow("Base URL:", self._base_url_edit)

        layout.addLayout(form)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self._save_llm_btn = QPushButton("保存 LLM 配置", self)
        self._save_llm_btn.clicked.connect(self._on_save_llm_clicked)
        save_row.addWidget(self._save_llm_btn)
        layout.addLayout(save_row)

        self._load_llm_config_to_ui()
        return box

    def _build_footer_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch(1)

        self._whitelist_btn = QPushButton("白名单管理", self)
        self._whitelist_btn.clicked.connect(self._on_whitelist_clicked)
        row.addWidget(self._whitelist_btn)

        self._console_btn = QPushButton("打开日志控制台", self)
        self._console_btn.clicked.connect(self._on_console_clicked)
        row.addWidget(self._console_btn)
        return row

    # -------------------- slot --------------------

    def _on_state_changed(self, state: str) -> None:
        self._state_label.setText(_STATE_LABELS.get(state, state))
        # 按钮 enable 状态
        self._start_btn.setEnabled(state in (STATE_DISCONNECTED, STATE_ERROR))
        self._stop_btn.setEnabled(state == STATE_CONNECTED)

    def _on_qr_ready(self, qr_content: str) -> None:
        pixmap = _render_qr_pixmap(qr_content)
        if pixmap is None:
            self._qr_label.setText(qr_content)
            self._qr_label.setStyleSheet("font-family: monospace;")
            self._qr_hint.setText("请用微信扫码（或复制此 URL 到扫码工具）")
            return
        self._qr_label.setPixmap(pixmap.scaled(
            220, 220, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        self._qr_hint.setText("请用微信扫码登录")

    def _on_error(self, message: str) -> None:
        # 不弹窗（避免刷屏）；写日志靠 CommandConsoleDialog
        logger.warning("RemoteDriver error: %s", message)

    def _on_start_clicked(self) -> None:
        self._driver.start()

    def _on_stop_clicked(self) -> None:
        self._driver.stop()
        self._qr_label.setText("（未启动）")
        self._qr_hint.setText("")

    def _on_whitelist_clicked(self) -> None:
        from autogame_xcx.ui.dialogs.whitelist_dialog import WhitelistDialog

        dialog = WhitelistDialog(self._driver, self)
        dialog.exec()

    def _on_console_clicked(self) -> None:
        from autogame_xcx.ui.dialogs.command_console import CommandConsoleDialog

        self._console_dialog = CommandConsoleDialog(self._driver, self)  # type: ignore[attr-defined]
        self._console_dialog.show()

    def _on_save_llm_clicked(self) -> None:
        cfg = self._collect_llm_config_from_ui()
        err = self._driver.update_llm_config(cfg)
        if err is not None:
            self._llm_enabled.setToolTip(err)
            # 简单提示：把错误写进 API Key 占位符（不弹窗）
            self._api_key_edit.setToolTip(err)
        else:
            self._llm_enabled.setToolTip("")
            self._api_key_edit.setToolTip("")

    # -------------------- LLM UI <-> config --------------------

    def _load_llm_config_to_ui(self) -> None:
        cfg = self._driver.llm_config
        self._llm_enabled.setChecked(cfg.enabled)
        if cfg.provider == PROVIDER_ANTHROPIC:
            self._rb_anthropic.setChecked(True)
        else:
            self._rb_openai.setChecked(True)
        self._api_key_edit.setText(cfg.api_key)
        self._model_edit.setText(cfg.model)
        self._base_url_edit.setText(cfg.base_url)

    def _collect_llm_config_from_ui(self) -> LlmConfig:
        return LlmConfig(
            enabled=self._llm_enabled.isChecked(),
            provider=PROVIDER_ANTHROPIC if self._rb_anthropic.isChecked() else PROVIDER_OPENAI,
            api_key=self._api_key_edit.text().strip(),
            model=self._model_edit.text().strip(),
            base_url=self._base_url_edit.text().strip(),
        )


def _render_qr_pixmap(content: str) -> QPixmap | None:
    """用 qrcode lib 把 content 渲染为 QPixmap。

    Returns:
        QPixmap — 成功；
        None    —— qrcode lib 未装 / 内容过长 / 渲染失败。
    """
    try:
        import qrcode  # type: ignore[import-not-found]
    except ImportError:
        logger.warning("qrcode lib not installed; falling back to text")
        return None
    try:
        img = qrcode.make(content)
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        pixmap = QPixmap()
        if not pixmap.loadFromData(buf.read(), "PNG"):
            return None
        return pixmap
    except Exception:
        logger.exception("QR render failed")
        return None
