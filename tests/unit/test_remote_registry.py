"""指令注册表测试（阶段 2.3）。"""
from __future__ import annotations

import pytest

from autogame_xcx.remote.commands import build_default_registry
from autogame_xcx.remote.commands.base import Command


def test_default_registry_six_commands() -> None:
    registry = build_default_registry()
    assert len(registry) == 6


def test_canonical_names_registered() -> None:
    registry = build_default_registry()
    for name in ("HELP", "LIST_TEMPLATES", "RUN_TEMPLATE", "STATUS", "STOP", "REPORT"):
        assert name in registry, f"{name} 未注册"


def test_alias_resolution() -> None:
    registry = build_default_registry()
    assert registry.resolve_alias("run") == "RUN_TEMPLATE"
    assert registry.resolve_alias("执行") == "RUN_TEMPLATE"
    assert registry.resolve_alias("运行") == "RUN_TEMPLATE"
    assert registry.resolve_alias("stop") == "STOP"
    assert registry.resolve_alias("停止") == "STOP"
    assert registry.resolve_alias("取消") == "STOP"


def test_alias_case_insensitive() -> None:
    registry = build_default_registry()
    assert registry.resolve_alias("LIST") == "LIST_TEMPLATES"
    assert registry.resolve_alias("List") == "LIST_TEMPLATES"
    assert registry.resolve_alias("Run") == "RUN_TEMPLATE"


def test_unknown_alias_returns_none() -> None:
    registry = build_default_registry()
    assert registry.resolve_alias("nonexistent") is None


def test_register_duplicate_name_raises() -> None:
    registry = build_default_registry()

    class Dup(Command):
        name = "HELP"  # 已存在
        aliases = ["dup"]
        description = ""
        usage = ""

        def execute(self, ctx, args):  # type: ignore[no-untyped-def]
            ...

    with pytest.raises(ValueError, match="已注册"):
        registry.register(Dup())


def test_register_alias_conflict_raises() -> None:
    registry = build_default_registry()

    class Conflict(Command):
        name = "NEW_CMD"
        aliases = ["run"]  # 别名冲突
        description = ""
        usage = ""

        def execute(self, ctx, args):  # type: ignore[no-untyped-def]
            ...

    with pytest.raises(ValueError, match="别名冲突"):
        registry.register(Conflict())


def test_find_returns_command_or_none() -> None:
    registry = build_default_registry()
    cmd = registry.find("RUN_TEMPLATE")
    assert cmd is not None
    assert cmd.name == "RUN_TEMPLATE"
    assert registry.find("NON_EXISTENT") is None
