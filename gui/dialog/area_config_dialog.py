import datetime

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, QLabel, QSpinBox, QDoubleSpinBox, \
    QComboBox, QPushButton, QMessageBox, QHBoxLayout

from gui.dialog.matching_test_dialog import MatchingTestDialog

import os

class AreaConfigDialog(QDialog):
    """区域配置对话框"""

    def __init__(self, area_coords, screenshot, parent=None):
        super().__init__(parent)
        self.area_coords = area_coords
        self.screenshot = screenshot
        self.area_data = {}

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("配置操作区域")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        # 区域信息
        info_group = QGroupBox("区域信息")
        info_layout = QFormLayout(info_group)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: 签到按钮")

        info_layout.addRow("区域名称:", self.name_edit)
        info_layout.addRow("坐标:", QLabel(f"({self.area_coords['x']}, {self.area_coords['y']})"))
        info_layout.addRow("大小:", QLabel(f"{self.area_coords['width']} x {self.area_coords['height']}"))
        layout.addWidget(info_group)

        # 点击位置配置
        self.click_group = QGroupBox("点击位置")
        click_layout = QFormLayout(self.click_group)

        self.click_x = QSpinBox()
        self.click_x.setRange(0, 9999)
        self.click_x.setValue(self.area_coords['x'] + self.area_coords['width'] // 2)

        self.click_y = QSpinBox()
        self.click_y.setRange(0, 9999)
        self.click_y.setValue(self.area_coords['y'] + self.area_coords['height'] // 2)

        click_layout.addRow("X坐标:", self.click_x)
        click_layout.addRow("Y坐标:", self.click_y)
        layout.addWidget(self.click_group)

        # 操作类型
        action_group = QGroupBox("操作类型")
        action_layout = QFormLayout(action_group)

        self.action_combo = QComboBox()
        action = [
            ("image_verify_and_click", "图像验证并点击"),
            ("image_verify_only", "仅图像验证"),
            ("click_only", "仅点击"),
            ("wait_for_image", "等待图片出现")
        ]
        for algo_id, algo_name in action:
            self.action_combo.addItem(algo_name, algo_id)
        self.action_combo.setCurrentText("图像验证并点击")

        action_layout.addRow("操作类型:", self.action_combo)
        layout.addWidget(action_group)

        # 匹配参数
        match_group = QGroupBox("匹配参数")
        match_layout = QFormLayout(match_group)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 1.0)
        self.threshold_spin.setValue(0.85)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setDecimals(2)

        self.algorithm_combo = QComboBox()
        algorithms = [
            ("template_matching", "模板匹配 - 快速精确"),
            ("ssim", "结构相似性 - 光照鲁棒"),
            ("feature_matching", "特征匹配 - 形变鲁棒"),
            ("hybrid", "混合匹配 - 智能选择")
        ]
        for algo_id, algo_name in algorithms:
            self.algorithm_combo.addItem(algo_name, algo_id)
        self.algorithm_combo.setCurrentText("混合匹配 - 智能选择")

        self.wait_after_spin = QSpinBox()
        self.wait_after_spin.setRange(0, 10000)
        self.wait_after_spin.setValue(2000)
        self.wait_after_spin.setSuffix(" ms")

        match_layout.addRow("匹配阈值:", self.threshold_spin)
        match_layout.addRow("匹配算法:", self.algorithm_combo)
        match_layout.addRow("执行后等待:", self.wait_after_spin)
        layout.addWidget(match_group)

        # 按钮
        button_layout = QHBoxLayout()

        test_btn = QPushButton("测试匹配")
        test_btn.clicked.connect(self.test_matching)

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(test_btn)
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def test_matching(self):
        """测试匹配功能"""
        # 生成临时参考图像名称
        area_name = self.name_edit.text() or f"area_{datetime.now().strftime('%H%M%S')}"
        reference_image_name = f"{area_name}.png"

        # 检查参考图像路径
        template_name = self.parent().template_name_edit.text() or "unnamed_template"
        reference_image_path = os.path.join(
            self.parent().template_manager.images_dir,
            template_name,
            reference_image_name
        )

        # 如果参考图像不存在，先保存当前区域图像
        if not os.path.exists(reference_image_path):
            if hasattr(self.parent(), 'current_screenshot') and self.parent().current_screenshot is not None:
                # 保存参考图像
                self.parent().save_reference_image(self.area_coords, area_name)
                QMessageBox.information(self, "提示", f"已保存参考图像: {reference_image_name}")
            else:
                QMessageBox.warning(self, "错误", "请先截取游戏界面")
                return

        # 显示匹配测试对话框
        test_dialog = MatchingTestDialog(self.area_coords, reference_image_path, self.parent())
        test_dialog.exec()

    def get_area_data(self):
        """获取区域数据"""
        return {
            'name': self.name_edit.text() or "未命名区域",
            'x': self.area_coords['x'],
            'y': self.area_coords['y'],
            'width': self.area_coords['width'],
            'height': self.area_coords['height'],
            'click_point': {"x":self.click_x.value(),"y": self.click_y.value()},
            'action_type': self.action_combo.currentText(),
            'match_threshold': self.threshold_spin.value(),
            'match_algorithm': self.algorithm_combo.currentText(),
            'wait_after': self.wait_after_spin.value()
        }

    def load_area_data(self, area_data):
        """加载区域数据"""
        self.name_edit.setText(area_data.get('name', ''))

        action_type = area_data.get('action_type', 'image_verify_and_click')
        index = self.action_combo.findText(action_type)
        if index >= 0:
            self.action_combo.setCurrentIndex(index)

        self.threshold_spin.setValue(area_data.get('match_threshold', 0.85))

        algorithm = area_data.get('match_algorithm', 'hybrid')
        index = self.algorithm_combo.findText(algorithm)
        if index >= 0:
            self.algorithm_combo.setCurrentIndex(index)