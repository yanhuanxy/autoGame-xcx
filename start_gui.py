"""
游戏自动化系统GUI启动器
快速启动PyQt6图形界面模板创建工具
"""
import sys

from PyQt6.QtWidgets import QApplication

from autogame_xcx.ui.template_creator import TemplateCreatorGUI


def main():
    """启动GUI工具"""
    print("正在启动游戏自动化模板创建工具...")
    app = QApplication(sys.argv)
    window = TemplateCreatorGUI()
    window.show()
    print("✓ 启动GUI界面...")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
