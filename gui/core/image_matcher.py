"""
图像匹配模块
实现多种图像相似度算法，用于模板匹配和识别
"""
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import os

from util.constants import DEBUG_IMAGES_PATH
from util.opencv_util import CvTool

class ImageMatcher:
    def __init__(self):
        self.methods = {
            'template_matching': self._template_matching,
            'ssim': self._ssim_matching,
            'feature_matching': self._feature_matching,
            'histogram': self._histogram_matching,
            'hybrid': self._hybrid_matching
        }
    
    def _template_matching(self, img1, img2, threshold=0.8):
        """
        模板匹配 - 适合精确匹配
        img1: 当前截图区域
        img2: 参考模板图像
        """
        try:
            # 确保图像尺寸一致
            if img1.shape != img2.shape:
                img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
            
            # 转换为灰度图进行匹配
            if len(img1.shape) == 3:
                gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            else:
                gray1 = img1
                
            if len(img2.shape) == 3:
                gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            else:
                gray2 = img2
            
            # 使用归一化相关系数匹配
            result = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            return max_val >= threshold, max_val
            
        except Exception as e:
            print(f"模板匹配出错: {e}")
            return False, 0.0
    
    def _ssim_matching(self, img1, img2, threshold=0.8):
        """
        结构相似性匹配 - 适合光照变化
        """
        try:
            # 转换为灰度图
            if len(img1.shape) == 3:
                gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            else:
                gray1 = img1
                
            if len(img2.shape) == 3:
                gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            else:
                gray2 = img2
            
            # 调整大小一致
            if gray1.shape != gray2.shape:
                gray2 = cv2.resize(gray2, (gray1.shape[1], gray1.shape[0]))
            
            # 计算结构相似性
            similarity = ssim(gray1, gray2)
            
            return similarity >= threshold, similarity
            
        except Exception as e:
            print(f"SSIM匹配出错: {e}")
            return False, 0.0
    
    def _feature_matching(self, img1, img2, threshold=0.3):
        """
        特征点匹配 - 适合形状识别
        """
        try:
            # 转换为灰度图
            if len(img1.shape) == 3:
                gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            else:
                gray1 = img1
                
            if len(img2.shape) == 3:
                gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
            else:
                gray2 = img2
            
            # 使用ORB特征检测器
            orb = cv2.ORB_create(nfeatures=1000)
            kp1, des1 = orb.detectAndCompute(gray1, None)
            kp2, des2 = orb.detectAndCompute(gray2, None)
            
            if des1 is None or des2 is None or len(des1) == 0 or len(des2) == 0:
                return False, 0.0
            
            # 使用BF匹配器
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            
            if len(matches) == 0:
                return False, 0.0
            
            # 计算好的匹配点
            good_matches = [m for m in matches if m.distance < 50]
            
            # 计算匹配度
            if len(kp1) > 0 and len(kp2) > 0:
                similarity = len(good_matches) / min(len(kp1), len(kp2))
            else:
                similarity = 0.0
            
            return similarity >= threshold, similarity
            
        except Exception as e:
            print(f"特征匹配出错: {e}")
            return False, 0.0
    
    def _histogram_matching(self, img1, img2, threshold=0.7):
        """
        直方图匹配 - 适合颜色分布相似的图像
        """
        try:
            # 计算直方图
            hist1 = cv2.calcHist([img1], [0, 1, 2], None, [50, 50, 50], [0, 256, 0, 256, 0, 256])
            hist2 = cv2.calcHist([img2], [0, 1, 2], None, [50, 50, 50], [0, 256, 0, 256, 0, 256])
            
            # 归一化直方图
            cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            
            # 计算相关性
            similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            
            return similarity >= threshold, similarity
            
        except Exception as e:
            print(f"直方图匹配出错: {e}")
            return False, 0.0
    
    def _hybrid_matching(self, img1, img2, threshold=0.8):
        """
        混合匹配策略 - 推荐使用
        按优先级尝试不同的匹配算法
        """
        # 1. 先用快速的模板匹配
        match1, score1 = self._template_matching(img1, img2, threshold)
        if match1 and score1 > 0.9:  # 高置信度直接返回
            return True, score1
        
        # 2. 再用SSIM（对光照变化更鲁棒）
        match2, score2 = self._ssim_matching(img1, img2, threshold)
        if match2 and score2 > 0.85:
            return True, score2
        
        # 3. 最后用特征匹配（对形变更鲁棒）
        match3, score3 = self._feature_matching(img1, img2, threshold * 0.6)  # 特征匹配阈值稍低
        
        # 综合判断
        max_score = max(score1, score2, score3)
        
        # 如果任何一种方法匹配成功，且最高分数达到阈值
        if (match1 or match2 or match3) and max_score >= threshold:
            return True, max_score
        
        return False, max_score
    
    def match_images(self, current_img, reference_img, method='hybrid', threshold=0.8):
        """
        主要的图像匹配接口
        
        Args:
            current_img: 当前截取的图像
            reference_img: 参考模板图像
            method: 匹配方法 ('template_matching', 'ssim', 'feature_matching', 'histogram', 'hybrid')
            threshold: 匹配阈值
        
        Returns:
            tuple: (是否匹配成功, 相似度分数)
        """
        if current_img is None or reference_img is None:
            return False, 0.0
        
        if method not in self.methods:
            print(f"不支持的匹配方法: {method}")
            return False, 0.0
        
        return self.methods[method](current_img, reference_img, threshold)
    
    def load_reference_image(self, image_path):
        """加载参考图像"""
        if not os.path.exists(image_path):
            print(f"参考图像不存在: {image_path}")
            return None
        
        try:
            image = CvTool.imread(image_path)
            if image is None:
                print(f"无法加载图像: {image_path}")
                return None
            return image
        except Exception as e:
            print(f"加载图像时出错: {e}")
            return None
    
    def save_debug_image(self, image, filename):
        """保存调试图像"""
        try:
            debug_dir = DEBUG_IMAGES_PATH
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            
            filepath = os.path.join(debug_dir, filename)
            CvTool.imwrite(filepath, image)
            print(f"调试图像已保存: {filepath}")
        except Exception as e:
            print(f"保存调试图像时出错: {e}")

# 测试函数
def test_image_matcher():
    """测试图像匹配功能"""
    matcher = ImageMatcher()
    
    # 创建测试图像
    print("创建测试图像...")
    
    # 原始图像
    original = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(original, (20, 20), (80, 80), (0, 255, 0), -1)
    CvTool.imwrite("test_original.png", original)
    
    # 相同图像
    same = original.copy()
    
    # 稍微不同的图像（亮度变化）
    different = cv2.convertScaleAbs(original, alpha=1.2, beta=10)
    
    # 完全不同的图像
    totally_different = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.circle(totally_different, (50, 50), 30, (255, 0, 0), -1)
    
    print("\n测试不同匹配方法:")
    
    methods = ['template_matching', 'ssim', 'feature_matching', 'hybrid']
    test_cases = [
        ("相同图像", same),
        ("亮度变化", different),
        ("完全不同", totally_different)
    ]
    
    for method in methods:
        print(f"\n--- {method} ---")
        for case_name, test_img in test_cases:
            match, score = matcher.match_images(original, test_img, method, 0.8)
            print(f"{case_name}: 匹配={match}, 分数={score:.3f}")

if __name__ == "__main__":
    test_image_matcher()
