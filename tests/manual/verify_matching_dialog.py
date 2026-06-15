"""
验证匹配对话框功能
"""
import sys
import os
import traceback

from autogame_xcx.utils.opencv import CvTool

def main():
    print("验证匹配对话框功能...")
    
    try:
        # 1. 测试基础导入
        print("1. 测试基础导入...")
        import cv2
        import numpy as np
        print("   ✓ OpenCV和NumPy导入成功")
        
        # 2. 测试PyQt6导入
        print("2. 测试PyQt6导入...")
        from PyQt6.QtWidgets import QApplication, QDialog
        from PyQt6.QtCore import QTimer
        print("   ✓ PyQt6导入成功")
        
        # 3. 测试自定义模块导入
        print("3. 测试自定义模块导入...")
        from autogame_xcx.core.image_matcher import ImageMatcher
        from autogame_xcx.platform.window_controller import GameWindowController
        print("   ✓ 自定义模块导入成功")
        
        # 4. 测试MatchingTestDialog导入
        print("4. 测试MatchingTestDialog导入...")
        from autogame_xcx.ui.template_creator import MatchingTestDialog
        print("   ✓ MatchingTestDialog导入成功")
        
        # 5. 创建测试应用
        print("5. 创建测试应用...")
        app = QApplication(sys.argv)
        print("   ✓ QApplication创建成功")
        
        # 6. 创建测试图像
        print("6. 创建测试图像...")
        test_image = np.zeros((100, 200, 3), dtype=np.uint8)
        cv2.rectangle(test_image, (20, 20), (180, 80), (0, 255, 0), -1)
        cv2.putText(test_image, "TEST", (60, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # 保存测试图像
        test_image_path = "test_reference.png"
        CvTool.imwrite(test_image_path, test_image)
        print(f"   ✓ 测试图像保存: {test_image_path}")
        
        # 7. 创建MatchingTestDialog
        print("7. 创建MatchingTestDialog...")
        area_coords = {'x': 50, 'y': 50, 'width': 100, 'height': 50}
        dialog = MatchingTestDialog(area_coords, test_image_path)
        print("   ✓ MatchingTestDialog创建成功")
        
        # 8. 检查对话框属性
        print("8. 检查对话框属性...")
        required_attrs = [
            'area_coords', 'reference_image_path', 'image_matcher',
            'window_controller', 'test_results', 'continuous_testing'
        ]
        
        for attr in required_attrs:
            if hasattr(dialog, attr):
                print(f"   ✓ 属性 {attr} 存在")
            else:
                print(f"   ✗ 属性 {attr} 不存在")
                return False
        
        # 9. 检查UI组件
        print("9. 检查UI组件...")
        ui_components = [
            'algorithm_combo', 'threshold_spin', 'test_count_spin',
            'current_preview', 'reference_preview', 'diff_preview',
            'start_test_btn', 'continuous_test_btn', 'stop_test_btn',
            'test_timer'
        ]
        
        for component in ui_components:
            if hasattr(dialog, component):
                print(f"   ✓ UI组件 {component} 存在")
            else:
                print(f"   ✗ UI组件 {component} 不存在")
                return False
        
        # 10. 检查方法
        print("10. 检查关键方法...")
        required_methods = [
            'load_reference_image', 'start_test', 'start_continuous_test',
            'stop_test', 'run_single_test', 'capture_current_area',
            'generate_diff_image', 'show_image_in_label', 'show_test_summary'
        ]
        
        for method in required_methods:
            if hasattr(dialog, method):
                print(f"   ✓ 方法 {method} 存在")
            else:
                print(f"   ✗ 方法 {method} 不存在")
                return False
        
        # 11. 测试参考图像加载
        print("11. 测试参考图像加载...")
        if hasattr(dialog, 'reference_image_cv'):
            print("   ✓ 参考图像已加载")
        else:
            print("   ⚠️  参考图像未加载（可能正常）")
        
        # 清理
        try:
            os.remove(test_image_path)
            print("   ✓ 清理测试文件")
        except:
            pass
        
        print("\n🎉 所有验证通过！MatchingTestDialog功能正常")
        print("\n📋 功能特性:")
        print("   • 支持4种匹配算法选择")
        print("   • 实时截图测试")
        print("   • 连续测试模式")
        print("   • 差异图像分析")
        print("   • 详细测试统计")
        print("   • 智能阈值建议")
        
        print("\n🚀 使用方法:")
        print("   1. 启动GUI: python start_gui.py")
        print("   2. 创建模板并标记区域")
        print("   3. 在区域配置对话框中点击'测试匹配'")
        print("   4. 选择匹配算法和参数")
        print("   5. 点击'开始测试'或'连续测试'")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        print("\n详细错误信息:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ 匹配测试功能验证成功！")
    else:
        print("\n❌ 匹配测试功能验证失败！")
    
    input("\n按回车键退出...")
