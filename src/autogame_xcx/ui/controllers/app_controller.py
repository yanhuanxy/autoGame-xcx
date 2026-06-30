"""UI ↔ core 中介控制器（Phase E3）。

集中持有 core 单件，供 ``ui/pages`` 经此访问 core，避免页面直接 ``import core``
（见 ``.claude/rules/ui-conventions.md``「UI 经 controller 访问 core」）。
``MainGUI`` 作为组合根构造本类并注入各页。
"""
from __future__ import annotations

import os

from autogame_xcx.core.game_executor import GameExecutor
from autogame_xcx.core.image_matcher import ImageMatcher
from autogame_xcx.core.report_generator import ReportGenerator
from autogame_xcx.core.template_manager import TemplateManager
from autogame_xcx.platform.window_controller import GameWindowController
from autogame_xcx.utils.constants import TEMPLATES_PATH


class AppController:
    """持有 core 单件并暴露页面需要的操作。"""

    def __init__(self) -> None:
        self.window_controller = GameWindowController()
        self.image_matcher = ImageMatcher()
        self.template_manager = TemplateManager()
        self.game_executor = GameExecutor()
        self.report_generator = ReportGenerator()

    # 模板操作（页面常用）
    def list_templates(self) -> list:
        """列出全部模板（透传 TemplateManager）。"""
        return self.template_manager.list_templates()

    def load_template(self, path: str):
        """加载指定路径的模板。"""
        return self.template_manager.load_template(path)

    def delete_template(self, filename: str) -> bool:
        """按文件名删除模板；返回是否实际删除了文件。"""
        path = os.path.join(TEMPLATES_PATH, filename)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
