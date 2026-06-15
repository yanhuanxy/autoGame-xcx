import win32gui
import win32process
import psutil
import pyautogui

def get_running_windows():
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
                pass # 忽略没有权限或已关闭的进程
    win32gui.EnumWindows(win_enum_handler, None)
    return windows

def find_target_window(name):
    """根据名称查找目标窗口 (会检查窗口标题和进程名)"""
    all_windows = get_running_windows()
    for hwnd, title, process_name in all_windows:
        if name in title or name in process_name:
            return (hwnd, title, process_name)
    return None

def activate_window(hwnd, title):
    """
    将指定窗口置于前台并激活。
    返回 True 表示成功，False 表示失败。
    """
    try:
        # 优先使用 win32gui 来激活
        win32gui.SetForegroundWindow(hwnd)
        # 使用 pyautogui 作为备用方案来确保窗口被激活
        pyautogui.getWindowsWithTitle(title)[0].activate()
        return True
    except Exception as e:
        print(f"激活窗口时出错: {e}")
        return False 