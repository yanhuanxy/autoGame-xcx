"""操作说明页（设计稿：左 TOC 目录 + 右分章节，mono 序号步骤 + info callout）。"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from autogame_xcx.ui.theme import C, MONO_FAMILIES
from autogame_xcx.ui.widgets import StepItem


class GuidePage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        mono = MONO_FAMILIES[0]
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 左 TOC
        toc = QWidget()
        toc.setFixedWidth(168)
        toc.setStyleSheet(f"background-color: {C.BG}; border-right: 1px solid {C.BORDER};")
        toc_layout = QVBoxLayout(toc)
        toc_layout.setContentsMargins(12, 14, 12, 12)
        toc_layout.setSpacing(2)
        header = QLabel("目录 / CONTENTS")
        header.setStyleSheet(
            f"color: {C.TEXT_4}; font-family: '{mono}'; font-size: 10px; letter-spacing: 1.5px;"
        )
        header.setContentsMargins(8, 0, 8, 6)
        toc_layout.addWidget(header)

        self._toc_group = QButtonGroup(self)
        self._toc_group.setExclusive(True)
        self._body_stack_index: dict[str, int] = {}

        # 右内容
        self.body_stack: QWidget = None  # set below
        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(0)

        sections = self._section_data()
        for idx, (key, title, eyebrow, page_title, steps, callout) in enumerate(sections):
            btn = QPushButton(title)
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _=False, i=idx: self._switch(i))
            self._toc_group.addButton(btn)
            toc_layout.addWidget(btn)
            self._body_layout.addWidget(self._build_section(eyebrow, page_title, steps, callout))
        toc_layout.addStretch()

        self._toc_buttons = self._toc_group.buttons()
        # 包一层滚动
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {C.BG}; border: none; }}")
        # QScrollArea 的 QSS 不覆盖 viewport —— 显式给 viewport 与正文设深色底，
        # 否则明亮标题/暗描述会落在浅色默认 viewport 上（看不清）。
        scroll.viewport().setStyleSheet(f"background-color: {C.BG};")
        self._body.setStyleSheet(f"background-color: {C.BG};")
        scroll.setWidget(self._body)

        root.addWidget(toc)
        root.addWidget(scroll, 1)
        self._switch(0)

    def _switch(self, idx: int) -> None:
        # 隐藏所有 section，显示第 idx 个
        for i in range(self._body_layout.count()):
            item = self._body_layout.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(i == idx)

    def _build_section(
        self, eyebrow: str, title: str, steps: list[tuple[int, str, str]], callout: str | None
    ) -> QWidget:
        mono = MONO_FAMILIES[0]
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(14)

        eb = QLabel(eyebrow)
        eb.setStyleSheet(f"color: {C.ACCENT}; font-family: '{mono}'; font-size: 11px; letter-spacing: 2px;")
        t = QLabel(title)
        t.setStyleSheet(f"color: {C.TEXT}; font-size: 19px; font-weight: 700;")
        layout.addWidget(eb)
        layout.addSpacing(7)
        layout.addWidget(t)
        layout.addSpacing(4)

        for num, head, desc in steps:
            layout.addWidget(StepItem(num, head, desc))

        if callout:
            box = QLabel(callout)
            box.setWordWrap(True)
            box.setStyleSheet(
                f"background-color: {C.PANEL}; border: 1px solid {C.BORDER}; "
                f"border-left: 2px solid {C.ACCENT}; border-radius: 0 8px 8px 0; "
                f"color: {C.TEXT_2}; font-size: 12.5px; padding: 12px 14px;"
            )
            layout.addSpacing(6)
            layout.addWidget(box)

        layout.addStretch()
        return page

    @staticmethod
    def _section_data() -> list[tuple[str, str, str, str, list[tuple[int, str, str]], str | None]]:
        return [
            (
                "toc_intro", "快速开始", "GETTING STARTED", "快速开始 · 六步创建第一个模板",
                [
                    (1, "打开「模板创建」", "点击左侧导航的「模板创建」进入创建工具。"),
                    (2, "填写模板基本信息", "输入模板名称、游戏名称与可选描述。"),
                    (3, "截取游戏界面", "点击「截取游戏界面」按钮抓取当前游戏画面。"),
                    (4, "拖拽框选操作区域", "在截图上用鼠标拖拽，框选需要识别或点击的区域。"),
                    (5, "配置任务与匹配算法", "为每个区域选择匹配算法并编排任务执行顺序。"),
                    (6, "保存并执行", "保存模板，在「模板管理」中点击执行即可运行。"),
                ],
                "提示：可在「模板创建」中先用「测试模板」验证识别效果，确认无误后再保存到模板库。",
            ),
            (
                "toc_mgmt", "模板管理", "TEMPLATE MANAGEMENT", "模板管理 · 执行与维护",
                [
                    (1, "查看模板列表", "在「模板管理」查看所有模板（名称、状态、最近执行）。"),
                    (2, "执行模板", "点击行内 ▶ 执行；运行中可暂停。"),
                    (3, "查看报告", "点击 📊 查看该模板的历史执行报告。"),
                    (4, "编辑 / 删除", "点击 ✎ 编辑或 🗑 删除模板。"),
                ],
                None,
            ),
            (
                "toc_create", "模板创建", "TEMPLATE CREATION", "模板创建 · 区域标记",
                [
                    (1, "截图", "点击「截取游戏界面」抓取当前画面。"),
                    (2, "标记区域", "鼠标拖拽框选，配置操作类型与阈值。"),
                    (3, "测试匹配", "即时测试识别效果，调整阈值。"),
                    (4, "保存", "保存模板与参考图。"),
                ],
                None,
            ),
            (
                "toc_mcp", "MCP 服务", "MCP SERVICE", "MCP 服务 · 远程调用",
                [
                    (1, "启动服务", "在「MCP 服务」页点击启动，默认监听 :8765。"),
                    (2, "客户端接入", "wechat-ilink-bot 通过 MCP 协议连接此端口。"),
                    (3, "调用工具", "tools/list 发现 5 个 tool，按需调用。"),
                ],
                "本项目是 MCP 服务端；客户端（wechat-ilink-bot）侧配置见其 docs/design/mcp-autogame.md。",
            ),
            (
                "toc_faq", "常见问题", "FAQ", "常见问题",
                [
                    (1, "找不到微信窗口", "确保微信 PC 客户端已启动并显示游戏界面。"),
                    (2, "匹配失败", "降低阈值或重新标记更清晰的区域；避免动画区域。"),
                    (3, "坐标不准", "确认截图时游戏界面完整显示，注意 DPI 缩放。"),
                ],
                None,
            ),
        ]
