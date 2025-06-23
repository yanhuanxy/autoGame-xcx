import time
from core import device, ocr

def run(hwnd):
    """执行BOSS模块的任务"""
    print("\n--- 开始执行 [BOSS] 模块 ---")

    print("开始执行[BOSS]模块...")
    # 1. 点击"BOSS"按钮
    if device.click_element_by_name("BOOS", hwnd):
        time.sleep(2)  # 等待界面切换
        # 2. 查找"修仙BOSS"
        boss_coords = ocr.find_text_in_window("修仙BOSS", hwnd)
        if boss_coords:
            print("  成功找到[修仙BOSS]")
            # ... 后续点击操作 ...
            return True
            
    print("  [BOSS]模块执行失败")
    return False 