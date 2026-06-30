"""CoordinateConverter 纯逻辑单测。

构造时会查真实 DPI（scale_factor 随机器 DPI 漂移），故对缩放相关方法直接覆盖
``scale_factor`` 隔离纯数学；``is_resolution_match`` / ``validate_coordinates``
不依赖 DPI，直接断言。模块顶层 import win32* → 仅 Windows 可运行。
"""

from __future__ import annotations

from autogame_xcx.core.coordinate_converter import CoordinateConverter


def _make(template=(1280, 720), current=(1280, 720)) -> CoordinateConverter:
    return CoordinateConverter(
        {"width": template[0], "height": template[1]},
        {"width": current[0], "height": current[1]},
    )


def test_convert_coordinates_scales_by_factor():
    cc = _make()
    cc.scale_factor = {"x": 2, "y": 3}  # 隔离 DPI，固定缩放
    out = cc.convert_coordinates({"x": 10, "y": 10, "width": 5, "height": 5})
    assert out == {"x": 20, "y": 30, "width": 10, "height": 15}


def test_convert_coordinates_clamps_nonnegative_and_min_size():
    cc = _make()
    cc.scale_factor = {"x": 1, "y": 1}
    out = cc.convert_coordinates({"x": -5, "y": -5, "width": 0, "height": 0})
    assert out["x"] == 0 and out["y"] == 0
    assert out["width"] >= 1 and out["height"] >= 1


def test_convert_click_point_scales():
    cc = _make()
    cc.scale_factor = {"x": 2, "y": 4}
    assert cc.convert_click_point({"x": 3, "y": 3}) == {"x": 6, "y": 12}


def test_convert_area_to_bbox_without_offset():
    cc = _make()
    cc.scale_factor = {"x": 1, "y": 1}
    assert cc.convert_area_to_bbox({"x": 10, "y": 20, "width": 30, "height": 40}) == (10, 20, 40, 60)


def test_convert_area_to_bbox_with_offset():
    cc = _make()
    cc.scale_factor = {"x": 1, "y": 1}
    out = cc.convert_area_to_bbox(
        {"x": 10, "y": 20, "width": 30, "height": 40}, {"x": 100, "y": 200}
    )
    assert out == (110, 220, 140, 260)


def test_is_resolution_match_when_equal():
    assert _make((1280, 720), (1280, 720)).is_resolution_match() is True


def test_is_resolution_match_within_default_tolerance():
    # 宽高各差 5%，默认容差 10% → 匹配
    assert _make((1000, 1000), (1050, 1050)).is_resolution_match() is True


def test_is_resolution_match_outside_tolerance():
    assert _make((1000, 1000), (1300, 1300)).is_resolution_match() is False


def test_validate_coordinates_inside_bounds():
    cc = _make()
    assert cc.validate_coordinates({"x": 10, "y": 10, "width": 50, "height": 50}, 1280, 720) is True


def test_validate_coordinates_negative_is_invalid():
    cc = _make()
    assert cc.validate_coordinates({"x": -1, "y": 10}, 1280, 720) is False


def test_validate_coordinates_overflow_is_invalid():
    cc = _make()
    # x + width = 1300 > 1280
    assert cc.validate_coordinates({"x": 1200, "y": 10, "width": 100, "height": 10}, 1280, 720) is False
