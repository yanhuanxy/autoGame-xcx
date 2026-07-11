"""MCP tools 元数据测试（Task #1）。

不依赖 ilink/JVM，仅校验 list_all_tools 返回结构与 schema 完整性。
"""

from __future__ import annotations

import asyncio
import json

import pytest
from mcp.types import Tool

from autogame_xcx.mcp import list_all_tools
from autogame_xcx.mcp.executor_bridge import DuplicateCallerError, QueueFullError
from autogame_xcx.mcp.tools import call_tool


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


def test_all_tools_have_optional_caller_property() -> None:
    """迭代C：所有 tool 都接受可选 caller 字段，且不强制必填（兼容旧客户端）。"""
    for tool in list_all_tools():
        assert "caller" in tool.inputSchema["properties"], f"{tool.name} 缺少 caller 字段"
        assert "caller" not in tool.inputSchema["required"], f"{tool.name} 的 caller 不应是必填"


class _StubBridge:
    """call_tool 分发测试用的最小 bridge 替身，记录收到的参数。"""

    def __init__(self) -> None:
        self.run_template_args: tuple | None = None
        self.stop_execution_args: tuple | None = None
        self.get_status_args: tuple | None = None
        self.run_template_error: Exception | None = None

    def run_template(self, name: str, caller: str | None = None) -> dict:
        if self.run_template_error is not None:
            raise self.run_template_error
        self.run_template_args = (name, caller)
        return {"template": name, "success": True}

    def stop_execution(self, caller: str | None = None) -> dict:
        self.stop_execution_args = (caller,)
        return {"stopped": False, "reason": "stub"}

    def get_status(self, caller: str | None = None) -> dict:
        self.get_status_args = (caller,)
        return {"running": False, "queue_length": 0, "queue_position": None}


def test_call_tool_run_template_passes_caller_to_bridge() -> None:
    bridge = _StubBridge()

    result = asyncio.run(call_tool(bridge, "run_template", {"name": "签到", "caller": "bot1"}))

    assert bridge.run_template_args == ("签到", "bot1")
    payload = json.loads(result[0].text)
    assert payload["template"] == "签到"


def test_call_tool_run_template_withoutCaller_passesNone() -> None:
    bridge = _StubBridge()

    asyncio.run(call_tool(bridge, "run_template", {"name": "签到"}))

    assert bridge.run_template_args == ("签到", None)


def test_call_tool_stop_execution_passes_caller_to_bridge() -> None:
    bridge = _StubBridge()

    asyncio.run(call_tool(bridge, "stop_execution", {"caller": "bot1"}))

    assert bridge.stop_execution_args == ("bot1",)


def test_call_tool_get_status_passes_caller_to_bridge() -> None:
    bridge = _StubBridge()

    asyncio.run(call_tool(bridge, "get_status", {"caller": "bot1"}))

    assert bridge.get_status_args == ("bot1",)


def test_call_tool_queue_full_returns_structured_error() -> None:
    bridge = _StubBridge()
    bridge.run_template_error = QueueFullError(queue_length=2, queue_capacity=2)

    result = asyncio.run(call_tool(bridge, "run_template", {"name": "签到", "caller": "bot3"}))

    payload = json.loads(result[0].text)
    assert payload["reason"] == "queue_full"
    assert payload["queue_length"] == 2
    assert payload["queue_capacity"] == 2


def test_call_tool_duplicate_caller_returns_structured_error() -> None:
    bridge = _StubBridge()
    bridge.run_template_error = DuplicateCallerError("bot1")

    result = asyncio.run(call_tool(bridge, "run_template", {"name": "签到", "caller": "bot1"}))

    payload = json.loads(result[0].text)
    assert payload["reason"] == "duplicate_caller"
