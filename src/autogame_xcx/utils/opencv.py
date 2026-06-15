# file: cv_tool.py
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Union, Optional

class CvTool:
    """
    Windows 下可读写中文路径的 OpenCV 工具类
    用法：
        img = CvTool.imread(r"D:/测试/图片/测试.jpg")
        CvTool.imwrite(r"D:/测试/输出/结果.png", img)
    """

    @staticmethod
    def imread(path: Union[str, Path], flags: int = cv2.IMREAD_COLOR) -> Optional[np.ndarray]:
        """
        读取图片，支持中文路径
        :param path: 文件路径
        :param flags: cv2.IMREAD_XXX，默认为彩色
        :return: 成功返回 ndarray，失败返回 None
        """
        if not Path(path).exists():
            return None
        # 二进制读 -> 解码
        data = np.fromfile(str(path), dtype=np.uint8)
        img = cv2.imdecode(data, flags)
        return img

    @staticmethod
    def imwrite(path: Union[str, Path], img: np.ndarray,
                params: Optional[Tuple[int, ...]] = None) -> bool:
        """
        写入图片，支持中文路径
        :param path: 保存路径（自动创建目录）
        :param img: 待保存图像
        :param params: 可选 cv2 编码参数，如 (cv2.IMWRITE_PNG_COMPRESSION, 9)
        :return: 成功返回 True
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        ext = Path(path).suffix.lower()
        # 根据扩展名选择编码器
        if ext in {'.jpg', '.jpeg'}:
            encode_flag = '.jpg'
        elif ext == '.png':
            encode_flag = '.png'
        elif ext == '.bmp':
            encode_flag = '.bmp'
        elif ext in {'.tif', '.tiff'}:
            encode_flag = '.tiff'
        else:
            encode_flag = '.png'  # 默认

        ok, buf = cv2.imencode(encode_flag, img, params or [])
        if not ok:
            return False
        buf.tofile(str(path))
        return True


# -------------- 演示 --------------
if __name__ == "__main__":
    src = r"D:/测试/图片/示例.jpg"
    dst = r"D:/测试/输出/结果.png"

    img = CvTool.imread(src)
    if img is None:
        print("读取失败")
    else:
        print("读取成功，尺寸:", img.shape)
        ok = CvTool.imwrite(dst, img)
        print("写入成功" if ok else "写入失败")