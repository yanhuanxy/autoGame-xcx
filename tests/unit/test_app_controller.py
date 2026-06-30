"""AppController 单测（Phase E3）：core 单件持有 + 模板操作透传。"""
from __future__ import annotations

from autogame_xcx.ui.controllers import AppController


def test_app_controller_holds_core_singletons() -> None:
    """构造后应持有 5 个 core 单件（经控制器，测试侧不直接 import core）。"""
    ctl = AppController()
    attrs = {
        "window_controller": ctl.window_controller,
        "image_matcher": ctl.image_matcher,
        "template_manager": ctl.template_manager,
        "game_executor": ctl.game_executor,
        "report_generator": ctl.report_generator,
    }
    for name, obj in attrs.items():
        assert obj is not None, name


def test_app_controller_list_templates_returns_list() -> None:
    """list_templates 透传 TemplateManager，返回 list。"""
    assert isinstance(AppController().list_templates(), list)


def test_app_controller_delete_missing_returns_false() -> None:
    """删除不存在的模板文件应返回 False（不抛异常）。"""
    assert AppController().delete_template("__definitely_not_exists__.json") is False
