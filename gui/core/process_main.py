"""
游戏自动化系统主程序
提供命令行界面进行系统测试和基本操作
"""
import sys
import os
import argparse
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.core.window_controller import GameWindowController
from gui.core.image_matcher import ImageMatcher
from gui.core.coordinate_converter import CoordinateConverter
from gui.core.template_manager import TemplateManager
from gui.core.game_executor import GameExecutor

def test_window_detection():
    """测试窗口检测功能"""
    print("=" * 50)
    print("测试窗口检测功能")
    print("=" * 50)
    
    controller = GameWindowController()
    
    print("1. 查找微信窗口...")
    wechat_window = controller.find_wechat_window()
    if wechat_window:
        print(f"✓ 找到微信窗口: {wechat_window['title']}")
        print(f"  进程名: {wechat_window['process_name']}")
    else:
        print("✗ 未找到微信窗口")
        return False
    
    print("\n2. 激活窗口...")
    if controller.activate_window():
        print("✓ 窗口激活成功")
    else:
        print("✗ 窗口激活失败")
        return False
    
    print("\n3. 获取窗口信息...")
    rect = controller.get_window_rect()
    if rect:
        print(f"✓ 窗口位置: x={rect['left']}, y={rect['top']}")
        print(f"  窗口大小: {rect['width']}x{rect['height']}")
    
    resolution = controller.get_current_resolution()
    if resolution:
        print(f"✓ 当前分辨率: {resolution['width']}x{resolution['height']}")
    
    dpi = controller.get_system_dpi()
    print(f"✓ 系统DPI: {dpi['x']}x{dpi['y']}")
    
    print("\n4. 截取窗口截图...")
    screenshot = controller.capture_window_screenshot()
    if screenshot is not None:
        print(f"✓ 截图成功，尺寸: {screenshot.shape}")
        
        # 保存截图
        screenshot_path = f"test_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        import cv2
        CvTool.imwrite(screenshot_path, screenshot)
        print(f"✓ 截图已保存: {screenshot_path}")
    else:
        print("✗ 截图失败")
        return False
    
    return True

def test_image_matching():
    """测试图像匹配功能"""
    print("=" * 50)
    print("测试图像匹配功能")
    print("=" * 50)
    
    matcher = ImageMatcher()
    
    # 创建测试图像
    import cv2
    import numpy as np
    
    print("1. 创建测试图像...")
    
    # 原始图像 - 绿色矩形
    original = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(original, (20, 20), (80, 80), (0, 255, 0), -1)
    
    # 相同图像
    same = original.copy()
    
    # 稍微不同的图像（亮度变化）
    different = cv2.convertScaleAbs(original, alpha=1.2, beta=10)
    
    # 完全不同的图像 - 红色圆形
    totally_different = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.circle(totally_different, (50, 50), 30, (255, 0, 0), -1)
    
    print("✓ 测试图像创建完成")
    
    print("\n2. 测试不同匹配方法:")
    
    methods = ['template_matching', 'ssim', 'feature_matching', 'hybrid']
    test_cases = [
        ("相同图像", same, True),
        ("亮度变化", different, True),
        ("完全不同", totally_different, False)
    ]
    
    for method in methods:
        print(f"\n--- {method} ---")
        for case_name, test_img, expected in test_cases:
            match, score = matcher.match_images(original, test_img, method, 0.8)
            status = "✓" if match == expected else "✗"
            print(f"{status} {case_name}: 匹配={match}, 分数={score:.3f}")
    
    return True

def test_coordinate_conversion():
    """测试坐标转换功能"""
    print("=" * 50)
    print("测试坐标转换功能")
    print("=" * 50)
    
    # 模拟不同分辨率场景
    test_cases = [
        {
            'name': '相同分辨率',
            'template_res': {'width': 1920, 'height': 1080},
            'current_res': {'width': 1920, 'height': 1080}
        },
        {
            'name': '缩小分辨率',
            'template_res': {'width': 1920, 'height': 1080},
            'current_res': {'width': 1366, 'height': 768}
        },
        {
            'name': '放大分辨率',
            'template_res': {'width': 1366, 'height': 768},
            'current_res': {'width': 1920, 'height': 1080}
        }
    ]
    
    # 测试坐标
    test_coords = {
        'area': {'x': 400, 'y': 300, 'width': 120, 'height': 40},
        'click': {'x': 460, 'y': 320}
    }
    
    for case in test_cases:
        print(f"\n--- {case['name']} ---")
        converter = CoordinateConverter(case['template_res'], case['current_res'])
        
        # 测试区域坐标转换
        converted_area = converter.convert_coordinates(test_coords['area'])
        print(f"区域坐标: {test_coords['area']} -> {converted_area}")
        
        # 测试点击坐标转换
        converted_click = converter.convert_click_point(test_coords['click'])
        print(f"点击坐标: {test_coords['click']} -> {converted_click}")
        
        # 测试分辨率匹配
        is_match = converter.is_resolution_match()
        print(f"分辨率匹配: {is_match}")
        
        # 获取缩放信息
        scale_info = converter.get_scale_info()
        print(f"缩放比例: x={scale_info['scale_ratio']['x']:.3f}, y={scale_info['scale_ratio']['y']:.3f}")
    
    return True

def test_template_management():
    """测试模板管理功能"""
    print("=" * 50)
    print("测试模板管理功能")
    print("=" * 50)
    
    manager = TemplateManager()
    
    print("1. 创建测试模板...")
    template = manager.create_template_structure(
        "测试模板",
        "测试小程序游戏",
        {'width': 1920, 'height': 1080, 'dpi': 96}
    )
    print("✓ 模板结构创建成功")
    
    print("\n2. 添加任务...")
    task = manager.add_task_to_template(template, "test_task", "测试任务", 1)
    print("✓ 任务添加成功")
    
    print("\n3. 添加步骤...")
    manager.add_step_to_task(
        task,
        "test_step",
        "image_verify_and_click",
        {'x': 400, 'y': 300, 'width': 120, 'height': 40},
        "test_button.png",
        0.85,
        {'x': 460, 'y': 320},
        2000
    )
    print("✓ 步骤添加成功")
    
    print("\n4. 保存模板...")
    filepath = manager.save_template(template, "test_template.json")
    if filepath:
        print(f"✓ 模板保存成功: {filepath}")
    else:
        print("✗ 模板保存失败")
        return False
    
    print("\n5. 加载模板...")
    loaded_template = manager.load_template(filepath)
    if loaded_template:
        print("✓ 模板加载成功")
        print(f"  模板名称: {loaded_template['template_info']['name']}")
        print(f"  任务数量: {len(loaded_template['tasks'])}")
    else:
        print("✗ 模板加载失败")
        return False
    
    print("\n6. 列出所有模板...")
    templates = manager.list_templates()
    print(f"✓ 找到 {len(templates)} 个模板:")
    for tmpl in templates:
        print(f"  - {tmpl['name']} ({tmpl['filename']})")
    
    return True

def run_full_test():
    """运行完整测试"""
    print("开始运行完整系统测试...\n")
    
    tests = [
        ("窗口检测", test_window_detection),
        ("图像匹配", test_image_matching),
        ("坐标转换", test_coordinate_conversion),
        ("模板管理", test_template_management)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"\n{test_name}测试: {'通过' if result else '失败'}")
        except Exception as e:
            print(f"\n{test_name}测试异常: {e}")
            results.append((test_name, False))
        
        print("\n" + "="*50 + "\n")
    
    # 打印测试总结
    print("测试总结:")
    print("-" * 30)
    passed = 0
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 项测试通过")
    
    return passed == len(results)

def execute_template(template_path):
    """执行指定模板"""
    if not os.path.exists(template_path):
        print(f"模板文件不存在: {template_path}")
        return False
    
    executor = GameExecutor()
    return executor.execute_template(template_path)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='游戏自动化系统 - Phase 2 完善版本')
    parser.add_argument('--test', choices=['window', 'image', 'coordinate', 'template', 'all'],
                       help='运行指定测试')
    parser.add_argument('--execute', type=str, help='执行指定模板文件')
    parser.add_argument('--list-templates', action='store_true', help='列出所有可用模板')
    parser.add_argument('--gui', action='store_true', help='启动图形界面模板创建工具')
    parser.add_argument('--report', type=str, help='生成指定执行数据的报告')

    args = parser.parse_args()
    
    if args.test:
        if args.test == 'window':
            test_window_detection()
        elif args.test == 'image':
            test_image_matching()
        elif args.test == 'coordinate':
            test_coordinate_conversion()
        elif args.test == 'template':
            test_template_management()
        elif args.test == 'all':
            run_full_test()
    elif args.execute:
        execute_template(args.execute)
    elif args.list_templates:
        manager = TemplateManager()
        templates = manager.list_templates()
        if templates:
            print("可用模板:")
            for tmpl in templates:
                print(f"  {tmpl['name']} - {tmpl['filename']}")
        else:
            print("未找到任何模板")
    elif args.gui:
        try:
            from template_creator_gui import main as gui_main
            gui_main()
        except ImportError as e:
            print(f"启动GUI失败，请确保已安装PyQt6: {e}")
        except Exception as e:
            print(f"GUI启动异常: {e}")
    elif args.report:
        try:
            from report_generator import ReportGenerator
            generator = ReportGenerator()

            # 加载执行数据
            with open(args.report, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)

            # 生成报告
            html_path = generator.generate_html_report(data.get('execution_data', {}),
                                                     data.get('template_info', {}))
            if html_path:
                print(f"HTML报告已生成: {html_path}")

        except Exception as e:
            print(f"生成报告时出错: {e}")
    else:
        print("游戏自动化系统 - Phase 2 完善版本")
        print("使用 --help 查看可用选项")
        print("\n快速测试:")
        print("  python process_main.py --test all")
        print("\n执行模板:")
        print("  python process_main.py --execute templates/your_template.json")
        print("\n启动GUI工具:")
        print("  python process_main.py --gui")
        print("\n生成报告:")
        print("  python process_main.py --report reports/execution_report.json")

if __name__ == "__main__":
    main()
