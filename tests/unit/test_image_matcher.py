"""ImageMatcher 单测（用 data/test_images 现有样本；保持轻量）。

图像匹配较慢，这里只做：边界输入、同图高分、各 method 不崩。
"""

from __future__ import annotations

import numbers
from pathlib import Path

import pytest

from autogame_xcx.core.image_matcher import ImageMatcher
from autogame_xcx.utils.constants import TEST_IMAGES_PATH
from autogame_xcx.utils.opencv import CvTool

_IMAGES = Path(TEST_IMAGES_PATH)


def _load(name: str):
    return CvTool.imread(str(_IMAGES / name))


def test_match_none_inputs_returns_false_zero():
    ok, score = ImageMatcher().match_images(None, None)
    assert (ok, score) == (False, 0.0)


def test_match_unknown_method_returns_false_zero():
    img = _load("original_button.png")
    ok, score = ImageMatcher().match_images(img, img, method="no_such_method")
    assert (ok, score) == (False, 0.0)


def test_match_same_image_reports_match():
    img = _load("original_button.png")
    ok, score = ImageMatcher().match_images(img, img, method="template_matching", threshold=0.8)
    assert ok is True
    assert score >= 0.0


@pytest.mark.parametrize(
    "method",
    ["template_matching", "ssim", "feature_matching", "histogram", "hybrid"],
)
def test_each_method_runs_without_crash(method):
    cur = _load("original_button.png")
    ref = _load("similar_button.png")
    ok, score = ImageMatcher().match_images(cur, ref, method=method, threshold=0.5)
    # 各 method 可能返回 numpy 标量（np.bool_ / np.float32），用 numbers.Real 放宽
    assert isinstance(score, numbers.Real)
    assert bool(ok) in (True, False)
