"""
游戏自动化系统主界面启动器
启动新设计的左侧菜单栏界面
"""
import sys

from PyQt6.QtWidgets import QApplication

from autogame_xcx.ui.main_window import MainGUI


def main():
    """启动主界面"""
    print("正在启动游戏自动化系统主界面...")
    app = QApplication(sys.argv)
    window = MainGUI()
    window.show()
    print("🎉 主界面启动成功！")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
