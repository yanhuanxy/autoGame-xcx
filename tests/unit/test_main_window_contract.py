"""MainGUI 导航契约特征化测试（Phase E UI 重构的护栏）。

锁定 Phase E 必须保持的契约：5 个导航项 + QStackedWidget 5 页 +
5 个 show_* 切换方法（索引 0..4）+ 初始页 = 项目介绍。
不穷尽测试 main_window.py 的 2252 行内部，只锁"导航外壳没被改坏"。

性能/稳定性：MainGUI 很重（5 页 + 对话框 + MCP QThread），整个模块共享 **1 个**实例
（模块级 fixture），避免反复 new 多个窗口累积 Qt 资源拖垮后续 GUI 测试。
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.gui


@pytest.fixture(scope="module")
def qapp():
    """模块级共享 QApplication（已存在则复用，不 new 第二个）。"""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture(scope="module")
def main_gui(qapp):
    """模块级共享 1 个 MainGUI；用完 deleteLater 清理。"""
    from autogame_xcx.ui.main_window import MainGUI

    window = MainGUI()
    yield window
    window.deleteLater()
    qapp.processEvents()


def test_main_gui_constructs_without_crash(main_gui):
    assert main_gui is not None


def test_menu_has_five_nav_items(main_gui):
    assert len(main_gui.menu_group.buttons()) == 5


def test_content_stack_is_stacked_widget_with_five_pages(main_gui):
    from PyQt6.QtWidgets import QStackedWidget

    stack = main_gui.content_stack
    assert isinstance(stack, QStackedWidget)
    assert stack.count() == 5


def test_initial_page_is_project_intro(main_gui):
    assert main_gui.content_stack.currentIndex() == 0


@pytest.mark.parametrize(
    "show_method, expected_index",
    [
        ("show_project_intro", 0),
        ("show_template_management", 1),
        ("show_template_creator", 2),
        ("show_user_guide", 3),
        ("show_mcp_server", 4),
    ],
)
def test_show_methods_switch_content_stack(main_gui, show_method, expected_index):
    getattr(main_gui, show_method)()
    assert main_gui.content_stack.currentIndex() == expected_index
