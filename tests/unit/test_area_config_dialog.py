"""AreaConfigDialog 业务逻辑回归测试（区域配置往返）。

锁定 bug B：动作类型 / 匹配算法必须以 **id**（executor / image_matcher 期望值）
持久化，而非中文显示名；且 get_area_data ↔ load_area_data 往返一致。
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.gui

# executor 按 id 判分支（core/game_executor.py）；image_matcher 按 id 选算法。
ACTION_IDS = {"image_verify_and_click", "image_verify_only", "click_only", "wait_for_image"}
ALGORITHM_IDS = {"template_matching", "ssim", "feature_matching", "hybrid"}


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _make_dialog(qapp):
    from autogame_xcx.ui.dialogs.area_config_dialog import AreaConfigDialog

    return AreaConfigDialog({"x": 10, "y": 20, "width": 100, "height": 50}, None)


def test_get_area_data_returns_ids_not_display_names(qapp):
    """默认选项下 get_area_data 应返回 executor/匹配器认得的 id，而非中文显示名。"""
    dlg = _make_dialog(qapp)
    data = dlg.get_area_data()
    assert data["action_type"] in ACTION_IDS, data["action_type"]
    assert data["match_algorithm"] in ALGORITHM_IDS, data["match_algorithm"]


def test_round_trip_action_and_algorithm(qapp):
    """选定动作/算法 → get_area_data → load_area_data 后 combo 选回同项（按 id）。"""
    dlg = _make_dialog(qapp)
    dlg.action_combo.setCurrentIndex(dlg.action_combo.findData("click_only"))
    dlg.algorithm_combo.setCurrentIndex(dlg.algorithm_combo.findData("ssim"))
    dlg.wait_after_spin.setValue(1234)
    dlg.click_x.setValue(77)
    dlg.click_y.setValue(88)

    data = dlg.get_area_data()
    assert data["action_type"] == "click_only"
    assert data["match_algorithm"] == "ssim"
    assert data["wait_after"] == 1234
    assert data["click_point"] == {"x": 77, "y": 88}

    dlg2 = _make_dialog(qapp)
    dlg2.load_area_data(data)
    assert dlg2.action_combo.currentData() == "click_only"
    assert dlg2.algorithm_combo.currentData() == "ssim"
    assert dlg2.wait_after_spin.value() == 1234
    assert dlg2.click_x.value() == 77
    assert dlg2.click_y.value() == 88
