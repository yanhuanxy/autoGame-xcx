"""
PyQt6可视化模板创建工具
提供用户友好的图形界面来创建视觉流程自动化模板
"""
import sys
import os
import cv2
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from autogame_xcx.ui.dialogs.area_test_dialog import AreaTestDialog
from autogame_xcx.ui.dialogs.matching_test_dialog import MatchingTestDialog
from autogame_xcx.ui.dialogs.template_test_dialog import TemplateTestDialog
from autogame_xcx.platform.window_controller import GameWindowController
from autogame_xcx.core.image_matcher import ImageMatcher
from autogame_xcx.core.template_manager import TemplateManager


class MarkableLabel(QLabel):
    """可标记的图像标签"""
    area_marked = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.setStyleSheet("border: 2px solid #ccc; background-color: #f9f9f9;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("点击'截取游戏界面'开始")
        
        self.start_point = None
        self.end_point = None
        self.drawing = False
        self.marked_areas = []  # 存储已标记的区域
        self.current_pixmap = None
        
    def set_image(self, cv_image):
        """设置要显示的图像"""
        if cv_image is not None:
            # 转换OpenCV图像到Qt格式
            height, width, channel = cv_image.shape
            bytes_per_line = 3 * width
            q_image = QImage(cv_image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
            
            # 缩放图像以适应标签大小
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            self.current_pixmap = scaled_pixmap
            self.setPixmap(scaled_pixmap)
            
            # 计算缩放比例（用于坐标转换）
            self.scale_x = scaled_pixmap.width() / width
            self.scale_y = scaled_pixmap.height() / height
        else:
            self.setText("截图失败")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.current_pixmap:
            self.start_point = event.position().toPoint()
            self.drawing = True
    
    def mouseMoveEvent(self, event):
        if self.drawing and self.current_pixmap:
            self.end_point = event.position().toPoint()
            self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.drawing and self.current_pixmap:
            self.end_point = event.position().toPoint()
            self.drawing = False
            
            # 计算标记区域（相对于原始图像的坐标）
            if self.start_point and self.end_point:
                # 获取图像在标签中的实际位置
                pixmap_rect = self.current_pixmap.rect()
                label_rect = self.rect()
                
                # 计算图像在标签中的偏移
                x_offset = (label_rect.width() - pixmap_rect.width()) // 2
                y_offset = (label_rect.height() - pixmap_rect.height()) // 2
                
                # 转换为相对于图像的坐标
                start_x = max(0, self.start_point.x() - x_offset)
                start_y = max(0, self.start_point.y() - y_offset)
                end_x = min(pixmap_rect.width(), self.end_point.x() - x_offset)
                end_y = min(pixmap_rect.height(), self.end_point.y() - y_offset)
                
                if start_x < end_x and start_y < end_y:
                    # 转换为原始图像坐标
                    area = {
                        'x': int(min(start_x, end_x) / self.scale_x),
                        'y': int(min(start_y, end_y) / self.scale_y),
                        'width': int(abs(end_x - start_x) / self.scale_x),
                        'height': int(abs(end_y - start_y) / self.scale_y)
                    }
                    
                    self.area_marked.emit(area)
            
            self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if self.current_pixmap:
            painter = QPainter(self)
            
            # 绘制当前正在标记的区域
            if self.drawing and self.start_point and self.end_point:
                painter.setPen(QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine))
                rect = QRect(self.start_point, self.end_point)
                painter.drawRect(rect)
            
            # 绘制已保存的标记区域
            painter.setPen(QPen(Qt.GlobalColor.green, 2))
            for area in self.marked_areas:
                # 转换坐标到显示坐标
                pixmap_rect = self.current_pixmap.rect()
                label_rect = self.rect()
                x_offset = (label_rect.width() - pixmap_rect.width()) // 2
                y_offset = (label_rect.height() - pixmap_rect.height()) // 2

                user_marked_area = area['user_marked_area']
                display_x = int(user_marked_area['x'] * self.scale_x) + x_offset
                display_y = int(user_marked_area['y'] * self.scale_y) + y_offset
                display_width = int(user_marked_area['width'] * self.scale_x)
                display_height = int(user_marked_area['height'] * self.scale_y)
                
                painter.drawRect(display_x, display_y, display_width, display_height)
                
                # 绘制区域标签
                painter.setPen(QPen(Qt.GlobalColor.blue, 1))
                painter.drawText(display_x + 5, display_y + 15, area.get('name', 'Area'))
    
    def add_marked_area(self, area):
        """添加已标记的区域用于显示"""
        self.marked_areas.append(area)
        self.update()
    
    def clear_marked_areas(self):
        """清除所有标记区域"""
        self.marked_areas.clear()
        self.update()

class AreaConfigDialog(QDialog):
    """区域配置对话框"""
    
    def __init__(self, area_coords, parent=None):
        super().__init__(parent)
        self.area_coords = area_coords
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("配置标记区域")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # 区域信息
        info_group = QGroupBox("区域信息")
        info_layout = QFormLayout(info_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如: signin_button")
        
        info_layout.addRow("区域名称:", self.name_edit)
        info_layout.addRow("坐标:", QLabel(f"({self.area_coords['x']}, {self.area_coords['y']})"))
        info_layout.addRow("大小:", QLabel(f"{self.area_coords['width']} x {self.area_coords['height']}"))
        
        layout.addWidget(info_group)
        
        # 操作类型
        action_group = QGroupBox("操作类型")
        action_layout = QVBoxLayout(action_group)
        
        self.action_type = QComboBox()
        self.action_type.addItems([
            "image_verify_and_click - 图像验证并点击",
            "image_verify_only - 仅图像验证"
        ])
        self.action_type.currentTextChanged.connect(self.on_action_type_changed)
        
        action_layout.addWidget(self.action_type)
        
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
        
        action_layout.addWidget(self.click_group)
        layout.addWidget(action_group)
        
        # 匹配参数
        match_group = QGroupBox("匹配参数")
        match_layout = QFormLayout(match_group)
        
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 1.0)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setValue(0.85)
        self.threshold_spin.setDecimals(2)
        
        self.wait_after_spin = QSpinBox()
        self.wait_after_spin.setRange(0, 10000)
        self.wait_after_spin.setValue(2000)
        self.wait_after_spin.setSuffix(" ms")
        
        match_layout.addRow("匹配阈值:", self.threshold_spin)
        match_layout.addRow("执行后等待:", self.wait_after_spin)
        
        layout.addWidget(match_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.test_btn = QPushButton("测试匹配")
        self.test_btn.clicked.connect(self.test_matching)
        
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.test_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 初始状态
        self.on_action_type_changed()
    
    def on_action_type_changed(self):
        """操作类型改变时的处理"""
        action_text = self.action_type.currentText()
        is_click_action = "click" in action_text
        self.click_group.setEnabled(is_click_action)
    
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
    
    def get_config(self):
        """获取配置信息"""
        action_text = self.action_type.currentText()
        action_type = action_text.split(" - ")[0]
        
        config = {
            'name': self.name_edit.text() or f"area_{datetime.now().strftime('%H%M%S')}",
            'action_type': action_type,
            'user_marked_area': self.area_coords,
            'match_threshold': self.threshold_spin.value(),
            'wait_after': self.wait_after_spin.value()
        }
        
        if action_type == "image_verify_and_click":
            config['click_point'] = {
                'x': self.click_x.value(),
                'y': self.click_y.value()
            }
        
        return config


class TemplateCreatorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.window_controller = GameWindowController()
        self.image_matcher = ImageMatcher()
        self.template_manager = TemplateManager()
        
        self.current_screenshot = None
        self.current_template = None
        self.current_task = None
        self.marked_areas = []
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("视觉流程自动化模板创建工具 - Phase 2")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板 - 截图和标记
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 2)
        
        # 右侧面板 - 控制和配置
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建模板', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_template)
        file_menu.addAction(new_action)
        
        open_action = QAction('打开模板', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_template)
        file_menu.addAction(open_action)
        
        save_action = QAction('保存模板', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_template)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        test_window_action = QAction('测试窗口检测', self)
        test_window_action.triggered.connect(self.test_window_detection)
        tools_menu.addAction(test_window_action)
    
    def create_left_panel(self):
        """创建左侧面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 截图控制
        screenshot_group = QGroupBox("游戏界面截图")
        screenshot_layout = QVBoxLayout(screenshot_group)
        
        button_layout = QHBoxLayout()
        
        self.screenshot_btn = QPushButton("截取游戏界面")
        self.screenshot_btn.clicked.connect(self.take_screenshot)
        self.screenshot_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.take_screenshot)
        
        button_layout.addWidget(self.screenshot_btn)
        button_layout.addWidget(self.refresh_btn)
        
        screenshot_layout.addLayout(button_layout)
        
        # 图像显示区域
        self.image_label = MarkableLabel()
        self.image_label.area_marked.connect(self.on_area_marked)
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.image_label)
        scroll_area.setWidgetResizable(True)
        
        screenshot_layout.addWidget(scroll_area)
        
        layout.addWidget(screenshot_group)

        return widget

    def create_right_panel(self):
        """创建右侧面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 模板信息
        template_group = QGroupBox("模板信息")
        template_layout = QFormLayout(template_group)

        self.template_name_edit = QLineEdit()
        self.template_name_edit.setPlaceholderText("例如: 每日签到模板")

        self.game_name_edit = QLineEdit()
        self.game_name_edit.setPlaceholderText("例如: 某某应用")

        template_layout.addRow("模板名称:", self.template_name_edit)
        template_layout.addRow("游戏名称:", self.game_name_edit)

        layout.addWidget(template_group)

        # 任务管理
        task_group = QGroupBox("任务管理")
        task_layout = QVBoxLayout(task_group)

        task_control_layout = QHBoxLayout()

        self.task_name_edit = QLineEdit()
        self.task_name_edit.setPlaceholderText("任务名称")

        self.add_task_btn = QPushButton("添加任务")
        self.add_task_btn.clicked.connect(self.add_task)

        task_control_layout.addWidget(self.task_name_edit)
        task_control_layout.addWidget(self.add_task_btn)

        task_layout.addLayout(task_control_layout)

        self.task_list = QListWidget()
        self.task_list.currentItemChanged.connect(self.on_task_selected)
        task_layout.addWidget(self.task_list)

        layout.addWidget(task_group)

        # 标记区域列表
        areas_group = QGroupBox("标记区域")
        areas_layout = QVBoxLayout(areas_group)

        self.areas_list = QListWidget()
        self.areas_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.areas_list.customContextMenuRequested.connect(self.show_area_context_menu)
        areas_layout.addWidget(self.areas_list)

        # 区域操作按钮
        area_btn_layout = QHBoxLayout()

        self.edit_area_btn = QPushButton("编辑")
        self.edit_area_btn.clicked.connect(self.edit_selected_area)
        self.edit_area_btn.setEnabled(False)

        self.delete_area_btn = QPushButton("删除")
        self.delete_area_btn.clicked.connect(self.delete_selected_area)
        self.delete_area_btn.setEnabled(False)

        self.test_area_btn = QPushButton("测试")
        self.test_area_btn.clicked.connect(self.test_selected_area)
        self.test_area_btn.setEnabled(False)

        area_btn_layout.addWidget(self.edit_area_btn)
        area_btn_layout.addWidget(self.delete_area_btn)
        area_btn_layout.addWidget(self.test_area_btn)

        areas_layout.addLayout(area_btn_layout)
        layout.addWidget(areas_group)

        # 全局设置
        settings_group = QGroupBox("全局设置")
        settings_layout = QFormLayout(settings_group)

        self.max_retry_spin = QSpinBox()
        self.max_retry_spin.setRange(1, 10)
        self.max_retry_spin.setValue(3)

        self.step_delay_spin = QSpinBox()
        self.step_delay_spin.setRange(100, 10000)
        self.step_delay_spin.setValue(1000)
        self.step_delay_spin.setSuffix(" ms")

        settings_layout.addRow("最大重试次数:", self.max_retry_spin)
        settings_layout.addRow("步骤间延迟:", self.step_delay_spin)

        layout.addWidget(settings_group)

        # 操作按钮
        action_layout = QVBoxLayout()

        self.save_template_btn = QPushButton("保存模板")
        self.save_template_btn.clicked.connect(self.save_template)
        self.save_template_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 10px; }")

        self.test_template_btn = QPushButton("测试模板")
        self.test_template_btn.clicked.connect(self.test_template)
        self.test_template_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 10px; }")

        action_layout.addWidget(self.save_template_btn)
        action_layout.addWidget(self.test_template_btn)

        layout.addLayout(action_layout)
        layout.addStretch()

        return widget

    def take_screenshot(self):
        """截取游戏界面"""
        self.statusBar().showMessage("正在截取游戏界面...")

        # 查找微信窗口
        wechat_window = self.window_controller.find_wechat_window()
        if not wechat_window:
            QMessageBox.warning(self, "错误", "未找到微信窗口，请确保微信已启动")
            self.statusBar().showMessage("截图失败")
            return

        # 激活窗口
        if not self.window_controller.activate_window():
            QMessageBox.warning(self, "错误", "无法激活微信窗口")
            self.statusBar().showMessage("截图失败")
            return

        # 截取截图
        screenshot = self.window_controller.capture_window_screenshot()
        if screenshot is not None:
            self.current_screenshot = screenshot
            self.image_label.set_image(screenshot)
            self.statusBar().showMessage("截图成功")

            # 清除之前的标记区域显示
            self.image_label.clear_marked_areas()

            # 重新显示当前任务的标记区域
            if self.current_task:
                for area_data in self.marked_areas:
                    if area_data.get('task_id') == self.current_task:
                        self.image_label.add_marked_area(area_data)
        else:
            QMessageBox.warning(self, "错误", "截图失败")
            self.statusBar().showMessage("截图失败")

    def on_area_marked(self, area_coords):
        """处理区域标记事件"""
        if not self.current_task:
            QMessageBox.warning(self, "提示", "请先选择或创建一个任务")
            return

        # 打开区域配置对话框
        dialog = AreaConfigDialog(area_coords, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_config()

            # 添加任务ID
            config['task_id'] = self.current_task

            # 保存参考图像
            self.save_reference_image(area_coords, config['name'])
            config['reference_image'] = f"{config['name']}.png"

            # 添加到标记区域列表
            self.marked_areas.append(config)

            # 更新UI
            self.update_areas_list()
            self.image_label.add_marked_area(config)

            self.statusBar().showMessage(f"已添加标记区域: {config['name']}")

    def save_reference_image(self, area_coords, area_name):
        """保存参考图像"""
        if self.current_screenshot is None:
            return

        # 提取标记区域的图像
        x, y, w, h = area_coords['x'], area_coords['y'], area_coords['width'], area_coords['height']
        area_image = self.current_screenshot[y:y+h, x:x+w]

        # 保存图像
        template_name = self.template_name_edit.text() or "unnamed_template"
        self.template_manager.save_reference_image(area_image, f"{area_name}.png", template_name)

    def add_task(self):
        """添加新任务"""
        task_name = self.task_name_edit.text().strip()
        if not task_name:
            QMessageBox.warning(self, "提示", "请输入任务名称")
            return

        # 生成任务ID
        task_id = task_name.lower().replace(' ', '_').replace('-', '_')

        # 检查任务是否已存在
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == task_id:
                QMessageBox.warning(self, "提示", "任务已存在")
                return

        # 添加到任务列表
        item = QListWidgetItem(task_name)
        item.setData(Qt.ItemDataRole.UserRole, task_id)
        self.task_list.addItem(item)

        # 选中新添加的任务
        self.task_list.setCurrentItem(item)

        # 清空输入框
        self.task_name_edit.clear()

        self.statusBar().showMessage(f"已添加任务: {task_name}")

    def on_task_selected(self, current, previous):
        """任务选择改变时的处理"""
        if current:
            self.current_task = current.data(Qt.ItemDataRole.UserRole)
            self.update_areas_list()

            # 更新图像显示的标记区域
            if self.current_screenshot is not None:
                self.image_label.clear_marked_areas()
                for area_data in self.marked_areas:
                    if area_data.get('task_id') == self.current_task:
                        self.image_label.add_marked_area(area_data)
        else:
            self.current_task = None

    def update_areas_list(self):
        """更新标记区域列表"""
        self.areas_list.clear()

        if self.current_task:
            for area_data in self.marked_areas:
                if area_data.get('task_id') == self.current_task:
                    item_text = f"{area_data['name']} ({area_data['action_type']})"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, area_data)
                    self.areas_list.addItem(item)

        # 更新按钮状态
        has_selection = self.areas_list.currentItem() is not None
        self.edit_area_btn.setEnabled(has_selection)
        self.delete_area_btn.setEnabled(has_selection)
        self.test_area_btn.setEnabled(has_selection)

    def show_area_context_menu(self, position):
        """显示区域右键菜单"""
        if self.areas_list.itemAt(position):
            menu = QMenu(self)

            edit_action = menu.addAction("编辑")
            edit_action.triggered.connect(self.edit_selected_area)

            delete_action = menu.addAction("删除")
            delete_action.triggered.connect(self.delete_selected_area)

            menu.addSeparator()

            test_action = menu.addAction("测试匹配")
            test_action.triggered.connect(self.test_selected_area)

            menu.exec(self.areas_list.mapToGlobal(position))

    def edit_selected_area(self):
        """编辑选中的区域"""
        current_item = self.areas_list.currentItem()
        if not current_item:
            return

        area_data = current_item.data(Qt.ItemDataRole.UserRole)

        # 打开编辑对话框
        dialog = AreaConfigDialog(area_data['user_marked_area'], self)

        # 设置当前值
        dialog.name_edit.setText(area_data['name'])
        dialog.threshold_spin.setValue(area_data['match_threshold'])
        dialog.wait_after_spin.setValue(area_data['wait_after'])

        # 设置操作类型
        action_type = area_data['action_type']
        for i in range(dialog.action_type.count()):
            if action_type in dialog.action_type.itemText(i):
                dialog.action_type.setCurrentIndex(i)
                break

        # 设置点击位置
        if 'click_point' in area_data:
            dialog.click_x.setValue(area_data['click_point']['x'])
            dialog.click_y.setValue(area_data['click_point']['y'])

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 更新配置
            new_config = dialog.get_config()
            new_config['task_id'] = area_data['task_id']
            new_config['reference_image'] = area_data['reference_image']

            # 如果名称改变了，需要重新保存参考图像
            if new_config['name'] != area_data['name']:
                self.save_reference_image(area_data['user_marked_area'], new_config['name'])
                new_config['reference_image'] = f"{new_config['name']}.png"

            # 更新数据
            for i, area in enumerate(self.marked_areas):
                if area == area_data:
                    self.marked_areas[i] = new_config
                    break

            # 更新UI
            self.update_areas_list()
            self.statusBar().showMessage(f"已更新区域: {new_config['name']}")

    def delete_selected_area(self):
        """删除选中的区域"""
        current_item = self.areas_list.currentItem()
        if not current_item:
            return

        area_data = current_item.data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(self, "确认删除",
                                   f"确定要删除区域 '{area_data['name']}' 吗？",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            # 从列表中移除
            self.marked_areas.remove(area_data)

            # 更新UI
            self.update_areas_list()

            # 更新图像显示
            if self.current_screenshot is not None:
                self.image_label.clear_marked_areas()
                for area in self.marked_areas:
                    if area.get('task_id') == self.current_task:
                        self.image_label.add_marked_area(area)

            self.statusBar().showMessage(f"已删除区域: {area_data['name']}")

    def test_selected_area(self):
        """测试选中区域的匹配"""
        current_item = self.areas_list.currentItem()
        if not current_item:
            return

        area_data = current_item.data(Qt.ItemDataRole.UserRole)

        if self.current_screenshot is None:
            QMessageBox.warning(self, "提示", "请先截取游戏界面")
            return

        # 显示详细测试对话框
        test_dialog = AreaTestDialog(area_data, self.current_screenshot, self)
        test_dialog.exec()

    def new_template(self):
        """新建模板"""
        if self.marked_areas:
            reply = QMessageBox.question(self, "确认",
                                       "当前有未保存的更改，确定要新建模板吗？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return

        # 清空所有数据
        self.template_name_edit.clear()
        self.game_name_edit.clear()
        self.task_name_edit.clear()
        self.task_list.clear()
        self.areas_list.clear()
        self.marked_areas.clear()
        self.current_task = None
        self.current_template = None
        self.image_label.clear_marked_areas()

        self.statusBar().showMessage("已创建新模板")

    def open_template(self):
        """打开模板"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开模板", "templates", "JSON文件 (*.json)"
        )

        if file_path:
            template = self.template_manager.load_template(file_path)
            if template:
                self.load_template_to_ui(template)
                self.current_template = template
                self.statusBar().showMessage(f"已打开模板: {file_path}")
            else:
                QMessageBox.warning(self, "错误", "无法加载模板文件")

    def load_template_to_ui(self, template):
        """将模板数据加载到UI"""
        # 清空当前数据
        self.new_template()

        # 加载模板信息
        template_info = template['template_info']
        self.template_name_edit.setText(template_info['name'])
        self.game_name_edit.setText(template_info.get('game_name', ''))

        # 加载全局设置
        global_settings = template['global_settings']
        self.max_retry_spin.setValue(global_settings.get('max_retry', 3))
        self.step_delay_spin.setValue(global_settings.get('step_delay', 1000))

        # 加载任务和步骤
        for task in template['tasks']:
            # 添加任务到列表
            item = QListWidgetItem(task['task_name'])
            item.setData(Qt.ItemDataRole.UserRole, task['task_id'])
            self.task_list.addItem(item)

            # 加载任务的步骤
            for step in task['steps']:
                area_data = {
                    'task_id': task['task_id'],
                    'name': step['step_id'],
                    'action_type': step['action_type'],
                    'user_marked_area': step['user_marked_area'],
                    'reference_image': step['reference_image'],
                    'match_threshold': step.get('match_threshold', 0.85),
                    'wait_after': step.get('wait_after', 2000)
                }

                if 'click_point' in step:
                    area_data['click_point'] = step['click_point']

                self.marked_areas.append(area_data)

        # 选中第一个任务
        if self.task_list.count() > 0:
            self.task_list.setCurrentRow(0)

    def save_template(self):
        """保存模板"""
        template_name = self.template_name_edit.text().strip()
        game_name = self.game_name_edit.text().strip()

        if not template_name:
            QMessageBox.warning(self, "提示", "请输入模板名称")
            return

        if not self.marked_areas:
            QMessageBox.warning(self, "提示", "请至少添加一个标记区域")
            return

        try:
            # 获取当前分辨率信息
            current_resolution = self.window_controller.get_current_resolution()
            if not current_resolution:
                current_resolution = {'width': 1920, 'height': 1080}

            dpi = self.window_controller.get_system_dpi()
            resolution_info = {
                'width': current_resolution['width'],
                'height': current_resolution['height'],
                'dpi': dpi['x']
            }

            # 创建模板结构
            template = self.template_manager.create_template_structure(
                template_name, game_name or "未知游戏", resolution_info
            )

            # 更新全局设置
            template['global_settings']['max_retry'] = self.max_retry_spin.value()
            template['global_settings']['step_delay'] = self.step_delay_spin.value()

            # 按任务组织步骤
            tasks_dict = {}
            for area_data in self.marked_areas:
                task_id = area_data['task_id']
                if task_id not in tasks_dict:
                    # 查找任务名称
                    task_name = task_id
                    for i in range(self.task_list.count()):
                        item = self.task_list.item(i)
                        if item.data(Qt.ItemDataRole.UserRole) == task_id:
                            task_name = item.text()
                            break

                    tasks_dict[task_id] = self.template_manager.add_task_to_template(
                        template, task_id, task_name
                    )

                # 添加步骤
                task = tasks_dict[task_id]
                self.template_manager.add_step_to_task(
                    task,
                    area_data['name'],
                    area_data['action_type'],
                    area_data['user_marked_area'],
                    area_data['reference_image'],
                    area_data.get('match_algorithm', 'hybrid'),
                    area_data['match_threshold'],
                    area_data.get('click_point'),
                    area_data['wait_after']
                )

            # 保存模板
            file_path = self.template_manager.save_template(template)
            if file_path:
                self.current_template = template
                QMessageBox.information(self, "成功", f"模板已保存: {file_path}")
                self.statusBar().showMessage(f"模板已保存: {file_path}")
            else:
                QMessageBox.warning(self, "错误", "保存模板失败")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存模板时出错: {str(e)}")

    def test_template(self):
        """测试模板"""
        if not self.current_template:
            # 先保存当前模板
            self.save_template()
            if not self.current_template:
                return

        # 显示测试选项对话框
        test_dialog = TemplateTestDialog(self.current_template, self)
        test_dialog.exec()

    def test_window_detection(self):
        """测试窗口检测"""
        wechat_window = self.window_controller.find_wechat_window()
        if wechat_window:
            info = f"找到微信窗口:\n"
            info += f"标题: {wechat_window['title']}\n"
            info += f"进程: {wechat_window['process_name']}\n"

            rect = self.window_controller.get_window_rect()
            if rect:
                info += f"位置: ({rect['left']}, {rect['top']})\n"
                info += f"大小: {rect['width']} x {rect['height']}"

            QMessageBox.information(self, "窗口检测", info)
        else:
            QMessageBox.warning(self, "窗口检测", "未找到微信窗口")

def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("视觉流程自动化模板创建工具")
    app.setApplicationVersion("Phase 2")
    app.setOrganizationName("AutoGame Team")

    # 创建主窗口
    window = TemplateCreatorGUI()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
