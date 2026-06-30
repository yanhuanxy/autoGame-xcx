"""功能卡片（设计稿 intro 页）：图标盒 + 标题 + 描述，深色面板 + hover 边。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from autogame_xcx.ui import icons
from autogame_xcx.ui.theme import C


class FeatureCard(QFrame):
    def __init__(self, icon_name: str, title: str, description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)
        icon_box = QLabel()
        icon_box.setFixedSize(30, 30)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setStyleSheet(f"background-color: {C.ACCENT_SOFT_2}; border-radius: 7px;")
        icon_box.setPixmap(icons.pixmap(icon_name, C.LINK, 17))
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {C.TEXT}; font-size: 13.5px; font-weight: 600;")
        header.addWidget(icon_box)
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)

        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"color: {C.TEXT_3}; font-size: 12px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
