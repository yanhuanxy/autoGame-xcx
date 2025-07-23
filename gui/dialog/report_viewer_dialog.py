import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem

from util.constants import REPORTS_PATH


class ReportViewerDialog(QDialog):
    """报告查看对话框"""

    def __init__(self, template_data, parent=None):
        super().__init__(parent)
        self.template_data = template_data
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"报告查看: {self.template_data.get('name', '未知模板')}")
        self.setModal(True)
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # 报告列表
        self.report_list = QListWidget()
        layout.addWidget(self.report_list)

        # 按钮
        button_layout = QHBoxLayout()

        view_btn = QPushButton("查看报告")
        view_btn.clicked.connect(self.view_selected_report)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_reports)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)

        button_layout.addWidget(view_btn)
        button_layout.addWidget(refresh_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        # 加载报告
        self.refresh_reports()

    def refresh_reports(self):
        """刷新报告列表"""
        self.report_list.clear()

        # 查找报告文件
        reports_dir = REPORTS_PATH
        if os.path.exists(reports_dir):
            for filename in os.listdir(reports_dir):
                if filename.endswith('.html'):
                    self.report_list.addItem(filename)

        if self.report_list.count() == 0:
            item = QListWidgetItem("暂无执行报告")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.report_list.addItem(item)

    def view_selected_report(self):
        """查看选中的报告"""
        current_item = self.report_list.currentItem()
        if not current_item:
            return

        report_file = current_item.text()
        report_path = os.path.join(REPORTS_PATH, report_file)

        if os.path.exists(report_path):
            # 在默认浏览器中打开报告
            import webbrowser
            webbrowser.open(f"file://{os.path.abspath(report_path)}")