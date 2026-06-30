"""McpServerThread：在独立 QThread 内跑 asyncio loop + MCP SSE server。

线程模型：
    GUI 主线程 → start()
                  ↓
              QThread.run()（新线程）
                  ↓
              asyncio.run(self._serve())
                  ↓
              uvicorn.Server.serve()（阻塞直到 should_exit=True）

跨线程控制：
    主线程 request_stop() → loop.call_soon_threadsafe(setattr, server, "should_exit", True)
    server 完成清理后 → run() 退出 → emit server_stopped

信号：
    server_started(int port) — server 监听就绪
    server_stopped()         — server 完全停止
    server_failed(str)       — 启动或运行异常
    tool_invoked(str, dict, object) — tool 调用日志（name, args, result）

使用：
    thread = McpServerThread(bridge=bridge, port=8765)
    thread.server_started.connect(ui.on_started)
    thread.start()
    ...
    thread.request_stop()
    thread.wait(5000)  # 等最多 5s

依赖：
    mcp（PyPI 包）+ starlette + uvicorn（mcp 的 SSE 实现依赖）
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QThread, pyqtSignal

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route
import uvicorn

from autogame_xcx.mcp.executor_bridge import ExecutorBridge
from autogame_xcx.mcp.tools import call_tool, list_all_tools

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class McpServerThread(QThread):
    """跑 MCP SSE server 的 QThread。"""

    server_started = pyqtSignal(int)
    server_stopped = pyqtSignal()
    server_failed = pyqtSignal(str)
    tool_invoked = pyqtSignal(str, dict, object)

    def __init__(
        self,
        bridge: ExecutorBridge,
        port: int = 8765,
        *,
        host: str = "127.0.0.1",
        parent: Any = None,
    ) -> None:
        super().__init__(parent=parent)
        self._bridge = bridge
        self._port = port
        self._host = host
        self._loop: asyncio.AbstractEventLoop | None = None
        self._uvicorn: uvicorn.Server | None = None

    @property
    def port(self) -> int:
        return self._port

    @property
    def host(self) -> str:
        return self._host

    def run(self) -> None:
        """QThread 入口；新线程里启动 asyncio loop 跑 server。"""
        try:
            asyncio.run(self._serve())
        except Exception as e:
            logger.exception("McpServerThread crashed")
            self.server_failed.emit(str(e))
        finally:
            self.server_stopped.emit()

    async def _serve(self) -> None:
        self._loop = asyncio.get_running_loop()
        mcp_server = self._build_mcp_server()
        app = self._build_asgi_app(mcp_server)

        config = uvicorn.Config(
            app=app,
            host=self._host,
            port=self._port,
            log_level="info",
            lifespan="on",
        )
        self._uvicorn = uvicorn.Server(config)

        # server 真正起来后再 emit（用 task 轮询 started 状态）
        asyncio.create_task(self._notify_started())

        try:
            await self._uvicorn.serve()
        except asyncio.CancelledError:
            logger.info("McpServerThread cancelled")
            raise

    async def _notify_started(self) -> None:
        while self._uvicorn is None or not self._uvicorn.started:
            await asyncio.sleep(0.1)
        self.server_started.emit(self._port)

    def _build_mcp_server(self) -> Server:
        """构造低级 Server 并注册 list_tools / call_tool 回调。"""
        server = Server("autogame-xcx")
        bridge = self._bridge

        @server.list_tools()
        async def _list_tools() -> list:
            return list_all_tools()

        @server.call_tool()
        async def _call_tool(name: str, arguments: dict) -> list:
            content = await call_tool(bridge, name, arguments or {})
            # 异步 emit 信号（Qt 跨线程信号槽自动转线程）
            self.tool_invoked.emit(name, dict(arguments or {}), _extract_result(content))
            return content

        return server

    @staticmethod
    def _build_asgi_app(mcp_server: Server) -> Starlette:
        """组装 SSE transport + Starlette ASGI app。

        MCP over SSE 标准路由：
            GET  /sse           —— 建立 SSE 长连接（server → client 推 JSON-RPC response）
            POST /messages/     —— client 发 JSON-RPC request
        """
        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send  # noqa: SLF001 — starlette 私有字段，MCP SDK 官方示例用法
            ) as streams:
                await mcp_server.run(
                    streams[0],
                    streams[1],
                    mcp_server.create_initialization_options(),
                )

        return Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

    def request_stop(self) -> None:
        """从主线程调用，触发优雅停止。

        通过 call_soon_threadsafe 在 server 线程设置 uvicorn.should_exit。
        uvicorn 会完成正在处理的请求后退出，QThread.run 自然返回。
        """
        if self._loop is None or self._uvicorn is None:
            return
        self._loop.call_soon_threadsafe(setattr, self._uvicorn, "should_exit", True)


def _extract_result(content: list) -> Any:
    """从 TextContent 列表反序列化 JSON，给 tool_invoked 信号用。

    解析失败时返回原始 text 字符串。
    """
    import json

    if not content:
        return None
    first = content[0]
    text = getattr(first, "text", str(first))
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text
