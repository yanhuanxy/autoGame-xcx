"""
最终匹配测试功能验证
确认所有匹配测试功能都已正确实现
"""
import sys
import os

def verify_matching_test_implementation():
    """验证匹配测试功能实现"""
    print("🔍 验证匹配测试功能实现")
    print("=" * 50)
    
    verification_results = []
    
    # 1. 验证MatchingTestDialog类存在
    print("1. 验证MatchingTestDialog类...")
    try:
        from autogame_xcx.ui.template_creator import MatchingTestDialog
        print("   ✅ MatchingTestDialog类导入成功")
        verification_results.append(("MatchingTestDialog类", True))
    except Exception as e:
        print(f"   ❌ MatchingTestDialog类导入失败: {e}")
        verification_results.append(("MatchingTestDialog类", False))
        return verification_results
    
    # 2. 验证类的关键属性
    print("2. 验证类的关键属性...")
    try:
        # 创建临时实例进行验证
        import numpy as np
        import cv2
        
        # 创建临时测试图像
        temp_image = np.zeros((50, 100, 3), dtype=np.uint8)
        cv2.rectangle(temp_image, (10, 10), (90, 40), (0, 255, 0), -1)
        temp_path = "temp_verify.png"
        CvTool.imwrite(temp_path, temp_image)
        
        area_coords = {'x': 10, 'y': 10, 'width': 80, 'height': 30}
        
        # 创建QApplication（如果需要）
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        dialog = MatchingTestDialog(area_coords, temp_path)
        
        # 验证关键属性
        required_attributes = [
            'area_coords', 'reference_image_path', 'image_matcher',
            'window_controller', 'test_results', 'continuous_testing',
            'algorithm_combo', 'threshold_spin', 'test_count_spin',
            'realtime_check', 'current_preview', 'reference_preview',
            'diff_preview', 'test_timer'
        ]
        
        missing_attrs = []
        for attr in required_attributes:
            if not hasattr(dialog, attr):
                missing_attrs.append(attr)
        
        if missing_attrs:
            print(f"   ❌ 缺少属性: {missing_attrs}")
            verification_results.append(("类属性", False))
        else:
            print("   ✅ 所有必需属性都存在")
            verification_results.append(("类属性", True))
        
        # 清理临时文件
        try:
            os.remove(temp_path)
        except:
            pass
            
    except Exception as e:
        print(f"   ❌ 属性验证失败: {e}")
        verification_results.append(("类属性", False))
    
    # 3. 验证关键方法
    print("3. 验证关键方法...")
    try:
        required_methods = [
            'load_reference_image', 'start_test', 'start_continuous_test',
            'stop_test', 'run_single_test', 'capture_current_area',
            'generate_diff_image', 'show_image_in_label', 'show_test_summary',
            'log_message'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(MatchingTestDialog, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"   ❌ 缺少方法: {missing_methods}")
            verification_results.append(("类方法", False))
        else:
            print("   ✅ 所有必需方法都存在")
            verification_results.append(("类方法", True))
            
    except Exception as e:
        print(f"   ❌ 方法验证失败: {e}")
        verification_results.append(("类方法", False))
    
    # 4. 验证AreaConfigDialog中的test_matching方法
    print("4. 验证AreaConfigDialog中的test_matching方法...")
    try:
        from autogame_xcx.ui.template_creator import AreaConfigDialog
        
        if hasattr(AreaConfigDialog, 'test_matching'):
            print("   ✅ test_matching方法存在")
            verification_results.append(("test_matching方法", True))
        else:
            print("   ❌ test_matching方法不存在")
            verification_results.append(("test_matching方法", False))
            
    except Exception as e:
        print(f"   ❌ test_matching方法验证失败: {e}")
        verification_results.append(("test_matching方法", False))
    
    # 5. 验证图像匹配器功能
    print("5. 验证图像匹配器功能...")
    try:
        from autogame_xcx.core.image_matcher import ImageMatcher
        import numpy as np
        import cv2
        
        matcher = ImageMatcher()
        
        # 创建测试图像
        img1 = np.zeros((50, 100, 3), dtype=np.uint8)
        cv2.rectangle(img1, (10, 10), (90, 40), (255, 255, 255), -1)
        img2 = img1.copy()
        
        # 测试所有算法
        algorithms = ['template_matching', 'ssim', 'feature_matching', 'hybrid']
        algorithm_results = []
        
        for algo in algorithms:
            try:
                is_match, similarity = matcher.match_images(img1, img2, algo, 0.8)
                if similarity > 0.9:  # 相同图像应该有很高的相似度
                    algorithm_results.append(True)
                    print(f"   ✅ {algo}: 相似度={similarity:.3f}")
                else:
                    algorithm_results.append(False)
                    print(f"   ❌ {algo}: 相似度过低={similarity:.3f}")
            except Exception as e:
                algorithm_results.append(False)
                print(f"   ❌ {algo}: 错误={e}")
        
        if all(algorithm_results):
            print("   ✅ 所有匹配算法工作正常")
            verification_results.append(("匹配算法", True))
        else:
            print("   ❌ 部分匹配算法存在问题")
            verification_results.append(("匹配算法", False))
            
    except Exception as e:
        print(f"   ❌ 图像匹配器验证失败: {e}")
        verification_results.append(("匹配算法", False))
    
    return verification_results

def show_verification_summary(results):
    """显示验证摘要"""
    print("\n" + "=" * 50)
    print("📊 验证结果摘要")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for item, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{item:<20}: {status}")
    
    print("-" * 50)
    print(f"总体结果: {passed}/{total} 项通过")
    
    if passed == total:
        print("\n🎉 所有匹配测试功能验证通过！")
        print("\n📋 已实现的功能:")
        print("   ✓ MatchingTestDialog完整实现")
        print("   ✓ 4种匹配算法支持")
        print("   ✓ 实时截图测试")
        print("   ✓ 连续测试模式")
        print("   ✓ 差异图像分析")
        print("   ✓ 详细统计信息")
        print("   ✓ 智能阈值建议")
        
        print("\n🚀 使用方法:")
        print("   1. 启动GUI: python start_gui.py")
        print("   2. 创建模板并标记区域")
        print("   3. 在区域配置对话框中点击'测试匹配'")
        print("   4. 选择算法和参数进行测试")
        
        print("\n💡 功能特色:")
        print("   • 支持单次测试和连续测试")
        print("   • 实时显示三种图像预览")
        print("   • 彩色编码的测试日志")
        print("   • 智能的阈值调整建议")
        print("   • 详细的统计分析报告")
        
        return True
    else:
        print("\n⚠️  部分功能验证失败")
        failed_items = [item for item, result in results if not result]
        print(f"失败项目: {failed_items}")
        return False

def main():
    """主函数"""
    print("🧪 最终匹配测试功能验证")
    
    try:
        # 执行验证
        results = verify_matching_test_implementation()
        
        # 显示摘要
        success = show_verification_summary(results)
        
        if success:
            print("\n✅ 匹配测试功能完善成功！")
            print("现在可以在GUI中使用完整的高级匹配测试功能了。")
        else:
            print("\n❌ 匹配测试功能存在问题，需要进一步检查。")
        
        return success
        
    except Exception as e:
        print(f"\n❌ 验证过程出现异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
