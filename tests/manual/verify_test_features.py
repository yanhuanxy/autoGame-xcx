"""
快速验证测试功能脚本
验证新增的测试功能是否可以正常使用
"""
import sys
import os

def main():
    """主验证函数"""
    print("🧪 验证视觉流程自动化系统测试功能")
    print("=" * 50)
    
    # 1. 验证依赖
    print("1. 检查依赖库...")
    try:
        import cv2
        import numpy as np
        from PyQt6.QtWidgets import QApplication
        print("   ✅ 核心依赖库正常")
    except ImportError as e:
        print(f"   ❌ 依赖库缺失: {e}")
        print("   请运行: pip install -r requirements.txt")
        return False
    
    # 2. 验证核心模块
    print("\n2. 检查核心模块...")
    try:
        from template_creator_gui import TemplateCreatorGUI, TemplateTestDialog, AreaTestDialog
        from game_executor import GameExecutor
        from image_matcher import ImageMatcher
        print("   ✅ 核心模块导入正常")
    except ImportError as e:
        print(f"   ❌ 模块导入失败: {e}")
        return False
    
    # 3. 验证测试功能
    print("\n3. 检查测试功能...")
    
    # 检查GameExecutor的新功能
    executor = GameExecutor()
    if hasattr(executor, 'dry_run_mode'):
        print("   ✅ 模拟运行模式支持")
    else:
        print("   ❌ 模拟运行模式不支持")
        return False
    
    if hasattr(executor, 'initialize_execution_for_test'):
        print("   ✅ 测试初始化方法存在")
    else:
        print("   ❌ 测试初始化方法不存在")
        return False
    
    # 检查图像匹配器
    matcher = ImageMatcher()
    required_methods = ['template_matching', 'ssim', 'feature_matching', 'hybrid']
    if all(method in matcher.methods for method in required_methods):
        print("   ✅ 图像匹配算法完整")
    else:
        print("   ❌ 图像匹配算法不完整")
        return False
    
    # 4. 验证GUI测试组件
    print("\n4. 检查GUI测试组件...")
    
    app = QApplication(sys.argv)
    
    try:
        # 创建测试数据
        test_template = {
            'template_info': {
                'name': '测试模板',
                'template_resolution': {'width': 1920, 'height': 1080}
            },
            'tasks': [
                {
                    'task_id': 'test_task',
                    'task_name': '测试任务',
                    'steps': [
                        {
                            'step_id': 'test_step',
                            'action_type': 'image_verify_and_click',
                            'user_marked_area': {'x': 100, 'y': 100, 'width': 50, 'height': 30},
                            'reference_image': 'test.png',
                            'match_threshold': 0.85
                        }
                    ]
                }
            ]
        }
        
        # 测试TemplateTestDialog
        test_dialog = TemplateTestDialog(test_template)
        print("   ✅ 模板测试对话框创建成功")
        
        # 测试AreaTestDialog
        area_data = {
            'name': 'test_area',
            'action_type': 'image_verify_and_click',
            'user_marked_area': {'x': 100, 'y': 100, 'width': 50, 'height': 30},
            'reference_image': 'test.png',
            'match_threshold': 0.85
        }
        test_screenshot = np.zeros((400, 600, 3), dtype=np.uint8)
        area_dialog = AreaTestDialog(area_data, test_screenshot)
        print("   ✅ 区域测试对话框创建成功")
        
    except Exception as e:
        print(f"   ❌ GUI测试组件创建失败: {e}")
        return False
    
    # 5. 验证主GUI集成
    print("\n5. 检查主GUI集成...")
    try:
        gui = TemplateCreatorGUI()
        
        # 检查测试相关方法
        test_methods = ['test_template', 'test_selected_area']
        for method in test_methods:
            if hasattr(gui, method):
                print(f"   ✅ {method} 方法存在")
            else:
                print(f"   ❌ {method} 方法不存在")
                return False
                
    except Exception as e:
        print(f"   ❌ 主GUI创建失败: {e}")
        return False
    
    # 6. 验证启动脚本
    print("\n6. 检查启动脚本...")
    if os.path.exists('../start_gui.py'):
        print("   ✅ GUI启动脚本存在")
    else:
        print("   ❌ GUI启动脚本不存在")
        return False
    
    if os.path.exists('test_template_features.py'):
        print("   ✅ 功能测试脚本存在")
    else:
        print("   ❌ 功能测试脚本不存在")
        return False
    
    # 验证完成
    print("\n" + "=" * 50)
    print("🎉 所有测试功能验证通过！")
    print("\n📋 可用的测试功能:")
    print("   • 完整模板测试（支持模拟运行）")
    print("   • 单任务测试")
    print("   • 图像匹配测试")
    print("   • 区域详细测试（4种算法对比）")
    print("   • 实时测试结果分析")
    
    print("\n🚀 快速开始:")
    print("   1. 启动GUI: python start_gui.py")
    print("   2. 创建模板并添加标记区域")
    print("   3. 点击'测试'按钮进行区域测试")
    print("   4. 点击'测试模板'按钮进行完整测试")
    print("   5. 使用模拟运行模式安全测试")
    
    print("\n💡 测试建议:")
    print("   • 先使用区域测试验证单个区域的匹配效果")
    print("   • 使用匹配测试模式快速检查所有区域")
    print("   • 在实际执行前使用模拟运行模式测试")
    print("   • 根据测试结果调整匹配阈值")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n⚠️  验证失败，请检查相关问题后重试")
        sys.exit(1)
    else:
        print("\n✅ 验证成功，可以开始使用测试功能！")
        sys.exit(0)
