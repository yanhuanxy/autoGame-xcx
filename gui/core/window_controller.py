"""
游戏窗口控制模块
基于现有的core/window.py扩展，增加游戏区域定位和窗口控制功能
"""
import win32gui
import win32process
import win32api
import win32con
import win32print
import psutil
import pyautogui
import cv2
import numpy as np
from PIL import ImageGrab
import time
from util.opencv_util import CvTool

class GameWindowController:
    def __init__(self):
        self.target_window = None
        self.game_area = None
        self.window_info = {}
    
    def find_wechat_window(self):
        """查找微信窗口"""
        all_windows = self._get_running_windows()
        for hwnd, title, process_name in all_windows:
            if "聊斋搜神记" in title or "聊斋搜神记" in process_name.lower():
                self.target_window = {
                    'hwnd': hwnd,
                    'title': title,
                    'process_name': process_name
                }
                return self.target_window
        return None
    
    def _get_running_windows(self):
        """获取当前所有可见且有标题的窗口"""
        windows = []
        def win_enum_handler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) != '':
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    process = psutil.Process(pid)
                    process_name = process.name()
                    windows.append((hwnd, win32gui.GetWindowText(hwnd), process_name))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        win32gui.EnumWindows(win_enum_handler, None)
        return windows
    
    def activate_window(self):
        """激活微信窗口"""
        if not self.target_window:
            return False
        
        try:
            hwnd = self.target_window['hwnd']
            title = self.target_window['title']
            
            # 使用win32gui激活窗口
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)  # 等待窗口激活
            
            # 备用方案：使用pyautogui
            try:
                windows = pyautogui.getWindowsWithTitle(title)
                if windows:
                    windows[0].activate()
            except:
                pass
            
            return True
        except Exception as e:
            print(f"激活窗口时出错: {e}")
            return False
    
    def get_window_rect(self):
        """获取窗口位置和大小"""
        if not self.target_window:
            return None
        
        try:
            hwnd = self.target_window['hwnd']
            rect = win32gui.GetWindowRect(hwnd)
            return {
                'left': rect[0],
                'top': rect[1],
                'right': rect[2],
                'bottom': rect[3],
                'width': rect[2] - rect[0],
                'height': rect[3] - rect[1]
            }
        except Exception as e:
            print(f"获取窗口位置时出错: {e}")
            return None
    
    def resize_window(self, target_resolution):
        """调整窗口大小到目标分辨率"""
        if not self.target_window:
            return False
        
        try:
            hwnd = self.target_window['hwnd']
            
            # 获取当前窗口位置
            current_rect = self.get_window_rect()
            if not current_rect:
                return False
            
            # 设置新的窗口大小，保持左上角位置不变
            win32gui.SetWindowPos(
                hwnd, 
                0,  # hWndInsertAfter
                current_rect['left'],  # X
                current_rect['top'],   # Y
                target_resolution['width'],   # cx
                target_resolution['height'],  # cy
                win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW
            )
            
            time.sleep(1)  # 等待窗口调整完成
            return True
            
        except Exception as e:
            print(f"调整窗口大小时出错: {e}")
            return False
    
    def capture_window_screenshot(self):
        """截取窗口截图"""
        if not self.target_window:
            return None
        
        try:
            # 激活窗口
            if not self.activate_window():
                print("无法激活窗口")
                return None
            
            # 获取窗口位置
            rect = self.get_window_rect()
            if not rect:
                print("无法获取窗口位置")
                return None
            
            # 截取窗口区域
            screenshot = ImageGrab.grab(bbox=(
                rect['left'], 
                rect['top'], 
                rect['right'], 
                rect['bottom']
            ))
            
            # 转换为OpenCV格式
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            return screenshot_cv
            
        except Exception as e:
            print(f"截取窗口截图时出错: {e}")
            return None
    
    def locate_game_area(self, screenshot=None):
        """定位小程序游戏区域（简单版本，后续可以优化）"""
        if screenshot is None:
            screenshot = self.capture_window_screenshot()
        
        if screenshot is None:
            return None
        
        # 简单实现：假设游戏区域在窗口中央的某个比例
        # 这里可以根据实际情况调整或使用图像识别
        height, width = screenshot.shape[:2]
        
        # 假设游戏区域占窗口的80%，居中显示
        margin_x = int(width * 0.1)
        margin_y = int(height * 0.1)
        
        game_area = {
            'x': margin_x,
            'y': margin_y,
            'width': width - 2 * margin_x,
            'height': height - 2 * margin_y
        }
        
        self.game_area = game_area
        return game_area
    
    def get_current_resolution(self):
        """获取当前窗口分辨率"""
        rect = self.get_window_rect()
        if rect:
            return {
                'width': rect['width'],
                'height': rect['height']
            }
        return None
    
    def get_system_dpi(self):
        """获取系统DPI设置"""
        try:
            hdc = win32gui.GetDC(0)
            dpi_x = win32print.GetDeviceCaps(hdc, win32con.LOGPIXELSX)
            dpi_y = win32print.GetDeviceCaps(hdc, win32con.LOGPIXELSY)
            win32gui.ReleaseDC(0, hdc)
            return {'x': dpi_x, 'y': dpi_y}
        except:
            return {'x': 96, 'y': 96}  # 默认DPI

# 测试函数
def test_window_controller():
    """测试窗口控制功能"""
    controller = GameWindowController()
    
    print("1. 查找微信窗口...")
    wechat_window = controller.find_wechat_window()
    if wechat_window:
        print(f"找到微信窗口: {wechat_window['title']}")
    else:
        print("未找到微信窗口")
        return
    
    print("2. 激活窗口...")
    if controller.activate_window():
        print("窗口激活成功")
    else:
        print("窗口激活失败")
        return
    
    print("3. 获取窗口信息...")
    rect = controller.get_window_rect()
    if rect:
        print(f"窗口位置: {rect}")
    
    resolution = controller.get_current_resolution()
    if resolution:
        print(f"当前分辨率: {resolution}")
    
    dpi = controller.get_system_dpi()
    print(f"系统DPI: {dpi}")
    
    print("4. 截取窗口截图...")
    screenshot = controller.capture_window_screenshot()
    if screenshot is not None:
        print(f"截图成功，尺寸: {screenshot.shape}")
        # 保存截图用于测试
        CvTool.imwrite("test_screenshot.png", screenshot)
        print("截图已保存为 test_screenshot.png")
    else:
        print("截图失败")
    
    print("5. 定位游戏区域...")
    game_area = controller.locate_game_area(screenshot)
    if game_area:
        print(f"游戏区域: {game_area}")

if __name__ == "__main__":
    test_window_controller()
