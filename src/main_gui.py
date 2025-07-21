"""
游戏自动化系统主界面
采用左侧菜单栏 + 右侧内容区域的现代化设计
"""
import sys
import os
import cv2
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from window_controller import GameWindowController
from image_matcher import ImageMatcher
from template_manager import TemplateManager
from game_executor import GameExecutor
from report_generator import ReportGenerator

class FlowLayout(QLayout):
    """流式布局 - 自动换行的布局管理器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.item_list = []
        self.spacing_value = 10

    def addItem(self, item):
        self.item_list.append(item)

    def count(self):
        return len(self.item_list)

    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())

        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def setSpacing(self, spacing):
        self.spacing_value = spacing

    def spacing(self):
        return self.spacing_value

    def doLayout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0

        for item in self.item_list:
            widget = item.widget()
            if widget is None:
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

class IntegratedTemplateCreator(QWidget):
    """集成的模板创建工具"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.window_controller = GameWindowController()
        self.image_matcher = ImageMatcher()
        self.template_manager = TemplateManager()

        # 当前状态
        self.current_screenshot = None
        self.current_template = None
        self.marked_areas = []
        self.current_task = None

        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 左侧控制面板
        self.control_panel = self.create_control_panel()
        layout.addWidget(self.control_panel)

        # 右侧截图和标记区域
        self.screenshot_area = self.create_screenshot_area()
        layout.addWidget(self.screenshot_area)

        # 设置灵活的比例 - 左侧固定，右侧自适应
        layout.setStretch(0, 0)  # 左侧不拉伸，保持固定宽度
        layout.setStretch(1, 1)  # 右侧完全拉伸，占用剩余空间

    def create_control_panel(self):
        """创建左侧控制面板"""
        panel = QWidget()
        panel.setMinimumWidth(320)  # 设置最小宽度
        panel.setMaximumWidth(400)  # 设置最大宽度
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        panel.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 2px;
            }
        """)
        areas_scroll = QScrollArea()
        areas_scroll.setWidgetResizable(True)
        areas_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        areas_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        areas_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ccc;
                border-radius: 8px;
                background-color: #f9f9f9;
            }
            QScrollBar:horizontal, QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal, QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-width: 20px;
                min-height: 20px;
            }
        """)
        scroll_content = QWidget()
        scroll_content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(15)

        # 模板基本信息
        info_group = self.create_template_info_group()
        layout.addWidget(info_group)

        # 操作按钮
        actions_group = self.create_actions_group()
        layout.addWidget(actions_group)

        # 任务管理
        tasks_group = self.create_tasks_group()
        layout.addWidget(tasks_group)

        # 标记区域列表
        areas_group = self.create_areas_group()
        layout.addWidget(areas_group)

        # 公共配置
        settings_group = self.create_config_group()
        layout.addWidget(settings_group)

        layout.addStretch()
        areas_scroll.setWidget(scroll_content)

        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(areas_scroll)
        return panel

    def create_template_info_group(self):
        """创建模板信息组"""
        group = QGroupBox("📝 模板信息")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

        layout = QFormLayout(group)

        self.template_name_edit = QLineEdit()
        self.template_name_edit.setPlaceholderText("例如: 每日签到模板")
        self.template_name_edit.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")

        self.game_name_edit = QLineEdit()
        self.game_name_edit.setPlaceholderText("例如: 开心消消乐")
        self.game_name_edit.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("模板描述（可选）")
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")

        layout.addRow("模板名称:", self.template_name_edit)
        layout.addRow("游戏名称:", self.game_name_edit)
        layout.addRow("描述:", self.description_edit)

        return group

    def create_actions_group(self):
        """创建操作按钮组"""
        group = QGroupBox("🎮 操作")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
        """)

        layout = QVBoxLayout(group)

        # 截图按钮
        self.screenshot_btn = QPushButton("📸 截取游戏界面")
        self.screenshot_btn.clicked.connect(self.take_screenshot)
        self.screenshot_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        # 保存模板按钮
        self.save_btn = QPushButton("💾 保存模板")
        self.save_btn.clicked.connect(self.save_template)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        # 测试模板按钮
        self.test_btn = QPushButton("🧪 测试模板")
        self.test_btn.clicked.connect(self.test_template)
        self.test_btn.setEnabled(False)
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        layout.addWidget(self.screenshot_btn)
        layout.addWidget(self.save_btn)
        layout.addWidget(self.test_btn)

        return group

    def create_tasks_group(self):
        """创建任务管理组"""
        group = QGroupBox("📋 任务管理")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
        """)

        layout = QVBoxLayout(group)

        # 任务列表
        self.tasks_list = QListWidget()
        self.tasks_list.setMinimumHeight(100)
        self.tasks_list.setMaximumHeight(200)
        self.tasks_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)

        # 任务操作按钮
        task_buttons = QHBoxLayout()

        add_task_btn = QPushButton("➕ 添加任务")
        add_task_btn.clicked.connect(self.add_task)
        add_task_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
        """)

        remove_task_btn = QPushButton("➖ 删除任务")
        remove_task_btn.clicked.connect(self.remove_task)
        remove_task_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
        """)

        task_buttons.addWidget(add_task_btn)
        task_buttons.addWidget(remove_task_btn)

        layout.addWidget(self.tasks_list)
        layout.addLayout(task_buttons)

        return group

    def create_areas_group(self):
        """创建标记区域组"""
        group = QGroupBox("🎯 标记区域")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
        """)

        layout = QVBoxLayout(group)

        # 区域列表
        self.areas_list = QListWidget()
        self.areas_list.setMinimumHeight(100)
        self.areas_list.setMaximumHeight(200)
        self.areas_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)

        # 区域操作按钮
        area_buttons = QHBoxLayout()

        edit_area_btn = QPushButton("✏️ 编辑")
        edit_area_btn.clicked.connect(self.edit_selected_area)
        edit_area_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 11px;
            }
        """)

        test_area_btn = QPushButton("🧪 测试")
        test_area_btn.clicked.connect(self.test_selected_area)
        test_area_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 11px;
            }
        """)

        delete_area_btn = QPushButton("🗑️ 删除")
        delete_area_btn.clicked.connect(self.delete_selected_area)
        delete_area_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 11px;
            }
        """)

        area_buttons.addWidget(edit_area_btn)
        area_buttons.addWidget(test_area_btn)
        area_buttons.addWidget(delete_area_btn)

        layout.addWidget(self.areas_list)
        layout.addLayout(area_buttons)

        return group

    def create_config_group(self):
        """创建标记区域组"""
        group = QGroupBox("🔧 全局设置")
        group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #e0e0e0;
                    border-radius: 8px;
                    margin-top: 10px;
                    padding-top: 10px;
                    background-color: white;
                }
            """)

        # 设置区域
        settings_layout = QFormLayout(group)
        # settings_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        # settings_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        # settings_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        settings_layout.setSpacing(15)
        settings_layout.setContentsMargins(10, 10, 10, 10)

        self.max_retry_spin = QSpinBox()
        self.max_retry_spin.setRange(1, 10)
        self.max_retry_spin.setValue(3)

        self.step_delay_spin = QSpinBox()
        self.step_delay_spin.setRange(100, 10000)
        self.step_delay_spin.setValue(1000)
        self.step_delay_spin.setSuffix(" ms")

        settings_layout.addRow("最大重试次数:", self.max_retry_spin)
        settings_layout.addRow("步骤间延迟:", self.step_delay_spin)

        return group

    def create_screenshot_area(self):
        """创建右侧截图和标记区域"""
        area = QWidget()
        area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        area.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(area)
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title = QLabel("🖼️ 游戏界面截图与区域标记")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)

        # 截图显示区域 - 使用滚动区域包装
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll_area.setMinimumSize(400, 300)  # 设置最小尺寸
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 2px dashed #ccc;
                border-radius: 8px;
                background-color: #f9f9f9;
            }
            QScrollBar:horizontal, QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal, QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-width: 20px;
                min-height: 20px;
            }
        """)

        self.screenshot_label = ClickableLabel()
        self.screenshot_label.setMinimumSize(400, 300)
        self.screenshot_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.screenshot_label.setStyleSheet("""
            QLabel {
                border: none;
                background-color: transparent;
                color: #666;
                font-size: 16px;
            }
        """)
        self.screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screenshot_label.setText("点击'截取游戏界面'开始创建模板")
        self.screenshot_label.setScaledContents(False)  # 关键：不缩放内容

        scroll_area.setWidget(self.screenshot_label)

        # 连接鼠标事件
        self.screenshot_label.area_selected.connect(self.on_area_selected)

        layout.addWidget(scroll_area)

        # 提示信息
        hint_label = QLabel("💡 提示: 截图后可以用鼠标拖拽选择操作区域")
        hint_label.setStyleSheet("""
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        """)
        layout.addWidget(hint_label)

        return area

    # 功能实现方法
    def take_screenshot(self):
        """截取游戏界面"""
        try:
            # 查找微信窗口
            wechat_window = self.window_controller.find_wechat_window()
            if not wechat_window:
                QMessageBox.warning(self, "错误", "未找到微信窗口，请确保微信已启动")
                return

            # 激活窗口
            if not self.window_controller.activate_window():
                QMessageBox.warning(self, "错误", "无法激活微信窗口")
                return

            # 截取截图
            screenshot = self.window_controller.capture_window_screenshot()
            if screenshot is not None:
                self.current_screenshot = screenshot
                self.display_screenshot(screenshot)
                self.save_btn.setEnabled(True)
                self.test_btn.setEnabled(True)

                # 更新状态
                if self.parent_window:
                    self.parent_window.statusBar().showMessage("截图成功，可以开始标记区域")
            else:
                QMessageBox.warning(self, "错误", "截图失败")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"截图时出错: {str(e)}")

    def display_screenshot(self, screenshot):
        """显示截图 - 保持原始比例"""
        try:
            # 转换为Qt格式
            height, width, channel = screenshot.shape
            bytes_per_line = 3 * width
            q_image = QImage(screenshot.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()

            # 创建pixmap - 保持原始尺寸
            pixmap = QPixmap.fromImage(q_image)

            # 设置标签尺寸为图像原始尺寸
            self.screenshot_label.setFixedSize(pixmap.size())
            self.screenshot_label.original_size = pixmap.size()

            # 直接设置pixmap，不进行缩放
            self.screenshot_label.setPixmap(pixmap)

            print(f"截图显示: 原始尺寸 {width}x{height}, 显示尺寸 {pixmap.width()}x{pixmap.height()}")

        except Exception as e:
            print(f"显示截图时出错: {e}")

    def on_area_selected(self, rect):
        """处理区域选择"""
        if self.current_screenshot is None:
            return

        # 转换坐标到原始图像尺寸
        original_rect = self.convert_to_original_coordinates(rect)

        # 打开区域配置对话框
        dialog = AreaConfigDialog(original_rect, self.current_screenshot, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            area_data = dialog.get_area_data()
            self.add_marked_area(area_data)

    def convert_to_original_coordinates(self, display_rect):
        """将显示坐标转换为原始图像坐标 - 现在1:1对应，无需转换"""
        # 由于现在显示的是原始尺寸，坐标直接对应
        return {
            'x': int(display_rect['x']),
            'y': int(display_rect['y']),
            'width': int(display_rect['width']),
            'height': int(display_rect['height'])
        }

    def add_marked_area(self, area_data):
        """添加标记区域"""
        self.marked_areas.append(area_data)
        self.update_areas_list()

        # 在截图上绘制标记
        self.draw_area_markers()

    def update_areas_list(self):
        """更新区域列表"""
        self.areas_list.clear()

        for i, area in enumerate(self.marked_areas):
            item_text = f"{i+1}. {area.get('name', '未命名区域')} ({area.get('action_type', '未知操作')})"
            self.areas_list.addItem(item_text)

    def draw_area_markers(self):
        """在截图上绘制区域标记 - 1:1坐标对应"""
        if self.current_screenshot is None:
            return

        try:
            # 重新加载原始截图
            height, width, channel = self.current_screenshot.shape
            bytes_per_line = 3 * width
            q_image = QImage(self.current_screenshot.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
            pixmap = QPixmap.fromImage(q_image)

            # 创建绘制器
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor(33, 150, 243), 3))  # 蓝色边框，稍微粗一点
            painter.setBrush(QBrush(QColor(33, 150, 243, 30)))  # 半透明填充

            # 绘制每个标记区域 - 直接使用原始坐标
            for i, area in enumerate(self.marked_areas):
                x = area['x']
                y = area['y']
                w = area['width']
                h = area['height']

                # 绘制矩形
                painter.drawRect(x, y, w, h)

                # 绘制序号标签
                painter.setPen(QPen(QColor(255, 255, 255), 2))
                painter.setBrush(QBrush(QColor(33, 150, 243)))

                # 绘制序号背景圆圈
                painter.drawEllipse(x + 5, y + 5, 20, 20)

                # 绘制序号文字
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.drawText(x + 10, y + 20, str(i + 1))

                # 恢复边框画笔
                painter.setPen(QPen(QColor(33, 150, 243), 3))
                painter.setBrush(QBrush(QColor(33, 150, 243, 30)))

            painter.end()
            self.screenshot_label.setPixmap(pixmap)

            print(f"绘制了 {len(self.marked_areas)} 个区域标记")

        except Exception as e:
            print(f"绘制区域标记时出错: {e}")

    # 任务管理方法
    def add_task(self):
        """添加任务"""
        task_name, ok = QInputDialog.getText(self, "添加任务", "请输入任务名称:")
        if ok and task_name.strip():
            task_data = {
                'task_id': f"task_{len(self.tasks_list) + 1}",
                'task_name': task_name.strip(),
                'steps': []
            }

            # 添加到任务列表
            self.tasks_list.addItem(f"{task_name.strip()} (0 个步骤)")

            # 设置为当前任务
            self.current_task = task_data

    def remove_task(self):
        """删除任务"""
        current_row = self.tasks_list.currentRow()
        if current_row >= 0:
            self.tasks_list.takeItem(current_row)

    # 区域管理方法
    def edit_selected_area(self):
        """编辑选中的区域"""
        current_row = self.areas_list.currentRow()
        if current_row >= 0 and current_row < len(self.marked_areas):
            area_data = self.marked_areas[current_row]

            # 创建区域坐标字典
            area_coords = {
                'x': area_data['x'],
                'y': area_data['y'],
                'width': area_data['width'],
                'height': area_data['height']
            }

            dialog = AreaConfigDialog(area_coords, self.current_screenshot, self)
            dialog.load_area_data(area_data)  # 加载现有数据

            if dialog.exec() == QDialog.DialogCode.Accepted:
                # 更新区域数据
                updated_data = dialog.get_area_data()
                self.marked_areas[current_row] = updated_data
                self.update_areas_list()
                self.draw_area_markers()

    def test_selected_area(self):
        """测试选中的区域"""
        current_row = self.areas_list.currentRow()
        if current_row >= 0 and current_row < len(self.marked_areas):
            area_data = self.marked_areas[current_row]

            # 创建测试对话框
            from template_creator_gui import AreaTestDialog
            dialog = AreaTestDialog(area_data, self.current_screenshot, self.image_matcher, self)
            dialog.exec()

    def delete_selected_area(self):
        """删除选中的区域"""
        current_row = self.areas_list.currentRow()
        if current_row >= 0 and current_row < len(self.marked_areas):
            reply = QMessageBox.question(
                self, "确认删除",
                f"确定要删除区域 '{self.marked_areas[current_row].get('name', '未命名区域')}' 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                del self.marked_areas[current_row]
                self.update_areas_list()
                self.draw_area_markers()

    def save_template(self):
        """保存模板"""
        template_name = self.template_name_edit.text().strip()
        game_name = self.game_name_edit.text().strip()

        if not template_name:
            QMessageBox.warning(self, "提示", "请填写模板名称")
            return

        if not game_name:
            QMessageBox.warning(self, "提示", "请填写游戏名称")
            return

        if not self.marked_areas:
            QMessageBox.warning(self, "提示", "请至少标记一个操作区域")
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

            # 如果有任务，添加任务数据
            if self.current_task:
                for area_data in self.marked_areas:
                    self.template_manager.add_step_to_task(
                        self.current_task,
                        area_data['name'],
                        area_data['action_type'],
                        area_data['user_marked_area'],
                        area_data['reference_image'],
                        area_data['match_algorithm'],
                        area_data['match_threshold'],
                        area_data.get('click_point'),
                        area_data['wait_after']
                    )

                template['tasks'].append(self.current_task)
            else:
                # 创建默认任务
                default_task = {
                    "task_id": "default_task",
                    "task_name": "默认任务",
                    "steps": []
                }

                for area_data in self.marked_areas:
                    self.template_manager.add_step_to_task(
                        default_task,
                        area_data['name'],
                        area_data['action_type'],
                        area_data['user_marked_area'],
                        area_data['reference_image'],
                        area_data['match_algorithm'],
                        area_data['match_threshold'],
                        area_data.get('click_point'),
                        area_data['wait_after']
                    )

                template['tasks'].append(default_task)

            # 保存模板
            file_path = self.template_manager.save_template(template)

            if file_path:
                self.current_template = template
                QMessageBox.information(self, "成功", f"模板 '{template_name}' 保存成功！")

                # 刷新父窗口的模板列表
                if hasattr(self.parent_window, 'refresh_templates'):
                    self.parent_window.refresh_templates()

            else:
                QMessageBox.critical(self, "错误", "模板保存失败")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存模板时出错: {str(e)}")

    def test_template(self):
        """测试模板"""
        if not self.current_template:
            # 先保存当前模板
            self.save_template()
            if not self.current_template:
                return

        # 创建模板测试对话框
        from template_creator_gui import TemplateTestDialog
        dialog = TemplateTestDialog(self.current_template, self)
        dialog.exec()

    def clear_current_template(self):
        """清空当前模板"""
        self.template_name_edit.clear()
        self.game_name_edit.clear()
        self.description_edit.clear()
        self.marked_areas.clear()
        self.current_task = None
        self.current_screenshot = None

        self.tasks_list.clear()
        self.areas_list.clear()

        self.screenshot_label.clear()
        self.screenshot_label.setText("点击'截取游戏界面'开始创建模板")

        self.save_btn.setEnabled(False)
        self.test_btn.setEnabled(False)

    def load_template_data(self, template_data):
        """加载模板数据"""
        try:
            # 加载基本信息
            template_info = template_data.get('template_info', {})
            self.template_name_edit.setText(template_info.get('name', ''))
            self.game_name_edit.setText(template_info.get('game_name', ''))
            self.description_edit.setPlainText(template_info.get('description', ''))

            # 加载全局设置
            global_settings = template_info.get('global_settings', {})
            self.max_retry_spin.setValue(global_settings.get('max_retry', 3))
            self.step_delay_spin.setValue(global_settings.get('step_delay', 1000))

             # 加载任务数据
            tasks = template_data.get('tasks', [])
            self.tasks_list.clear()

            for task in tasks:
                task_name = task.get('task_name', '未命名任务')
                steps_count = len(task.get('steps', []))
                self.tasks_list.addItem(f"{task_name} ({steps_count} 个步骤)")

            # 设置当前任务为第一个任务
            if tasks:
                self.current_task = tasks[0]

            # 加载区域数据（从任务步骤中提取）
            self.marked_areas.clear()
            for task in tasks:
                for step in task.get('steps', []):
                    area_data = {
                        'name': step.get('step_id', '未命名区域'),
                        'action_type': step.get('action_type', 'image_verify_and_click'),
                        'match_threshold': step.get('match_threshold', 0.85),
                        'match_algorithm': step.get('match_algorithm', 'hybrid'),
                        'reference_image': step['reference_image'],
                        'wait_after': step.get('wait_after', 2000),
                        'x': step.get('user_marked_area', {}).get('x', 0),
                        'y': step.get('user_marked_area', {}).get('y', 0),
                        'width': step.get('user_marked_area', {}).get('width', 100),
                        'height': step.get('user_marked_area', {}).get('height', 50)
                    }
                    self.marked_areas.append(area_data)

            self.update_areas_list()

            # 启用保存和测试按钮
            self.save_btn.setEnabled(True)
            self.test_btn.setEnabled(True)

            QMessageBox.information(self, "成功", f"模板 '{template_info.get('name', '未知模板')}' 加载成功")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载模板数据时出错: {str(e)}")

class ClickableLabel(QLabel):
    """可点击和拖拽选择区域的标签"""

    area_selected = pyqtSignal(dict)  # 区域选择信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_point = None
        self.end_point = None
        self.selecting = False
        self.selection_rect = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.pixmap():
            self.start_point = event.position().toPoint()
            self.selecting = True

    def mouseMoveEvent(self, event):
        if self.selecting and self.start_point:
            self.end_point = event.position().toPoint()
            self.update()  # 触发重绘

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.selecting:
            self.end_point = event.position().toPoint()
            self.selecting = False

            if self.start_point and self.end_point:
                # 计算选择区域
                x1, y1 = self.start_point.x(), self.start_point.y()
                x2, y2 = self.end_point.x(), self.end_point.y()

                # 确保坐标正确
                x = min(x1, x2)
                y = min(y1, y2)
                width = abs(x2 - x1)
                height = abs(y2 - y1)

                # 检查选择区域大小
                if width > 10 and height > 10:  # 最小选择区域
                    rect = {'x': x, 'y': y, 'width': width, 'height': height}
                    self.area_selected.emit(rect)

            self.start_point = None
            self.end_point = None
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.selecting and self.start_point and self.end_point:
            painter = QPainter(self)
            painter.setPen(QPen(QColor(33, 150, 243), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(33, 150, 243, 50)))

            # 绘制选择矩形
            x1, y1 = self.start_point.x(), self.start_point.y()
            x2, y2 = self.end_point.x(), self.end_point.y()

            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)

            painter.drawRect(x, y, width, height)

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
            'action_type': self.action_combo.currentText(),
            'match_threshold': self.threshold_spin.value(),
            'match_algorithm': self.algorithm_combo.currentText(),
            'x': self.area_coords['x'],
            'y': self.area_coords['y'],
            'width': self.area_coords['width'],
            'height': self.area_coords['height']
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

class MenuButton(QPushButton):
    """自定义菜单按钮"""
    def __init__(self, text, icon_text="", parent=None):
        super().__init__(parent)
        self.setText(f"{icon_text}  {text}")
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 15px 20px;
                border: none;
                background-color: transparent;
                color: #333;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                color: #2196F3;
            }
            QPushButton:checked {
                background-color: #2196F3;
                color: white;
                border-left: 4px solid #1976D2;
            }
        """)


class MatchingTestDialog(QDialog):
    """匹配测试对话框 - 专门用于测试图像匹配功能"""

    def __init__(self, area_coords, reference_image_path, parent=None):
        super().__init__(parent)
        self.area_coords = area_coords
        self.reference_image_path = reference_image_path
        self.parent_window = parent
        self.image_matcher = ImageMatcher()
        self.window_controller = GameWindowController()
        self.test_results = []
        self.continuous_testing = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("图像匹配测试")
        self.setModal(True)
        self.resize(800, 700)

        layout = QVBoxLayout(self)

        # 测试配置区域
        config_group = QGroupBox("测试配置")
        config_layout = QFormLayout(config_group)

        # 匹配算法选择
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

        # 匹配阈值
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 1.0)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setValue(0.85)
        self.threshold_spin.setDecimals(2)

        # 测试次数
        self.test_count_spin = QSpinBox()
        self.test_count_spin.setRange(1, 10)
        self.test_count_spin.setValue(3)

        # 实时截图
        self.realtime_check = QCheckBox("实时截图测试")
        self.realtime_check.setChecked(True)
        self.realtime_check.setToolTip("每次测试都重新截图，模拟真实使用场景")

        config_layout.addRow("匹配算法:", self.algorithm_combo)
        config_layout.addRow("匹配阈值:", self.threshold_spin)
        config_layout.addRow("测试次数:", self.test_count_spin)
        config_layout.addRow("", self.realtime_check)

        layout.addWidget(config_group)

        # 图像预览区域
        preview_group = QGroupBox("图像预览")
        preview_layout = QHBoxLayout(preview_group)

        # 当前截图预览
        current_layout = QVBoxLayout()
        current_layout.addWidget(QLabel("当前截图:"))
        self.current_preview = QLabel()
        self.current_preview.setFixedSize(200, 150)
        self.current_preview.setStyleSheet("border: 2px solid #ccc; background-color: #f9f9f9;")
        self.current_preview.setScaledContents(True)
        self.current_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        current_layout.addWidget(self.current_preview)

        # 参考图像预览
        reference_layout = QVBoxLayout()
        reference_layout.addWidget(QLabel("参考图像:"))
        self.reference_preview = QLabel()
        self.reference_preview.setFixedSize(200, 150)
        self.reference_preview.setStyleSheet("border: 2px solid #ccc; background-color: #f9f9f9;")
        self.reference_preview.setScaledContents(True)
        self.reference_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reference_layout.addWidget(self.reference_preview)

        # 差异图像预览
        diff_layout = QVBoxLayout()
        diff_layout.addWidget(QLabel("差异分析:"))
        self.diff_preview = QLabel()
        self.diff_preview.setFixedSize(200, 150)
        self.diff_preview.setStyleSheet("border: 2px solid #ccc; background-color: #f9f9f9;")
        self.diff_preview.setScaledContents(True)
        self.diff_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        diff_layout.addWidget(self.diff_preview)

        preview_layout.addLayout(current_layout)
        preview_layout.addLayout(reference_layout)
        preview_layout.addLayout(diff_layout)

        layout.addWidget(preview_group)

        # 测试结果区域
        results_group = QGroupBox("测试结果")
        results_layout = QVBoxLayout(results_group)

        # 结果统计
        self.stats_label = QLabel("等待测试...")
        self.stats_label.setStyleSheet("font-weight: bold; color: #666;")
        results_layout.addWidget(self.stats_label)

        # 详细结果
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        results_layout.addWidget(self.results_text)

        layout.addWidget(results_group)

        # 按钮区域
        button_layout = QHBoxLayout()

        self.start_test_btn = QPushButton("开始测试")
        self.start_test_btn.clicked.connect(self.start_test)
        self.start_test_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")

        self.continuous_test_btn = QPushButton("连续测试")
        self.continuous_test_btn.clicked.connect(self.start_continuous_test)
        self.continuous_test_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 10px; }")

        self.stop_test_btn = QPushButton("停止测试")
        self.stop_test_btn.clicked.connect(self.stop_test)
        self.stop_test_btn.setEnabled(False)
        self.stop_test_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }")

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)

        button_layout.addWidget(self.start_test_btn)
        button_layout.addWidget(self.continuous_test_btn)
        button_layout.addWidget(self.stop_test_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        # 加载参考图像
        self.load_reference_image()

        # 初始化定时器（用于连续测试）
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self.run_single_test)

    def load_reference_image(self):
        """加载并显示参考图像"""
        try:
            reference_image = self.image_matcher.load_reference_image(self.reference_image_path)
            if reference_image is not None:
                self.reference_image_cv = reference_image
                self.show_image_in_label(reference_image, self.reference_preview)
                self.log_message("✓ 参考图像加载成功")
            else:
                self.log_message("✗ 参考图像加载失败", "error")
        except Exception as e:
            self.log_message(f"✗ 加载参考图像时出错: {e}", "error")

    def start_test(self):
        """开始单次测试"""
        self.start_test_btn.setEnabled(False)
        self.continuous_test_btn.setEnabled(False)
        self.stop_test_btn.setEnabled(True)

        self.results_text.clear()
        self.test_results.clear()

        test_count = self.test_count_spin.value()
        self.log_message(f"开始匹配测试，共 {test_count} 次...")

        try:
            for i in range(test_count):
                self.log_message(f"\n--- 第 {i+1} 次测试 ---")
                result = self.run_single_test()
                if result:
                    self.test_results.append(result)

                # 处理事件，更新界面
                QApplication.processEvents()

                if not self.stop_test_btn.isEnabled():  # 用户停止了测试
                    break

                if i < test_count - 1:  # 不是最后一次测试
                    import time
                    time.sleep(0.5)  # 短暂延迟

            self.show_test_summary()

        except Exception as e:
            self.log_message(f"测试异常: {e}", "error")
        finally:
            self.start_test_btn.setEnabled(True)
            self.continuous_test_btn.setEnabled(True)
            self.stop_test_btn.setEnabled(False)

    def start_continuous_test(self):
        """开始连续测试"""
        self.continuous_testing = True
        self.start_test_btn.setEnabled(False)
        self.continuous_test_btn.setEnabled(False)
        self.stop_test_btn.setEnabled(True)

        self.results_text.clear()
        self.test_results.clear()

        self.log_message("开始连续匹配测试...")
        self.log_message("每2秒进行一次测试，点击'停止测试'结束")

        # 启动定时器，每2秒测试一次
        self.test_timer.start(2000)

    def stop_test(self):
        """停止测试"""
        self.continuous_testing = False
        self.test_timer.stop()

        self.start_test_btn.setEnabled(True)
        self.continuous_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)

        self.log_message("\n测试已停止", "warning")
        if self.test_results:
            self.show_test_summary()

    def run_single_test(self):
        """运行单次测试"""
        try:
            # 获取当前截图
            if self.realtime_check.isChecked():
                # 实时截图
                if not self.capture_current_area():
                    return None

            # 获取测试参数
            algorithm = self.algorithm_combo.currentData()
            threshold = self.threshold_spin.value()

            # 进行匹配测试
            if hasattr(self, 'current_image_cv') and hasattr(self, 'reference_image_cv'):
                is_match, similarity = self.image_matcher.match_images(
                    self.current_image_cv, self.reference_image_cv, algorithm, threshold
                )

                # 记录结果
                result = {
                    'algorithm': algorithm,
                    'threshold': threshold,
                    'similarity': similarity,
                    'is_match': is_match,
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                }

                # 显示结果
                status = "✓ 匹配" if is_match else "✗ 失败"
                color = "success" if is_match else "error"
                self.log_message(f"{result['timestamp']} | {algorithm} | {similarity:.3f} | {status}", color)

                # 生成差异图像
                self.generate_diff_image()

                return result
            else:
                self.log_message("图像数据不完整", "error")
                return None

        except Exception as e:
            self.log_message(f"测试出错: {e}", "error")
            return None

    def capture_current_area(self):
        """截取当前区域图像"""
        try:
            # 查找并激活微信窗口
            wechat_window = self.window_controller.find_wechat_window()
            if not wechat_window:
                self.log_message("未找到微信窗口", "error")
                return False

            if not self.window_controller.activate_window():
                self.log_message("无法激活微信窗口", "error")
                return False

            # 截取窗口截图
            screenshot = self.window_controller.capture_window_screenshot()
            if screenshot is None:
                self.log_message("截图失败", "error")
                return False

            # 提取指定区域
            x, y, w, h = (self.area_coords['x'], self.area_coords['y'],
                          self.area_coords['width'], self.area_coords['height'])

            if (x + w > screenshot.shape[1] or y + h > screenshot.shape[0] or
                    x < 0 or y < 0):
                self.log_message("区域坐标超出截图范围", "error")
                return False

            self.current_image_cv = screenshot[y:y+h, x:x+w]
            self.show_image_in_label(self.current_image_cv, self.current_preview)

            return True

        except Exception as e:
            self.log_message(f"截取区域图像时出错: {e}", "error")
            return False

    def generate_diff_image(self):
        """生成差异图像"""
        try:
            if hasattr(self, 'current_image_cv') and hasattr(self, 'reference_image_cv'):
                # 确保两个图像尺寸一致
                current = self.current_image_cv.copy()
                reference = self.reference_image_cv.copy()

                if current.shape != reference.shape:
                    reference = cv2.resize(reference, (current.shape[1], current.shape[0]))

                # 计算差异
                diff = cv2.absdiff(current, reference)

                # 增强差异显示
                diff_enhanced = cv2.convertScaleAbs(diff, alpha=3.0, beta=0)

                # 显示差异图像
                self.show_image_in_label(diff_enhanced, self.diff_preview)

        except Exception as e:
            self.log_message(f"生成差异图像时出错: {e}", "error")

    def show_image_in_label(self, cv_image, label):
        """在标签中显示图像"""
        try:
            # 转换为RGB
            if len(cv_image.shape) == 3:
                rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
            else:
                rgb_image = cv_image

            # 转换为Qt格式
            height, width = rgb_image.shape[:2]
            if len(rgb_image.shape) == 3:
                bytes_per_line = 3 * width
                q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            else:
                bytes_per_line = width
                q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)

            pixmap = QPixmap.fromImage(q_image)
            label.setPixmap(pixmap)

        except Exception as e:
            self.log_message(f"显示图像时出错: {e}", "error")

    def show_test_summary(self):
        """显示测试摘要"""
        if not self.test_results:
            return

        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r['is_match'])
        success_rate = (successful_tests / total_tests) * 100

        # 计算平均相似度
        avg_similarity = sum(r['similarity'] for r in self.test_results) / total_tests

        # 找到最佳和最差结果
        best_result = max(self.test_results, key=lambda x: x['similarity'])
        worst_result = min(self.test_results, key=lambda x: x['similarity'])

        # 更新统计标签
        stats_text = f"测试完成: {successful_tests}/{total_tests} 成功 ({success_rate:.1f}%) | 平均相似度: {avg_similarity:.3f}"
        self.stats_label.setText(stats_text)

        # 显示详细摘要
        self.log_message("\n" + "="*50, "info")
        self.log_message("测试摘要", "info")
        self.log_message("="*50, "info")
        self.log_message(f"总测试次数: {total_tests}", "info")
        self.log_message(f"成功次数: {successful_tests}", "success")
        self.log_message(f"失败次数: {total_tests - successful_tests}", "error")
        self.log_message(f"成功率: {success_rate:.1f}%", "info")
        self.log_message(f"平均相似度: {avg_similarity:.3f}", "info")
        self.log_message(f"最高相似度: {best_result['similarity']:.3f} ({best_result['timestamp']})", "success")
        self.log_message(f"最低相似度: {worst_result['similarity']:.3f} ({worst_result['timestamp']})", "warning")

        # 提供建议
        if success_rate < 50:
            self.log_message("\n💡 建议:", "warning")
            self.log_message("• 成功率较低，考虑重新标记区域", "warning")
            self.log_message("• 或者降低匹配阈值", "warning")
        elif success_rate < 80:
            self.log_message("\n💡 建议:", "info")
            self.log_message(f"• 可以将阈值调整为 {avg_similarity - 0.05:.2f}", "info")
        else:
            self.log_message("\n🎉 测试结果良好！", "success")

    def log_message(self, message, level="info"):
        """记录消息"""
        color_map = {
            "info": "#333333",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#f44336"
        }

        color = color_map.get(level, "#333333")
        formatted_message = f'<span style="color: {color};">{message}</span>'

        self.results_text.append(formatted_message)

        # 滚动到底部
        scrollbar = self.results_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # 处理事件以更新界面
        QApplication.processEvents()


class MainGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.window_controller = GameWindowController()
        self.image_matcher = ImageMatcher()
        self.template_manager = TemplateManager()
        self.game_executor = GameExecutor()
        self.report_generator = ReportGenerator()
        
        # 当前状态
        self.current_template = None
        self.current_screenshot = None
        self.marked_areas = []
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("游戏自动化系统 - 智能模板管理平台")
        self.setGeometry(100, 100, 1300, 800)
        self.setMinimumSize(1000, 800)
        
        # 设置应用程序样式
        self.setStyleSheet(self.get_main_stylesheet())
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧菜单面板
        self.menu_panel = self.create_menu_panel()
        main_layout.addWidget(self.menu_panel)
        
        # 右侧内容区域
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)
        
        # 创建各个页面
        self.create_pages()
        
        # 创建状态栏
        self.create_status_bar()
        
        # 默认显示项目介绍
        self.show_project_intro()
    
    def get_main_stylesheet(self):
        """获取主样式表"""
        return """
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
            }
            QStackedWidget {
                background-color: white;
                border-left: 1px solid #e0e0e0;
            }
        """
    
    def create_menu_panel(self):
        """创建左侧菜单面板"""
        menu_widget = QWidget()
        menu_widget.setFixedWidth(250)
        menu_widget.setStyleSheet("""
            QWidget {
                background-color: #fafafa;
                border-right: 1px solid #e0e0e0;
            }
        """)
        
        layout = QVBoxLayout(menu_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标题区域
        title_widget = QWidget()
        title_widget.setStyleSheet("""
            QWidget {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
            }
        """)
        title_layout = QVBoxLayout(title_widget)
        
        title_label = QLabel("🎮 游戏自动化")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        
        subtitle_label = QLabel("智能模板管理平台")
        subtitle_label.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.8); margin-top: 5px;")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        layout.addWidget(title_widget)
        
        # 菜单按钮组
        self.menu_group = QButtonGroup()
        self.menu_group.setExclusive(True)
        
        # 菜单项
        menu_items = [
            ("项目介绍", "📋", self.show_project_intro),
            ("模板管理", "📁", self.show_template_management),
            ("模板创建", "✨", self.show_template_creator),
            ("操作说明", "📖", self.show_user_guide),
        ]
        
        menu_container = QWidget()
        menu_layout = QVBoxLayout(menu_container)
        menu_layout.setContentsMargins(0, 10, 0, 0)
        menu_layout.setSpacing(2)
        
        for text, icon, callback in menu_items:
            btn = MenuButton(text, icon)
            btn.clicked.connect(callback)
            self.menu_group.addButton(btn)
            menu_layout.addWidget(btn)
        
        menu_layout.addStretch()
        
        # 底部信息
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(20, 10, 20, 20)
        
        version_label = QLabel("版本: Phase 2.0")
        version_label.setStyleSheet("color: #666; font-size: 11px;")
        
        time_label = QLabel(f"更新: {datetime.now().strftime('%Y-%m-%d')}")
        time_label.setStyleSheet("color: #666; font-size: 11px;")
        
        info_layout.addWidget(version_label)
        info_layout.addWidget(time_label)
        
        layout.addWidget(menu_container)
        layout.addWidget(info_widget)
        
        return menu_widget
    
    def create_pages(self):
        """创建各个页面"""
        # 项目介绍页面
        self.intro_page = self.create_intro_page()
        self.content_stack.addWidget(self.intro_page)
        
        # 模板管理页面
        self.management_page = self.create_management_page()
        self.content_stack.addWidget(self.management_page)
        
        # 模板创建页面
        self.creator_page = self.create_creator_page()
        self.content_stack.addWidget(self.creator_page)
        
        # 操作说明页面
        self.guide_page = self.create_guide_page()
        self.content_stack.addWidget(self.guide_page)
    
    def create_intro_page(self):
        """创建项目介绍页面"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
            }
        """)

        # 内容页面
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(30)

        # 标题区域
        title = QLabel("🎮 游戏自动化系统")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #2196F3;
            margin-bottom: 10px;
        """)
        title.setWordWrap(True)

        subtitle = QLabel("基于图像识别的智能游戏自动化解决方案")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 16px;
            color: #666;
            margin-bottom: 20px;
        """)
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # 功能特性网格 - 使用FlowLayout实现自动换行
        features_widget = QWidget()
        features_layout = FlowLayout(features_widget)
        features_layout.setSpacing(15)

        # 功能特性数据
        features = [
            ("🖥️", "可视化模板创建", "拖拽式区域标记，所见即所得的模板创建体验"),
            ("🔍", "智能图像匹配", "4种匹配算法，适应不同场景的图像识别需求"),
            ("📊", "详细执行报告", "HTML格式的可视化报告，全面分析执行结果"),
            ("🎯", "精确坐标转换", "自动处理不同分辨率下的坐标适配问题"),
            ("🧪", "完善测试系统", "多种测试模式，确保模板质量和稳定性"),
            ("⚡", "高效执行引擎", "稳定可靠的自动化执行，支持重试和错误处理")
        ]

        # 创建功能卡片
        for icon, title_text, desc in features:
            card = self.create_feature_card(icon, title_text, desc)
            features_layout.addWidget(card)

        layout.addWidget(features_widget)

        # 底部信息
        version_info = QLabel("版本: Phase 2.0 | 更新时间: 2024-12-17")
        version_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_info.setStyleSheet("""
            font-size: 12px;
            color: #999;
            margin-top: 20px;
        """)

        layout.addWidget(version_info)
        layout.addStretch()

        # 设置滚动区域的内容
        scroll_area.setWidget(page)

        return scroll_area


    
    def create_feature_card(self, icon, title, description):
        """创建功能特性卡片"""
        card = QWidget()
        card.setFixedSize(300, 140)  # 固定大小，确保一致性

        card.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                margin: 5px;
            }
            QWidget:hover {
                border-color: #2196F3;
                background-color: #f8f9ff;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # 图标和标题行
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 32px;")
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #333;
        """)
        title_label.setWordWrap(True)

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # 描述文本
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            font-size: 13px;
            color: #666;
            line-height: 1.4;
        """)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addLayout(header_layout)
        layout.addWidget(desc_label)

        return card

    def create_management_page(self):
        """创建模板管理页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 20)

        # 页面标题
        header_layout = QHBoxLayout()

        title = QLabel("📁 模板管理")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh_templates)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # 模板列表容器
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)

        # 搜索框
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索模板...")
        self.search_edit.textChanged.connect(self.filter_templates)
        self.search_edit.setStyleSheet("""
            QLineEdit {
                padding: 10px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)

        search_layout.addWidget(self.search_edit)
        list_layout.addLayout(search_layout)

        # 模板列表
        self.template_list = QListWidget()
        self.template_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.template_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.template_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.template_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
                padding: 5px;
                outline: none;
            }
            QListWidget::item {
                border: none;
                padding: 0px;
                margin: 5px 0px;
                background-color: transparent;
            }
            QListWidget::item:hover {
                background-color: transparent;
            }
            QListWidget::item:selected {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
        """)

        list_layout.addWidget(self.template_list)

        layout.addWidget(list_container)

        # 操作按钮区域
        button_layout = QHBoxLayout()

        execute_btn = QPushButton("▶️ 执行模板")
        execute_btn.clicked.connect(self.execute_selected_template)
        execute_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)

        report_btn = QPushButton("📊 查看报告")
        report_btn.clicked.connect(self.view_template_reports)
        report_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)

        edit_btn = QPushButton("✏️ 编辑模板")
        edit_btn.clicked.connect(self.edit_selected_template)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)

        delete_btn = QPushButton("🗑️ 删除模板")
        delete_btn.clicked.connect(self.delete_selected_template)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)

        button_layout.addWidget(execute_btn)
        button_layout.addWidget(report_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # 初始加载模板
        self.refresh_templates()

        return page

    def create_creator_page(self):
        """创建模板创建页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)

        # 页面标题
        header_layout = QHBoxLayout()

        title = QLabel("✨ 模板创建工具")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #333; margin-bottom: 15px;")

        # 创建集成的模板创建工具
        self.integrated_creator = IntegratedTemplateCreator(self)

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.integrated_creator.clear_current_template)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)
        layout.addWidget(self.integrated_creator)

        return page

    def create_guide_page(self):
        """创建操作说明页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 20, 30, 20)

        # 页面标题
        title = QLabel("📖 操作说明")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #333; margin-bottom: 20px;")
        layout.addWidget(title)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
            }
        """)

        # 说明内容
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)

        # 添加操作说明内容
        guides = [
            ("🎯 快速开始", [
                "1. 点击左侧菜单的'模板创建'",
                "2. 选择'快速创建'选项卡",
                "3. 填写模板基本信息",
                "4. 点击'截取游戏界面'按钮",
                "5. 用鼠标拖拽选择操作区域",
                "6. 配置操作参数并保存"
            ]),
            ("📁 模板管理", [
                "1. 在'模板管理'页面查看所有模板",
                "2. 选择模板后可以执行、编辑或删除",
                "3. 点击'执行模板'开始自动化任务",
                "4. 点击'查看报告'查看执行结果",
                "5. 支持模板的导入和导出功能"
            ]),
            ("🔧 高级功能", [
                "1. 使用'高级创建'进行复杂模板设计",
                "2. 支持多任务、多步骤的自动化流程",
                "3. 提供4种图像匹配算法选择",
                "4. 支持实时测试和连续测试模式",
                "5. 自动生成详细的HTML执行报告"
            ]),
            ("💡 使用技巧", [
                "1. 标记区域时选择稳定、特征明显的部分",
                "2. 避免标记包含动画或变化内容的区域",
                "3. 在不同光照条件下测试模板稳定性",
                "4. 使用模拟运行模式安全测试模板",
                "5. 定期更新模板以适应游戏界面变化"
            ])
        ]

        for section_title, items in guides:
            section_widget = self.create_guide_section(section_title, items)
            content_layout.addWidget(section_widget)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        return page

    def create_guide_section(self, title, items):
        """创建操作说明章节"""
        section = QWidget()
        section.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 15px;
            }
        """)

        layout = QVBoxLayout(section)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2196F3;
            margin-bottom: 15px;
        """)
        layout.addWidget(title_label)

        for item in items:
            item_label = QLabel(item)
            item_label.setStyleSheet("""
                font-size: 14px;
                color: #333;
                margin-bottom: 8px;
                padding-left: 10px;
            """)
            layout.addWidget(item_label)

        return section



    def create_status_bar(self):
        """创建状态栏"""
        status_bar = self.statusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f5f5f5;
                border-top: 1px solid #e0e0e0;
                padding: 5px;
            }
        """)
        status_bar.showMessage("就绪")

    # 菜单切换方法
    def show_project_intro(self):
        """显示项目介绍"""
        self.content_stack.setCurrentIndex(0)
        self.statusBar().showMessage("项目介绍")

    def show_template_management(self):
        """显示模板管理"""
        self.content_stack.setCurrentIndex(1)
        self.refresh_templates()
        self.statusBar().showMessage("模板管理")

    def show_template_creator(self):
        """显示模板创建"""
        self.content_stack.setCurrentIndex(2)
        self.statusBar().showMessage("模板创建")

    def show_user_guide(self):
        """显示操作说明"""
        self.content_stack.setCurrentIndex(3)
        self.statusBar().showMessage("操作说明")

    # 功能实现方法
    def refresh_templates(self):
        """刷新模板列表"""
        self.template_list.clear()

        try:
            templates = self.template_manager.list_templates()

            if not templates:
                # 创建空状态提示
                empty_widget = self.create_empty_state_widget()
                item = QListWidgetItem()
                item.setSizeHint(QSize(0, 120))
                item.setFlags(Qt.ItemFlag.NoItemFlags)

                self.template_list.addItem(item)
                self.template_list.setItemWidget(item, empty_widget)
                return

            # 存储所有模板数据用于搜索
            self.all_templates = templates

            # 添加模板项
            self.load_template_items(templates)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载模板列表失败: {str(e)}")

    def load_template_items(self, templates):
        """加载模板项到列表"""
        for template in templates:
            item_widget = self.create_template_item(template)
            item = QListWidgetItem()

            # 设置固定高度，解决挤压问题
            item.setSizeHint(QSize(0, 100))
            item.setData(Qt.ItemDataRole.UserRole, template)

            self.template_list.addItem(item)
            self.template_list.setItemWidget(item, item_widget)

    def filter_templates(self, text):
        """过滤模板列表"""
        if not hasattr(self, 'all_templates'):
            return

        # 清空当前列表
        self.template_list.clear()

        if not text.strip():
            # 如果搜索框为空，显示所有模板
            self.load_template_items(self.all_templates)
        else:
            # 过滤模板
            filtered_templates = []
            search_text = text.lower()

            for template in self.all_templates:
                # 在模板名称、游戏名称、文件名中搜索
                if (search_text in template.get('name', '').lower() or
                    search_text in template.get('game_name', '').lower() or
                    search_text in template.get('filename', '').lower()):
                    filtered_templates.append(template)

            if filtered_templates:
                self.load_template_items(filtered_templates)
            else:
                # 显示无结果提示
                no_result_widget = self.create_no_result_widget()
                item = QListWidgetItem()
                item.setSizeHint(QSize(0, 80))
                item.setFlags(Qt.ItemFlag.NoItemFlags)

                self.template_list.addItem(item)
                self.template_list.setItemWidget(item, no_result_widget)

    def create_template_item(self, template):
        """创建模板列表项"""
        widget = QWidget()
        widget.setFixedHeight(90)  # 固定高度
        widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
                margin: 2px;
            }
            QWidget:hover {
                background-color: #f8f9fa;
                border-color: #2196F3;
            }
        """)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)

        # 左侧图标
        icon_label = QLabel("📋")
        icon_label.setStyleSheet("""
            font-size: 24px;
            color: #2196F3;
            background-color: #e3f2fd;
            border-radius: 20px;
            padding: 8px;
            min-width: 40px;
            max-width: 40px;
            min-height: 40px;
            max-height: 40px;
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # 中间信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # 模板名称
        name_label = QLabel(template.get('name', '未知模板'))
        name_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #333;
            margin: 0px;
        """)
        name_label.setWordWrap(False)
        name_label.setMaximumHeight(20)

        # 游戏名称
        game_name = template.get('game_name', '未知游戏')
        game_label = QLabel(f"🎮 {game_name}")
        game_label.setStyleSheet("""
            font-size: 13px;
            color: #666;
            margin: 0px;
        """)
        game_label.setWordWrap(False)
        game_label.setMaximumHeight(18)

        # 详细信息
        details = []
        if 'filename' in template:
            details.append(f"📄 {template['filename']}")
        if 'created_time' in template:
            details.append(f"📅 {template['created_time']}")

        if details:
            detail_text = " • ".join(details)
            detail_label = QLabel(detail_text)
            detail_label.setStyleSheet("""
                font-size: 11px;
                color: #999;
                margin: 0px;
            """)
            detail_label.setWordWrap(False)
            detail_label.setMaximumHeight(16)
        else:
            detail_label = QLabel("")

        info_layout.addWidget(name_label)
        info_layout.addWidget(game_label)
        info_layout.addWidget(detail_label)
        info_layout.addStretch()

        layout.addLayout(info_layout)
        layout.addStretch()

        # 右侧状态和操作区域
        right_layout = QVBoxLayout()
        right_layout.setSpacing(2)

        # 状态指示器
        status_label = QLabel("✅")
        status_label.setStyleSheet("""
            font-size: 18px;
            color: #4CAF50;
        """)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 任务数量（如果有的话）
        task_count = len(template.get('tasks', []))
        if task_count > 0:
            count_label = QLabel(f"{task_count} 个任务")
            count_label.setStyleSheet("""
                font-size: 10px;
                color: #666;
                background-color: #f0f0f0;
                border-radius: 8px;
                padding: 2px 6px;
            """)
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            count_label = QLabel("")

        right_layout.addWidget(status_label)
        right_layout.addWidget(count_label)
        right_layout.addStretch()

        layout.addLayout(right_layout)

        return widget

    def create_empty_state_widget(self):
        """创建空状态提示组件"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 2px dashed #ddd;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("📋")
        icon_label.setStyleSheet("font-size: 32px; color: #ccc;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_label = QLabel("暂无模板")
        text_label.setStyleSheet("font-size: 16px; color: #666; font-weight: bold;")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint_label = QLabel("点击'模板创建'开始制作您的第一个模板")
        hint_label.setStyleSheet("font-size: 12px; color: #999;")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        layout.addWidget(hint_label)

        return widget

    def create_no_result_widget(self):
        """创建无搜索结果提示组件"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 8px;
            }
        """)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)

        icon_label = QLabel("🔍")
        icon_label.setStyleSheet("font-size: 20px;")

        text_label = QLabel("未找到匹配的模板，请尝试其他关键词")
        text_label.setStyleSheet("font-size: 14px; color: #856404;")

        layout.addWidget(icon_label)
        layout.addWidget(text_label)
        layout.addStretch()

        return widget

    def execute_selected_template(self):
        """执行选中的模板"""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择要执行的模板")
            return

        template_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not template_data:
            return

        # 确认执行
        reply = QMessageBox.question(
            self, "确认执行",
            f"确定要执行模板 '{template_data.get('name', '未知模板')}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.run_template_execution(template_data)

    def run_template_execution(self, template_data):
        """运行模板执行"""
        try:
            # 显示执行对话框
            dialog = TemplateExecutionDialog(template_data, self.game_executor, self)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "执行错误", f"模板执行失败: {str(e)}")

    def view_template_reports(self):
        """查看模板报告"""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择模板")
            return

        template_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not template_data:
            return

        # 打开报告查看器
        dialog = ReportViewerDialog(template_data, self)
        dialog.exec()

    def edit_selected_template(self):
        """编辑选中的模板"""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择要编辑的模板")
            return

        template_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not template_data:
            return

        # 启动高级编辑器
        self.launch_advanced_creator(template_data.get('filename'))

    def delete_selected_template(self):
        """删除选中的模板"""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择要删除的模板")
            return

        template_data = current_item.data(Qt.ItemDataRole.UserRole)
        if not template_data:
            return

        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模板 '{template_data.get('name', '未知模板')}' 吗？\n此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 删除模板文件
                if 'filename' in template_data:
                    template_path = os.path.join("templates", template_data['filename'])
                    if os.path.exists(template_path):
                        os.remove(template_path)

                # 刷新列表
                self.refresh_templates()
                QMessageBox.information(self, "成功", "模板已删除")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除模板失败: {str(e)}")

    def take_screenshot(self):
        """截取游戏界面"""
        self.statusBar().showMessage("正在截取游戏界面...")

        try:
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
                self.display_screenshot(screenshot)
                self.statusBar().showMessage("截图成功")
            else:
                QMessageBox.warning(self, "错误", "截图失败")
                self.statusBar().showMessage("截图失败")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"截图时出错: {str(e)}")
            self.statusBar().showMessage("截图失败")

    def display_screenshot(self, screenshot):
        """显示截图"""
        try:
            # 转换为Qt格式
            height, width, channel = screenshot.shape
            bytes_per_line = 3 * width
            q_image = QImage(screenshot.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()

            # 缩放以适应预览区域
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            self.preview_label.setPixmap(scaled_pixmap)

        except Exception as e:
            print(f"显示截图时出错: {e}")

    def launch_creator_wizard(self):
        """启动创建向导"""
        template_name = self.template_name_edit.text().strip()
        game_name = self.game_name_edit.text().strip()

        if not template_name:
            QMessageBox.warning(self, "提示", "请先填写模板名称")
            return

        if not self.current_screenshot is not None:
            QMessageBox.warning(self, "提示", "请先截取游戏界面")
            return

        # 启动创建向导
        wizard = TemplateCreatorWizard(template_name, game_name, self.current_screenshot, self)
        wizard.exec()

    def launch_advanced_creator(self, template_file=None):
        """切换到集成的创建工具"""
        # 切换到模板创建页面
        self.show_template_creator()

        # 如果指定了模板文件，加载它
        if template_file:
            try:
                template_path = os.path.join("templates", template_file)
                if os.path.exists(template_path):
                    template = self.template_manager.load_template(template_path)
                    if template and hasattr(self, 'integrated_creator'):
                        self.integrated_creator.load_template_data(template)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载模板失败: {str(e)}")

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
                template_path = os.path.join("templates", template_file)
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
        reports_dir = "reports"
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
        report_path = os.path.join("reports", report_file)

        if os.path.exists(report_path):
            # 在默认浏览器中打开报告
            import webbrowser
            webbrowser.open(f"file://{os.path.abspath(report_path)}")

class TemplateCreatorWizard(QDialog):
    """模板创建向导"""

    def __init__(self, template_name, game_name, screenshot, parent=None):
        super().__init__(parent)
        self.template_name = template_name
        self.game_name = game_name
        self.screenshot = screenshot
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("模板创建向导")
        self.setModal(True)
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        info_label = QLabel("模板创建向导功能正在开发中...")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("font-size: 18px; color: #666;")

        layout.addWidget(info_label)

        # 临时按钮
        temp_btn = QPushButton("启动完整创建工具")
        temp_btn.clicked.connect(self.launch_full_creator)
        layout.addWidget(temp_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    def launch_full_creator(self):
        """启动完整创建工具"""
        try:
            from template_creator_gui import TemplateCreatorGUI

            self.creator_window = TemplateCreatorGUI()
            self.creator_window.show()
            self.close()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动创建工具失败: {str(e)}")

def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用程序信息
    app.setApplicationName("游戏自动化系统")
    app.setApplicationVersion("Phase 2.0")
    app.setOrganizationName("AutoGame Team")

    # 创建主窗口
    window = MainGUI()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
