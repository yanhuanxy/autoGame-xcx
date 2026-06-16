"""parser 测试（阶段 2.3）。"""
from __future__ import annotations

from autogame_xcx.remote.commands import CommandParser, build_default_registry


def _make_parser() -> CommandParser:
    return CommandParser(build_default_registry())


def test_parse_simple_command_with_arg() -> None:
    parser = _make_parser()
    parsed = parser.parse("#run 签到模板")
    assert parsed is not None
    assert parsed.name == "RUN_TEMPLATE"
    assert parsed.args == "签到模板"
    assert parsed.raw == "#run 签到模板"


def test_parse_no_arg() -> None:
    parser = _make_parser()
    parsed = parser.parse("#list")
    assert parsed is not None
    assert parsed.name == "LIST_TEMPLATES"
    assert parsed.args == ""


def test_parse_help() -> None:
    parser = _make_parser()
    parsed = parser.parse("#help")
    assert parsed is not None
    assert parsed.name == "HELP"


def test_parse_strips_whitespace_in_args() -> None:
    parser = _make_parser()
    parsed = parser.parse("#run    签到   ")
    assert parsed is not None
    assert parsed.args == "签到"


def test_parse_case_insensitive_alias() -> None:
    parser = _make_parser()
    parsed = parser.parse("#RUN 签到")
    assert parsed is not None
    assert parsed.name == "RUN_TEMPLATE"


def test_parse_unknown_alias_maps_to_unknown() -> None:
    parser = _make_parser()
    parsed = parser.parse("#nonexistent arg1")
    assert parsed is not None
    assert parsed.name == "UNKNOWN"
    assert parsed.args == "arg1"


def test_parse_non_command_returns_none() -> None:
    parser = _make_parser()
    assert parser.parse("hello world") is None
    assert parser.parse("") is None
    assert parser.parse("  ") is None


def test_parse_hash_only_returns_none() -> None:
    parser = _make_parser()
    assert parser.parse("#") is None
    assert parser.parse("#   ") is None


def test_parse_preserves_arg_with_multiple_words() -> None:
    parser = _make_parser()
    parsed = parser.parse("#run 模板 名 字")
    assert parsed is not None
    assert parsed.args == "模板 名 字"


def test_is_command_only_checks_prefix() -> None:
    parser = _make_parser()
    assert parser.is_command("#anything") is True
    assert parser.is_command("#") is True
    assert parser.is_command("plain text") is False
    assert parser.is_command("") is False
