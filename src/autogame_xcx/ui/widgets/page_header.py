"""页头部条（设计稿：每页统一 header）。

左：页图标（nav.*，#58a6ff 16px）+ 页名（14px 600 #e6edf3）+ 可选 mono 计数（11px #6e7681）；
右：可选动作按钮（图标+文字，边框按钮；主按钮 objectName=PrimaryBtn）。
底部 border-bottom 1px #21262d，padding 11px 20px。5 页共用，保证头部一致。
"""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from autogame_xcx.ui import icons
from autogame_xcx.ui.theme import MONO_FAMILIES, C

_MONO = MONO_FAMILIES[0]


class PageHeader(QWidget):
    """页统一头部条。"""

    def __init__(
        self,
        icon_name: str,
        title: str,
        *,
        count: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PageHeader")
        # 仅给自身加 border-bottom，不影响子控件（子控件走全局 theme.QSS）
        self.setStyleSheet(f"QWidget#PageHeader {{ border-bottom: 1px solid {C.BORDER}; }}")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 11, 20, 11)
        lay.setSpacing(9)

        ic = QLabel()
        ic.setPixmap(icons.pixmap(icon_name, C.LINK, 16))
        self._title = QLabel(title)
        self._title.setStyleSheet(f"color: {C.TEXT}; font-size: 14px; font-weight: 600;")
        self._count = QLabel(count or "")
        self._count.setStyleSheet(
            f"color: {C.TEXT_4}; font-family: '{_MONO}'; font-size: 11px; margin-left: 2px;"
        )
        self._count.setVisible(bool(count))

        lay.addWidget(ic)
        lay.addWidget(self._title)
        lay.addWidget(self._count)
        lay.addStretch()

        self._right = QHBoxLayout()
        self._right.setSpacing(8)
        lay.addLayout(self._right)

    def set_count(self, text: str | None) -> None:
        """更新右侧紧邻页名的 mono 计数（如「4 个模板」）；空串隐藏。"""
        self._count.setText(text or "")
        self._count.setVisible(bool(text))

    def add_action(
        self,
        text: str,
        icon_name: str | None = None,
        *,
        primary: bool = False,
        danger: bool = False,
    ) -> QPushButton:
        """在右侧追加一个动作按钮，返回它（调用方 connect 信号）。"""
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if primary:
            btn.setObjectName("PrimaryBtn")
        elif danger:
            btn.setObjectName("DangerBtn")
        if icon_name:
            color = "#ffffff" if primary else C.TEXT_4
            btn.setIcon(icons.icon(icon_name, color, 14))
            btn.setIconSize(QSize(14, 14))
        self._right.addWidget(btn)
        return btn
