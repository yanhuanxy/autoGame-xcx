import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QFormLayout, QComboBox, QDoubleSpinBox, QSpinBox, \
    QCheckBox, QLabel, QHBoxLayout, QTextEdit, QPushButton, QApplication

from autogame_xcx.core.image_matcher import ImageMatcher
from autogame_xcx.platform.window_controller import GameWindowController
from autogame_xcx.ui.theme import C

import cv2


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
        self.current_preview.setStyleSheet(f"border: 1px solid {C.BORDER_STRONG}; background-color: {C.PANEL};")
        self.current_preview.setScaledContents(True)
        self.current_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        current_layout.addWidget(self.current_preview)

        # 参考图像预览
        reference_layout = QVBoxLayout()
        reference_layout.addWidget(QLabel("参考图像:"))
        self.reference_preview = QLabel()
        self.reference_preview.setFixedSize(200, 150)
        self.reference_preview.setStyleSheet(f"border: 1px solid {C.BORDER_STRONG}; background-color: {C.PANEL};")
        self.reference_preview.setScaledContents(True)
        self.reference_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        reference_layout.addWidget(self.reference_preview)

        # 差异图像预览
        diff_layout = QVBoxLayout()
        diff_layout.addWidget(QLabel("差异分析:"))
        self.diff_preview = QLabel()
        self.diff_preview.setFixedSize(200, 150)
        self.diff_preview.setStyleSheet(f"border: 1px solid {C.BORDER_STRONG}; background-color: {C.PANEL};")
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
        self.stats_label.setStyleSheet(f"font-weight: bold; color: {C.TEXT_3};")
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
        self.start_test_btn.setObjectName("PrimaryBtn")
        self.start_test_btn.clicked.connect(self.start_test)

        self.continuous_test_btn = QPushButton("连续测试")
        self.continuous_test_btn.clicked.connect(self.start_continuous_test)

        self.stop_test_btn = QPushButton("停止测试")
        self.stop_test_btn.setObjectName("DangerBtn")
        self.stop_test_btn.clicked.connect(self.stop_test)
        self.stop_test_btn.setEnabled(False)

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
            "info": C.TEXT_2,
            "success": C.GREEN,
            "warning": C.YELLOW,
            "error": C.RED,
        }

        color = color_map.get(level, C.TEXT_2)
        formatted_message = f'<span style="color: {color};">{message}</span>'

        self.results_text.append(formatted_message)

        # 滚动到底部
        scrollbar = self.results_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # 处理事件以更新界面
        QApplication.processEvents()