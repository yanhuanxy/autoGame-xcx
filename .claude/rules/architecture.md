# 架构规则（约束速查）

> **权威分层表 / 依赖方向 / 已知债清单见 [AGENTS.md](../../AGENTS.md)**；详细证据与隔离示例见 [doc/architecture/boundaries.md](../../doc/architecture/boundaries.md)。本文只列须随手遵守的约束，不重画分层图。

## 依赖方向

- 严格向下，严禁反向：`ui → mcp → core → platform → utils`；`ocr` 当前自包含。
- `core` 不得 `import ui/mcp`；`mcp` 不得 `import ui/platform`；`utils` 不向上 import。

## 平台 / SDK 隔离

- `win32gui` / `win32api` / `win32process` / `pyautogui` / `psutil` 等 Windows 专属调用**只允许出现在 `platform/window_controller.py`**。
- `ui/` 与 `core/` 需要窗口/截图能力时经 `GameWindowController`，**不得直接 import 上述库**。
- 非 Windows 平台调用平台能力应抛 `PlatformNotSupportedError`（或条件导入），不得 import 即崩。

```python
# 正确 — 经 platform 间接使用窗口能力
from autogame_xcx.platform.window_controller import GameWindowController

# 错误 — ui/core 内直接调
import pyautogui                       # 禁止
import win32gui                        # 禁止
```

## MCP 桥接

- `mcp/executor_bridge.py` 是 MCP 工具到 `core.GameExecutor` 的唯一桥；MCP 工具不直接 new 业务对象，经 bridge。
- `mcp/` 只 `import core`，不 `import ui/platform`。MCP server 由 `ui` 经 `McpServerThread` 启停，生命周期见 `start_main_gui.py`。

> 已知违规（如 `core/process_main.py` 的 `--gui` 分支反向 `import ui`、`core`/`ocr` 直接调平台库）统一登记在 [AGENTS.md 「已知债」表](../../AGENTS.md)，本文不再单列——避免行号/清单多处漂移。
