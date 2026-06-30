"""侧栏导航按钮（设计稿：icon + text，active 态左侧蓝条 + 软蓝底）。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QWidget

from autogame_xcx.ui import icons
from autogame_xcx.ui.theme import C


class NavButton(QPushButton):
    def __init__(self, text: str, icon_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon_name = icon_name
        self.setText(text)
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self._refresh_icon)
        self._refresh_icon()

    def _refresh_icon(self, *_args) -> None:
        color = C.LINK if self.isChecked() else C.TEXT_3
        self.setIcon(icons.icon(self._icon_name, color, 16))
        self.setIconSize(self.iconSize())  # keep layout stable
