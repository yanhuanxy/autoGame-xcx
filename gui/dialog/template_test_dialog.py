import datetime
import os

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QFormLayout, QComboBox, QPushButton, QHBoxLayout, \
    QRadioButton, QCheckBox, QTextEdit, QApplication

from gui.core.game_executor import GameExecutor


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
