"""McpServerConfig：MCP server 的 host + 鉴权 token 配置。

文件位置：data/mcp_server_config.json（不存在则生成模板，host 缺省 127.0.0.1、auth_token 缺省 null=不校验）。
仿 Java 端 AutogameConfig 的加载模式（../wechat-ilink-bot/.../config/AutogameConfig.java）。
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from autogame_xcx.utils.constants import MCP_SERVER_CONFIG_PATH

logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_QUEUE_CAPACITY = 2
DEFAULT_QUEUE_WAIT_TIMEOUT_SECONDS = 300.0
DEFAULT_EXECUTION_TIMEOUT_SECONDS = 480.0


@dataclass
class McpServerConfig:
    host: str = DEFAULT_HOST
    auth_token: str | None = None
    # 迭代（Phase H）：执行队列容量与超时保护，见 mcp/executor_bridge.py
    queue_capacity: int = DEFAULT_QUEUE_CAPACITY
    queue_wait_timeout_seconds: float | None = DEFAULT_QUEUE_WAIT_TIMEOUT_SECONDS
    execution_timeout_seconds: float | None = DEFAULT_EXECUTION_TIMEOUT_SECONDS


def _load_timeout(data: dict, key: str, default: float | None) -> float | None:
    """<=0 显式表示禁用该超时（None）；字段缺失则回退默认值。"""
    if key not in data:
        return default
    value = data.get(key)
    if value is None:
        return None
    return None if value <= 0 else float(value)


def load(path: str = MCP_SERVER_CONFIG_PATH) -> McpServerConfig:
    """读取配置；文件不存在则生成模板并返回默认值，读取失败则返回默认值。"""
    file = Path(path)
    if not file.exists():
        _create_template(file)
        logger.info("MCP server 配置未找到，已生成模板：%s", path)
        return McpServerConfig()
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
        queue_capacity = data.get("queue_capacity")
        config = McpServerConfig(
            host=data.get("host") or DEFAULT_HOST,
            auth_token=data.get("auth_token") or None,
            queue_capacity=queue_capacity
            if queue_capacity and queue_capacity > 0
            else DEFAULT_QUEUE_CAPACITY,
            queue_wait_timeout_seconds=_load_timeout(
                data, "queue_wait_timeout_seconds", DEFAULT_QUEUE_WAIT_TIMEOUT_SECONDS
            ),
            execution_timeout_seconds=_load_timeout(
                data, "execution_timeout_seconds", DEFAULT_EXECUTION_TIMEOUT_SECONDS
            ),
        )
        logger.info(
            "MCP server 配置已加载：host=%s, authTokenSet=%s, queue_capacity=%s",
            config.host,
            bool(config.auth_token),
            config.queue_capacity,
        )
        return config
    except (OSError, json.JSONDecodeError):
        logger.exception("MCP server 配置读取失败：%s", path)
        return McpServerConfig()


def _create_template(file: Path) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(
        json.dumps(asdict(McpServerConfig()), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
