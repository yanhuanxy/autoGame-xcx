from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QFormLayout, QLabel, QTextEdit, QHBoxLayout, QPushButton

from autogame_xcx.core.image_matcher import ImageMatcher
from autogame_xcx.ui.theme import C

import cv2
import os


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

        coords = self.area_data.get('user_marked_area')

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
        self.current_image_label.setStyleSheet(f"border: 1px solid {C.BORDER_STRONG}; background-color: {C.PANEL};")
        self.current_image_label.setScaledContents(True)

        # 参考图像
        reference_label = QLabel("参考图像:")
        self.reference_image_label = QLabel()
        self.reference_image_label.setFixedSize(100, 100)
        self.reference_image_label.setStyleSheet(f"border: 1px solid {C.BORDER_STRONG}; background-color: {C.PANEL};")
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