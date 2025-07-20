"""
PyQt6可视化模板创建工具
提供用户友好的图形界面来创建游戏自动化模板
"""
import sys
import os
import cv2
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from window_controller import GameWindowController
from image_matcher import ImageMatcher
from template_manager import TemplateManager
from game_executor import GameExecutor

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

class TemplateTestDialog(QDialog):
    """模板测试对话框"""

    def __init__(self, template_data, parent=None):
        super().__init__(parent)
        self.template_data = template_data
        self.executor = GameExecutor()
        self.test_results = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("模板测试")
        self.setModal(True)
        self.resize(600, 500)

        layout = QVBoxLayout(self)

        # 测试选项
        options_group = QGroupBox("测试选项")
        options_layout = QVBoxLayout(options_group)

        self.test_all_radio = QRadioButton("完整测试 - 执行所有任务")
        self.test_all_radio.setChecked(True)

        self.test_single_radio = QRadioButton("单任务测试 - 仅测试选中任务")

        self.test_match_radio = QRadioButton("匹配测试 - 仅测试图像匹配，不执行操作")

        options_layout.addWidget(self.test_all_radio)
        options_layout.addWidget(self.test_single_radio)
        options_layout.addWidget(self.test_match_radio)

        layout.addWidget(options_group)

        # 任务选择（单任务测试时使用）
        self.task_group = QGroupBox("选择测试任务")
        task_layout = QVBoxLayout(self.task_group)

        self.task_combo = QComboBox()
        for task in self.template_data.get('tasks', []):
            self.task_combo.addItem(task['task_name'], task['task_id'])

        task_layout.addWidget(self.task_combo)
        layout.addWidget(self.task_group)

        # 测试设置
        settings_group = QGroupBox("测试设置")
        settings_layout = QFormLayout(settings_group)

        self.dry_run_check = QCheckBox("模拟运行（不执行实际点击）")
        self.dry_run_check.setChecked(True)

        self.screenshot_check = QCheckBox("保存测试截图")
        self.screenshot_check.setChecked(True)

        self.detailed_log_check = QCheckBox("详细日志输出")
        self.detailed_log_check.setChecked(True)

        settings_layout.addRow(self.dry_run_check)
        settings_layout.addRow(self.screenshot_check)
        settings_layout.addRow(self.detailed_log_check)

        layout.addWidget(settings_group)

        # 测试结果显示区域
        results_group = QGroupBox("测试结果")
        results_layout = QVBoxLayout(results_group)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        results_layout.addWidget(self.results_text)

        layout.addWidget(results_group)

        # 按钮
        button_layout = QHBoxLayout()

        self.start_test_btn = QPushButton("开始测试")
        self.start_test_btn.clicked.connect(self.start_test)
        self.start_test_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")

        self.stop_test_btn = QPushButton("停止测试")
        self.stop_test_btn.clicked.connect(self.stop_test)
        self.stop_test_btn.setEnabled(False)
        self.stop_test_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; }")

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)

        button_layout.addWidget(self.start_test_btn)
        button_layout.addWidget(self.stop_test_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        # 连接信号
        self.test_single_radio.toggled.connect(self.on_test_mode_changed)
        self.on_test_mode_changed()

    def on_test_mode_changed(self):
        """测试模式改变时的处理"""
        self.task_group.setEnabled(self.test_single_radio.isChecked())

    def start_test(self):
        """开始测试"""
        self.start_test_btn.setEnabled(False)
        self.stop_test_btn.setEnabled(True)
        self.results_text.clear()

        try:
            if self.test_all_radio.isChecked():
                self.run_full_test()
            elif self.test_single_radio.isChecked():
                self.run_single_task_test()
            elif self.test_match_radio.isChecked():
                self.run_match_test()

        except Exception as e:
            self.log_result(f"测试异常: {str(e)}", "error")
        finally:
            self.start_test_btn.setEnabled(True)
            self.stop_test_btn.setEnabled(False)

    def stop_test(self):
        """停止测试"""
        self.log_result("用户停止测试", "warning")
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)

    def run_full_test(self):
        """运行完整测试"""
        self.log_result("开始完整模板测试...", "info")

        # 保存临时模板文件
        import tempfile
        import json

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(self.template_data, f, ensure_ascii=False, indent=2)
            temp_template_path = f.name

        try:
            # 设置模拟运行模式
            if self.dry_run_check.isChecked():
                self.executor.dry_run_mode = True

            # 执行模板
            success = self.executor.execute_template(temp_template_path)

            if success:
                self.log_result("✓ 完整测试执行成功", "success")
                self.show_execution_summary()
            else:
                self.log_result("✗ 完整测试执行失败", "error")

        finally:
            # 清理临时文件
            import os
            try:
                os.unlink(temp_template_path)
            except:
                pass

    def run_single_task_test(self):
        """运行单任务测试"""
        selected_task_id = self.task_combo.currentData()
        if not selected_task_id:
            self.log_result("请选择要测试的任务", "warning")
            return

        self.log_result(f"开始测试任务: {self.task_combo.currentText()}", "info")

        # 找到选中的任务
        selected_task = None
        for task in self.template_data.get('tasks', []):
            if task['task_id'] == selected_task_id:
                selected_task = task
                break

        if not selected_task:
            self.log_result("未找到选中的任务", "error")
            return

        # 执行单个任务测试
        self.test_single_task(selected_task)

    def run_match_test(self):
        """运行匹配测试"""
        self.log_result("开始图像匹配测试...", "info")

        # 初始化执行环境
        if not self.executor.initialize_execution_for_test(self.template_data):
            self.log_result("✗ 初始化执行环境失败", "error")
            return

        total_steps = 0
        successful_matches = 0

        for task in self.template_data.get('tasks', []):
            self.log_result(f"\n测试任务: {task['task_name']}", "info")

            for step in task.get('steps', []):
                total_steps += 1
                self.log_result(f"  测试步骤: {step['step_id']}", "info")

                # 执行匹配测试
                match_result = self.test_step_matching(step)
                if match_result['success']:
                    successful_matches += 1
                    self.log_result(f"    ✓ 匹配成功 (相似度: {match_result['similarity']:.3f})", "success")
                else:
                    self.log_result(f"    ✗ 匹配失败 ({match_result['error']})", "error")

        # 显示匹配测试总结
        success_rate = (successful_matches / total_steps * 100) if total_steps > 0 else 0
        self.log_result(f"\n匹配测试完成:", "info")
        self.log_result(f"总步骤数: {total_steps}", "info")
        self.log_result(f"成功匹配: {successful_matches}", "success")
        self.log_result(f"成功率: {success_rate:.1f}%", "info")

    def test_single_task(self, task):
        """测试单个任务"""
        try:
            # 初始化执行环境
            if not self.executor.initialize_execution_for_test(self.template_data):
                self.log_result("✗ 初始化执行环境失败", "error")
                return

            # 设置模拟运行模式
            original_dry_run = getattr(self.executor, 'dry_run_mode', False)
            if self.dry_run_check.isChecked():
                self.executor.dry_run_mode = True

            try:
                # 执行任务
                task_result = self.executor.execute_task(task)

                if task_result['status'] == 'completed':
                    self.log_result(f"✓ 任务 '{task['task_name']}' 执行成功", "success")
                else:
                    self.log_result(f"✗ 任务 '{task['task_name']}' 执行失败", "error")
                    if task_result.get('error_message'):
                        self.log_result(f"  错误: {task_result['error_message']}", "error")

                # 显示步骤详情
                for step_result in task_result.get('steps', []):
                    step_status = "✓" if step_result['success'] else "✗"
                    similarity = step_result.get('similarity_score', 0)
                    self.log_result(f"  {step_status} {step_result['step_id']} (相似度: {similarity:.3f})",
                                  "success" if step_result['success'] else "error")

            finally:
                # 恢复原始设置
                self.executor.dry_run_mode = original_dry_run

        except Exception as e:
            self.log_result(f"任务测试异常: {str(e)}", "error")

    def test_step_matching(self, step):
        """测试单个步骤的图像匹配"""
        try:
            # 获取窗口截图
            screenshot = self.executor.window_controller.capture_window_screenshot()
            if screenshot is None:
                return {'success': False, 'error': '无法截取窗口截图'}

            # 转换坐标
            marked_area = step['user_marked_area']
            converted_area = self.executor.coordinate_converter.convert_coordinates(marked_area)

            # 获取窗口位置
            window_rect = self.executor.window_controller.get_window_rect()
            if not window_rect:
                return {'success': False, 'error': '无法获取窗口位置'}

            # 截取指定区域
            x = converted_area['x']
            y = converted_area['y']
            w = converted_area['width']
            h = converted_area['height']

            if x + w > screenshot.shape[1] or y + h > screenshot.shape[0]:
                return {'success': False, 'error': '区域超出截图范围'}

            current_image = screenshot[y:y+h, x:x+w]

            # 加载参考图像
            template_name = self.template_data['template_info']['name']
            reference_image_path = os.path.join(
                self.executor.template_manager.images_dir,
                template_name,
                step['reference_image']
            )

            reference_image = self.executor.image_matcher.load_reference_image(reference_image_path)
            if reference_image is None:
                return {'success': False, 'error': f'无法加载参考图像: {step["reference_image"]}'}

            # 进行匹配
            threshold = step.get('match_threshold', 0.85)
            is_match, similarity = self.executor.image_matcher.match_images(
                current_image, reference_image, 'hybrid', threshold
            )

            return {
                'success': is_match,
                'similarity': similarity,
                'threshold': threshold,
                'error': f'相似度 {similarity:.3f} 低于阈值 {threshold}' if not is_match else None
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def show_execution_summary(self):
        """显示执行摘要"""
        if hasattr(self.executor, 'execution_report'):
            report = self.executor.execution_report
            summary = report.get('summary', {})

            self.log_result("\n执行摘要:", "info")
            self.log_result(f"总任务数: {summary.get('total_tasks', 0)}", "info")
            self.log_result(f"完成任务: {summary.get('completed', 0)}", "success")
            self.log_result(f"失败任务: {summary.get('failed', 0)}", "error")
            self.log_result(f"成功率: {summary.get('success_rate', '0%')}", "info")

    def log_result(self, message, level="info"):
        """记录测试结果"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 设置颜色
        color_map = {
            "info": "#333333",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#f44336"
        }

        color = color_map.get(level, "#333333")
        formatted_message = f'<span style="color: {color};">[{timestamp}] {message}</span>'

        self.results_text.append(formatted_message)

        # 滚动到底部
        scrollbar = self.results_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # 处理事件以更新界面
        QApplication.processEvents()

class AreaTestDialog(QDialog):
    """区域测试对话框"""

    def __init__(self, area_data, screenshot, parent=None):
        super().__init__(parent)
        self.area_data = area_data
        self.screenshot = screenshot
        self.image_matcher = ImageMatcher()
        self.init_ui()
        self.run_test()

    def init_ui(self):
        self.setWindowTitle(f"测试区域: {self.area_data['name']}")
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout(self)

        # 区域信息
        info_group = QGroupBox("区域信息")
        info_layout = QFormLayout(info_group)

        coords = self.area_data['user_marked_area']
        info_layout.addRow("区域名称:", QLabel(self.area_data['name']))
        info_layout.addRow("操作类型:", QLabel(self.area_data['action_type']))
        info_layout.addRow("坐标位置:", QLabel(f"({coords['x']}, {coords['y']})"))
        info_layout.addRow("区域大小:", QLabel(f"{coords['width']} x {coords['height']}"))
        info_layout.addRow("匹配阈值:", QLabel(f"{self.area_data['match_threshold']:.2f}"))

        layout.addWidget(info_group)

        # 测试结果
        results_group = QGroupBox("测试结果")
        results_layout = QVBoxLayout(results_group)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        results_layout.addWidget(self.results_text)

        layout.addWidget(results_group)

        # 图像预览
        preview_group = QGroupBox("图像预览")
        preview_layout = QHBoxLayout(preview_group)

        # 当前图像
        current_label = QLabel("当前截图:")
        self.current_image_label = QLabel()
        self.current_image_label.setFixedSize(100, 100)
        self.current_image_label.setStyleSheet("border: 1px solid #ccc;")
        self.current_image_label.setScaledContents(True)

        # 参考图像
        reference_label = QLabel("参考图像:")
        self.reference_image_label = QLabel()
        self.reference_image_label.setFixedSize(100, 100)
        self.reference_image_label.setStyleSheet("border: 1px solid #ccc;")
        self.reference_image_label.setScaledContents(True)

        preview_layout.addWidget(current_label)
        preview_layout.addWidget(self.current_image_label)
        preview_layout.addStretch()
        preview_layout.addWidget(reference_label)
        preview_layout.addWidget(self.reference_image_label)

        layout.addWidget(preview_group)

        # 按钮
        button_layout = QHBoxLayout()

        self.retest_btn = QPushButton("重新测试")
        self.retest_btn.clicked.connect(self.run_test)

        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)

        button_layout.addWidget(self.retest_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def run_test(self):
        """运行测试"""
        self.results_text.clear()
        self.log_message("开始区域匹配测试...")

        try:
            # 提取当前区域图像
            coords = self.area_data['user_marked_area']
            x, y, w, h = coords['x'], coords['y'], coords['width'], coords['height']

            if (x + w > self.screenshot.shape[1] or y + h > self.screenshot.shape[0] or
                x < 0 or y < 0):
                self.log_message("❌ 区域坐标超出截图范围", "error")
                return

            current_area_image = self.screenshot[y:y+h, x:x+w]
            self.log_message(f"✓ 成功提取区域图像 ({w}x{h})")

            # 显示当前图像
            self.show_image(current_area_image, self.current_image_label)

            # 加载参考图像
            template_name = self.parent().template_name_edit.text() or "unnamed_template"
            reference_image_path = os.path.join(
                self.parent().template_manager.images_dir,
                template_name,
                self.area_data['reference_image']
            )

            reference_image = self.image_matcher.load_reference_image(reference_image_path)
            if reference_image is None:
                self.log_message(f"❌ 无法加载参考图像: {self.area_data['reference_image']}", "error")
                return

            self.log_message(f"✓ 成功加载参考图像")

            # 显示参考图像
            self.show_image(reference_image, self.reference_image_label)

            # 进行多种算法测试
            threshold = self.area_data['match_threshold']
            algorithms = ['template_matching', 'ssim', 'feature_matching', 'hybrid']

            self.log_message(f"\n使用阈值: {threshold}")
            self.log_message("=" * 40)

            best_score = 0
            best_algorithm = None

            for algorithm in algorithms:
                try:
                    is_match, similarity = self.image_matcher.match_images(
                        current_area_image, reference_image, algorithm, threshold
                    )

                    status = "✓ 通过" if is_match else "✗ 失败"
                    self.log_message(f"{algorithm:18} | {similarity:.3f} | {status}")

                    if similarity > best_score:
                        best_score = similarity
                        best_algorithm = algorithm

                except Exception as e:
                    self.log_message(f"{algorithm:18} | 错误: {str(e)}", "error")

            # 显示最佳结果
            self.log_message("=" * 40)
            if best_algorithm:
                self.log_message(f"最佳算法: {best_algorithm}")
                self.log_message(f"最高相似度: {best_score:.3f}")

                if best_score >= threshold:
                    self.log_message("🎉 测试通过！区域匹配成功", "success")
                else:
                    self.log_message("⚠️  测试失败！相似度低于阈值", "warning")
                    self.log_message(f"建议: 将阈值调整为 {best_score - 0.05:.2f} 或重新标记区域", "info")
            else:
                self.log_message("❌ 所有算法都失败了", "error")

        except Exception as e:
            self.log_message(f"测试异常: {str(e)}", "error")

    def show_image(self, cv_image, label):
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
            print(f"显示图像时出错: {e}")

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
        self.setWindowTitle("游戏自动化模板创建工具 - Phase 2")
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
        self.game_name_edit.setPlaceholderText("例如: 某某小程序游戏")

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
    app.setApplicationName("游戏自动化模板创建工具")
    app.setApplicationVersion("Phase 2")
    app.setOrganizationName("AutoGame Team")

    # 创建主窗口
    window = TemplateCreatorGUI()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
