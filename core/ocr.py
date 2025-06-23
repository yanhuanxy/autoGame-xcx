import os

import pyautogui
import win32gui


def find_text_in_window(text_to_find, hwnd, lang='chi_sim'):
    """
    在指定窗口内查找特定文字，并返回其中心坐标。
    :param text_to_find: 要查找的文字字符串。
    :param hwnd: 目标窗口的句柄。
    :param lang: Tesseract OCR 使用的语言包 (chi_sim 代表简体中文)。
    :return: 如果找到文字，返回其在窗口内的中心坐标 (x, y)；否则返回 None。
    """
    try:
        # 1. 获取窗口位置和大小
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        # 2. 对窗口区域进行截图
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        save_dir = "./data"  # 目标目录
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)  # 递归创建目录

        save_path = os.path.join(save_dir, "region_screenshot.png")
        screenshot.save(save_path)
        # 3. 使用 pytesseract 获取详细的 OCR 数据
        # image_to_data 返回一个字典，包含已识别的文字、位置、置信度等信息
        ocr_data = {} # pytesseract.image_to_data(screenshot, lang=lang, output_type=Output.DICT)
        
        # 4. 遍历 OCR 结果，查找目标文字
        num_boxes = len(ocr_data['level'])
        for i in range(num_boxes):
            # 只有当 OCR 引擎对识别结果有一定置信度时才进行比较
            if int(float(ocr_data['conf'][i])) > 60: # 置信度阈值，可以调整
                if text_to_find in ocr_data['text'][i]:
                    # 找到了！计算该文字的中心点坐标
                    x = ocr_data['left'][i] + ocr_data['width'][i] // 2
                    y = ocr_data['top'][i] + ocr_data['height'][i] // 2
                    
                    print(f"在窗口中找到文字 '{text_to_find}'，位置: ({x}, {y})，置信度: {ocr_data['conf'][i]}%")
                    return (x, y)
                    
    except Exception as e:
        print(f"查找文字 '{text_to_find}' 时发生错误: {e}")

    # 5. 如果遍历完所有结果都找不到，则返回 None
    print(f"在窗口中未找到文字: '{text_to_find}'")
    return None
