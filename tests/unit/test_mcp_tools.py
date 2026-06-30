"""MCP tools 元数据测试（Task #1）。

不依赖 ilink/JVM，仅校验 list_all_tools 返回结构与 schema 完整性。
"""
from __future__ import annotations

import pytest

from mcp.types import Tool

from autogame_xcx.mcp import list_all_tools


def test_list_all_tools_returns_five() -> None:
    tools = list_all_tools()
    assert len(tools) == 5
    names = {t.name for t in tools}
    assert names == {
        "list_templates",
        "run_template",
        "get_status",
        "stop_execution",
        "get_report",
    }


def test_all_tools_are_mcp_tool_instances() -> None:
    for tool in list_all_tools():
        assert isinstance(tool, Tool)
        assert tool.description, f"{tool.name} 缺少 description"
        assert tool.inputSchema["type"] == "object", f"{tool.name} inputSchema 必须是 object"


def test_run_template_requires_name() -> None:
    tools = {t.name: t for t in list_all_tools()}
    schema = tools["run_template"].inputSchema
    assert "name" in schema["properties"]
    assert schema["required"] == ["name"]


def test_no_param_tools_have_empty_required() -> None:
    no_param = ["list_templates", "get_status", "stop_execution", "get_report"]
    tools = {t.name: t for t in list_all_tools()}
    for name in no_param:
        assert tools[name].inputSchema["required"] == [], f"{name} 应该无必填参数"


@pytest.mark.parametrize("missing", ["description", "inputSchema"])
def test_tool_metadata_complete(missing: str) -> None:
    """每个 tool 都必须有 description 和 inputSchema（防止漏填）。"""
    for tool in list_all_tools():
        assert hasattr(tool, missing), f"{tool.name} 缺少 {missing}"
