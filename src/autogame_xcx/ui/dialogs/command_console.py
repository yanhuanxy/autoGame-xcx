"""指令执行日志控制台（阶段 2.6 PLAN_02 §6.2）。

只读 QTextEdit，订阅 RemoteDriver.log_message 信号。
所有 GUI 更新在主线程（Qt 信号槽自动跨线程）。
"""
from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTextEdit, QVBoxLayout


class CommandConsoleDialog(QDialog):
    """远程驱动日志查看器。

    用法：
        dialog = CommandConsoleDialog(driver, parent)
        dialog.exec()  # 模态
    """

    def __init__(self, driver, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent=parent)
        self.setWindowTitle("远程驱动日志")
        self.resize(640, 480)
        self._driver = driver

        layout = QVBoxLayout(self)

        self._text = QTextEdit(self)
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self._text)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # 订阅 driver 日志信号
        driver.log_message.connect(self.append_log)

    def append_log(self, message: str) -> None:
        """追加一行日志。被 driver.log_message 信号调用（主线程）。"""
        self._text.append(message)
        # 自动滚到底部
        cursor = self._text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._text.setTextCursor(cursor)
