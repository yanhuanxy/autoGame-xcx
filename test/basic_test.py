"""
基础测试
"""
import sys
sys.path.append('../gui')

print("开始基础测试...")

try:
    print("1. 导入模块...")
    from gui.core.coordinate_converter import CoordinateConverter
    print("   ✓ 导入成功")
    
    print("2. 创建实例...")
    converter = CoordinateConverter(
        {'width': 1920, 'height': 1080}, 
        {'width': 1920, 'height': 1080}
    )
    print("   ✓ 创建成功")
    
    print("3. 测试坐标转换...")
    result = converter.convert_coordinates({'x': 100, 'y': 100, 'width': 50, 'height': 30})
    print(f"   ✓ 转换结果: {result}")
    
    print("4. 测试DPI信息...")
    if hasattr(converter, 'get_dpi_debug_info'):
        dpi_info = converter.get_dpi_debug_info()
        print(f"   ✓ DPI感知: {dpi_info['dpi_awareness']}")
        print(f"   ✓ 系统DPI: {dpi_info['system_dpi']}")
    else:
        print("   ⚠️ DPI调试方法不存在")
    
    print("\n🎉 基础测试成功！")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
