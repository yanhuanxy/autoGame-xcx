"""白名单管理对话框（阶段 2.6 PLAN_02 §6.5）。

显示当前白名单，允许添加/移除并持久化。
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)


class WhitelistDialog(QDialog):
    """白名单管理。

    用法：
        dialog = WhitelistDialog(driver, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            ...
    """

    def __init__(self, driver, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent=parent)
        self.setWindowTitle("白名单管理")
        self.resize(420, 380)
        self._driver = driver

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("已授权用户：", self))

        self._list = QListWidget(self)
        layout.addWidget(self._list)

        # 添加行
        add_row = QHBoxLayout()
        self._input = QLineEdit(self)
        self._input.setPlaceholderText("输入 wxid（如 wxid_xxx）")
        add_row.addWidget(self._input)
        self._add_btn = QPushButton("添加", self)
        self._add_btn.clicked.connect(self._on_add)
        add_row.addWidget(self._add_btn)
        layout.addLayout(add_row)

        # 移除按钮
        self._remove_btn = QPushButton("移除选中", self)
        self._remove_btn.clicked.connect(self._on_remove)
        layout.addWidget(self._remove_btn)

        # OK / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_list()

    def _refresh_list(self) -> None:
        """从 driver.session 重新加载列表。"""
        self._list.clear()
        users = self._driver.list_users()
        # 先列 admins，再列 allowed
        for wxid in users.get("admins", []):
            self._list.addItem(f"{wxid}  (admin)")
        for wxid in users.get("allowed", []):
            self._list.addItem(wxid)

    def _on_add(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        self._driver.add_user(text)
        self._input.clear()
        self._refresh_list()

    def _on_remove(self) -> None:
        row = self._list.currentRow()
        if row < 0:
            return
        # 取 wxid（去掉可能的 "(admin)" 后缀）
        item_text = self._list.item(row).text()
        wxid = item_text.split(" ", 1)[0]
        self._driver.remove_user(wxid)
        self._refresh_list()

    def _on_save(self) -> None:
        self._driver.save_whitelist()
        self.accept()
