"""McpServerConfig 加载测试（迭代C）。"""

from __future__ import annotations

import json
from pathlib import Path

from autogame_xcx.mcp.server_config import DEFAULT_HOST, McpServerConfig, load


def test_defaults_localhost_no_token() -> None:
    config = McpServerConfig()
    assert config.host == DEFAULT_HOST
    assert config.auth_token is None


def test_load_missingFile_returnsDefaultsAndCreatesTemplate(tmp_path: Path) -> None:
    missing = tmp_path / "nope" / "mcp_server_config.json"

    config = load(str(missing))

    assert config.host == DEFAULT_HOST
    assert config.auth_token is None
    assert missing.exists()


def test_load_validFile_appliesValues(tmp_path: Path) -> None:
    file = tmp_path / "mcp_server_config.json"
    file.write_text(json.dumps({"host": "0.0.0.0", "auth_token": "secret-token"}), encoding="utf-8")

    config = load(str(file))

    assert config.host == "0.0.0.0"
    assert config.auth_token == "secret-token"


def test_load_malformedFile_returnsDefaults(tmp_path: Path) -> None:
    file = tmp_path / "mcp_server_config.json"
    file.write_text("not-json-at-all", encoding="utf-8")

    config = load(str(file))

    assert config.host == DEFAULT_HOST
    assert config.auth_token is None
