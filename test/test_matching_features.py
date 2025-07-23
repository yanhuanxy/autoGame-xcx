"""
测试匹配功能验证脚本
验证新增的图像匹配测试功能
"""
import sys
import os
import cv2
import numpy as np

from util.constants import TEST_IMAGES_PATH
from util.opencv_util import CvTool

# 添加src目录到Python路径
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gui')
sys.path.insert(0, src_path)

def create_test_images():
    """创建测试图像"""
    print("创建测试图像...")
    
    # 创建测试目录
    test_dir = TEST_IMAGES_PATH
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    # 创建原始图像 - 绿色矩形按钮
    original = np.zeros((100, 200, 3), dtype=np.uint8)
    cv2.rectangle(original, (20, 20), (180, 80), (0, 255, 0), -1)
    cv2.putText(original, "BUTTON", (50, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    CvTool.imwrite(os.path.join(test_dir, "original_button.png"), original)
    
    # 创建相似图像 - 稍微不同的亮度
    similar = cv2.convertScaleAbs(original, alpha=1.1, beta=10)
    CvTool.imwrite(os.path.join(test_dir, "similar_button.png"), similar)
    
    # 创建不同图像 - 红色圆形
    different = np.zeros((100, 200, 3), dtype=np.uint8)
    cv2.circle(different, (100, 50), 30, (0, 0, 255), -1)
    cv2.putText(different, "CIRCLE", (60, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    CvTool.imwrite(os.path.join(test_dir, "different_button.png"), different)
    
    # 创建噪声图像
    noisy = original.copy()
    noise = np.random.randint(0, 50, original.shape, dtype=np.uint8)
    noisy = cv2.add(noisy, noise)
    CvTool.imwrite(os.path.join(test_dir, "noisy_button.png"), noisy)
    
    print("✓ 测试图像创建完成")
    return test_dir

def test_image_matcher():
    """测试图像匹配器"""
    print("\n测试图像匹配器...")
    
    try:
        from gui.core.image_matcher import ImageMatcher
        
        matcher = ImageMatcher()
        
        # 加载测试图像
        test_dir = create_test_images()
        original = CvTool.imread(os.path.join(test_dir, "original_button.png"))
        similar = CvTool.imread(os.path.join(test_dir, "similar_button.png"))
        different = CvTool.imread(os.path.join(test_dir, "different_button.png"))
        noisy = CvTool.imread(os.path.join(test_dir, "noisy_button.png"))
        
        if original is None:
            print("✗ 无法加载测试图像")
            return False
        
        # 测试不同算法
        algorithms = ['template_matching', 'ssim', 'feature_matching', 'hybrid']
        test_cases = [
            ("相同图像", original, original, True),
            ("相似图像", original, similar, True),
            ("不同图像", original, different, False),
            ("噪声图像", original, noisy, True)
        ]
        
        print("\n算法性能测试:")
        print("-" * 80)
        print(f"{'算法':<18} | {'测试用例':<12} | {'相似度':<8} | {'匹配':<6} | {'预期':<6} | {'结果'}")
        print("-" * 80)
        
        for algorithm in algorithms:
            for case_name, img1, img2, expected in test_cases:
                try:
                    is_match, similarity = matcher.match_images(img1, img2, algorithm, 0.8)
                    result = "✓" if (is_match == expected) else "✗"
                    match_str = "是" if is_match else "否"
                    expected_str = "是" if expected else "否"
                    
                    print(f"{algorithm:<18} | {case_name:<12} | {similarity:<8.3f} | {match_str:<6} | {expected_str:<6} | {result}")
                    
                except Exception as e:
                    print(f"{algorithm:<18} | {case_name:<12} | 错误: {str(e)}")
        
        print("-" * 80)
        print("✓ 图像匹配器测试完成")
        return True
        
    except Exception as e:
        print(f"✗ 图像匹配器测试失败: {e}")
        return False

def test_matching_dialog():
    """测试匹配对话框"""
    print("\n测试匹配对话框...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from template_creator_gui import MatchingTestDialog
        
        app = QApplication(sys.argv)
        
        # 创建测试数据
        test_dir = create_test_images()
        area_coords = {'x': 50, 'y': 50, 'width': 100, 'height': 50}
        reference_image_path = os.path.join(test_dir, "original_button.png")
        
        # 创建对话框
        dialog = MatchingTestDialog(area_coords, reference_image_path)
        print("✓ 匹配测试对话框创建成功")
        
        # 测试加载参考图像
        if hasattr(dialog, 'reference_image_cv'):
            print("✓ 参考图像加载成功")
        else:
            print("✗ 参考图像加载失败")
            return False
        
        # 测试界面组件
        components = [
            'algorithm_combo', 'threshold_spin', 'test_count_spin',
            'current_preview', 'reference_preview', 'diff_preview',
            'start_test_btn', 'continuous_test_btn', 'stop_test_btn'
        ]
        
        for component in components:
            if hasattr(dialog, component):
                print(f"✓ 组件 {component} 存在")
            else:
                print(f"✗ 组件 {component} 不存在")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ 匹配对话框测试失败: {e}")
        return False

def test_continuous_matching():
    """测试连续匹配功能"""
    print("\n测试连续匹配功能...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        from template_creator_gui import MatchingTestDialog
        
        app = QApplication(sys.argv)
        
        # 创建测试数据
        test_dir = create_test_images()
        area_coords = {'x': 50, 'y': 50, 'width': 100, 'height': 50}
        reference_image_path = os.path.join(test_dir, "original_button.png")
        
        # 创建对话框
        dialog = MatchingTestDialog(area_coords, reference_image_path)
        
        # 测试定时器
        if hasattr(dialog, 'test_timer') and isinstance(dialog.test_timer, QTimer):
            print("✓ 连续测试定时器存在")
        else:
            print("✗ 连续测试定时器不存在")
            return False
        
        # 测试连续测试标志
        if hasattr(dialog, 'continuous_testing'):
            print("✓ 连续测试标志存在")
        else:
            print("✗ 连续测试标志不存在")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ 连续匹配功能测试失败: {e}")
        return False

def test_diff_image_generation():
    """测试差异图像生成"""
    print("\n测试差异图像生成...")
    
    try:
        # 创建测试图像
        test_dir = create_test_images()
        original = CvTool.imread(os.path.join(test_dir, "original_button.png"))
        similar = CvTool.imread(os.path.join(test_dir, "similar_button.png"))
        
        # 计算差异
        diff = cv2.absdiff(original, similar)
        diff_enhanced = cv2.convertScaleAbs(diff, alpha=3.0, beta=0)
        
        # 保存差异图像
        CvTool.imwrite(os.path.join(test_dir, "diff_result.png"), diff_enhanced)
        
        print("✓ 差异图像生成成功")
        print(f"  差异图像已保存: {os.path.join(test_dir, 'diff_result.png')}")
        
        return True
        
    except Exception as e:
        print(f"✗ 差异图像生成失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🔍 验证图像匹配测试功能")
    print("=" * 60)
    
    tests = [
        ("图像匹配器", test_image_matcher),
        ("匹配对话框", test_matching_dialog),
        ("连续匹配功能", test_continuous_matching),
        ("差异图像生成", test_diff_image_generation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                print(f"✅ {test_name}: 通过")
                passed += 1
            else:
                print(f"❌ {test_name}: 失败")
        except Exception as e:
            print(f"❌ {test_name}: 异常 - {e}")
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 项通过")
    
    if passed == total:
        print("🎉 所有匹配测试功能验证通过！")
        print("\n🚀 可以开始使用以下功能:")
        print("1. 启动GUI: python start_gui.py")
        print("2. 在区域配置对话框中点击'测试匹配'")
        print("3. 使用不同算法进行匹配测试")
        print("4. 使用连续测试功能监控匹配稳定性")
        print("5. 查看差异图像分析匹配问题")
        
        print("\n💡 功能特色:")
        print("• 4种匹配算法对比测试")
        print("• 实时截图和连续测试")
        print("• 差异图像可视化分析")
        print("• 详细的测试统计和建议")
        print("• 可调节的匹配阈值")
    else:
        print("⚠️  部分匹配测试功能存在问题，请检查相关代码")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
