import os

import pyautogui
import win32gui

from util.opencv_util import CvTool
from dgocr.dgocr import DGOCR
import cv2
import numpy as np


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
        screenshot.convert("RGB")
        # 将 PIL.Image 转换为 OpenCV 格式的 BGR 图像
        image_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        # 获取图像的宽度和高度
        img_height, img_width = image_cv.shape[:2]

        left_crop = int(img_width * 0.8)
        right_crop = img_width
        top_crop = int(img_height * 0.4)
        bottom_crop = int(img_height * 0.8)

        # 创建一个新的白色画布，与原始图像大小相同
        white_canvas = np.ones_like(image_cv) * 255  # 白色（RGB：255, 255, 255）

        # 将中间部分的图像复制到白色画布的相应位置
        white_canvas[top_crop:bottom_crop, left_crop:right_crop] = image_cv[top_crop:bottom_crop, left_crop:right_crop]

        # # 获取图像的宽度和高度
        # width, height = screenshot.size
        # # 创建一个白色背景的图像
        # white_image = Image.new('RGB', (width, height), (255, 255, 255))
        # # 将上半部分复制到白色背景图像上
        # white_image.paste(screenshot.crop((width * 0.8, height * 0.4, width, height * 0.8)), (0, 0))
        save_path = os.path.join(save_dir, "region_screenshot_0.png")
        # white_image.save(save_path)
        CvTool.imwrite(save_path, white_canvas)

        # 3. 使用 读光OCR 获取详细的 OCR 数据
        # image_to_data 返回一个字典，包含已识别的文字、位置、置信度等信息
        # pytesseract.image_to_data(screenshot, lang=lang, output_type=Output.DICT)
        ocr_data = do_handle_image(screenshot)

        # 4. 遍历 OCR 结果，查找目标文字
        num_boxes = len(ocr_data['level'])
        for i in range(len(ocr_data)):
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


def do_handle_image(image, type):
    # 模型参数
    rec_path = r"models\duguang-ocr-onnx-v2\base_seglink++\recognition_model_general"                     # 文字识别模型路径
    det_path = r"models\duguang-ocr-onnx-v2\base_seglink++\detection_model_general\model_1600x1600.onnx"    # 文本检测模型文件路径
    img_size=1600           # 文本检测模型内部预处理时使用的固定尺寸（单位：像素），与输入图片的实际尺寸无关
    model_type = "seglink"  # 模型类型
    cpu_thread_num=4        # onnx 运行线程数, 线程越多，识别速度越快
    device = "cpu"          # 如果想使用gpu设置为 `device = "gpu"`，同时cpu_thread_num会失效

    # 初始化模型
    ocr = DGOCR(rec_path, det_path, img_size=img_size, model_type=model_type, device=device, cpu_thread_num=cpu_thread_num)

    # img1 = "data/region_screenshot.png"     # 图片
    batch_image = [image]  # 批量，输入的图片数量就是批次大小

    # 识别图片
    ocr_result = ocr.run(images=batch_image)

    # # 打印结果
    # for i in range(len(ocr_result)):
    #     print(f"第{i+1}张图片结果")
    #     print(f"{ocr_result[i]}")

    # 可视化
    for i in range(len(ocr_result)):
        org_path = f"data/region_screenshot.png"
        save_path = f"data/region_screenshot-{i}.png"
        ocr.draw(org_path, ocr_result[i], save_path)
        print(f"已经将可视化结果保存至：{save_path}")

    return ocr_result