"""SVG 图标集 + 着色渲染。

设计稿图标为内联 SVG（24×24 viewBox, fill=none, stroke=currentColor, 1.8 round）。
本模块把路径数据集中成字典，按颜色实时渲染成 QPixmap/QIcon（QSvgRenderer），
实现设计稿"currentColor 按状态着色"的效果。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QImage, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

from autogame_xcx.ui.theme import C

# name → SVG 内部路径（viewBox 0 0 24 24，stroke 由 _wrap 注入）
_PATHS: dict[str, str] = {
    # 导航
    "nav.intro": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v5h5"/><path d="M9 13h6M9 17h4"/>',
    "nav.management": '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7l-2-2H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2Z"/>',
    "nav.creator": '<path d="M12 3l1.8 6.2L20 11l-6.2 1.8L12 19l-1.8-6.2L4 11l6.2-1.8Z"/>',
    "nav.guide": '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h5a3 3 0 0 1 3 3 3 3 0 0 1 3-3h5a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-6a2 2 0 0 0-2 2 2 2 0 0 0-2-2Z"/>',
    "nav.mcp": '<path d="M9 2v6M15 2v6M6 8h12v3a6 6 0 0 1-12 0Z"/><path d="M12 17v5"/>',
    # 功能卡
    "card.monitor": '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>',
    "card.match": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    "card.report": '<path d="M3 3v18h18"/><path d="M7 16v-4M12 16V8M17 16v-7"/>',
    "card.target": '<circle cx="12" cy="12" r="9"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/><circle cx="12" cy="12" r="2.2"/>',
    "card.test": '<path d="M9 3h6M10 3v6.5L5 19a1.5 1.5 0 0 0 1.3 2.3h11.4A1.5 1.5 0 0 0 19 19l-5-9.5V3M7.5 15h9"/>',
    "card.engine": '<path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z"/>',
    # 通用动作
    "refresh": '<path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "play": '<path d="M6 4l14 8-14 8Z"/>',
    "pause": '<rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/>',
    "save": '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
    "flask": '<path d="M9 3h6M10 3v6.5L5 19a1.5 1.5 0 0 0 1.3 2.3h11.4A1.5 1.5 0 0 0 19 19l-5-9.5V3M7.5 15h9"/>',
    "camera": '<rect x="2" y="5" width="20" height="15" rx="2"/><path d="m8 5 1.5-2h5L16 5"/><circle cx="12" cy="12.5" r="3.2"/>',
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    "trash": '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-5M12 8h.01"/>',
    "bulb": '<path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7c.6.5 1 1 1 2.3h6c0-1.3.4-1.8 1-2.3A7 7 0 0 0 12 2Z"/>',
    "chevron-down": '<path d="m6 15 6-6 6 6"/>',
    "crosshair": '<path d="M12 2v6M12 16v6M2 12h6M16 12h6"/><circle cx="12" cy="12" r="3"/>',
    "dot": '<circle cx="12" cy="12" r="9"/>',
    "dots-v": '<circle cx="12" cy="5" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="12" cy="19" r="1.4"/>',
    # 窗口控制
    "win.min": '<path d="M5 12h14"/>',
    "win.max": '<rect x="5" y="5" width="14" height="14" rx="2"/>',
    "win.close": '<path d="M6 6l12 12M18 6 6 18"/>',
    # MCP
    "logo": '<circle cx="12" cy="12" r="9"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/><circle cx="12" cy="12" r="2.2"/>',
}


def _wrap(inner: str, color: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{inner}</svg>'
    )


def _renderer(name: str, color: str) -> QSvgRenderer:
    return QSvgRenderer(_wrap(_PATHS[name], color).encode("utf-8"))


def pixmap(name: str, color: str = C.TEXT_3, size: int = 16) -> QPixmap:
    """按颜色渲染图标为透明背景 QPixmap。"""
    r = _renderer(name, color)
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    r.render(p)
    p.end()
    return QPixmap.fromImage(img)


def icon(name: str, color: str = C.TEXT_3, size: int = 16) -> QIcon:
    return QIcon(pixmap(name, color, size))
