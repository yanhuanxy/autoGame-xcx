"""深色控制台主题（方案 A）—— 调色板 / 字体 / QSS 的唯一来源。

权威设计稿：``重设计方案.dc.html``。所有颜色/字号集中于此，UI 控件不内联颜色
（见 ``.claude/rules/ui-conventions.md``）。随页面迁移逐步丰富 QSS。
"""

from __future__ import annotations

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication


class C:  # noqa: N801 — 调色板常量（design 稿方案 A）
    """设计稿调色板。命名对应设计稿语义，勿散落到控件内联样式。"""

    BG = "#0d1117"            # 主背景 / titlebar
    PANEL = "#161b22"         # 面板 / 卡片 / 表头
    PANEL_SOFT = "#11161d"    # 悬停行
    BORDER = "#21262d"        # 细分隔
    BORDER_STRONG = "#30363d" # 输入框/强边
    STATUSBAR_BG = "#010409"  # 底栏最深
    ACCENT = "#4493f8"        # 品牌蓝 / 激活
    ACCENT_SOFT = "rgba(68,147,248,0.14)"  # 激活背景
    ACCENT_SOFT_2 = "rgba(68,147,248,0.12)"
    LINK = "#58a6ff"          # 图标亮 / 链接
    TEXT = "#e6edf3"          # 主文
    TEXT_2 = "#c9d1d9"        # 次文
    TEXT_3 = "#8b949e"        # 三级
    TEXT_4 = "#6e7681"        # 更弱（mono 元信息）
    SEP = "#484f58"           # 分隔符 "|"
    GREEN = "#3fb950"
    RED = "#f85149"
    RED_BG = "#da3633"
    YELLOW = "#d29922"
    PURPLE = "#a371f7"


# 字体族（IBM Plex 优先；离线未安装时回退到系统等价字体）
UI_FAMILIES = ["IBM Plex Sans SC", "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Segoe UI", "Arial"]
MONO_FAMILIES = ["IBM Plex Mono", "Cascadia Mono", "Consolas", "Courier New"]


def ui_font(size: int = 13, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    f = QFont()
    f.setFamilies(UI_FAMILIES)
    f.setPointSize(size)
    f.setWeight(weight)
    return f


def mono_font(size: int = 11) -> QFont:
    f = QFont()
    f.setFamilies(MONO_FAMILIES)
    f.setPointSize(size)
    return f


def apply_theme(app: QApplication) -> None:
    """对 QApplication 应用深色控制台 QSS。"""
    app.setStyleSheet(QSS)


# 完整 QSS —— 随 E1/E2 页面迁移逐步补 page/控件专属规则
QSS = f"""
* {{
    font-family: {UI_FAMILIES[0]}, {', '.join(UI_FAMILIES[1:])};
    color: {C.TEXT_2};
}}
QMainWindow, QWidget#MainGUI {{
    background-color: {C.BG};
}}
QWidget#NavSideBar {{
    background-color: {C.BG};
    border-right: 1px solid {C.BORDER};
}}
QStackedWidget#ContentStack {{
    background-color: {C.BG};
}}
QStatusBar {{
    background-color: {C.STATUSBAR_BG};
    border-top: 1px solid {C.BORDER};
    color: {C.TEXT_3};
    font-family: {MONO_FAMILIES[0]}, {', '.join(MONO_FAMILIES[1:])};
}}
QStatusBar QLabel {{ color: {C.TEXT_3}; }}

/* 滚动条 —— 细、圆角、深色 */
QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {C.BORDER_STRONG}; border-radius: 4px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {C.TEXT_4}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {C.BORDER_STRONG}; border-radius: 4px; min-width: 24px; }}

/* 输入控件 */
QLineEdit {{
    background-color: {C.STATUSBAR_BG}; color: {C.TEXT};
    border: 1px solid {C.BORDER_STRONG}; border-radius: 6px;
    padding: 6px 10px; selection-background-color: {C.ACCENT};
}}
QLineEdit:focus {{ border-color: {C.ACCENT}; }}

/* 按钮 —— 主按钮（objectName=PrimaryBtn）/ 次按钮（默认） */
QPushButton {{
    background-color: transparent; color: {C.TEXT_3};
    border: 1px solid {C.BORDER_STRONG}; border-radius: 6px;
    padding: 6px 13px;
}}
QPushButton:hover {{ border-color: {C.ACCENT}; color: {C.TEXT_2}; }}
QPushButton#PrimaryBtn {{
    background-color: {C.ACCENT}; color: #fff; border: none; font-weight: 500;
}}
QPushButton#PrimaryBtn:hover {{ background-color: {C.LINK}; }}
QPushButton#DangerBtn:hover {{ border-color: {C.RED_BG}; color: {C.RED}; }}

/* 侧栏导航按钮（设计稿：active 态软蓝底 + 左侧蓝条） */
QPushButton#NavButton {{
    text-align: left; padding: 8px 11px; border-radius: 7px;
    border: none; border-left: 2px solid transparent;
    background: transparent; color: {C.TEXT_3}; font-size: 13px;
}}
QPushButton#NavButton:hover {{ background-color: {C.PANEL}; color: {C.TEXT_2}; }}
QPushButton#NavButton:checked {{
    background-color: {C.ACCENT_SOFT}; color: {C.TEXT}; border-left: 2px solid {C.ACCENT};
}}

/* 卡片 / 面板容器 */
QFrame#Card, QWidget#Card {{
    background-color: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 8px;
}}
QFrame#Card:hover {{ border-color: {C.BORDER_STRONG}; }}

/* 页面标题等 */
QLabel#Eyebrow {{
    color: {C.ACCENT}; font-family: {MONO_FAMILIES[0]}, {', '.join(MONO_FAMILIES[1:])};
}}
QLabel#PageTitle {{ color: {C.TEXT}; }}
QLabel#SectionLabel {{
    color: {C.TEXT_4}; font-family: {MONO_FAMILIES[0]}, {', '.join(MONO_FAMILIES[1:])};
}}

/* 列表/表格行 */
QListWidget, QTableWidget {{
    background-color: {C.BG}; color: {C.TEXT_2};
    border: 1px solid {C.BORDER}; border-radius: 8px; outline: 0;
}}
QListWidget::item, QTableWidget::item {{ padding: 8px 10px; border-bottom: 1px solid {C.PANEL}; }}
QListWidget::item:selected, QTableWidget::item:selected {{ background-color: {C.ACCENT_SOFT}; color: {C.TEXT}; }}
QHeaderView::section {{
    background-color: {C.PANEL}; color: {C.TEXT_4}; border: none;
    border-bottom: 1px solid {C.BORDER}; padding: 9px 16px;
    font-family: {MONO_FAMILIES[0]}, {', '.join(MONO_FAMILIES[1:])};
}}

QToolTip {{
    background-color: {C.PANEL}; color: {C.TEXT}; border: 1px solid {C.BORDER_STRONG};
}}
"""
