"""
模板管理模块
处理JSON模板的加载、保存和验证
"""
import json
import os
from datetime import datetime
from core.opencv_util import CvTool

class TemplateManager:
    def __init__(self, templates_dir="templates", images_dir="reference_images"):
        self.templates_dir = templates_dir
        self.images_dir = images_dir
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        for directory in [self.templates_dir, self.images_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"创建目录: {directory}")
    
    def create_template_structure(self, template_name, game_name, resolution):
        """
        创建基础模板结构
        
        Args:
            template_name: 模板名称
            game_name: 游戏名称
            resolution: 分辨率信息 {'width': int, 'height': int, 'dpi': int}
        
        Returns:
            dict: 模板数据结构
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = f"v1.0_{timestamp}"
        
        template = {
            "template_info": {
                "name": template_name,
                "version": version,
                "game_name": game_name,
                "description": f"{template_name}自动化模板",
                "created_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "template_resolution": {
                    "width": resolution['width'],
                    "height": resolution['height'],
                    "dpi": resolution.get('dpi', 96)
                }
            },
            "tasks": [],
            "global_settings": {
                "max_retry": 3,
                "step_delay": 1000,
                "screenshot_path": "./screenshots/",
                "reference_images_path": f"./{self.images_dir}/",
                "log_level": "INFO",
                "auto_scale": True,
                "scale_method": "force_resize"
            }
        }
        
        return template
    
    def add_task_to_template(self, template, task_id, task_name, priority=1):
        """向模板添加任务"""
        task = {
            "task_id": task_id,
            "task_name": task_name,
            "priority": priority,
            "enabled": True,
            "steps": []
        }
        
        template["tasks"].append(task)
        return task
    
    def add_step_to_task(self, task, step_id, action_type, user_marked_area, 
                        reference_image, match_threshold=0.85, click_point=None, 
                        wait_after=2000, timeout=5000):
        """向任务添加步骤"""
        step = {
            "step_id": step_id,
            "action_type": action_type,
            "user_marked_area": user_marked_area,
            "reference_image": reference_image,
            "match_threshold": match_threshold,
            "wait_after": wait_after
        }
        
        if action_type == "image_verify_and_click" and click_point:
            step["click_point"] = click_point
        
        if action_type == "image_verify_only":
            step["timeout"] = timeout
        
        task["steps"].append(step)
        return step
    
    def save_template(self, template, filename=None):
        """保存模板到文件"""
        if filename is None:
            template_name = template["template_info"]["name"]
            version = template["template_info"]["version"]
            filename = f"{template_name}_{version}.json"
        
        filename = self._sanitize_filename(filename)
        filepath = os.path.join(self.templates_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
            
            print(f"模板已保存: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"保存模板时出错: {e}")
            return None
    
    def load_template(self, filepath):
        """从文件加载模板"""
        if not os.path.exists(filepath):
            print(f"模板文件不存在: {filepath}")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                template = json.load(f)
            
            if self.validate_template(template):
                print(f"模板加载成功: {filepath}")
                return template
            else:
                print(f"模板格式无效: {filepath}")
                return None
                
        except Exception as e:
            print(f"加载模板时出错: {e}")
            return None
    
    def validate_template(self, template):
        """验证模板数据结构"""
        try:
            required_fields = ["template_info", "tasks", "global_settings"]
            for field in required_fields:
                if field not in template:
                    print(f"缺少必要字段: {field}")
                    return False
            
            template_info = template["template_info"]
            required_info_fields = ["name", "version", "template_resolution"]
            for field in required_info_fields:
                if field not in template_info:
                    print(f"缺少模板信息字段: {field}")
                    return False
            
            resolution = template_info["template_resolution"]
            if "width" not in resolution or "height" not in resolution:
                print("缺少分辨率信息")
                return False
            
            for task in template["tasks"]:
                if not self._validate_task(task):
                    return False
            
            return True
            
        except Exception as e:
            print(f"验证模板时出错: {e}")
            return False
    
    def _validate_task(self, task):
        """验证任务结构"""
        required_fields = ["task_id", "task_name", "steps"]
        for field in required_fields:
            if field not in task:
                print(f"任务缺少必要字段: {field}")
                return False
        
        for step in task["steps"]:
            if not self._validate_step(step):
                return False
        
        return True
    
    def _validate_step(self, step):
        """验证步骤结构"""
        required_fields = ["step_id", "action_type", "user_marked_area", "reference_image"]
        for field in required_fields:
            if field not in step:
                print(f"步骤缺少必要字段: {field}")
                return False
        
        area = step["user_marked_area"]
        required_area_fields = ["x", "y", "width", "height"]
        for field in required_area_fields:
            if field not in area:
                print(f"标记区域缺少字段: {field}")
                return False
        
        return True
    
    def list_templates(self):
        """列出所有可用的模板"""
        templates = []
        
        if not os.path.exists(self.templates_dir):
            return templates
        
        for filename in os.listdir(self.templates_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.templates_dir, filename)
                template = self.load_template(filepath)
                if template:
                    templates.append({
                        'filename': filename,
                        'filepath': filepath,
                        'name': template['template_info']['name'],
                        'version': template['template_info']['version'],
                        'game_name': template['template_info'].get('game_name', 'Unknown'),
                        'created_time': template['template_info'].get('created_time', 'Unknown')
                    })
        
        return templates
    
    def save_reference_image(self, image, image_name, template_name=None):
        """保存参考图像"""
        if template_name:
            template_dir = os.path.join(self.images_dir, template_name)
            if not os.path.exists(template_dir):
                os.makedirs(template_dir)
            filepath = os.path.join(template_dir, image_name)
        else:
            filepath = os.path.join(self.images_dir, image_name)
        
        try:
            CvTool.imwrite(filepath, image)
            print(f"参考图像已保存: {filepath}")
            return filepath
        except Exception as e:
            print(f"保存参考图像时出错: {e}")
            return None
    
    def _sanitize_filename(self, filename):
        """清理文件名，移除不安全字符"""
        import re
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        return filename

# 测试函数
def test_template_manager():
    """测试模板管理功能"""
    print("测试模板管理功能...")
    
    manager = TemplateManager()
    
    # 创建测试模板
    template = manager.create_template_structure(
        "每日签到模板",
        "测试小程序游戏",
        {'width': 1920, 'height': 1080, 'dpi': 96}
    )
    
    # 添加任务和步骤
    task = manager.add_task_to_template(template, "daily_signin", "每日签到", 1)
    manager.add_step_to_task(
        task,
        "signin_button_check",
        "image_verify_and_click",
        {'x': 400, 'y': 300, 'width': 120, 'height': 40},
        "signin_button.png",
        0.85,
        {'x': 460, 'y': 320},
        2000
    )
    
    # 保存和加载测试
    filepath = manager.save_template(template)
    if filepath:
        loaded_template = manager.load_template(filepath)
        if loaded_template:
            print("模板测试成功!")

if __name__ == "__main__":
    test_template_manager()
