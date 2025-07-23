"""
游戏执行引擎
核心执行模块，基于图像比对执行游戏自动化任务
"""
import cv2
import pyautogui
import time
import json
import numpy as np
from PIL import ImageGrab
import os
from datetime import datetime

from gui.core.window_controller import GameWindowController
from gui.core.image_matcher import ImageMatcher
from gui.core.coordinate_converter import CoordinateConverter
from gui.core.template_manager import TemplateManager
from gui.core.report_generator import ReportGenerator
from util.constants import REPORTS_PATH
from util.opencv_util import CvTool

class GameExecutor:
    def __init__(self):
        self.window_controller = GameWindowController()
        self.image_matcher = ImageMatcher()
        self.template_manager = TemplateManager()
        self.report_generator = ReportGenerator()
        self.coordinate_converter = None
        self.current_template = None
        self.dry_run_mode = False  # 模拟运行模式
        self.execution_report = {
            'start_time': None,
            'end_time': None,
            'tasks': [],
            'summary': {}
        }
        
        # 禁用pyautogui的安全机制（仅用于开发测试）
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.5
    
    def load_template(self, template_path):
        """加载模板文件"""
        print(f"加载模板: {template_path}")
        
        self.current_template = self.template_manager.load_template(template_path)
        if not self.current_template:
            print("模板加载失败")
            return False
        
        print(f"模板加载成功: {self.current_template['template_info']['name']}")
        return True
    
    def initialize_execution(self):
        """初始化执行环境"""
        print("初始化执行环境...")
        
        # 1. 查找微信窗口
        wechat_window = self.window_controller.find_wechat_window()
        if not wechat_window:
            print("未找到微信窗口")
            return False
        
        print(f"找到微信窗口: {wechat_window['title']}")
        
        # 2. 激活窗口
        if not self.window_controller.activate_window():
            print("无法激活微信窗口")
            return False
        
        # 3. 获取当前分辨率
        current_resolution = self.window_controller.get_current_resolution()
        if not current_resolution:
            print("无法获取当前分辨率")
            return False
        
        template_resolution = self.current_template['template_info']['template_resolution']
        
        print(f"模板分辨率: {template_resolution['width']}x{template_resolution['height']}")
        print(f"当前分辨率: {current_resolution['width']}x{current_resolution['height']}")
        
        # 4. 初始化坐标转换器
        self.coordinate_converter = CoordinateConverter(template_resolution, current_resolution)
        
        # 5. 检查是否需要调整窗口大小
        if not self.coordinate_converter.is_resolution_match():
            print("分辨率不匹配，尝试调整窗口大小...")
            if self.window_controller.resize_window(template_resolution):
                print("窗口大小调整成功")
                # 重新获取分辨率
                current_resolution = self.window_controller.get_current_resolution()
                self.coordinate_converter = CoordinateConverter(template_resolution, current_resolution)
            else:
                print("窗口大小调整失败，将使用坐标转换")
        
        return True

    def initialize_execution_for_test(self, template_data):
        """为测试初始化执行环境"""
        print("初始化测试执行环境...")

        # 设置当前模板
        self.current_template = template_data

        # 1. 查找微信窗口
        wechat_window = self.window_controller.find_wechat_window()
        if not wechat_window:
            print("未找到微信窗口")
            return False

        print(f"找到微信窗口: {wechat_window['title']}")

        # 2. 激活窗口
        if not self.window_controller.activate_window():
            print("无法激活微信窗口")
            return False

        # 3. 获取当前分辨率
        current_resolution = self.window_controller.get_current_resolution()
        if not current_resolution:
            print("无法获取当前分辨率")
            return False

        template_resolution = template_data['template_info']['template_resolution']

        print(f"模板分辨率: {template_resolution['width']}x{template_resolution['height']}")
        print(f"当前分辨率: {current_resolution['width']}x{current_resolution['height']}")

        # 4. 初始化坐标转换器
        self.coordinate_converter = CoordinateConverter(template_resolution, current_resolution)

        return True

    def execute_template(self, template_path):
        """执行模板"""
        print(f"\n开始执行模板: {template_path}")
        
        # 初始化执行报告
        self.execution_report = {
            'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'end_time': None,
            'template_path': template_path,
            'tasks': [],
            'summary': {}
        }
        
        # 1. 加载模板
        if not self.load_template(template_path):
            return False
        
        # 2. 初始化执行环境
        if not self.initialize_execution():
            return False
        
        # 3. 按优先级执行任务
        tasks = sorted(self.current_template['tasks'], key=lambda x: x.get('priority', 999))
        
        completed_tasks = 0
        failed_tasks = 0
        
        for task in tasks:
            if not task.get('enabled', True):
                print(f"跳过已禁用的任务: {task['task_name']}")
                continue
            
            print(f"\n执行任务: {task['task_name']}")
            
            task_result = self.execute_task(task)
            self.execution_report['tasks'].append(task_result)
            
            if task_result['status'] == 'completed':
                completed_tasks += 1
            else:
                failed_tasks += 1
            
            # 任务间延迟
            time.sleep(self.current_template['global_settings'].get('step_delay', 1000) / 1000)
        
        # 4. 生成执行报告
        self.execution_report['end_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.execution_report['summary'] = {
            'total_tasks': len(tasks),
            'completed': completed_tasks,
            'failed': failed_tasks,
            'success_rate': f"{(completed_tasks / len(tasks) * 100):.1f}%" if tasks else "0%"
        }
        
        self.save_execution_report()
        self.generate_enhanced_reports()
        self.print_execution_summary()

        return True
    
    def execute_task(self, task):
        """执行单个任务"""
        task_result = {
            'task_name': task['task_name'],
            'task_id': task['task_id'],
            'status': 'failed',
            'steps': [],
            'retry_count': 0,
            'error_message': None
        }
        
        max_retry = self.current_template['global_settings'].get('max_retry', 3)
        
        for retry in range(max_retry + 1):
            if retry > 0:
                print(f"  重试第 {retry} 次...")
                task_result['retry_count'] = retry
                time.sleep(2)  # 重试前等待
            
            success = True
            task_result['steps'] = []
            
            # 执行任务的所有步骤
            for step in task['steps']:
                step_result = self.execute_step(step)
                task_result['steps'].append(step_result)
                
                if not step_result['success']:
                    success = False
                    task_result['error_message'] = step_result.get('error_message', '步骤执行失败')
                    break
                
                # 步骤间延迟
                wait_time = step.get('wait_after', 1000) / 1000
                time.sleep(wait_time)
            
            if success:
                task_result['status'] = 'completed'
                print(f"  任务完成: {task['task_name']}")
                break
            else:
                print(f"  任务失败: {task['task_name']} - {task_result['error_message']}")
        
        return task_result
    
    def execute_step(self, step):
        """执行单个步骤"""
        step_result = {
            'step_id': step['step_id'],
            'action_type': step['action_type'],
            'success': False,
            'similarity_score': 0.0,
            'error_message': None
        }
        
        try:
            print(f"    执行步骤: {step['step_id']}")
            
            # 1. 转换用户标记区域坐标
            marked_area = step['user_marked_area']
            converted_area = self.coordinate_converter.convert_coordinates(marked_area)
            
            # 2. 获取窗口位置偏移
            window_rect = self.window_controller.get_window_rect()
            if not window_rect:
                step_result['error_message'] = "无法获取窗口位置"
                return step_result
            
            # 3. 计算绝对屏幕坐标
            abs_left = window_rect['left'] + converted_area['x']
            abs_top = window_rect['top'] + converted_area['y']
            abs_right = abs_left + converted_area['width']
            abs_bottom = abs_top + converted_area['height']
            
            # 4. 截取指定区域
            current_image = ImageGrab.grab(bbox=(abs_left, abs_top, abs_right, abs_bottom))
            current_image_cv = cv2.cvtColor(np.array(current_image), cv2.COLOR_RGB2BGR)
            
            # 5. 加载参考图像
            reference_image_path = os.path.join(
                self.template_manager.images_dir,
                self.current_template['template_info']['name'],
                step['reference_image']
            )
            
            reference_image = self.image_matcher.load_reference_image(reference_image_path)
            CvTool.imwrite('./data/test.png', reference_image)
            CvTool.imwrite('./data/test1.png', current_image_cv)
            # 6. 进行图像比对
            match_threshold = step.get('match_threshold', 0.85)
            is_match, similarity = self.image_matcher.match_images(
                current_image_cv, 
                reference_image, 
                'hybrid', 
                match_threshold
            )
            
            step_result['similarity_score'] = similarity
            
            print(f"      图像匹配: {is_match}, 相似度: {similarity:.3f}")
            
            if is_match:
                # 7. 执行对应操作
                if step['action_type'] == 'image_verify_and_click':
                    # 转换点击坐标
                    click_point = step.get('click_point', {'x': marked_area['x'] + marked_area['width']//2, 
                                                          'y': marked_area['y'] + marked_area['height']//2})
                    converted_click = self.coordinate_converter.convert_click_point(click_point)
                    
                    # 计算绝对点击坐标
                    abs_click_x = window_rect['left'] + converted_click['x']
                    abs_click_y = window_rect['top'] + converted_click['y']
                    
                    # 执行点击（如果不是模拟运行模式）
                    if not self.dry_run_mode:
                        pyautogui.click(abs_click_x, abs_click_y)
                        print(f"      点击位置: ({abs_click_x}, {abs_click_y})")
                    else:
                        print(f"      [模拟] 点击位置: ({abs_click_x}, {abs_click_y})")
                    
                elif step['action_type'] == 'image_verify_only':
                    print(f"      验证成功")
                
                step_result['success'] = True
            else:
                step_result['error_message'] = f"图像匹配失败，相似度 {similarity:.3f} 低于阈值 {match_threshold}"
        
        except Exception as e:
            step_result['error_message'] = f"步骤执行异常: {str(e)}"
            print(f"      步骤执行异常: {e}")
        
        return step_result
    
    def save_execution_report(self):
        """保存执行报告"""
        try:
            reports_dir = REPORTS_PATH
            if not os.path.exists(reports_dir):
                os.makedirs(reports_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"execution_report_{timestamp}.json"
            report_path = os.path.join(reports_dir, report_filename)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(self.execution_report, f, ensure_ascii=False, indent=2)
            
            print(f"\n执行报告已保存: {report_path}")
            
        except Exception as e:
            print(f"保存执行报告时出错: {e}")

    def generate_enhanced_reports(self):
        """生成增强的执行报告"""
        try:
            # 获取模板信息
            template_info = None
            if self.current_template:
                template_info = self.current_template.get('template_info', {})

            # 生成HTML报告
            html_path = self.report_generator.generate_html_report(
                self.execution_report, template_info
            )

            # 生成JSON报告
            json_path = self.report_generator.generate_json_report(
                self.execution_report, template_info
            )

            if html_path:
                print(f"HTML报告已生成: {html_path}")
            if json_path:
                print(f"JSON报告已生成: {json_path}")

        except Exception as e:
            print(f"生成增强报告时出错: {e}")

    def print_execution_summary(self):
        """打印执行摘要"""
        print(f"\n{'='*50}")
        print(f"执行摘要")
        print(f"{'='*50}")
        print(f"开始时间: {self.execution_report['start_time']}")
        print(f"结束时间: {self.execution_report['end_time']}")
        print(f"总任务数: {self.execution_report['summary']['total_tasks']}")
        print(f"完成任务: {self.execution_report['summary']['completed']}")
        print(f"失败任务: {self.execution_report['summary']['failed']}")
        print(f"成功率: {self.execution_report['summary']['success_rate']}")
        print(f"{'='*50}")

# 测试函数
def test_game_executor():
    """测试游戏执行引擎"""
    executor = GameExecutor()
    
    # 这里需要一个实际的模板文件进行测试
    # executor.execute_template("templates/test_template.json")
    
    print("游戏执行引擎测试完成")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        template_path = sys.argv[1]
        executor = GameExecutor()
        executor.execute_template(template_path)
    else:
        test_game_executor()
