"""MCP tools 定义：5 个 tool 对接 ExecutorBridge。

低级 API（mcp.server.Server + mcp.types.Tool），明确控制 tool 元数据。
tool handler 通过 asyncio.to_thread 包装 bridge 的同步方法，避免阻塞 asyncio loop。
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from mcp.types import TextContent, Tool

from autogame_xcx.mcp.executor_bridge import ExecutorBridge

logger = logging.getLogger(__name__)


def list_all_tools() -> list[Tool]:
    """返回所有 MCP tool 的元数据（schema + description）。

    被 Server.list_tools 回调调用，最终会通过 tools/list 暴露给 bot。
    """
    return [
        Tool(
            name="list_templates",
            description="列出所有可用的本地模板。返回 [{name, filepath, version, game_name, created_time}]。",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="run_template",
            description=(
                "按名称执行模板，阻塞到完成。"
                "返回 {template, filepath, success, summary:{completed,total_tasks,success_rate}}。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "模板名（list_templates 返回的 name 字段）",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="get_status",
            description="查询当前执行状态。返回 {running, current_template, last_template}。",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="stop_execution",
            description="请求停止当前执行（GameExecutor 当前不支持中断，会返回原因）。",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="get_report",
            description="返回最近一次执行的完整报告（无则空 dict）。",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


async def call_tool(bridge: ExecutorBridge, name: str, arguments: dict) -> list[TextContent]:
    """分发 tool 调用到 bridge。

    被 Server.call_tool 回调调用。所有 bridge 方法在线程池里跑（不阻塞 asyncio loop）。

    失败时不抛——把异常序列化成 {"error": ...} 返回，便于 bot 端识别 isError 内容。
    """
    args = dict(arguments or {})
    result: Any
    try:
        if name == "list_templates":
            result = await asyncio.to_thread(bridge.list_templates)
        elif name == "run_template":
            result = await asyncio.to_thread(bridge.run_template, args.get("name", ""))
        elif name == "get_status":
            result = await asyncio.to_thread(bridge.get_status)
        elif name == "stop_execution":
            result = await asyncio.to_thread(bridge.stop_execution)
        elif name == "get_report":
            result = await asyncio.to_thread(bridge.get_report)
        else:
            result = {"error": f"unknown tool: {name}"}
    except Exception as e:
        logger.exception("tool %s crashed", name)
        result = {"error": str(e), "tool": name}

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]
