"""OCR 引擎封装：基于自研 DGOCR 提供文字查找能力。

DGOCR.run 返回结构：
    batch_ocr_result: list[list[list[box, (text, score)]]]
    - 外层：每张图片一个元素
    - 中层：该图片的所有识别结果
    - 内层：[box, (text, score)]
        - box：4 个点坐标，shape (4, 2)
        - text：识别出的字符串
        - score：置信度（0.0 ~ 1.0）
"""
import logging
import os

import cv2
import numpy as np
import pyautogui
import win32gui
from PIL import Image

from autogame_xcx.ocr.dgocr.dgocr import DGOCR
from autogame_xcx.utils.opencv import CvTool

logger = logging.getLogger(__name__)


# DGOCR 模型路径（基于项目根的相对路径）
_REC_PATH = r"models/duguang-ocr-onnx-v2/base_seglink++/recognition_model_general"
_DET_PATH = r"models/duguang-ocr-onnx-v2/base_seglink++/detection_model_general/model_1600x1600.onnx"
_IMG_SIZE = 1600
_MODEL_TYPE = "seglink"
_CPU_THREAD_NUM = 4
_DEVICE = "cpu"

# 置信度阈值：低于此值的识别结果视为噪声
_CONFIDENCE_THRESHOLD = 0.6

# 单例：避免每次调用都重新加载 ONNX 模型（加载耗时数秒）
_OCR_SINGLETON: DGOCR | None = None


def _get_ocr() -> DGOCR:
    global _OCR_SINGLETON
    if _OCR_SINGLETON is None:
        _OCR_SINGLETON = DGOCR(
            rec_path=_REC_PATH,
            det_path=_DET_PATH,
            img_size=_IMG_SIZE,
            model_type=_MODEL_TYPE,
            device=_DEVICE,
            cpu_thread_num=_CPU_THREAD_NUM,
        )
    return _OCR_SINGLETON


def find_text_in_window(text_to_find: str, hwnd: int) -> tuple[int, int] | None:
    """在指定窗口内查找文字，返回中心坐标（相对窗口左上角）。

    Args:
        text_to_find: 要查找的文字字符串。
        hwnd: 目标窗口的句柄。

    Returns:
        找到时返回 (x, y) 中心坐标；未找到返回 None。
    """
    try:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        screenshot = screenshot.convert("RGB")

        # 仅保留右下区域用于识别（与原逻辑保持一致：80%~100% 宽，40%~80% 高）
        img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        img_height, img_width = img_cv.shape[:2]
        left_crop = int(img_width * 0.8)
        right_crop = img_width
        top_crop = int(img_height * 0.4)
        bottom_crop = int(img_height * 0.8)

        white_canvas = np.ones_like(img_cv) * 255
        white_canvas[top_crop:bottom_crop, left_crop:right_crop] = (
            img_cv[top_crop:bottom_crop, left_crop:right_crop]
        )

        save_dir = "./data"
        os.makedirs(save_dir, exist_ok=True)
        CvTool.imwrite(os.path.join(save_dir, "region_screenshot.png"), white_canvas)

        cropped_pil = Image.fromarray(
            cv2.cvtColor(white_canvas, cv2.COLOR_BGR2RGB)
        )

        ocr_result = do_handle_image(cropped_pil)
        if not ocr_result:
            logger.info("OCR 未识别到任何文字")
            return None

        one_image_result = ocr_result[0] if isinstance(ocr_result, list) and ocr_result else []
        for item in one_image_result:
            box, text_score = item[0], item[1]
            text, score = text_score
            if score < _CONFIDENCE_THRESHOLD:
                continue
            if text_to_find in text:
                cx, cy = _box_center(box)
                logger.info(
                    "在窗口中找到文字 '%s'（命中：'%s'），位置: (%d, %d)，置信度: %.3f",
                    text_to_find, text, cx, cy, score,
                )
                return (cx, cy)

        logger.info("在窗口中未找到文字: '%s'", text_to_find)
        return None

    except Exception as e:
        logger.exception("查找文字 '%s' 时发生错误", text_to_find)
        return None


def do_handle_image(image) -> list:
    """对单张图片执行 OCR，返回 DGOCR 原始结果。

    Args:
        image: PIL.Image 或 np.ndarray 输入图像。

    Returns:
        DGOCR.run 的原始返回值：list[list[list[box, (text, score)]]]。
        一张图片时取 [0] 即该图所有识别结果。
    """
    ocr = _get_ocr()
    batch_image = [image]
    return ocr.run(images=batch_image, type=_MODEL_TYPE)


def _box_center(box) -> tuple[int, int]:
    """根据 4 个点计算中心坐标。box 形如 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]。"""
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return int(sum(xs) / len(xs)), int(sum(ys) / len(ys))
