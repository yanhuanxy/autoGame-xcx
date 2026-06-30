"""单元测试共享 fixtures。

旧版（基于 RemoteDriver / ilink 嵌入）的 fixtures 已随 src/autogame_xcx/remote/
一并移除。如需 mock GameExecutor/TemplateManager，请在各自测试文件内定义最小 mock
（参考 tests/unit/test_mcp_executor_bridge.py 的 _MockExecutor / _MockTemplateManager）。

此处仅提供跨文件复用的通用 fixture：样例模板、临时模板目录。

GUI 测试不在此提供共享 QApplication fixture——现有 GUI 测试各自创建 QApplication，
引入 session 级长生命周期 app 会与它们冲突（多实例 access violation）。GUI 测试沿用
"各自 `QApplication.instance() or QApplication(sys.argv)`"的现有模式。
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture
def sample_template() -> dict:
    """最小合法模板 dict（能通过 TemplateManager.validate_template）。"""
    return {
        "template_info": {
            "name": "签到",
            "version": "md_test_0001",
            "game_name": "测试游戏",
            "template_resolution": {"width": 1280, "height": 720, "dpi": 96},
        },
        "tasks": [],
        "global_settings": {"max_retry": 3, "step_delay": 1000},
    }


@pytest.fixture
def tmp_templates(tmp_path, monkeypatch) -> Iterator[object]:
    """把 TemplateManager 的 templates_dir / images_dir 指向临时目录。

    注意：``template_manager.py`` 用 ``from ...constants import TEMPLATES_PATH``
    在模块加载时把路径绑进自身命名空间，故须 patch ``template_manager`` 模块上的
    这两个名字（patch ``constants`` 不生效）。在 ``TemplateManager()`` 实例化前生效。
    """
    import autogame_xcx.core.template_manager as tm_mod

    templates_dir = tmp_path / "templates"
    images_dir = tmp_path / "reference_images"
    templates_dir.mkdir()
    images_dir.mkdir()
    monkeypatch.setattr(tm_mod, "TEMPLATES_PATH", str(templates_dir))
    monkeypatch.setattr(tm_mod, "REFERENCE_IMAGES_PATH", str(images_dir))
    yield tmp_path
