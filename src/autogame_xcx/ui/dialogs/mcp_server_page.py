"""MCP 服务页（设计稿：监控台风格）。

配合 McpServerThread，提供：
- 端口 stepper + 状态指示 + 启动/停止并排
- 服务描述 callout
- 最近调用日志（等宽终端，方法名高亮、ok/error 配色、"等待新调用"呼吸点）

线程模型：McpServerThread 在独立 QThread 内跑 asyncio loop；
信号通过 Qt 信号槽自动跨线程，所有 UI 更新在主线程。
"""
from __future__ import annotations

import logging
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from autogame_xcx.ui import icons
from autogame_xcx.ui.theme import C, MONO_FAMILIES

logger = logging.getLogger(__name__)


class McpServerPage(QWidget):
    """MCP 服务主导航页（深色控制台）。"""

    def __init__(self, mcp_server, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self._server = mcp_server
        mono = MONO_FAMILIES[0]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(14)

        layout.addLayout(self._build_header())
        layout.addLayout(self._build_control_row(mono))
        layout.addWidget(self._build_description())

        self._log_box, self._waiting = self._build_log(mono)
        layout.addWidget(self._log_box, stretch=1)

        # 信号接入
        mcp_server.server_started.connect(self._on_started)
        mcp_server.server_stopped.connect(self._on_stopped)
        mcp_server.server_failed.connect(self._on_failed)
        mcp_server.tool_invoked.connect(self._on_tool_invoked)
        self._refresh_button_state(running=False)

        # 呼吸点（等待新调用）
        self._dot_bright = True
        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(self._blink_waiting)
        self._dot_timer.start(1200)

    # -------------------- 构造子段 --------------------

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(9)
        title = QLabel("MCP 服务")
        title.setStyleSheet(f"color: {C.TEXT}; font-size: 14px; font-weight: 600;")
        icon = QLabel()
        icon.setPixmap(icons.pixmap("nav.mcp", C.LINK, 16))
        clear = QPushButton("清空日志")
        clear.setObjectName("DangerBtn")
        clear.setCursor(Qt.CursorShape.PointingHandCursor)
        clear.clicked.connect(lambda: self._log.clear())
        row.addWidget(icon)
        row.addWidget(title)
        row.addStretch()
        row.addWidget(clear)
        return row

    def _build_control_row(self, mono: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        # 端口盒
        port_box = self._panel()
        port_lay = QHBoxLayout(port_box)
        port_lay.setContentsMargins(14, 11, 14, 11)
        port_lay.setSpacing(10)
        port_lay.addWidget(self._caption("端口"))
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1024, 65535)
        self._port_spin.setValue(self._server.port)
        self._port_spin.setFixedHeight(30)
        self._port_spin.setStyleSheet(self._spin_qss(mono))
        port_lay.addWidget(self._port_spin)
        row.addWidget(port_box)

        # 状态盒
        status_box = self._panel()
        status_lay = QHBoxLayout(status_box)
        status_lay.setContentsMargins(14, 11, 14, 11)
        status_lay.setSpacing(10)
        status_lay.addWidget(self._caption("状态"))
        self._state_dot = QLabel("●")
        self._state_dot.setStyleSheet(f"color: {C.TEXT_3}; font-size: 13px;")
        self._state_label = QLabel("已停止")
        self._state_label.setStyleSheet(f"color: {C.TEXT_3}; font-size: 13px; font-weight: 500;")
        self._listening = QLabel("")
        self._listening.setStyleSheet(f"color: {C.TEXT_4}; font-family: '{mono}'; font-size: 11px;")
        status_lay.addWidget(self._state_dot)
        status_lay.addWidget(self._state_label)
        status_lay.addStretch()
        status_lay.addWidget(self._listening)
        row.addWidget(status_box, stretch=1)

        # 启动 / 停止
        self._start_btn = self._action_btn("启动", "play", primary=True)
        self._start_btn.clicked.connect(self._on_start_clicked)
        self._stop_btn = self._action_btn("停止", "pause", danger=True)
        self._stop_btn.clicked.connect(self._on_stop_clicked)
        row.addWidget(self._start_btn)
        row.addWidget(self._stop_btn)
        return row

    def _build_description(self) -> QWidget:
        box = self._panel()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(14, 11, 14, 11)
        lay.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(icons.pixmap("info", C.TEXT_4, 15))
        ic.setStyleSheet("margin-top: 1px;")
        mono = MONO_FAMILIES[0]
        txt = QLabel(
            f'启动后，<span style="color:{C.TEXT_2};font-family:\'{mono}\'">wechat-ilink-bot</span> '
            f'可通过 MCP 协议连接此端口，调用本项目的模板执行能力'
            f'（<span style="color:{C.LINK};font-family:\'{mono}\'">tools/list</span> → 5 个 tool）。'
        )
        txt.setTextFormat(Qt.TextFormat.RichText)
        txt.setWordWrap(True)
        txt.setStyleSheet(f"color: {C.TEXT_3}; font-size: 12.5px;")
        lay.addWidget(ic)
        lay.addWidget(txt, stretch=1)
        return box

    def _build_log(self, mono: str) -> tuple[QFrame, QLabel]:
        box = QFrame()
        box.setObjectName("Card")
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        # log 头
        head = QWidget()
        head.setStyleSheet(f"background-color: {C.PANEL}; border-bottom: 1px solid {C.BORDER};")
        head_lay = QHBoxLayout(head)
        head_lay.setContentsMargins(14, 9, 14, 9)
        title = QLabel("最近调用 / RECENT CALLS")
        title.setStyleSheet(f"color: {C.TEXT_4}; font-family: '{mono}'; font-size: 10px; letter-spacing: 1.5px;")
        live = QLabel("● LIVE")
        live.setStyleSheet(f"color: {C.GREEN}; font-family: '{mono}'; font-size: 10px;")
        head_lay.addWidget(title)
        head_lay.addStretch()
        head_lay.addWidget(live)
        outer.addWidget(head)
        # log 体
        self._log = QTextBrowser()
        self._log.setOpenExternalLinks(False)
        self._log.setStyleSheet(
            f"QTextBrowser {{ background-color: {C.STATUSBAR_BG}; border: none; "
            f"color: {C.TEXT_3}; font-family: '{mono}'; font-size: 11.5px; padding: 12px 14px; }}"
        )
        self._log.document().setDocumentMargin(0)
        waiting = QLabel()
        waiting.setStyleSheet(
            f"color: {C.GREEN}; font-family: '{mono}'; font-size: 11.5px; padding: 0 14px 12px 14px;"
        )
        outer.addWidget(self._log, stretch=1)
        outer.addWidget(waiting)
        self._waiting = waiting
        self._set_waiting_text()
        return box, waiting

    # -------------------- 小工具 --------------------

    def _panel(self) -> QFrame:
        f = QFrame()
        f.setObjectName("Card")
        return f

    def _caption(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C.TEXT_3}; font-size: 12px;")
        return lbl

    def _action_btn(self, text: str, icon_name: str, *, primary: bool = False, danger: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(40)
        if primary:
            btn.setObjectName("PrimaryBtn")
        elif danger:
            btn.setObjectName("DangerBtn")
            btn.setStyleSheet(
                f"QPushButton {{ background-color: rgba(218,54,51,0.12); border: 1px solid rgba(218,54,51,0.4); "
                f"color: {C.RED}; border-radius: 7px; padding: 0 16px; font-weight: 500; }}"
                f"QPushButton:hover {{ background-color: rgba(218,54,51,0.2); }}"
            )
        else:
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {C.PANEL}; border: 1px solid {C.BORDER}; "
                f"color: {C.TEXT_4}; border-radius: 7px; padding: 0 16px; }}"
                f"QPushButton:hover {{ border-color: {C.ACCENT}; color: {C.LINK}; }}"
            )
        return btn

    @staticmethod
    def _spin_qss(mono: str) -> str:
        return (
            f"QSpinBox {{ background-color: {C.STATUSBAR_BG}; color: {C.TEXT}; "
            f"border: 1px solid {C.BORDER_STRONG}; border-radius: 6px; padding: 0 12px; "
            f"font-family: '{mono}'; font-size: 13px; }}"
            f"QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; border: none; background: transparent; }}"
            f"QSpinBox::up-arrow {{ image: none; width: 0; height: 0; "
            f"border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid {C.TEXT_4}; }}"
            f"QSpinBox::down-arrow {{ image: none; width: 0; height: 0; "
            f"border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {C.TEXT_4}; }}"
        )

    def _set_waiting_text(self) -> None:
        self._waiting.setText(
            f'<span style="color:{C.TEXT_4}">●</span> '
            f'<span style="color:{C.TEXT_4}">等待新调用…</span>'
        )
        self._waiting.setTextFormat(Qt.TextFormat.RichText)

    def _blink_waiting(self) -> None:
        self._dot_bright = not self._dot_bright
        dot = C.GREEN if self._dot_bright else C.TEXT_4
        self._waiting.setText(
            f'<span style="color:{dot}">●</span> '
            f'<span style="color:{C.TEXT_4}">等待新调用…</span>'
        )
        self._waiting.setTextFormat(Qt.TextFormat.RichText)

    # -------------------- slot --------------------

    def _on_start_clicked(self) -> None:
        port = self._port_spin.value()
        if self._server.isRunning():
            self._set_state("启动中", C.YELLOW, listening=f"启动中 :{self._server.port}")
            return
        if port != self._server.port:
            self._server._port = port  # noqa: SLF001 — 受控修改
        self._set_state("启动中", C.YELLOW, listening=f"启动中 :{port}")
        self._server.start()

    def _on_stop_clicked(self) -> None:
        if not self._server.isRunning():
            return
        self._set_state("正在停止", C.YELLOW, listening="正在停止…")
        self._server.request_stop()

    def _on_started(self, port: int) -> None:
        self._set_state("运行中", C.GREEN, listening=f"listening 127.0.0.1:{port}")
        self._refresh_button_state(running=True)

    def _on_stopped(self) -> None:
        self._set_state("已停止", C.TEXT_3, listening="")
        self._refresh_button_state(running=False)

    def _on_failed(self, reason: str) -> None:
        self._set_state("错误", C.RED, listening=reason)
        self._refresh_button_state(running=False)

    def _set_state(self, text: str, color: str, *, listening: str = "") -> None:
        self._state_label.setText(text)
        self._state_label.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 500;")
        self._state_dot.setStyleSheet(f"color: {color}; font-size: 13px;")
        self._listening.setText(listening)

    def _on_tool_invoked(self, name: str, args: dict, result) -> None:  # noqa: ARG002
        ts = datetime.now().strftime("%H:%M:%S")
        args_str = ", ".join(f"{k}={v!r}" for k, v in (args or {}).items())
        if isinstance(result, dict) and "error" in result:
            arrow, tail = C.RED, f"<span style='color:{C.RED}'>error</span> <span style='color:{C.TEXT_4}'>{result['error']}</span>"
        elif isinstance(result, dict):
            summary = result.get("summary") or "ok"
            arrow, tail = C.GREEN, f"<span style='color:{C.GREEN}'>ok</span> <span style='color:{C.TEXT_4}'>{summary}</span>"
        else:
            arrow, tail = C.TEXT_3, f"<span style='color:{C.TEXT_3}'>{result}</span>"
        line = (
            f"<span style='color:{C.TEXT_4}'>[{ts}]</span> "
            f"<span style='color:{C.LINK}'>{name}</span>"
            f"<span style='color:{C.TEXT_4}'>({args_str})</span> "
            f"<span style='color:{C.SEP}'>→</span> {tail}"
        )
        self._log.append(line)

    # -------------------- 内部 --------------------

    def _refresh_button_state(self, *, running: bool) -> None:
        self._start_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        self._port_spin.setEnabled(not running)
