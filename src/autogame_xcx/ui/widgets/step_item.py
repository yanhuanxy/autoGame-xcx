"""步骤项（设计稿 guide）：mono 序号块 + 标题 + 描述。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from autogame_xcx.ui.theme import C, MONO_FAMILIES


class StepItem(QWidget):
    def __init__(self, number: int, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        mono = MONO_FAMILIES[0]
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(13)

        num = QLabel(str(number))
        num.setFixedSize(24, 24)
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setStyleSheet(
            f"background-color: {C.ACCENT_SOFT_2}; color: {C.LINK}; border-radius: 7px; "
            f"font-family: '{mono}'; font-size: 12px; font-weight: 600;"
        )
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(f"color: {C.TEXT}; font-size: 13.5px;")
        d = QLabel(description)
        d.setStyleSheet(f"color: {C.TEXT_3}; font-size: 12.5px;")
        d.setWordWrap(True)
        col.addWidget(t)
        col.addWidget(d)
        h.addWidget(num)
        h.addLayout(col)
        h.addStretch()
