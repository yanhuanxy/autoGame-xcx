"""MCP Server 包：把本地 GameExecutor 能力暴露给 wechat-ilink-bot。

通过 MCP 协议（HTTP+SSE）让 bot 端发现并调用本项目的执行能力。
配置主权（模板、坐标、OCR、API key）留在本地，bot 端只看到 tool schema。

组件：
    ExecutorBridge  — 串行化 GameExecutor/TemplateManager 访问的桥接层
    list_all_tools / call_tool — MCP tool 元数据与分发（tools.py）
    McpServerThread — 跑 SSE server 的 QThread（server.py）
"""
from autogame_xcx.mcp.executor_bridge import ExecutorBridge
from autogame_xcx.mcp.server import McpServerThread
from autogame_xcx.mcp.tools import call_tool, list_all_tools

__all__ = ["ExecutorBridge", "McpServerThread", "call_tool", "list_all_tools"]
