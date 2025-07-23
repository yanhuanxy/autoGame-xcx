import os

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QTextEdit, QPushButton, QProgressBar

from util.constants import TEMPLATES_PATH


class TemplateExecutionDialog(QDialog):
    """模板执行对话框"""

    def __init__(self, template_data, executor, parent=None):
        super().__init__(parent)
        self.template_data = template_data
        self.executor = executor
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"执行模板: {self.template_data.get('name', '未知模板')}")
        self.setModal(True)
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        # 执行信息
        info_label = QLabel(f"正在执行模板: {self.template_data.get('name', '未知模板')}")
        info_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(info_label)

        # 进度显示
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不确定进度
        layout.addWidget(self.progress_bar)

        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # 按钮
        button_layout = QHBoxLayout()

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setEnabled(False)

        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        # 开始执行
        QTimer.singleShot(500, self.start_execution)

    def start_execution(self):
        """开始执行模板"""
        self.log_text.append("开始执行模板...")

        try:
            # 这里应该调用实际的执行逻辑
            template_file = self.template_data.get('filename')
            if template_file:
                template_path = os.path.join(TEMPLATES_PATH, template_file)
                success = self.executor.execute_template(template_path)

                if success:
                    self.log_text.append("✅ 模板执行成功！")
                else:
                    self.log_text.append("❌ 模板执行失败！")
            else:
                self.log_text.append("❌ 模板文件不存在！")

        except Exception as e:
            self.log_text.append(f"❌ 执行异常: {str(e)}")

        finally:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1)
            self.close_btn.setEnabled(True)