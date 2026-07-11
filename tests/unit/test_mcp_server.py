"""_BearerAuthMiddleware 鉴权测试（迭代C）。

不依赖 QThread/GUI/真实 MCP server：直接用最小 Starlette app + TestClient 验证中间件行为。
"""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from autogame_xcx.mcp.server import _BearerAuthMiddleware


def _build_app(auth_token: str | None) -> Starlette:
    async def probe(request):
        return PlainTextResponse("ok")

    return Starlette(
        routes=[Route("/probe", endpoint=probe)],
        middleware=[Middleware(_BearerAuthMiddleware, auth_token=auth_token)],
    )


def test_no_token_configured_allows_any_request() -> None:
    client = TestClient(_build_app(auth_token=None))
    resp = client.get("/probe")
    assert resp.status_code == 200


def test_token_configured_rejects_missing_header() -> None:
    client = TestClient(_build_app(auth_token="secret"))
    resp = client.get("/probe")
    assert resp.status_code == 401


def test_token_configured_rejects_wrong_token() -> None:
    client = TestClient(_build_app(auth_token="secret"))
    resp = client.get("/probe", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401


def test_token_configured_allows_correct_token() -> None:
    client = TestClient(_build_app(auth_token="secret"))
    resp = client.get("/probe", headers={"Authorization": "Bearer secret"})
    assert resp.status_code == 200
    assert resp.text == "ok"
