"""
游戏自动化系统主界面启动器
启动新设计的左侧菜单栏界面
"""
import sys
import os

# 添加src目录到Python路径
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_path)

def main():
    """启动主界面"""
    try:
        print("正在启动游戏自动化系统主界面...")
        
        # 检查PyQt6是否安装
        try:
            from PyQt6.QtWidgets import QApplication
            print("✓ PyQt6 已安装")
        except ImportError:
            print("✗ PyQt6 未安装，请运行: pip install PyQt6")
            return
        
        # 检查其他依赖
        try:
            import cv2
            import numpy as np
            from PIL import Image
            print("✓ 图像处理库已安装")
        except ImportError as e:
            print(f"✗ 缺少依赖库: {e}")
            print("请运行: pip install -r requirements.txt")
            return
        
        # 启动主界面
        from src.main_gui import MainGUI
        print("✓ 启动主界面...")
        
        app = QApplication(sys.argv)
        window = MainGUI()
        window.show()
        
        print("🎉 主界面启动成功！")
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"启动失败: {e}")
        print("\n故障排除:")
        print("1. 确保已安装所有依赖: pip install -r requirements.txt")
        print("2. 确保Python版本为3.13")
        print("3. 确保在项目根目录运行此脚本")

if __name__ == "__main__":
    main()
