"""
游戏自动化系统主界面启动器
启动新设计的左侧菜单栏界面
"""
import ctypes
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


def main():
    """启动主界面"""
    print("正在启动游戏自动化系统主界面...")
    app = QApplication(sys.argv)
    window = MainGUI()
    window.show()

    # 阶段 2.6：app 退出前优雅清理远程驱动（client.stop + scheduler.stop + JVM shutdown）
    # 幂等；未启动远程驱动时也安全调用
    app.aboutToQuit.connect(window.remote_driver.shutdown)

    print("🎉 主界面启动成功！")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
