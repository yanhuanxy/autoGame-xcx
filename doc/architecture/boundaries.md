# 架构边界与依赖方向

> 速查规则见 [.claude/rules/architecture.md](../../.claude/rules/architecture.md)。本文档给出依据、证据与执行细节。

## 依赖方向（经 import 图谱核实）

```
ui ──→ mcp ──→ core ──→ platform
 │       │       │         │
 │       └───────┴──→ utils ←─── ocr（当前自包含）
 └──────────────┘
```

| 层 | 可调用 | 不可调用 |
|----|--------|----------|
| `ui/` | core, mcp, platform, utils | — |
| `mcp/` | core（仅） | ui, platform |
| `core/` | platform, utils, core 自身 | ui, mcp |
| `platform/` | utils | core, ui, mcp |
| `ocr/` | （当前自包含） | core, ui |
| `utils/` | （不向上） | core, ui, mcp, platform, ocr |

## 核实证据（grep `from/import autogame_xcx.*`）

- `ui/` → `core.{image_matcher,template_manager,game_executor,report_generator}`、`platform.window_controller`、`utils.constants`、`mcp.{ExecutorBridge,McpServerThread}`、内部 `ui.dialogs.*` ✓
- `mcp/executor_bridge.py` → `core.{game_executor,template_manager}` ✓（仅 core）
- `core/` → `platform.window_controller`、`utils.{constants,opencv}`、core 自身 ✓
- `platform/` · `ocr/` · `utils/` → 无 `core`/`ui` 反向引用 ✓

## 平台 / SDK 隔离

`win32gui` / `win32api` / `win32process` / `pyautogui` / `psutil` 等 Windows 专属调用**只允许出现在 `platform/window_controller.py`**。`ui/` 与 `core/` 需要窗口/截图时经 `GameWindowController`，**不得直接 import 这些库**。

```python
# 正确
from autogame_xcx.platform.window_controller import GameWindowController

# 错误（ui/core 内禁止）
import pyautogui
import win32gui
```

## MCP 边界

- `mcp/` 只依赖 `core`（`executor_bridge` 是唯一桥）；不依赖 `ui/platform`。
- MCP server 由 `ui` 经 `McpServerThread` 启停；`start_main_gui.py` 在退出前优雅 `request_stop`。
- 客户端侧（wechat-ilink-bot）接入设计见 `../wechat-ilink-bot/docs/design/mcp-autogame.md`。

## 已知违规（历史债）

> 权威清单见 [AGENTS.md「已知债」表](../../AGENTS.md)（统一登记，避免多处漂移），含：
> - `core/process_main.py` 的 `--gui` 分支反向 `import ui.template_creator`（core → ui）；
> - `core/game_executor.py`、`core/coordinate_converter.py`、`ocr/engine.py` 直接 `import pyautogui/win32`（破坏上节"平台调用只在 `platform/`"的隔离，属历史债，重构时收敛）；
> - `ui/dialogs/*_dialog.py` 直接 `import core`、`ui/pages/creator_page.py` 超 500 行等。
>
> 一律**不得扩大、不得效仿**；CLI 启动 GUI 的职责应上提到入口层。

## 守则

- 新代码不得引入反向依赖；重构方向是收敛而非放宽。
- 改动若触及层边界，按 [.claude/rules/doc-maintenance.md](../../.claude/rules/doc-maintenance.md) 同步本文档与 `.claude/rules/architecture.md`。
