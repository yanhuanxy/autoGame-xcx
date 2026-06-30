---
name: add-template-page
description: 按 wechat-link-autogame-xcx 现有约定脚手架新增一个主导航页（深色控制台方案 A）。新页需接入侧栏导航 + content_stack + 控制器 + 契约测试，保持索引顺序。
---

# /add-template-page —— 新增主导航页脚手架

按既有 5 页模式（intro/management/creator/guide/mcp）加第 6 页。**必须同步改契约测试**，否则破坏导航护栏。

## 步骤（顺序固定）

1. **建页文件** `src/autogame_xcx/ui/pages/<name>_page.py`：
   ```python
   from __future__ import annotations
   from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
   from autogame_xcx.ui.theme import C

   class <Name>Page(QWidget):
       def __init__(self, parent: QWidget | None = None) -> None:
           super().__init__(parent)
           lay = QVBoxLayout(self)
           lay.setContentsMargins(20, 18, 20, 20)
           lay.addWidget(QLabel("<标题>"))  # 用 C.TEXT 配色，不内联浅色
   ```
   - 经 `ui/controllers` 访问 core（**禁止** `from autogame_xcx.core...`）。
   - 颜色/字号走 `ui/theme.py` 的 `C` / `MONO_FAMILIES`；图标走 `ui/icons.py`（SVG，非 emoji）。

2. **导出**：加到 `src/autogame_xcx/ui/pages/__init__.py`（import + `__all__`）。

3. **注册导航**（`src/autogame_xcx/ui/main_window.py`）：
   - `create_menu_panel` 的 `menu_items` 末尾追加 `("<名>", "nav.<name>", self.show_<name>)`。
   - `create_pages` 末尾追加 `self.<name>_page = <Name>Page(); self.content_stack.addWidget(...)`。
   - 新增 `def show_<name>(self): self.content_stack.setCurrentIndex(<新索引>); self._console_status.set_page("<名>")`。

4. **图标**：若 `nav.<name>` 不存在，在 `ui/icons.py` 的 `_PATHS` 加一个 stroke SVG。

5. **契约测试**：更新 `tests/unit/test_main_window_contract.py`——`menu_group` 按钮数、`content_stack.count()`、`show_*` 索引参数表全部 +1（新页取下一个索引）。

6. **验证**：
   - `uv run ruff check <新文件> src/autogame_xcx/ui/main_window.py`
   - `QT_QPA_PLATFORM=offscreen uv run pytest tests/unit/test_main_window_contract.py -q` 必须绿
   - `uv run pytest tests/unit -q` 无回归
   - 可选：用 `/run-gui` 截图对照设计稿。

## 红线
- 不得 `print(...)` 做日志（用 `logging.getLogger(__name__)`）。
- 不得在 `ui/pages` 直接 `import core` 或 `pyautogui/win32gui`（经 controller / platform）。
- 单文件 ≤ 500 行。
