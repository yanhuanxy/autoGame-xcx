from core import ocr, device
import time

def run(hwnd):
    """执行历练模块的任务"""
    print("\n--- 开始执行 [历练] 模块 ---")

    print("开始执行[历练]模块...")
    # 1. 点击"历练"按钮
    if device.click_element_by_name("历练", hwnd):
        time.sleep(2)  # 等待界面切换
        # 2. 查找"云游"
        exp_coords = ocr.find_text_in_window("云游", hwnd)
        if exp_coords:
            print("  成功找到[云游]")
            # ... 后续点击操作 ...
            return True
            
    print("  [历练]模块执行失败")
    return False

    print("正在查找 [云游] ...")
    sub_coords = ocr.find_text_in_window("云游", hwnd)
    if not sub_coords:
        print("[历练] 模块执行失败：未找到 '云游'。")
        return False

    print("[历练] 模块执行成功！")
    return True 