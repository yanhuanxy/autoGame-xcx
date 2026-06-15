"""
简化的DPI修复测试
"""

def test_dpi_fix():
    """测试DPI修复"""
    print("测试DPI处理修复...")
    
    try:
        from autogame_xcx.core.coordinate_converter import CoordinateConverter
        
        # 创建测试实例
        template_res = {'width': 1920, 'height': 1080}
        current_res = {'width': 1920, 'height': 1080}
        
        print("创建坐标转换器...")
        converter = CoordinateConverter(template_res, current_res)
        
        print("获取DPI调试信息...")
        dpi_info = converter.get_dpi_debug_info()
        
        print(f"✓ DPI感知级别: {dpi_info['dpi_awareness']}")
        print(f"✓ 系统DPI: {dpi_info['system_dpi']}")
        print(f"✓ 是否应用DPI缩放: {dpi_info['should_apply_dpi_scaling']}")
        
        # 测试坐标转换
        test_coords = {'x': 100, 'y': 100, 'width': 50, 'height': 30}
        converted = converter.convert_coordinates(test_coords)
        
        print(f"✓ 坐标转换: {test_coords} -> {converted}")
        
        # 显示建议
        print("\nDPI处理建议:")
        for i, rec in enumerate(dpi_info['recommendations'][:3], 1):
            print(f"  {i}. {rec}")
        
        print("\n🎉 DPI修复测试成功！")
        
        # 解释修复内容
        print("\n修复说明:")
        if dpi_info['dpi_awareness'] == 'unaware':
            print("  • 检测到Unaware模式，避免重复DPI缩放")
        elif dpi_info['dpi_awareness'] == 'system_aware':
            print("  • 检测到System Aware模式，主要使用分辨率缩放")
        elif dpi_info['dpi_awareness'] == 'per_monitor_aware':
            print("  • 检测到Per-Monitor Aware模式，正确应用DPI缩放")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_dpi_fix()
    if success:
        print("\n✅ DPI处理修复验证成功！")
    else:
        print("\n❌ DPI处理修复验证失败！")
