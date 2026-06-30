"""模板创建页（设计稿 FRAME D：深色控制台 · 左参数栏 + 右画布）。

本文件= ``IntegratedTemplateCreator``（交互核心）+ ``ClickableLabel``（拖拽选区）+
``CreatorPage``（页壳：PageHeader 工具栏 + creator）。

**FT2 全量重设计**：构造方法（init_ui/create_control_panel/create_*_section/create_screenshot_area）
按 FRAME D 重做——扁平 mono 分区（模板信息/任务流程/标记区域/全局设置）+ 右画布（标题栏 +
截图区 + 提示条）+ 顶部工具栏（截图/保存/测试）。

**全部 action 方法逐字保留**（take_screenshot / display_screenshot / on_area_selected /
convert_to_original_coordinates / add_marked_area / update_areas_list / save_reference_image /
add_task / remove_task / edit_selected_area / test_selected_area / delete_selected_area /
save_template / test_template / clear_current_template / load_template_data）；
仅 ``draw_area_markers`` 把标记色改为按索引交替 #4493f8 / #a371f7（设计稿多色标记）。

为保逻辑不变，tasks/areas 仍用 QListWidget（深色紧凑 item 样式近似设计稿行）；toolbar 的
保存/测试按钮经 CreatorPage 注入到 creator.save_btn / test_btn 属性（action 方法 setEnabled 依赖）。
"""
from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from autogame_xcx.ui import icons
from autogame_xcx.ui.dialogs.area_config_dialog import AreaConfigDialog
from autogame_xcx.ui.theme import MONO_FAMILIES, C
from autogame_xcx.ui.widgets import PageHeader

logger = logging.getLogger(__name__)
_MONO = MONO_FAMILIES[0]

# 区域标记交替色（设计稿 FRAME D：蓝 / 紫）
_MARK_COLORS = [C.ACCENT, C.PURPLE]

# 本页局部 QSS —— 参数栏输入控件 + 任务/区域紧凑行 + 画布容器
_CREATOR_QSS = f"""
QScrollArea {{ background: transparent; border: none; }}
QLineEdit {{
    background-color: {C.STATUSBAR_BG}; color: {C.TEXT};
    border: 1px solid {C.BORDER_STRONG}; border-radius: 6px; padding: 6px 10px;
}}
QLineEdit:focus {{ border-color: {C.ACCENT}; }}
QTextEdit {{
    background-color: {C.STATUSBAR_BG}; color: {C.TEXT};
    border: 1px solid {C.BORDER_STRONG}; border-radius: 6px; padding: 6px;
}}
QSpinBox {{
    background-color: {C.STATUSBAR_BG}; color: {C.TEXT};
    border: 1px solid {C.BORDER_STRONG}; border-radius: 6px; padding: 4px 8px;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 16px; border: none; background: transparent; }}
QSpinBox::up-arrow {{ width:0;height:0;border-left:4px solid transparent;
    border-right:4px solid transparent;border-bottom:5px solid {C.TEXT_4}; }}
QSpinBox::down-arrow {{ width:0;height:0;border-left:4px solid transparent;
    border-right:4px solid transparent;border-top:5px solid {C.TEXT_4}; }}
QListWidget {{ background-color: transparent; border: none; outline: 0; }}
QListWidget::item {{
    color: {C.TEXT_2}; padding: 7px 9px; margin-bottom: 5px;
    border: 1px solid {C.BORDER}; border-radius: 6px; background-color: {C.PANEL};
}}
QListWidget::item:selected {{ background-color: {C.ACCENT_SOFT}; color: {C.TEXT}; }}
QPushButton#DangerBtn {{ background-color: {C.RED_BG}; color: #fff; border: none; font-weight: 500; }}
QPushButton#DangerBtn:hover {{ background-color: {C.RED}; }}
QWidget#CreatorCanvasScroll {{
    background-color: #0a1a26; border: 1px solid {C.BORDER_STRONG}; border-radius: 8px;
}}
"""


class IntegratedTemplateCreator(QWidget):
    """集成的模板创建工具（FT2 按 FRAME D 重设计外观，逻辑不变）。"""

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.controller = controller
        # core 单件经控制器注入（页面不直接 import core）
        self.window_controller = controller.window_controller
        self.template_manager = controller.template_manager

        # 当前状态
        self.current_screenshot = None
        self.current_template = None
        self.marked_areas = []
        self.current_task = None

        # 保存/测试按钮由 CreatorPage 工具栏注入（action 方法 setEnabled 依赖）
        self.save_btn = None
        self.test_btn = None

        self.init_ui()

    # ==================== 构造（FT2 重设计） ====================

    def init_ui(self):
        """左参数栏 320px | 右画布。"""
        self.setStyleSheet(_CREATOR_QSS)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.control_panel = self.create_control_panel()
        layout.addWidget(self.control_panel)

        self.screenshot_area = self.create_screenshot_area()
        layout.addWidget(self.screenshot_area, stretch=1)

    def create_control_panel(self):
        """左侧参数栏：320px，扁平 mono 分区，滚动。"""
        panel = QWidget()
        panel.setFixedWidth(320)
        panel.setStyleSheet(f"QWidget {{ border-right: 1px solid {C.BORDER}; }}")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(18)

        layout.addWidget(self._section_info())
        layout.addWidget(self._section_tasks())
        layout.addWidget(self._section_regions())
        layout.addWidget(self._section_config())
        layout.addStretch()

        scroll.setWidget(content)
        outer = QVBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return panel

    @staticmethod
    def _eyebrow(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {C.TEXT_4}; font-family: '{_MONO}'; font-size: 10px; letter-spacing: 1.5px;"
        )
        return lbl

    def _labeled(self, text: str, widget: QWidget) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C.TEXT_3}; font-size: 11px;")
        lay.addWidget(lbl)
        lay.addWidget(widget)
        return wrap

    def _section_info(self) -> QWidget:
        """模板信息 / INFO：名称 / 游戏 / 描述。"""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(9)
        lay.addWidget(self._eyebrow("模板信息 / INFO"))

        self.template_name_edit = QLineEdit()
        self.template_name_edit.setPlaceholderText("例如：每日签到模板")
        self.template_name_edit.setFixedHeight(32)
        lay.addWidget(self._labeled("模板名称", self.template_name_edit))

        self.game_name_edit = QLineEdit()
        self.game_name_edit.setPlaceholderText("例如：开心消消乐")
        self.game_name_edit.setFixedHeight(32)
        lay.addWidget(self._labeled("游戏名称", self.game_name_edit))

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("模板描述（可选）")
        self.description_edit.setFixedHeight(54)
        lay.addWidget(self._labeled("描述", self.description_edit))
        return w

    def _section_tasks(self) -> QWidget:
        """任务流程 / TASKS：任务列表 + 添加/删除。"""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(9)
        lay.addWidget(self._eyebrow("任务流程 / TASKS"))

        self.tasks_list = QListWidget()
        self.tasks_list.setMinimumHeight(110)
        self.tasks_list.setMaximumHeight(200)
        lay.addWidget(self.tasks_list)

        buttons = QHBoxLayout()
        buttons.setSpacing(7)
        add_task_btn = QPushButton("添加任务")
        add_task_btn.setIcon(icons.icon("plus", C.TEXT_4, 13))
        add_task_btn.clicked.connect(self.add_task)
        remove_task_btn = QPushButton("删除")
        remove_task_btn.setObjectName("DangerBtn")
        remove_task_btn.clicked.connect(self.remove_task)
        buttons.addWidget(add_task_btn, stretch=1)
        buttons.addWidget(remove_task_btn)
        lay.addLayout(buttons)
        return w

    def _section_regions(self) -> QWidget:
        """标记区域 / REGIONS：区域列表（编辑/测试/删除由画布/行内操作）。"""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(9)
        lay.addWidget(self._eyebrow("标记区域 / REGIONS"))

        self.areas_list = QListWidget()
        self.areas_list.setMinimumHeight(110)
        self.areas_list.setMaximumHeight(200)
        lay.addWidget(self.areas_list)

        buttons = QHBoxLayout()
        buttons.setSpacing(7)
        edit_area_btn = QPushButton("编辑")
        edit_area_btn.clicked.connect(self.edit_selected_area)
        test_area_btn = QPushButton("测试")
        test_area_btn.clicked.connect(self.test_selected_area)
        delete_area_btn = QPushButton("删除")
        delete_area_btn.setObjectName("DangerBtn")
        delete_area_btn.clicked.connect(self.delete_selected_area)
        for b in (edit_area_btn, test_area_btn, delete_area_btn):
            buttons.addWidget(b, stretch=1)
        lay.addLayout(buttons)
        return w

    def _section_config(self) -> QWidget:
        """全局设置 / CONFIG：最大重试 + 步骤延迟。"""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(9)
        lay.addWidget(self._eyebrow("全局设置 / CONFIG"))

        row = QHBoxLayout()
        row.setSpacing(10)

        self.max_retry_spin = QSpinBox()
        self.max_retry_spin.setRange(1, 10)
        self.max_retry_spin.setValue(3)
        self.step_delay_spin = QSpinBox()
        self.step_delay_spin.setRange(100, 10000)
        self.step_delay_spin.setValue(1000)
        self.step_delay_spin.setSuffix(" ms")

        row.addWidget(self._labeled("最大重试", self.max_retry_spin), stretch=1)
        row.addWidget(self._labeled("步骤延迟", self.step_delay_spin), stretch=1)
        lay.addLayout(row)
        return w

    def create_screenshot_area(self):
        """右画布：标题栏 + 截图区（ClickableLabel） + 提示条。"""
        area = QWidget()
        area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(area)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # 标题栏：图标 + 文字
        head = QHBoxLayout()
        head.setSpacing(8)
        ic = QLabel()
        ic.setPixmap(icons.pixmap("card.monitor", C.LINK, 15))
        title = QLabel("游戏界面截图与区域标记")
        title.setStyleSheet(f"color: {C.TEXT_2}; font-size: 13px;")
        head.addWidget(ic)
        head.addWidget(title)
        head.addStretch()
        layout.addLayout(head)

        # 截图区（滚动 + ClickableLabel）
        scroll_area = QScrollArea()
        scroll_area.setObjectName("CreatorCanvasScroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll_area.setMinimumSize(400, 300)

        self.screenshot_label = ClickableLabel()
        self.screenshot_label.setMinimumSize(400, 300)
        self.screenshot_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screenshot_label.setText("点击 '截取游戏界面' 开始创建模板")
        self.screenshot_label.setStyleSheet(
            f"color: {C.TEXT_4}; font-family: '{_MONO}'; font-size: 11px; "
            f"background: transparent; border: none;"
        )
        self.screenshot_label.setScaledContents(False)
        scroll_area.setWidget(self.screenshot_label)

        # 连接鼠标拖拽事件
        self.screenshot_label.area_selected.connect(self.on_area_selected)

        layout.addWidget(scroll_area, stretch=1)

        # 底部提示条
        tip = QWidget()
        tip.setStyleSheet(
            f"QWidget {{ border: 1px solid {C.BORDER}; border-radius: 6px; "
            f"background-color: {C.PANEL}; }}"
        )
        tip_lay = QHBoxLayout(tip)
        tip_lay.setContentsMargins(12, 8, 12, 8)
        tip_lay.setSpacing(8)
        bulb = QLabel()
        bulb.setPixmap(icons.pixmap("bulb", C.YELLOW, 14))
        tip_txt = QLabel("提示：截图后可用鼠标拖拽框选操作区域，松开即生成标记。")
        tip_txt.setStyleSheet(f"color: {C.TEXT_3}; font-size: 12px;")
        tip_txt.setWordWrap(True)
        tip_lay.addWidget(bulb)
        tip_lay.addWidget(tip_txt, stretch=1)
        layout.addWidget(tip)

        return area

    # ==================== 功能实现方法（逐字保留，仅 draw_area_markers 改交替色） ====================

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

        except Exception:
            logger.exception("截图时出错")
            QMessageBox.critical(self, "错误", "截图时出错，详见日志")

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

            logger.debug("截图显示: 原始尺寸 %sx%s, 显示尺寸 %sx%s",
                         width, height, pixmap.width(), pixmap.height())

        except Exception:
            logger.exception("显示截图时出错")

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
            # 保存参考图像
            self.save_reference_image(area_data, area_data['name'])
            area_data['reference_image'] = f"{area_data['name']}.png"
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
        """在截图上绘制区域标记 - 1:1坐标对应；按索引交替蓝/紫（设计稿 FRAME D）。"""
        if self.current_screenshot is None:
            return

        try:
            # 重新加载原始截图
            height, width, channel = self.current_screenshot.shape
            bytes_per_line = 3 * width
            q_image = QImage(
                self.current_screenshot.data, width, height, bytes_per_line, QImage.Format.Format_RGB888
            ).rgbSwapped()
            pixmap = QPixmap.fromImage(q_image)

            painter = QPainter(pixmap)

            # 绘制每个标记区域 - 直接使用原始坐标，颜色按索引交替
            for i, area in enumerate(self.marked_areas):
                hexc = _MARK_COLORS[i % len(_MARK_COLORS)]
                stroke = QColor(hexc)
                fill = QColor(hexc)
                fill.setAlpha(40)

                x = area['x']
                y = area['y']
                w = area['width']
                h = area['height']

                # 矩形边框 + 半透明填充
                painter.setPen(QPen(stroke, 3))
                painter.setBrush(QBrush(fill))
                painter.drawRect(x, y, w, h)

                # 序号背景圆圈
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(stroke))
                painter.drawEllipse(x + 5, y + 5, 20, 20)

                # 序号文字
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.drawText(x + 10, y + 20, str(i + 1))

            painter.end()
            self.screenshot_label.setPixmap(pixmap)

            logger.debug("绘制了 %s 个区域标记", len(self.marked_areas))

        except Exception:
            logger.exception("绘制区域标记时出错")

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
                # 如果名称改变了，需要重新保存参考图像
                if updated_data['name'] != area_data['name']:
                    self.save_reference_image(area_data['user_marked_area'], updated_data['name'])
                    updated_data['reference_image'] = f"{updated_data['name']}.png"

                self.marked_areas[current_row] = updated_data
                self.update_areas_list()
                self.draw_area_markers()

    def test_selected_area(self):
        """测试选中的区域"""
        current_row = self.areas_list.currentRow()
        if current_row >= 0 and current_row < len(self.marked_areas):
            area_data = self.marked_areas[current_row]

            area_data['user_marked_area'] = {
                    'x': area_data['x'],
                    'y': area_data['y'],
                    'width': area_data['width'],
                    'height': area_data['height']
                }
            if self.current_screenshot is None:
                QMessageBox.warning(self, "提示", "请先截取游戏界面")
                return

            # 创建测试对话框
            from autogame_xcx.ui.dialogs.area_test_dialog import AreaTestDialog
            dialog = AreaTestDialog(area_data, self.current_screenshot, self)
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
                        {'x': area_data['x'],
                         'y': area_data['y'],
                         'width': area_data['width'],
                         'height': area_data['height']},
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
                        {'x': area_data['x'],
                         'y': area_data['y'],
                         'width': area_data['width'],
                         'height': area_data['height']},
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

        except Exception:
            logger.exception("保存模板时出错")
            QMessageBox.critical(self, "错误", "保存模板时出错，详见日志")

    def test_template(self):
        """测试模板"""
        if not self.current_template:
            # 先保存当前模板
            self.save_template()
            if not self.current_template:
                return

        # 创建模板测试对话框
        from dialog.template_test_dialog import TemplateTestDialog
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
        self.current_template = None

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

        except Exception:
            logger.exception("加载模板数据时出错")
            QMessageBox.critical(self, "错误", "加载模板数据时出错，详见日志")


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
            painter.setPen(QPen(QColor(C.ACCENT), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(68, 147, 248, 50)))

            # 绘制选择矩形
            x1, y1 = self.start_point.x(), self.start_point.y()
            x2, y2 = self.end_point.x(), self.end_point.y()

            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)

            painter.drawRect(x, y, width, height)


class CreatorPage(QWidget):
    """模板创建主导航页：PageHeader 工具栏（截图/保存/测试）+ IntegratedTemplateCreator。"""

    def __init__(self, main_gui, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.creator = IntegratedTemplateCreator(controller=main_gui.controller, parent=main_gui)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 头部条 + 工具栏（截图/保存/测试）
        header = PageHeader("nav.creator", "模板创建工具")
        screenshot_btn = header.add_action("截取游戏界面", "camera", primary=True)
        screenshot_btn.clicked.connect(self.creator.take_screenshot)
        save_btn = header.add_action("保存", "save")
        save_btn.setEnabled(False)
        save_btn.clicked.connect(self.creator.save_template)
        test_btn = header.add_action("测试", "flask")
        test_btn.setEnabled(False)
        test_btn.clicked.connect(self.creator.test_template)
        # 注入到 creator（action 方法 setEnabled 依赖）
        self.creator.save_btn = save_btn
        self.creator.test_btn = test_btn

        layout.addWidget(header)
        layout.addWidget(self.creator, stretch=1)
