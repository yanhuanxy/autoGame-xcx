from core import ocr, device
import time

def run(hwnd):
    """执行试炼模块的任务"""
    print("\n--- 开始执行 [试炼] 模块 ---")
    
    # 1. 点击"试炼"按钮
    if device.click_element_by_name("试炼", hwnd):
        time.sleep(2)  # 等待界面切换
        # 2. 查找"鬼影迷境"
        dungeon_coords = ocr.find_text_in_window("鬼影迷境", hwnd)
        if dungeon_coords:
            print("  成功找到[鬼影迷境]")
            # ... 后续点击操作 ...
            return True
            
    print("  [试炼]模块执行失败")
    return False

    # 在这里可以继续点击 "鬼影迷境" 等后续操作
    # device.click_in_window(dungeon_coords[0], dungeon_coords[1], hwnd)
    
    return True 