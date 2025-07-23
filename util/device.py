import pyautogui
from . import window
from .constants import ele_coords

def click(x, y):
    """
    Performs a mouse click at the given screen coordinates.
    """
    pyautogui.click(x, y)

def click_in_window(x, y, hwnd):
    """
    Performs a mouse click at coordinates relative to a specified window.
    """
    try:
        win_rect = window.get_window_rect(hwnd)
        if win_rect:
            absolute_x = win_rect[0] + x
            absolute_y = win_rect[1] + y
            click(absolute_x, absolute_y)
            return True
        else:
            print("无法获取窗口位置, 点击失败")
            return False
    except Exception as e:
        print(f"在窗口内点击时发生错误: {e}")
        return False

def click_element_by_name(name, hwnd):
    """
    Finds an element by its name in the ele_coords dictionary and clicks on its center.

    Args:
        name (str): The name of the element to click.
        hwnd: The handle of the window.

    Returns:
        bool: True if the element was found and clicked, False otherwise.
    """
    for group in ele_coords.values():
        if name in group["children"]:
            # [[[x,y],...]]
            coords = group["children"][name][0][0]
            # Calculate the center of the polygon
            center_x = sum(p[0]for p in coords) / len(coords)
            center_y = sum(p[1] for p in coords) / len(coords)
            
            print(f"  找到元素 '{name}' 在坐标: ({center_x}, {center_y})")
            click_in_window(center_x, center_y, hwnd)
            return True
    
    print(f"  未找到元素: {name}")
    return False


def calculate_center(points):
    """
    计算一组坐标点的中心点（质心）
    :param points: 二维坐标列表，格式 [[x1, y1], [x2, y2], ...]
    :return: 中心点坐标 (center_x, center_y)
    """
    total_x = sum(point[0] for point in points)
    total_y = sum(point[1] for point in points)
    num_points = len(points)
    return (total_x / num_points, total_y / num_points)

# 您的坐标数据（提取顶点部分）
coordinate_data = [[399.0, 799.0], [438.0, 799.0], [439.0, 821.0], [399.0, 821.0]]

# 计算中心点
center_point = calculate_center(coordinate_data)
print(f"矩形中心点坐标: ({center_point[0]:.1f}, {center_point[1]:.1f})")

# 输出结果: 矩形中心点坐标: (418.8, 810.0)