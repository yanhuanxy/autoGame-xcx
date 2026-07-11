"""McpServerConfig 加载测试（迭代C）。"""

from __future__ import annotations

import json
from pathlib import Path

from autogame_xcx.mcp.server_config import (
    DEFAULT_EXECUTION_TIMEOUT_SECONDS,
    DEFAULT_HOST,
    DEFAULT_QUEUE_CAPACITY,
    DEFAULT_QUEUE_WAIT_TIMEOUT_SECONDS,
    McpServerConfig,
    load,
)


def test_defaults_localhost_no_token() -> None:
    config = McpServerConfig()
    assert config.host == DEFAULT_HOST
    assert config.auth_token is None
    assert config.queue_capacity == DEFAULT_QUEUE_CAPACITY
    assert config.queue_wait_timeout_seconds == DEFAULT_QUEUE_WAIT_TIMEOUT_SECONDS
    assert config.execution_timeout_seconds == DEFAULT_EXECUTION_TIMEOUT_SECONDS


def test_load_missingFile_returnsDefaultsAndCreatesTemplate(tmp_path: Path) -> None:
    missing = tmp_path / "nope" / "mcp_server_config.json"

    config = load(str(missing))

    assert config.host == DEFAULT_HOST
    assert config.auth_token is None
    assert missing.exists()
    assert config.queue_capacity == DEFAULT_QUEUE_CAPACITY


def test_load_validFile_appliesValues(tmp_path: Path) -> None:
    file = tmp_path / "mcp_server_config.json"
    file.write_text(
        json.dumps(
            {
                "host": "0.0.0.0",
                "auth_token": "secret-token",
                "queue_capacity": 5,
                "queue_wait_timeout_seconds": 120.0,
                "execution_timeout_seconds": 200.0,
            }
        ),
        encoding="utf-8",
    )

    config = load(str(file))

    assert config.host == "0.0.0.0"
    assert config.auth_token == "secret-token"
    assert config.queue_capacity == 5
    assert config.queue_wait_timeout_seconds == 120.0
    assert config.execution_timeout_seconds == 200.0


def test_load_malformedFile_returnsDefaults(tmp_path: Path) -> None:
    file = tmp_path / "mcp_server_config.json"
    file.write_text("not-json-at-all", encoding="utf-8")

    config = load(str(file))

    assert config.host == DEFAULT_HOST
    assert config.auth_token is None
    assert config.queue_capacity == DEFAULT_QUEUE_CAPACITY


def test_load_missingNewFields_fallsBackToDefaults(tmp_path: Path) -> None:
    """旧版本只生成了 host/auth_token 两个字段的配置文件，新增字段应回退默认值。"""
    file = tmp_path / "mcp_server_config.json"
    file.write_text(json.dumps({"host": "0.0.0.0", "auth_token": "t"}), encoding="utf-8")

    config = load(str(file))

    assert config.queue_capacity == DEFAULT_QUEUE_CAPACITY
    assert config.queue_wait_timeout_seconds == DEFAULT_QUEUE_WAIT_TIMEOUT_SECONDS
    assert config.execution_timeout_seconds == DEFAULT_EXECUTION_TIMEOUT_SECONDS


def test_load_zeroTimeout_meansDisabled(tmp_path: Path) -> None:
    file = tmp_path / "mcp_server_config.json"
    file.write_text(
        json.dumps({"queue_wait_timeout_seconds": 0, "execution_timeout_seconds": -1}),
        encoding="utf-8",
    )

    config = load(str(file))

    assert config.queue_wait_timeout_seconds is None
    assert config.execution_timeout_seconds is None


def test_load_invalidQueueCapacity_fallsBackToDefault(tmp_path: Path) -> None:
    file = tmp_path / "mcp_server_config.json"
    file.write_text(json.dumps({"queue_capacity": 0}), encoding="utf-8")

    config = load(str(file))

    assert config.queue_capacity == DEFAULT_QUEUE_CAPACITY
