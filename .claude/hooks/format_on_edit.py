"""PostToolUse hook：对被 Edit/Write/MultiEdit 改动的 *.py 自动 ruff format + check --fix。

stdin 收到 Claude Code 的 PostToolUse 事件 JSON（含 tool_input.file_path）。
非 *.py 或无 file_path 时跳过。始终退出 0（不阻断工具流）；ruff 输出回显给 Claude。

这是 wechat-link-autogame-xcx 超越 wechat-ilink-bot 的点：bot 的 hooks 为空，本项目用
hooks 做"必须每次发生"的格式/lint 自洽（见 .claude/rules/python-conventions.md）。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    file_path = (event.get("tool_input") or {}).get("file_path", "")
    if not file_path or not file_path.endswith(".py"):
        return 0

    path = Path(file_path)
    if not path.is_file():
        return 0

    # format 幂等；check --fix 自动修可修的 lint，剩余告警回显但不阻断（check=False → exit 0）
    subprocess.run(["uv", "run", "ruff", "format", str(path)], check=False)
    subprocess.run(["uv", "run", "ruff", "check", "--fix", str(path)], check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
