"""
视觉流程自动化系统主界面启动器
启动新设计的左侧菜单栏界面
"""

import ctypes
import logging
import sys

# PyQt6 在 Windows 上默认会调用 SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2)。
# 若进程已被外部（IDE/终端继承、pywin32 等）设置过 DPI awareness，Windows 拒绝 Qt 的调用，
# Qt 会打印 "SetProcessDpiAwarenessContext() failed: 拒绝访问" 警告。
# 此处先预设同一级 DPI awareness——Qt 启动时检测当前级别已满足，跳过自己的调用，警告消失。
if sys.platform == "win32":
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        pass

from PyQt6.QtWidgets import QApplication

from autogame_xcx.ui.main_window import MainGUI
from autogame_xcx.ui.theme import apply_theme


def _shutdown_mcp_server(window: MainGUI) -> None:
    """退出前优雅停止 MCP server（如果用户启动过）。

    幂等：未启动时 request_stop 直接返回。最多等 3s 让 uvicorn 完成 shutdown。
    """
    server = window.mcp_server
    if server.isRunning():
        server.request_stop()
        server.wait(3000)


def main():
    """启动主界面"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    print("正在启动视觉流程自动化系统主界面...")
    app = QApplication(sys.argv)
    apply_theme(app)
    window = MainGUI()
    window.show()

    # app 退出前优雅停止 MCP server thread（用户可能未启动，幂等）
    app.aboutToQuit.connect(lambda: _shutdown_mcp_server(window))

    print("🎉 主界面启动成功！")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
