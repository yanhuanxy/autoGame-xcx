"""GUI 快速启动器（向后兼容入口）。

历史：早期版本的 GUI 入口，现已被 `start_main_gui.py`（集成远程驱动 + DPI 处理）
取代。本文件保留为 thin wrapper，避免外部文档/脚本失效。

推荐使用：`python start_main_gui.py`
"""
from start_main_gui import main


if __name__ == "__main__":
    main()
