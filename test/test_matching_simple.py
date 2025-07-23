"""
简单的匹配功能测试脚本
"""
import sys
import os

# 添加src目录到Python路径
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gui')
sys.path.insert(0, src_path)

def test_imports():
    """测试导入"""
    print("测试导入...")
    
    try:
        # 测试基础导入
        import cv2
        import numpy as np
        print("✓ OpenCV和NumPy导入成功")
        
        # 测试PyQt6导入
        from PyQt6.QtWidgets import QApplication, QDialog
        from PyQt6.QtCore import QTimer
        print("✓ PyQt6基础组件导入成功")
        
        # 测试自定义模块导入
        from image_matcher import ImageMatcher
        from window_controller import GameWindowController
        print("✓ 自定义模块导入成功")
        
        # 测试GUI模块导入
        from template_creator_gui import MatchingTestDialog
        print("✓ MatchingTestDialog导入成功")
        
        return True
        
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 其他错误: {e}")
        return False

def test_matching_dialog_creation():
    """测试匹配对话框创建"""
    print("\n测试匹配对话框创建...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from gui.template_creator_gui import MatchingTestDialog
        import numpy as np
        import cv2
        
        # 创建应用程序
        app = QApplication(sys.argv)
        
        # 创建测试数据
        area_coords = {'x': 50, 'y': 50, 'width': 100, 'height': 50}
        
        # 创建临时参考图像
        test_image = np.zeros((100, 200, 3), dtype=np.uint8)
        cv2.rectangle(test_image, (20, 20), (180, 80), (0, 255, 0), -1)
        
        # 保存临时图像
        temp_image_path = "temp_test_image.png"
        CvTool.imwrite(temp_image_path, test_image)
        
        # 创建对话框
        dialog = MatchingTestDialog(area_coords, temp_image_path)
        print("✓ MatchingTestDialog创建成功")
        
        # 检查关键属性
        required_attrs = [
            'area_coords', 'reference_image_path', 'image_matcher',
            'window_controller', 'test_results', 'continuous_testing'
        ]
        
        for attr in required_attrs:
            if hasattr(dialog, attr):
                print(f"✓ 属性 {attr} 存在")
            else:
                print(f"✗ 属性 {attr} 不存在")
                return False
        
        # 检查UI组件
        ui_components = [
            'algorithm_combo', 'threshold_spin', 'test_count_spin',
            'current_preview', 'reference_preview', 'diff_preview',
            'start_test_btn', 'continuous_test_btn', 'stop_test_btn'
        ]
        
        for component in ui_components:
            if hasattr(dialog, component):
                print(f"✓ UI组件 {component} 存在")
            else:
                print(f"✗ UI组件 {component} 不存在")
                return False
        
        # 清理临时文件
        try:
            os.remove(temp_image_path)
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"✗ 对话框创建失败: {e}")
        return False

def test_image_matcher():
    """测试图像匹配器"""
    print("\n测试图像匹配器...")
    
    try:
        from gui.core.image_matcher import ImageMatcher
        import numpy as np
        import cv2
        
        matcher = ImageMatcher()
        
        # 创建测试图像
        img1 = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.rectangle(img1, (20, 20), (80, 80), (255, 255, 255), -1)
        
        img2 = img1.copy()
        
        # 测试匹配
        is_match, similarity = matcher.match_images(img1, img2, 'hybrid', 0.8)
        print(f"✓ 图像匹配测试: 匹配={is_match}, 相似度={similarity:.3f}")
        
        if similarity > 0.9:
            print("✓ 相同图像匹配正常")
            return True
        else:
            print("✗ 相同图像匹配异常")
            return False
        
    except Exception as e:
        print(f"✗ 图像匹配器测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🔍 简单匹配功能测试")
    print("=" * 40)
    
    tests = [
        ("导入测试", test_imports),
        ("图像匹配器测试", test_image_matcher),
        ("匹配对话框创建测试", test_matching_dialog_creation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name}: 通过")
                passed += 1
            else:
                print(f"❌ {test_name}: 失败")
        except Exception as e:
            print(f"❌ {test_name}: 异常 - {e}")
    
    print("\n" + "=" * 40)
    print(f"测试结果: {passed}/{total} 项通过")
    
    if passed == total:
        print("🎉 匹配功能基础测试通过！")
        print("\n可以使用的功能:")
        print("• 在区域配置对话框中点击'测试匹配'")
        print("• 选择不同的匹配算法")
        print("• 使用连续测试模式")
        print("• 查看差异图像分析")
    else:
        print("⚠️  部分功能存在问题")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
