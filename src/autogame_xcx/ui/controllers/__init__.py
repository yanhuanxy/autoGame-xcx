"""UI 控制器层（UI ↔ core 中介）。

``ui/pages`` 经此访问 core，不直接 ``import core``（架构规则见
``.claude/rules/architecture.md``：UI 经 controller 调 core）。
"""

from autogame_xcx.ui.controllers.app_controller import AppController

__all__ = ["AppController"]
