"""VS Code 式状态栏（设计稿：26px，mono，左 status dot+页名，右 上下文+Phase）。

QMainWindow 自带 QStatusBar；这里封装结构化的左右标签 + setter，
show_* 切页时调 set_page() 更新左侧页名。
"""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QStatusBar, QWidget

from autogame_xcx.ui.theme import C, mono_font


class ConsoleStatusBar(QStatusBar):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizeGripEnabled(False)
        for w in self._build_left().values():
            self.addWidget(w)
        self._phase_label = QLabel("Phase 2.0")
        self._context_label = QLabel("")
        self.addPermanentWidget(self._sep())
        self.addPermanentWidget(self._context_label)
        self.addPermanentWidget(self._sep())
        self.addPermanentWidget(self._phase_label)
        self._apply_mono()
        self.set_page("项目介绍")
        self.set_status("就绪", C.GREEN)

    def _build_left(self) -> dict:
        self._dot_label = QLabel("●")
        self._status_label = QLabel("就绪")
        self._page_label = QLabel("")
        return {"dot": self._dot_label, "status": self._status_label, "sep0": self._sep(), "page": self._page_label}

    def _sep(self) -> QLabel:
        lbl = QLabel("|")
        lbl.setStyleSheet(f"color: {C.SEP};")
        return lbl

    def _apply_mono(self) -> None:
        f = mono_font(11)
        for lbl in (self._status_label, self._page_label, self._context_label, self._phase_label):
            lbl.setFont(f)

    def set_page(self, name: str) -> None:
        self._page_label.setText(name)
        self._page_label.setStyleSheet(f"color: {C.TEXT_3};")

    def set_context(self, text: str) -> None:
        self._context_label.setText(text)
        self._context_label.setStyleSheet(f"color: {C.TEXT_4};")

    def set_status(self, text: str, color: str = C.TEXT_3) -> None:
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color};")
        self._dot_label.setStyleSheet(f"color: {color};")

    # 让 QStatusBar 也接受深色背景（QSS 已覆盖，这里补 frame 风格）
    def as_frame(self) -> QFrame:  # pragma: no cover - 占位，shell 直接用本对象
        return QFrame()
