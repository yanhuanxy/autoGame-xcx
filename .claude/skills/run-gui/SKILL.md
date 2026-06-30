---
name: run-gui
description: 启动 GUI 并对 5 个导航页逐一截图存到 data/debug/，用于对照设计稿、排查渲染问题或验证 UI 改动。无显示器时用 offscreen headless 抓图；有显示器时可真实启动。
---

# /run-gui —— GUI 页面截图

## 用途
对照设计稿（`D:\note-yym\工作笔迹\杂记\微信ilink\Qt6 桌面应用重设计\重设计方案.dc.html`）逐页核对，或验证 UI 改动后的实际渲染。

## 步骤

### 1. 无头截图（默认，CI/无显示器）
写入临时脚本（如 `tests/manual/_shoot_pages.py`）并 `uv run` 执行：

```python
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication
from autogame_xcx.ui.theme import apply_theme
from autogame_xcx.ui.main_window import MainGUI

app = QApplication(sys.argv)
apply_theme(app)
w = MainGUI()
out = "data/debug"
os.makedirs(out, exist_ok=True)
pages = [
    (w.show_project_intro, "intro"),
    (w.show_template_management, "management"),
    (w.show_template_creator, "creator"),
    (w.show_user_guide, "guide"),
    (w.show_mcp_server, "mcp"),
]
w.show()
for show, name in pages:
    show()
    app.processEvents()
    w.grab().save(f"{out}/page_{name}.png")
    print("saved", f"{out}/page_{name}.png")
```

截图存 `data/debug/page_<name>.png`（5 张：intro/management/creator/guide/mcp）。

### 2. 真实启动（有显示器、需交互验证）
`uv run python start_main_gui.py`，手动逐页切换观察。

### 3. 对照
用 Read 工具读取 `data/debug/page_*.png` 与设计稿截图并排比对（配色/布局/图标/字号）。

## 注意
- 截图后临时脚本可删（`tests/manual/` 默认不被 pytest 收集，留着也无妨）。
- offscreen 下字体回退到系统字体（IBM Plex 若未离线安装），与真机略有差异——像素级核对以真机为准。
