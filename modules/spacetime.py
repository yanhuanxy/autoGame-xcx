from core import ocr, device
import time

def run(hwnd):
    """执行时空模块的任务"""
    print("\n--- 开始执行 [时空] 模块 ---")

    print("开始执行[时空]模块...")
    # 1. 点击"时空"按钮
    if device.click_element_by_name("时空", hwnd):
        time.sleep(2)  # 等待界面切换
        # 2. 查找"时空之门"
        st_coords = ocr.find_text_in_window("时空之门", hwnd)
        if st_coords:
            print("  成功找到[时空之门]")
            # ... 后续点击操作 ...
            return True
            
    print("  [时空]模块执行失败")
    return False 