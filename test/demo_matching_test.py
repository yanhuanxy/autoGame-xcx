"""
匹配测试功能演示脚本
展示如何使用新的匹配测试功能
"""
import sys
import os
import cv2
import numpy as np
from core.opencv_util import CvTool

# 添加src目录到Python路径
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_path)

def create_demo_images():
    """创建演示图像"""
    print("创建演示图像...")
    
    # 创建演示目录
    demo_dir = "demo_images"
    if not os.path.exists(demo_dir):
        os.makedirs(demo_dir)
    
    # 1. 创建原始按钮图像
    original = np.zeros((80, 160, 3), dtype=np.uint8)
    # 绘制按钮背景
    cv2.rectangle(original, (10, 10), (150, 70), (50, 150, 50), -1)
    # 绘制按钮边框
    cv2.rectangle(original, (10, 10), (150, 70), (255, 255, 255), 2)
    # 添加文字
    cv2.putText(original, "START", (45, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    CvTool.imwrite(os.path.join(demo_dir, "start_button.png"), original)
    
    # 2. 创建相似按钮（亮度稍有不同）
    similar = cv2.convertScaleAbs(original, alpha=1.1, beta=15)
    CvTool.imwrite(os.path.join(demo_dir, "start_button_bright.png"), similar)
    
    # 3. 创建不同的按钮
    different = np.zeros((80, 160, 3), dtype=np.uint8)
    cv2.rectangle(different, (10, 10), (150, 70), (150, 50, 50), -1)
    cv2.rectangle(different, (10, 10), (150, 70), (255, 255, 255), 2)
    cv2.putText(different, "STOP", (50, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    CvTool.imwrite(os.path.join(demo_dir, "stop_button.png"), different)
    
    # 4. 创建带噪声的按钮
    noisy = original.copy()
    noise = np.random.randint(0, 30, original.shape, dtype=np.uint8)
    noisy = cv2.add(noisy, noise)
    CvTool.imwrite(os.path.join(demo_dir, "start_button_noisy.png"), noisy)
    
    print(f"✓ 演示图像已创建在 {demo_dir} 目录")
    return demo_dir

def demo_image_matching():
    """演示图像匹配功能"""
    print("\n演示图像匹配功能...")
    
    try:
        from src.image_matcher import ImageMatcher
        
        matcher = ImageMatcher()
        demo_dir = create_demo_images()
        
        # 加载图像
        original = CvTool.imread(os.path.join(demo_dir, "start_button.png"))
        similar = CvTool.imread(os.path.join(demo_dir, "start_button_bright.png"))
        different = CvTool.imread(os.path.join(demo_dir, "stop_button.png"))
        noisy = CvTool.imread(os.path.join(demo_dir, "start_button_noisy.png"))
        
        # 测试用例
        test_cases = [
            ("相同图像", original, original),
            ("亮度变化", original, similar),
            ("不同按钮", original, different),
            ("噪声图像", original, noisy)
        ]
        
        algorithms = [
            ("template_matching", "模板匹配"),
            ("ssim", "结构相似性"),
            ("feature_matching", "特征匹配"),
            ("hybrid", "混合匹配")
        ]
        
        print("\n匹配测试结果:")
        print("=" * 80)
        print(f"{'算法':<15} | {'测试用例':<12} | {'相似度':<8} | {'匹配结果':<8} | {'建议'}")
        print("=" * 80)
        
        for algo_id, algo_name in algorithms:
            for case_name, img1, img2 in test_cases:
                try:
                    is_match, similarity = matcher.match_images(img1, img2, algo_id, 0.8)
                    match_str = "✓ 匹配" if is_match else "✗ 失败"
                    
                    # 生成建议
                    if similarity > 0.9:
                        suggestion = "优秀"
                    elif similarity > 0.8:
                        suggestion = "良好"
                    elif similarity > 0.6:
                        suggestion = "可调整阈值"
                    else:
                        suggestion = "需重新标记"
                    
                    print(f"{algo_name:<15} | {case_name:<12} | {similarity:<8.3f} | {match_str:<8} | {suggestion}")
                    
                except Exception as e:
                    print(f"{algo_name:<15} | {case_name:<12} | 错误: {str(e)}")
        
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"演示失败: {e}")
        return False

def show_usage_guide():
    """显示使用指南"""
    print("\n" + "="*60)
    print("🔍 匹配测试功能使用指南")
    print("="*60)
    
    print("\n📋 功能特性:")
    print("   ✓ 4种匹配算法：模板匹配、SSIM、特征匹配、混合匹配")
    print("   ✓ 实时截图测试：每次测试重新截图")
    print("   ✓ 连续测试模式：定时自动测试")
    print("   ✓ 差异图像分析：可视化显示图像差异")
    print("   ✓ 详细统计信息：成功率、平均相似度等")
    print("   ✓ 智能阈值建议：根据测试结果推荐最佳阈值")
    
    print("\n🚀 使用步骤:")
    print("   1. 启动GUI工具:")
    print("      python start_gui.py")
    print()
    print("   2. 创建模板:")
    print("      • 填写模板名称和游戏名称")
    print("      • 点击'截取游戏界面'")
    print("      • 添加任务")
    print()
    print("   3. 标记区域:")
    print("      • 用鼠标拖拽选择操作区域")
    print("      • 在配置对话框中设置参数")
    print()
    print("   4. 测试匹配:")
    print("      • 点击'测试匹配'按钮")
    print("      • 选择匹配算法和参数")
    print("      • 点击'开始测试'或'连续测试'")
    print()
    print("   5. 分析结果:")
    print("      • 查看匹配成功率和相似度")
    print("      • 观察差异图像分析")
    print("      • 根据建议调整阈值")
    
    print("\n💡 最佳实践:")
    print("   • 先使用'混合匹配'算法进行初步测试")
    print("   • 如果成功率低于80%，考虑重新标记区域")
    print("   • 使用连续测试验证匹配稳定性")
    print("   • 根据差异图像分析调整标记区域")
    print("   • 在不同光照条件下测试匹配效果")
    
    print("\n🔧 参数调整建议:")
    print("   • 匹配阈值：0.8-0.9（推荐0.85）")
    print("   • 测试次数：3-5次（验证稳定性）")
    print("   • 连续测试：用于监控动态变化")
    print("   • 实时截图：模拟真实使用场景")
    
    print("\n⚠️  注意事项:")
    print("   • 确保微信窗口处于前台")
    print("   • 游戏界面应保持稳定（无动画）")
    print("   • 标记区域应包含足够的特征信息")
    print("   • 避免标记包含动态内容的区域")

def main():
    """主函数"""
    print("🎮 匹配测试功能演示")
    print("="*40)
    
    # 演示图像匹配
    if demo_image_matching():
        print("\n✅ 图像匹配演示成功！")
    else:
        print("\n❌ 图像匹配演示失败！")
        return
    
    # 显示使用指南
    show_usage_guide()
    
    print("\n🎉 匹配测试功能已完善！")
    print("现在可以在GUI中使用完整的匹配测试功能了。")

if __name__ == "__main__":
    main()
