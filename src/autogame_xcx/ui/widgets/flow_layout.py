"""流式布局 —— 自动换行（从 main_window.py 抽出，算法不变）。"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect, QSize, Qt
from PyQt6.QtWidgets import QLayout, QWidget


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item_list: list = []
        self.spacing_value = 10

    def addItem(self, item) -> None:  # type: ignore[override]
        self.item_list.append(item)

    def count(self) -> int:  # type: ignore[override]
        return len(self.item_list)

    def itemAt(self, index):  # type: ignore[override]
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index):  # type: ignore[override]
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:  # type: ignore[override]
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:  # type: ignore[override]
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # type: ignore[override]
        size = QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect: QRect, test_only: bool) -> int:
        x = rect.x()
        y = rect.y()
        line_height = 0

        for item in self.item_list:
            if item.widget() is None:
                continue
            space_x = self.spacing_value
            space_y = self.spacing_value

            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()
