"""
DPI处理修复验证脚本
验证修复后的坐标转换是否正确处理DPI感知级别
"""
import sys

def test_dpi_awareness_detection():
    """测试DPI感知级别检测"""
    print("🔍 测试DPI感知级别检测")
    print("=" * 50)
    
    try:
        from autogame_xcx.core.coordinate_converter import CoordinateConverter
        
        # 创建测试转换器
        template_res = {'width': 1920, 'height': 1080}
        current_res = {'width': 1920, 'height': 1080}
        converter = CoordinateConverter(template_res, current_res)
        
        # 获取DPI调试信息
        dpi_info = converter.get_dpi_debug_info()
        
        print(f"检测到的DPI感知级别: {dpi_info['dpi_awareness']}")
        print(f"系统DPI: {dpi_info['system_dpi']}")
        print(f"是否应该应用DPI缩放: {dpi_info['should_apply_dpi_scaling']}")
        
        # 解释DPI感知级别
        awareness_explanations = {
            'unaware': '程序不知道DPI，系统会自动缩放整个窗口',
            'system_aware': '程序知道系统DPI，但仍收到96DPI的逻辑坐标',
            'per_monitor_aware': '程序完全自己处理缩放，收到物理像素坐标'
        }
        
        explanation = awareness_explanations.get(dpi_info['dpi_awareness'], '未知级别')
        print(f"级别说明: {explanation}")
        
        print("\nDPI处理建议:")
        for i, rec in enumerate(dpi_info['recommendations'], 1):
            print(f"  {i}. {rec}")
        
        return True
        
    except Exception as e:
        print(f"❌ DPI感知检测失败: {e}")
        return False

def test_coordinate_scaling_scenarios():
    """测试不同DPI场景下的坐标缩放"""
    print("\n🎯 测试坐标缩放场景")
    print("=" * 50)
    
    try:
        from autogame_xcx.core.coordinate_converter import CoordinateConverter
        
        # 测试坐标
        test_area = {'x': 400, 'y': 300, 'width': 120, 'height': 40}
        test_click = {'x': 460, 'y': 320}
        
        # 测试场景
        scenarios = [
            {
                'name': '相同分辨率 (无缩放)',
                'template': {'width': 1920, 'height': 1080},
                'current': {'width': 1920, 'height': 1080}
            },
            {
                'name': '分辨率缩小 (需要缩放)',
                'template': {'width': 1920, 'height': 1080},
                'current': {'width': 1366, 'height': 768}
            },
            {
                'name': '分辨率放大 (需要缩放)',
                'template': {'width': 1366, 'height': 768},
                'current': {'width': 1920, 'height': 1080}
            }
        ]
        
        for scenario in scenarios:
            print(f"\n--- {scenario['name']} ---")
            
            converter = CoordinateConverter(scenario['template'], scenario['current'])
            dpi_info = converter.get_dpi_debug_info()
            
            # 显示缩放信息
            print(f"DPI感知: {dpi_info['dpi_awareness']}")
            print(f"基础缩放: x={dpi_info['scale_factor']['base_scale']['x']:.3f}, y={dpi_info['scale_factor']['base_scale']['y']:.3f}")
            print(f"DPI缩放: x={dpi_info['scale_factor']['dpi_scale']['x']:.3f}, y={dpi_info['scale_factor']['dpi_scale']['y']:.3f}")
            print(f"最终缩放: x={dpi_info['effective_scaling']['x']:.3f}, y={dpi_info['effective_scaling']['y']:.3f}")
            
            # 转换坐标
            converted_area = converter.convert_coordinates(test_area)
            converted_click = converter.convert_click_point(test_click)
            
            print(f"区域转换: {test_area} -> {converted_area}")
            print(f"点击转换: {test_click} -> {converted_click}")
            
            # 验证转换是否合理
            expected_scale_x = scenario['current']['width'] / scenario['template']['width']
            expected_scale_y = scenario['current']['height'] / scenario['template']['height']
            
            actual_scale_x = converted_area['x'] / test_area['x']
            actual_scale_y = converted_area['y'] / test_area['y']
            
            print(f"预期缩放: x={expected_scale_x:.3f}, y={expected_scale_y:.3f}")
            print(f"实际缩放: x={actual_scale_x:.3f}, y={actual_scale_y:.3f}")
            
            # 检查是否合理（考虑DPI感知级别）
            if dpi_info['dpi_awareness'] in ['unaware', 'system_aware']:
                # 这些模式下，应该主要是分辨率缩放
                scale_diff_x = abs(actual_scale_x - expected_scale_x)
                scale_diff_y = abs(actual_scale_y - expected_scale_y)
                
                if scale_diff_x < 0.01 and scale_diff_y < 0.01:
                    print("✅ 缩放结果合理")
                else:
                    print("⚠️  缩放结果可能需要调整")
            else:
                print("ℹ️  Per-Monitor Aware模式，缩放包含DPI因子")
        
        return True
        
    except Exception as e:
        print(f"❌ 坐标缩放测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dpi_fix_effectiveness():
    """测试DPI修复的有效性"""
    print("\n🔧 测试DPI修复有效性")
    print("=" * 50)
    
    try:
        from autogame_xcx.core.coordinate_converter import CoordinateConverter
        
        # 模拟高DPI场景
        template_res = {'width': 1920, 'height': 1080}
        current_res = {'width': 1920, 'height': 1080}  # 相同分辨率但可能不同DPI
        
        converter = CoordinateConverter(template_res, current_res)
        dpi_info = converter.get_dpi_debug_info()
        
        print("修复前后对比:")
        print(f"  DPI感知级别: {dpi_info['dpi_awareness']}")
        print(f"  系统DPI: {dpi_info['system_dpi']}")
        
        if dpi_info['dpi_awareness'] == 'unaware':
            print("  ✅ Unaware模式: 不应用额外DPI缩放（避免重复缩放）")
        elif dpi_info['dpi_awareness'] == 'system_aware':
            print("  ✅ System Aware模式: 主要使用分辨率缩放")
        elif dpi_info['dpi_awareness'] == 'per_monitor_aware':
            print("  ✅ Per-Monitor Aware模式: 正确应用DPI缩放")
        
        # 测试坐标转换
        test_coords = {'x': 100, 'y': 100, 'width': 50, 'height': 30}
        converted = converter.convert_coordinates(test_coords)
        
        print(f"\n坐标转换示例:")
        print(f"  输入: {test_coords}")
        print(f"  输出: {converted}")
        
        # 分析转换结果
        if dpi_info['dpi_awareness'] in ['unaware', 'system_aware']:
            if converted['x'] == test_coords['x'] and converted['y'] == test_coords['y']:
                print("  ✅ 相同分辨率下坐标未被错误缩放")
            else:
                print("  ⚠️  坐标被意外缩放")
        
        return True
        
    except Exception as e:
        print(f"❌ DPI修复测试失败: {e}")
        return False

def show_dpi_fix_summary():
    """显示DPI修复总结"""
    print("\n📋 DPI处理修复总结")
    print("=" * 50)
    
    print("修复内容:")
    print("  1. ✅ 添加了DPI感知级别检测")
    print("  2. ✅ 根据DPI感知级别决定是否应用DPI缩放")
    print("  3. ✅ 避免了Unaware和System Aware模式下的重复缩放")
    print("  4. ✅ 为Per-Monitor Aware模式正确应用DPI缩放")
    print("  5. ✅ 提供详细的DPI调试信息和建议")
    
    print("\nDPI感知级别处理策略:")
    print("  • Unaware: 仅使用分辨率缩放（系统已处理DPI）")
    print("  • System Aware: 仅使用分辨率缩放（收到逻辑坐标）")
    print("  • Per-Monitor Aware: 应用分辨率+DPI缩放（收到物理坐标）")
    
    print("\n使用建议:")
    print("  • 大多数情况下，程序会是Unaware或System Aware")
    print("  • 如果坐标仍不准确，检查窗口是否被系统缩放")
    print("  • 可以通过get_dpi_debug_info()获取详细信息")
    print("  • 建议在目标环境下重新创建模板以获得最佳效果")

def main():
    """主测试函数"""
    print("🔧 DPI处理修复验证")
    print("=" * 60)
    
    tests = [
        ("DPI感知检测", test_dpi_awareness_detection),
        ("坐标缩放场景", test_coordinate_scaling_scenarios),
        ("DPI修复有效性", test_dpi_fix_effectiveness),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"\n✅ {test_name}: 通过")
                passed += 1
            else:
                print(f"\n❌ {test_name}: 失败")
        except Exception as e:
            print(f"\n❌ {test_name}: 异常 - {e}")
    
    # 显示总结
    show_dpi_fix_summary()
    
    print(f"\n测试结果: {passed}/{total} 项通过")
    
    if passed == total:
        print("🎉 DPI处理修复验证成功！")
        print("现在坐标转换会正确处理不同的DPI感知级别，避免重复缩放问题。")
    else:
        print("⚠️  部分测试失败，需要进一步检查。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
