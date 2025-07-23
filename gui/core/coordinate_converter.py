"""
坐标转换模块
处理不同分辨率下的坐标转换，确保模板在不同设备上的准确执行
正确处理Windows DPI感知级别，避免重复缩放问题
"""
import win32print
import win32gui
import win32con
import win32api
import win32process
import ctypes
from ctypes import wintypes
import math

class CoordinateConverter:
    def __init__(self, template_resolution, current_resolution):
        """
        初始化坐标转换器

        Args:
            template_resolution: 模板创建时的分辨率 {'width': int, 'height': int}
            current_resolution: 当前运行时的分辨率 {'width': int, 'height': int}
        """
        self.template_res = template_resolution
        self.current_res = current_resolution
        self.system_dpi = self._get_system_dpi()
        self.dpi_awareness = self._get_dpi_awareness()
        self.scale_factor = self._calculate_scale_factor()
        
        print(f"坐标转换器初始化:")
        print(f"  模板分辨率: {self.template_res}")
        print(f"  当前分辨率: {self.current_res}")
        print(f"  系统DPI: {self.system_dpi}")
        print(f"  DPI感知级别: {self.dpi_awareness}")
        print(f"  缩放因子: {self.scale_factor}")
    
    def _get_system_dpi(self):
        """获取系统DPI设置"""
        try:
            hdc = win32gui.GetDC(0)
            dpi_x = win32print.GetDeviceCaps(hdc, win32con.LOGPIXELSX)
            dpi_y = win32print.GetDeviceCaps(hdc, win32con.LOGPIXELSY)
            win32gui.ReleaseDC(0, hdc)
            return {'x': dpi_x, 'y': dpi_y}
        except Exception as e:
            print(f"获取系统DPI时出错: {e}")
            return {'x': 96, 'y': 96}  # 默认DPI

    def _get_dpi_awareness(self):
        """
        检测当前进程的DPI感知级别
        返回: 'unaware', 'system_aware', 'per_monitor_aware'
        """
        try:
            # 定义DPI感知常量
            DPI_AWARENESS_INVALID = -1
            DPI_AWARENESS_UNAWARE = 0
            DPI_AWARENESS_SYSTEM_AWARE = 1
            DPI_AWARENESS_PER_MONITOR_AWARE = 2

            # 尝试使用Windows 10+ API
            try:
                shcore = ctypes.windll.shcore
                # GetProcessDpiAwareness需要进程句柄，使用-1表示当前进程
                awareness = ctypes.c_int()
                result = shcore.GetProcessDpiAwareness(-1, ctypes.byref(awareness))
                if result == 0:  # S_OK
                    awareness = awareness.value
                else:
                    raise OSError("GetProcessDpiAwareness failed")

                if awareness == DPI_AWARENESS_UNAWARE:
                    return 'unaware'
                elif awareness == DPI_AWARENESS_SYSTEM_AWARE:
                    return 'system_aware'
                elif awareness == DPI_AWARENESS_PER_MONITOR_AWARE:
                    return 'per_monitor_aware'
                else:
                    return 'unknown'

            except (AttributeError, OSError):
                # 回退到Windows 8.1+ API
                try:
                    user32 = ctypes.windll.user32
                    if hasattr(user32, 'IsProcessDPIAware'):
                        if user32.IsProcessDPIAware():
                            return 'system_aware'
                        else:
                            return 'unaware'
                    else:
                        return 'unaware'  # 老版本Windows
                except:
                    return 'unaware'

        except Exception as e:
            print(f"检测DPI感知级别时出错: {e}")
            return 'unaware'  # 默认假设为unaware

    def _calculate_scale_factor(self):
        """
        计算缩放因子
        根据DPI感知级别正确处理缩放，避免重复缩放问题
        """
        # 基础分辨率缩放比例
        scale_x = self.current_res['width'] / self.template_res['width']
        scale_y = self.current_res['height'] / self.template_res['height']

        # 根据DPI感知级别决定是否应用DPI缩放
        base_dpi = 96

        if self.dpi_awareness == 'unaware':
            # Unaware程序：系统已经处理了DPI缩放，坐标已经是逻辑坐标
            # 不需要额外的DPI缩放，只需要分辨率缩放
            final_scale_x = scale_x
            final_scale_y = scale_y
            print(f"  DPI处理: Unaware模式，使用分辨率缩放")

        elif self.dpi_awareness == 'system_aware':
            # System Aware程序：程序知道系统DPI，但收到的仍是96DPI的逻辑坐标
            # 通常不需要额外DPI缩放，除非分辨率确实不同
            final_scale_x = scale_x
            final_scale_y = scale_y
            print(f"  DPI处理: System Aware模式，使用分辨率缩放")

        elif self.dpi_awareness == 'per_monitor_aware':
            # Per-Monitor Aware程序：程序完全自己处理缩放，收到物理像素坐标
            # 需要考虑DPI缩放
            dpi_scale_x = self.system_dpi['x'] / base_dpi
            dpi_scale_y = self.system_dpi['y'] / base_dpi
            final_scale_x = scale_x * dpi_scale_x
            final_scale_y = scale_y * dpi_scale_y
            print(f"  DPI处理: Per-Monitor Aware模式，应用DPI缩放 {dpi_scale_x:.2f}x{dpi_scale_y:.2f}")

        else:
            # 未知模式，保守处理，只使用分辨率缩放
            final_scale_x = scale_x
            final_scale_y = scale_y
            print(f"  DPI处理: 未知模式，仅使用分辨率缩放")

        return {
            'x': final_scale_x,
            'y': final_scale_y,
            'uniform': (final_scale_x + final_scale_y) / 2,  # 统一缩放因子
            'dpi_awareness': self.dpi_awareness,
            'base_scale': {'x': scale_x, 'y': scale_y},
            'dpi_scale': {'x': self.system_dpi['x'] / base_dpi, 'y': self.system_dpi['y'] / base_dpi}
        }
    
    def convert_coordinates(self, template_coords):
        """
        转换坐标区域
        
        Args:
            template_coords: 模板中的坐标 {'x': int, 'y': int, 'width': int, 'height': int}
        
        Returns:
            dict: 转换后的坐标
        """
        try:
            converted = {
                'x': int(template_coords['x'] * self.scale_factor['x']),
                'y': int(template_coords['y'] * self.scale_factor['y']),
                'width': int(template_coords.get('width', 0) * self.scale_factor['x']),
                'height': int(template_coords.get('height', 0) * self.scale_factor['y'])
            }
            
            # 确保坐标不为负数
            converted['x'] = max(0, converted['x'])
            converted['y'] = max(0, converted['y'])
            converted['width'] = max(1, converted['width'])
            converted['height'] = max(1, converted['height'])
            
            return converted
            
        except Exception as e:
            print(f"转换坐标时出错: {e}")
            return template_coords
    
    def convert_click_point(self, template_point):
        """
        转换点击坐标
        
        Args:
            template_point: 模板中的点击坐标 {'x': int, 'y': int}
        
        Returns:
            dict: 转换后的点击坐标
        """
        try:
            converted = {
                'x': int(template_point['x'] * self.scale_factor['x']),
                'y': int(template_point['y'] * self.scale_factor['y'])
            }
            
            # 确保坐标不为负数
            converted['x'] = max(0, converted['x'])
            converted['y'] = max(0, converted['y'])
            
            return converted
            
        except Exception as e:
            print(f"转换点击坐标时出错: {e}")
            return template_point
    
    def is_resolution_match(self, tolerance=0.1):
        """
        检查分辨率是否匹配
        
        Args:
            tolerance: 容差比例，默认10%
        
        Returns:
            bool: 是否匹配
        """
        width_diff = abs(self.current_res['width'] - self.template_res['width']) / self.template_res['width']
        height_diff = abs(self.current_res['height'] - self.template_res['height']) / self.template_res['height']
        
        return width_diff <= tolerance and height_diff <= tolerance
    
    def get_scale_info(self):
        """获取缩放信息，用于调试和报告"""
        return {
            'template_resolution': self.template_res,
            'current_resolution': self.current_res,
            'scale_factor': self.scale_factor,
            'system_dpi': self.system_dpi,
            'is_match': self.is_resolution_match(),
            'scale_ratio': {
                'x': self.scale_factor['x'],
                'y': self.scale_factor['y']
            }
        }
    
    def convert_area_to_bbox(self, area_coords, window_offset=None):
        """
        将区域坐标转换为绝对屏幕坐标（用于截图）
        
        Args:
            area_coords: 区域坐标
            window_offset: 窗口在屏幕上的偏移 {'x': int, 'y': int}
        
        Returns:
            tuple: (left, top, right, bottom) 绝对坐标
        """
        converted = self.convert_coordinates(area_coords)
        
        offset_x = window_offset['x'] if window_offset else 0
        offset_y = window_offset['y'] if window_offset else 0
        
        left = offset_x + converted['x']
        top = offset_y + converted['y']
        right = left + converted['width']
        bottom = top + converted['height']
        
        return (left, top, right, bottom)
    
    def validate_coordinates(self, coords, max_width, max_height):
        """
        验证坐标是否在有效范围内
        
        Args:
            coords: 要验证的坐标
            max_width: 最大宽度
            max_height: 最大高度
        
        Returns:
            bool: 是否有效
        """
        if 'x' in coords and 'y' in coords:
            if coords['x'] < 0 or coords['y'] < 0:
                return False
            if coords['x'] >= max_width or coords['y'] >= max_height:
                return False
        
        if 'width' in coords and 'height' in coords:
            if coords['x'] + coords['width'] > max_width:
                return False
            if coords['y'] + coords['height'] > max_height:
                return False
        
        return True

    def get_dpi_debug_info(self):
        """
        获取详细的DPI调试信息

        Returns:
            dict: 包含详细DPI信息的字典
        """
        return {
            'dpi_awareness': self.dpi_awareness,
            'system_dpi': self.system_dpi,
            'template_resolution': self.template_res,
            'current_resolution': self.current_res,
            'scale_factor': self.scale_factor,
            'should_apply_dpi_scaling': self.dpi_awareness == 'per_monitor_aware',
            'effective_scaling': {
                'x': self.scale_factor['x'],
                'y': self.scale_factor['y']
            },
            'recommendations': self._get_dpi_recommendations()
        }

    def _get_dpi_recommendations(self):
        """获取DPI处理建议"""
        recommendations = []

        if self.dpi_awareness == 'unaware':
            recommendations.append("程序为DPI Unaware，系统已处理缩放")
            recommendations.append("如果坐标不准确，检查是否需要设置DPI感知")

        elif self.dpi_awareness == 'system_aware':
            recommendations.append("程序为System DPI Aware，适合大多数场景")
            if self.system_dpi['x'] != 96 or self.system_dpi['y'] != 96:
                recommendations.append(f"检测到非标准DPI ({self.system_dpi['x']}x{self.system_dpi['y']})，注意测试")

        elif self.dpi_awareness == 'per_monitor_aware':
            recommendations.append("程序为Per-Monitor DPI Aware，需要精确处理DPI")
            recommendations.append("已应用DPI缩放，适合多显示器环境")

        else:
            recommendations.append("未知DPI感知级别，使用保守的缩放策略")
            recommendations.append("建议手动测试坐标准确性")

        # 缩放比例建议
        scale_diff_x = abs(self.scale_factor['x'] - 1.0)
        scale_diff_y = abs(self.scale_factor['y'] - 1.0)

        if scale_diff_x > 0.1 or scale_diff_y > 0.1:
            recommendations.append(f"检测到显著缩放 ({self.scale_factor['x']:.2f}x{self.scale_factor['y']:.2f})")
            recommendations.append("建议在目标分辨率下重新创建模板")

        return recommendations

# 测试函数
def test_coordinate_converter():
    """测试坐标转换功能"""
    print("测试坐标转换功能...")
    
    # 模拟不同分辨率场景
    test_cases = [
        {
            'name': '相同分辨率',
            'template_res': {'width': 1920, 'height': 1080},
            'current_res': {'width': 1920, 'height': 1080}
        },
        {
            'name': '缩小分辨率',
            'template_res': {'width': 1920, 'height': 1080},
            'current_res': {'width': 1366, 'height': 768}
        },
        {
            'name': '放大分辨率',
            'template_res': {'width': 1366, 'height': 768},
            'current_res': {'width': 1920, 'height': 1080}
        }
    ]
    
    # 测试坐标
    test_coords = {
        'area': {'x': 400, 'y': 300, 'width': 120, 'height': 40},
        'click': {'x': 460, 'y': 320}
    }
    
    for case in test_cases:
        print(f"\n--- {case['name']} ---")
        converter = CoordinateConverter(case['template_res'], case['current_res'])

        # 显示DPI调试信息
        dpi_info = converter.get_dpi_debug_info()
        print(f"DPI感知级别: {dpi_info['dpi_awareness']}")
        print(f"系统DPI: {dpi_info['system_dpi']}")
        print(f"有效缩放: x={dpi_info['effective_scaling']['x']:.3f}, y={dpi_info['effective_scaling']['y']:.3f}")

        # 测试区域坐标转换
        converted_area = converter.convert_coordinates(test_coords['area'])
        print(f"区域坐标: {test_coords['area']} -> {converted_area}")

        # 测试点击坐标转换
        converted_click = converter.convert_click_point(test_coords['click'])
        print(f"点击坐标: {test_coords['click']} -> {converted_click}")

        # 测试分辨率匹配
        is_match = converter.is_resolution_match()
        print(f"分辨率匹配: {is_match}")

        # 显示DPI建议
        if dpi_info['recommendations']:
            print("DPI建议:")
            for rec in dpi_info['recommendations'][:2]:  # 只显示前两个建议
                print(f"  • {rec}")

if __name__ == "__main__":
    test_coordinate_converter()
