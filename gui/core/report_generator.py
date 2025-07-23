"""
增强的执行报告生成器
生成详细的HTML和JSON格式执行报告
"""
import json
import os
import base64
from datetime import datetime
import cv2
import numpy as np

from util.constants import REPORTS_PATH


class ReportGenerator:
    def __init__(self, reports_dir=REPORTS_PATH):
        self.reports_dir = reports_dir
        self._ensure_directory()
    
    def _ensure_directory(self):
        """确保报告目录存在"""
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)
    
    def generate_html_report(self, execution_data, template_info=None):
        """生成HTML格式的执行报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_filename = f"execution_report_{timestamp}.html"
        html_path = os.path.join(self.reports_dir, template_info, html_filename)
        
        html_content = self._create_html_content(execution_data, template_info)
        
        try:
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"HTML报告已生成: {html_path}")
            return html_path
            
        except Exception as e:
            print(f"生成HTML报告时出错: {e}")
            return None
    
    def _create_html_content(self, execution_data, template_info):
        """创建HTML报告内容"""
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>游戏自动化执行报告</title>
    <style>
        {self._get_css_styles()}
    </style>
</head>
<body>
    <div class="container">
        <header class="report-header">
            <h1>🎮 游戏自动化执行报告</h1>
            <div class="report-meta">
                <span>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
            </div>
        </header>
        
        {self._create_summary_section(execution_data)}
        {self._create_template_info_section(template_info)}
        {self._create_resolution_info_section(execution_data)}
        {self._create_tasks_section(execution_data)}
        {self._create_statistics_section(execution_data)}
        
        <footer class="report-footer">
            <p>报告由游戏自动化系统自动生成 - Phase 2</p>
        </footer>
    </div>
    
    <script>
        {self._get_javascript()}
    </script>
</body>
</html>
        """
        return html
    
    def _get_css_styles(self):
        """获取CSS样式"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .report-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .report-header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .report-meta {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .section {
            background: white;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .section-header {
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #dee2e6;
            font-weight: bold;
            font-size: 1.2em;
        }
        
        .section-content {
            padding: 20px;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .summary-card {
            text-align: center;
            padding: 20px;
            border-radius: 8px;
            color: white;
        }
        
        .summary-card.success { background: #28a745; }
        .summary-card.warning { background: #ffc107; color: #333; }
        .summary-card.danger { background: #dc3545; }
        .summary-card.info { background: #17a2b8; }
        
        .summary-card h3 {
            font-size: 2em;
            margin-bottom: 5px;
        }
        
        .task-item {
            border: 1px solid #dee2e6;
            border-radius: 8px;
            margin-bottom: 15px;
            overflow: hidden;
        }
        
        .task-header {
            padding: 15px;
            background: #f8f9fa;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
        }
        
        .task-header:hover {
            background: #e9ecef;
        }
        
        .task-status {
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .status-completed { background: #d4edda; color: #155724; }
        .status-failed { background: #f8d7da; color: #721c24; }
        .status-skipped { background: #fff3cd; color: #856404; }
        
        .task-details {
            padding: 15px;
            background: #fff;
            display: none;
        }
        
        .step-item {
            padding: 10px;
            margin: 5px 0;
            border-left: 4px solid #dee2e6;
            background: #f8f9fa;
        }
        
        .step-item.success { border-left-color: #28a745; }
        .step-item.failed { border-left-color: #dc3545; }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s ease;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }
        
        .info-item {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }
        
        .report-footer {
            text-align: center;
            padding: 20px;
            color: #6c757d;
            font-size: 0.9em;
        }
        
        .collapsible {
            cursor: pointer;
            user-select: none;
        }
        
        .collapsible:after {
            content: '▼';
            float: right;
            transition: transform 0.3s ease;
        }
        
        .collapsible.active:after {
            transform: rotate(180deg);
        }
        """
    
    def _create_summary_section(self, execution_data):
        """创建摘要部分"""
        summary = execution_data.get('summary', {})
        
        total_tasks = summary.get('total_tasks', 0)
        completed = summary.get('completed', 0)
        failed = summary.get('failed', 0)
        success_rate = summary.get('success_rate', '0%')
        
        duration = self._calculate_duration(
            execution_data.get('start_time'),
            execution_data.get('end_time')
        )
        
        return f"""
        <div class="section">
            <div class="section-header">📊 执行摘要</div>
            <div class="section-content">
                <div class="summary-grid">
                    <div class="summary-card info">
                        <h3>{total_tasks}</h3>
                        <p>总任务数</p>
                    </div>
                    <div class="summary-card success">
                        <h3>{completed}</h3>
                        <p>完成任务</p>
                    </div>
                    <div class="summary-card danger">
                        <h3>{failed}</h3>
                        <p>失败任务</p>
                    </div>
                    <div class="summary-card warning">
                        <h3>{success_rate}</h3>
                        <p>成功率</p>
                    </div>
                </div>
                
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {success_rate}"></div>
                </div>
                
                <div class="info-grid">
                    <div class="info-item">
                        <span>开始时间:</span>
                        <span>{execution_data.get('start_time', 'N/A')}</span>
                    </div>
                    <div class="info-item">
                        <span>结束时间:</span>
                        <span>{execution_data.get('end_time', 'N/A')}</span>
                    </div>
                    <div class="info-item">
                        <span>执行时长:</span>
                        <span>{duration}</span>
                    </div>
                    <div class="info-item">
                        <span>模板文件:</span>
                        <span>{os.path.basename(execution_data.get('template_path', 'N/A'))}</span>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _create_template_info_section(self, template_info):
        """创建模板信息部分"""
        if not template_info:
            return ""
        
        return f"""
        <div class="section">
            <div class="section-header">📋 模板信息</div>
            <div class="section-content">
                <div class="info-grid">
                    <div class="info-item">
                        <span>模板名称:</span>
                        <span>{template_info.get('name', 'N/A')}</span>
                    </div>
                    <div class="info-item">
                        <span>游戏名称:</span>
                        <span>{template_info.get('game_name', 'N/A')}</span>
                    </div>
                    <div class="info-item">
                        <span>模板版本:</span>
                        <span>{template_info.get('version', 'N/A')}</span>
                    </div>
                    <div class="info-item">
                        <span>创建时间:</span>
                        <span>{template_info.get('created_time', 'N/A')}</span>
                    </div>
                </div>
            </div>
        </div>
        """
    
    def _create_resolution_info_section(self, execution_data):
        """创建分辨率信息部分"""
        resolution_info = execution_data.get('resolution_info', {})
        if not resolution_info:
            return ""
        
        template_res = resolution_info.get('template_resolution', 'N/A')
        current_res = resolution_info.get('current_resolution', 'N/A')
        scale_applied = resolution_info.get('scale_applied', False)
        scale_ratio = resolution_info.get('scale_ratio', {})
        
        return f"""
        <div class="section">
            <div class="section-header">🖥️ 分辨率信息</div>
            <div class="section-content">
                <div class="info-grid">
                    <div class="info-item">
                        <span>模板分辨率:</span>
                        <span>{template_res}</span>
                    </div>
                    <div class="info-item">
                        <span>当前分辨率:</span>
                        <span>{current_res}</span>
                    </div>
                    <div class="info-item">
                        <span>缩放应用:</span>
                        <span>{'是' if scale_applied else '否'}</span>
                    </div>
                    <div class="info-item">
                        <span>缩放比例:</span>
                        <span>X: {scale_ratio.get('x', 1):.3f}, Y: {scale_ratio.get('y', 1):.3f}</span>
                    </div>
                </div>
            </div>
        </div>
        """

    def _create_tasks_section(self, execution_data):
        """创建任务详情部分"""
        tasks = execution_data.get('tasks', [])
        if not tasks:
            return ""

        tasks_html = ""
        for i, task in enumerate(tasks):
            task_status = task.get('status', 'unknown')
            status_class = f"status-{task_status}"

            steps_html = ""
            for step in task.get('steps', []):
                step_success = step.get('success', False)
                step_class = "success" if step_success else "failed"
                similarity = step.get('similarity_score', 0)
                error_msg = step.get('error_message', '')

                steps_html += f"""
                <div class="step-item {step_class}">
                    <strong>{step.get('step_id', 'Unknown Step')}</strong>
                    <span style="float: right;">相似度: {similarity:.3f}</span>
                    <br>
                    <small>操作类型: {step.get('action_type', 'N/A')}</small>
                    {f'<br><small style="color: #dc3545;">错误: {error_msg}</small>' if error_msg else ''}
                </div>
                """

            retry_info = f" (重试 {task.get('retry_count', 0)} 次)" if task.get('retry_count', 0) > 0 else ""

            tasks_html += f"""
            <div class="task-item">
                <div class="task-header collapsible" onclick="toggleTask({i})">
                    <span><strong>{task.get('task_name', 'Unknown Task')}</strong>{retry_info}</span>
                    <span class="task-status {status_class}">{task_status.upper()}</span>
                </div>
                <div class="task-details" id="task-{i}">
                    <p><strong>任务ID:</strong> {task.get('task_id', 'N/A')}</p>
                    {f'<p><strong>错误信息:</strong> <span style="color: #dc3545;">{task.get("error_message", "")}</span></p>' if task.get('error_message') else ''}
                    <h4>执行步骤:</h4>
                    {steps_html}
                </div>
            </div>
            """

        return f"""
        <div class="section">
            <div class="section-header">📝 任务详情</div>
            <div class="section-content">
                {tasks_html}
            </div>
        </div>
        """

    def _create_statistics_section(self, execution_data):
        """创建统计信息部分"""
        tasks = execution_data.get('tasks', [])
        if not tasks:
            return ""

        # 计算统计信息
        total_steps = sum(len(task.get('steps', [])) for task in tasks)
        successful_steps = sum(
            sum(1 for step in task.get('steps', []) if step.get('success', False))
            for task in tasks
        )

        avg_similarity = 0
        similarity_count = 0
        for task in tasks:
            for step in task.get('steps', []):
                if 'similarity_score' in step:
                    avg_similarity += step['similarity_score']
                    similarity_count += 1

        if similarity_count > 0:
            avg_similarity /= similarity_count

        total_retries = sum(task.get('retry_count', 0) for task in tasks)

        return f"""
        <div class="section">
            <div class="section-header">📈 统计信息</div>
            <div class="section-content">
                <div class="info-grid">
                    <div class="info-item">
                        <span>总步骤数:</span>
                        <span>{total_steps}</span>
                    </div>
                    <div class="info-item">
                        <span>成功步骤:</span>
                        <span>{successful_steps}</span>
                    </div>
                    <div class="info-item">
                        <span>步骤成功率:</span>
                        <span>{(successful_steps/total_steps*100):.1f}%</span>
                    </div>
                    <div class="info-item">
                        <span>平均相似度:</span>
                        <span>{avg_similarity:.3f}</span>
                    </div>
                    <div class="info-item">
                        <span>总重试次数:</span>
                        <span>{total_retries}</span>
                    </div>
                    <div class="info-item">
                        <span>平均重试次数:</span>
                        <span>{(total_retries/len(tasks)):.1f}</span>
                    </div>
                </div>
            </div>
        </div>
        """

    def _calculate_duration(self, start_time, end_time):
        """计算执行时长"""
        if not start_time or not end_time:
            return "N/A"

        try:
            start = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            duration = end - start

            total_seconds = int(duration.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60

            if minutes > 0:
                return f"{minutes}分{seconds}秒"
            else:
                return f"{seconds}秒"

        except Exception:
            return "N/A"

    def _get_javascript(self):
        """获取JavaScript代码"""
        return """
        function toggleTask(taskIndex) {
            const taskDetails = document.getElementById('task-' + taskIndex);
            const header = taskDetails.previousElementSibling;

            if (taskDetails.style.display === 'none' || taskDetails.style.display === '') {
                taskDetails.style.display = 'block';
                header.classList.add('active');
            } else {
                taskDetails.style.display = 'none';
                header.classList.remove('active');
            }
        }

        // 初始化：隐藏所有任务详情
        document.addEventListener('DOMContentLoaded', function() {
            const taskDetails = document.querySelectorAll('.task-details');
            taskDetails.forEach(detail => {
                detail.style.display = 'none';
            });
        });
        """

    def generate_json_report(self, execution_data, template_info=None):
        """生成JSON格式的执行报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"execution_report_{timestamp}.json"
        json_path = os.path.join(self.reports_dir, json_filename)

        # 合并数据
        report_data = {
            'report_info': {
                'generated_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'report_version': 'Phase 2',
                'generator': 'ReportGenerator'
            },
            'execution_data': execution_data,
            'template_info': template_info
        }

        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)

            print(f"JSON报告已生成: {json_path}")
            return json_path

        except Exception as e:
            print(f"生成JSON报告时出错: {e}")
            return None

    def generate_summary_report(self, execution_data):
        """生成简要的文本摘要报告"""
        summary = execution_data.get('summary', {})

        report_lines = [
            "=" * 50,
            "游戏自动化执行摘要报告",
            "=" * 50,
            f"执行时间: {execution_data.get('start_time', 'N/A')} - {execution_data.get('end_time', 'N/A')}",
            f"模板文件: {os.path.basename(execution_data.get('template_path', 'N/A'))}",
            "",
            "执行结果:",
            f"  总任务数: {summary.get('total_tasks', 0)}",
            f"  完成任务: {summary.get('completed', 0)}",
            f"  失败任务: {summary.get('failed', 0)}",
            f"  成功率: {summary.get('success_rate', '0%')}",
            "",
            "任务详情:"
        ]

        for task in execution_data.get('tasks', []):
            status_symbol = "✓" if task.get('status') == 'completed' else "✗"
            retry_info = f" (重试{task.get('retry_count', 0)}次)" if task.get('retry_count', 0) > 0 else ""
            report_lines.append(f"  {status_symbol} {task.get('task_name', 'Unknown')}{retry_info}")

            if task.get('error_message'):
                report_lines.append(f"    错误: {task['error_message']}")

        report_lines.extend([
            "",
            "=" * 50
        ])

        return "\n".join(report_lines)

# 测试函数
def test_report_generator():
    """测试报告生成器"""
    generator = ReportGenerator()

    # 创建测试数据
    test_execution_data = {
        'start_time': '2024-12-17 14:30:00',
        'end_time': '2024-12-17 14:35:30',
        'template_path': 'templates/test_template.json',
        'summary': {
            'total_tasks': 3,
            'completed': 2,
            'failed': 1,
            'success_rate': '66.7%'
        },
        'tasks': [
            {
                'task_name': '每日签到',
                'task_id': 'daily_signin',
                'status': 'completed',
                'retry_count': 0,
                'steps': [
                    {
                        'step_id': 'signin_button',
                        'action_type': 'image_verify_and_click',
                        'success': True,
                        'similarity_score': 0.92
                    }
                ]
            }
        ]
    }

    test_template_info = {
        'name': '测试模板',
        'game_name': '测试游戏',
        'version': 'v1.0_20241217_143000',
        'created_time': '2024-12-17 14:30:00'
    }

    # 生成报告
    html_path = generator.generate_html_report(test_execution_data, test_template_info)
    json_path = generator.generate_json_report(test_execution_data, test_template_info)

    summary = generator.generate_summary_report(test_execution_data)
    print("\n文本摘要报告:")
    print(summary)

    return html_path, json_path

if __name__ == "__main__":
    test_report_generator()
