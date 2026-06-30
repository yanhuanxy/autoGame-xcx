"""TemplateManager 单测。

涉及文件读写的用例用 ``tmp_templates`` fixture 把 templates_dir / images_dir
重定向到临时目录，避免污染 data/。
"""

from __future__ import annotations

import pytest

from autogame_xcx.core.template_manager import TemplateManager


def test_create_template_structure_has_required_shape():
    tm = TemplateManager()
    t = tm.create_template_structure("签到", "测试游戏", {"width": 1280, "height": 720, "dpi": 96})
    assert t["template_info"]["name"] == "签到"
    assert t["template_info"]["template_resolution"] == {"width": 1280, "height": 720, "dpi": 96}
    assert t["tasks"] == []
    assert "global_settings" in t


def test_add_task_and_step_into_template():
    tm = TemplateManager()
    t = tm.create_template_structure("签到", "g", {"width": 1280, "height": 720})
    task = tm.add_task_to_template(t, "t1", "点击签到")
    assert task["task_id"] == "t1" and task["steps"] == []
    step = tm.add_step_to_task(
        task, "s1", "image_verify_and_click",
        {"x": 10, "y": 10, "width": 20, "height": 20}, "ref.png",
        click_point={"x": 15, "y": 15},
    )
    assert step["step_id"] == "s1"
    assert step["click_point"] == {"x": 15, "y": 15}  # action_type=click 且有 click_point 才写入
    assert t["tasks"][0]["steps"][0] is step


def test_validate_template_accepts_minimal_valid(sample_template):
    assert TemplateManager().validate_template(sample_template) is True


def test_validate_template_rejects_missing_top_field():
    broken = {  # 缺 tasks / global_settings
        "template_info": {"name": "x", "version": "v", "template_resolution": {"width": 1, "height": 1}}
    }
    assert TemplateManager().validate_template(broken) is False


def test_validate_template_rejects_bad_resolution():
    broken = {  # template_resolution 缺 height
        "template_info": {"name": "x", "version": "v", "template_resolution": {"width": 1}},
        "tasks": [],
        "global_settings": {},
    }
    assert TemplateManager().validate_template(broken) is False


def test_save_and_load_round_trip(tmp_templates, sample_template):
    tm = TemplateManager()
    path = tm.save_template(sample_template, filename="qiandao.json")
    assert path is not None and path.endswith("qiandao.json")

    loaded = tm.load_template(path)
    assert loaded is not None
    assert loaded["template_info"]["name"] == sample_template["template_info"]["name"]


def test_load_template_missing_file_returns_none():
    assert TemplateManager().load_template("does/not/exist.json") is None


def test_list_templates_reads_saved_files(tmp_templates, sample_template):
    tm = TemplateManager()
    tm.save_template(sample_template, filename="a.json")
    tm.save_template(sample_template, filename="b.json")

    items = tm.list_templates()
    assert len(items) == 2
    assert {it["filename"] for it in items} == {"a.json", "b.json"}
