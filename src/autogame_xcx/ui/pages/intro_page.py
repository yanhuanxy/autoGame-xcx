"""项目介绍页（设计稿：PROJECT OVERVIEW eyebrow + 标题 + 3×2 FeatureCard 网格）。"""

from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from autogame_xcx.ui.theme import C, MONO_FAMILIES
from autogame_xcx.ui.widgets import FeatureCard


class IntroPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        mono = MONO_FAMILIES[0]
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(0)

        eyebrow = QLabel("PROJECT OVERVIEW")
        eyebrow.setStyleSheet(
            f"color: {C.ACCENT}; font-family: '{mono}'; font-size: 11px; letter-spacing: 2px;"
        )
        title = QLabel("游戏自动化系统")
        title.setStyleSheet(f"color: {C.TEXT}; font-size: 24px; font-weight: 700;")
        subtitle = QLabel("基于图像识别的智能游戏自动化解决方案")
        subtitle.setStyleSheet(f"color: {C.TEXT_3}; font-size: 13px;")

        outer.addWidget(eyebrow)
        outer.addSpacing(9)
        outer.addWidget(title)
        outer.addSpacing(7)
        outer.addWidget(subtitle)
        outer.addSpacing(22)

        features = [
            ("card.monitor", "可视化模板创建", "拖拽式区域标记，所见即所得的模板创建体验"),
            ("card.match", "智能图像匹配", "多种匹配算法，适应不同场景的图像识别需求"),
            ("card.report", "详细执行报告", "HTML 格式的可视化报告，全面分析执行结果"),
            ("card.target", "精确坐标转换", "自动处理不同分辨率下的坐标适配问题"),
            ("card.test", "完善测试系统", "多种测试模式，确保模板质量和稳定性"),
            ("card.engine", "高效执行引擎", "稳定可靠的自动化执行，支持重试和错误处理"),
        ]
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setSpacing(13)
        grid.setContentsMargins(0, 0, 0, 0)
        for i, (icon_name, head, desc) in enumerate(features):
            card = FeatureCard(icon_name, head, desc)
            grid.addWidget(card, i // 3, i % 3)
            grid.setColumnStretch(i % 3, 1)
        outer.addWidget(grid_host)
        outer.addStretch()
