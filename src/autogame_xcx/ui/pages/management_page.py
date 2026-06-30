"""模板管理页（设计稿 FRAME E：深色控制台 · 紧凑表格）。

表格 6 列：模板名称 / 游戏 / 任务(mono) / 状态(色点) / 最近执行(mono) / 操作(4 SVG 图标)。
core 对象经 ``self._main``（MainGUI → AppController）；跨页（新建/编辑）走 ``self._main``。
数据/操作逻辑（refresh/filter/execute/report/edit/delete）保留，仅渲染层按设计稿重做。

⚠️ 数据局限：``list_templates`` 只返回元数据（无运行态/最近执行时间），故：
- 状态列恒为「就绪」(绿)；「运行中/错误」需执行器状态追踪（不在本 pass 范围）。
- 「最近执行」列暂用 created_time 近似（无 last-exec 字段）。
"""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from autogame_xcx.ui import icons
from autogame_xcx.ui.dialogs.report_viewer_dialog import ReportViewerDialog
from autogame_xcx.ui.dialogs.template_execution_dialog import TemplateExecutionDialog
from autogame_xcx.ui.theme import MONO_FAMILIES, C, mono_font
from autogame_xcx.ui.widgets import PageHeader

_MONO = MONO_FAMILIES[0]
_MONO_11 = mono_font(11)
_MONO_12 = mono_font(12)

# 本页局部 QSS —— 表头 mono letter-spacing、表框、行内图标按钮 hover
_MGMT_QSS = f"""
QTableWidget#TemplateTable {{
    background-color: {C.BG}; border: 1px solid {C.BORDER}; border-radius: 8px;
    gridline-color: transparent; outline: 0;
}}
QTableWidget#TemplateTable::item {{
    padding: 6px 10px; border-bottom: 1px solid {C.PANEL};
}}
QHeaderView::section {{
    background-color: {C.PANEL}; color: {C.TEXT_4}; border: none;
    border-bottom: 1px solid {C.BORDER}; padding: 9px 16px;
    font-family: '{_MONO}'; font-size: 10px; letter-spacing: 1px;
}}
QTableCornerButton::section {{ background-color: {C.PANEL}; border: none; }}
QPushButton#IconBtn {{ border: none; background: transparent; border-radius: 5px; }}
QPushButton#IconBtn:hover {{ background-color: {C.PANEL}; }}
"""


class ManagementPage(QWidget):
    """模板管理主导航页（深色控制台 · 表格）。"""

    def __init__(self, main_gui, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._main = main_gui
        self.all_templates: list = []
        self.setStyleSheet(_MGMT_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 头部条
        self._header = PageHeader("nav.management", "模板管理")
        self._header.add_action("刷新", "refresh").clicked.connect(self.refresh_templates)
        root.addWidget(self._header)

        # 内容区（toolbar + 表格 stack）
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(14)
        cl.addLayout(self._build_toolbar())

        self._stack = QStackedWidget()
        self.template_table = self._build_table()
        self._empty = self.create_empty_state_widget()
        self._no_result = self.create_no_result_widget()
        self._stack.addWidget(self.template_table)
        self._stack.addWidget(self._empty)
        self._stack.addWidget(self._no_result)
        cl.addWidget(self._stack, stretch=1)
        root.addWidget(content, stretch=1)

        # 初始加载
        self.refresh_templates()

    # -------------------- UI 构造 --------------------

    def _build_toolbar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)

        # 搜索框（icon + lineedit，#010409 底 #30363d 边）
        sw = QWidget()
        sw.setObjectName("SearchField")
        sw.setFixedHeight(34)
        sw.setStyleSheet(
            f"QWidget#SearchField {{ border: 1px solid {C.BORDER_STRONG}; "
            f"border-radius: 7px; background-color: {C.STATUSBAR_BG}; }}"
        )
        sl = QHBoxLayout(sw)
        sl.setContentsMargins(12, 0, 12, 0)
        sl.setSpacing(9)
        ic = QLabel()
        ic.setPixmap(icons.pixmap("search", C.TEXT_4, 14))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索模板名称 / 游戏…")
        self.search_edit.textChanged.connect(self.filter_templates)
        self.search_edit.setFrame(False)
        self.search_edit.setStyleSheet("background: transparent; border: none;")
        sl.addWidget(ic)
        sl.addWidget(self.search_edit)
        row.addWidget(sw, stretch=1)

        # 新建模板（主按钮 → 跳模板创建页）
        new_btn = QPushButton("新建模板")
        new_btn.setObjectName("PrimaryBtn")
        new_btn.setIcon(icons.icon("plus", "#ffffff", 14))
        new_btn.setIconSize(QSize(14, 14))
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.clicked.connect(lambda: self._main.launch_advanced_creator())
        row.addWidget(new_btn)
        return row

    def _build_table(self) -> QTableWidget:
        t = QTableWidget()
        t.setObjectName("TemplateTable")
        t.setColumnCount(6)
        t.setHorizontalHeaderLabels(["模板名称", "游戏", "任务", "状态", "最近执行", "操作"])
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        t.setShowGrid(False)
        t.horizontalScrollBar().setEnabled(False)

        hh = t.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        t.setColumnWidth(1, 150)
        t.setColumnWidth(2, 56)
        t.setColumnWidth(3, 96)
        t.setColumnWidth(4, 150)
        t.setColumnWidth(5, 156)
        hh.setStretchLastSection(False)
        hh.setHighlightSections(False)
        return t

    # -------------------- 行渲染 --------------------

    def _add_row(self, template: dict) -> None:
        t = self.template_table
        r = t.rowCount()
        t.insertRow(r)

        # 0 模板名称（#e6edf3 500；UserRole 存 template 供选中类操作）
        name_item = QTableWidgetItem(template.get("name", "未知模板"))
        name_item.setData(Qt.ItemDataRole.UserRole, template)
        name_item.setForeground(QColor(C.TEXT))
        f = name_item.font()
        f.setWeight(QFont.Weight.Medium)
        name_item.setFont(f)
        t.setItem(r, 0, name_item)

        # 1 游戏（#8b949e）
        game_item = QTableWidgetItem(template.get("game_name", "未知游戏"))
        game_item.setForeground(QColor(C.TEXT_3))
        t.setItem(r, 1, game_item)

        # 2 任务数（mono center）
        task_count = len(template.get("tasks", []))
        task_item = QTableWidgetItem(str(task_count) if task_count else "—")
        task_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        task_item.setFont(_MONO_12)
        task_item.setForeground(QColor(C.TEXT_2))
        t.setItem(r, 2, task_item)

        # 3 状态（色点 + 就绪）
        t.setCellWidget(r, 3, self._status_widget())

        # 4 最近执行（mono，暂用 created_time 近似）
        ts_item = QTableWidgetItem(template.get("created_time", ""))
        ts_item.setFont(_MONO_11)
        ts_item.setForeground(QColor(C.TEXT_4))
        t.setItem(r, 4, ts_item)

        # 5 操作（4 个 SVG 图标）
        t.setCellWidget(r, 5, self._actions_widget(template))

        t.setRowHeight(r, 46)

    def _status_widget(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(6)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {C.GREEN}; font-size: 9px;")
        txt = QLabel("就绪")
        txt.setStyleSheet(f"color: {C.GREEN}; font-size: 11.5px;")
        lay.addWidget(dot)
        lay.addWidget(txt)
        lay.addStretch()
        return w

    def _actions_widget(self, template: dict) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(8, 0, 8, 0)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        play = self._icon_btn("play", "执行")
        play.clicked.connect(lambda: self._row_execute(template))
        report = self._icon_btn("card.report", "查看报告")
        report.clicked.connect(lambda: self._row_report(template))
        edit = self._icon_btn("edit", "编辑")
        edit.clicked.connect(lambda: self._row_edit(template))
        delete = self._icon_btn("trash", "删除")
        delete.clicked.connect(lambda: self._row_delete(template))

        for b in (play, report, edit, delete):
            lay.addWidget(b)
        return w

    def _icon_btn(self, icon_name: str, tip: str) -> QPushButton:
        b = QPushButton()
        b.setObjectName("IconBtn")
        b.setIcon(icons.icon(icon_name, C.TEXT_4, 15))
        b.setIconSize(QSize(15, 15))
        b.setFixedSize(30, 30)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setToolTip(tip)
        return b

    # -------------------- 空态 --------------------

    def create_empty_state_widget(self) -> QWidget:
        """空状态（无任何模板）。"""
        w = QWidget()
        w.setStyleSheet(
            f"QWidget {{ background-color: {C.PANEL}; border: 2px dashed {C.BORDER_STRONG}; "
            f"border-radius: 8px; }}"
        )
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(8)
        for text, size, color, weight in (
            ("📋", 32, C.TEXT_4, False),
            ("暂无模板", 15, C.TEXT_3, True),
            ("点击「新建模板」开始制作您的第一个模板", 12, C.TEXT_4, False),
        ):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            style = f"font-size: {size}px; color: {color};"
            if weight:
                style += " font-weight: 600;"
            lbl.setStyleSheet(style)
            lay.addWidget(lbl)
        return w

    def create_no_result_widget(self) -> QWidget:
        """搜索无结果。"""
        w = QWidget()
        w.setStyleSheet(
            f"QWidget {{ background-color: {C.PANEL}; border: 1px solid {C.BORDER}; "
            f"border-radius: 8px; }}"
        )
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(icons.pixmap("search", C.TEXT_4, 18))
        txt = QLabel("未找到匹配的模板，请尝试其他关键词")
        txt.setStyleSheet(f"font-size: 13px; color: {C.TEXT_3};")
        lay.addWidget(ic)
        lay.addWidget(txt)
        lay.addStretch()
        return w

    # -------------------- 数据 / 操作逻辑（保留；渲染改表格） --------------------

    def refresh_templates(self) -> None:
        """刷新模板列表。"""
        try:
            templates = self._main.controller.list_templates()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载模板列表失败: {str(e)}")
            return

        self.all_templates = templates
        self._header.set_count(f"{len(templates)} 个模板" if templates else None)
        self._load_rows(templates)

    def _load_rows(self, templates: list) -> None:
        """把模板列表渲染到表格；空则显空态。"""
        self.template_table.setRowCount(0)
        if not templates:
            self._stack.setCurrentWidget(self._empty)
            return
        self._stack.setCurrentWidget(self.template_table)
        for template in templates:
            self._add_row(template)

    def filter_templates(self, text: str) -> None:
        """按搜索文本过滤。"""
        if not hasattr(self, "all_templates"):
            return
        text = text.strip()
        if not text:
            self._load_rows(self.all_templates)
            return
        search = text.lower()
        filtered = [
            t for t in self.all_templates
            if search in t.get("name", "").lower()
            or search in t.get("game_name", "").lower()
            or search in t.get("filename", "").lower()
        ]
        if filtered:
            self._load_rows(filtered)
        else:
            self.template_table.setRowCount(0)
            self._stack.setCurrentWidget(self._no_result)

    # 行内操作（原 selected_* 方法的逻辑，参数化为接受 template_data）

    def _row_execute(self, template_data: dict) -> None:
        reply = QMessageBox.question(
            self, "确认执行",
            f"确定要执行模板 '{template_data.get('name', '未知模板')}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.run_template_execution(template_data)

    def run_template_execution(self, template_data: dict) -> None:
        try:
            dialog = TemplateExecutionDialog(template_data, self._main.controller.game_executor, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "执行错误", f"模板执行失败: {str(e)}")

    def _row_report(self, template_data: dict) -> None:
        ReportViewerDialog(template_data, self).exec()

    def _row_edit(self, template_data: dict) -> None:
        self._main.launch_advanced_creator(template_data.get("filename"))

    def _row_delete(self, template_data: dict) -> None:
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模板 '{template_data.get('name', '未知模板')}' 吗？\n此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if "filename" in template_data:
                    self._main.controller.delete_template(template_data["filename"])
                self.refresh_templates()
                QMessageBox.information(self, "成功", "模板已删除")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除模板失败: {str(e)}")
