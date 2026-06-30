# AGENTS.md

> **本文件是本项目的唯一契约真相源（single source of truth）。** Claude Code 经 [CLAUDE.md](CLAUDE.md) 的 `@AGENTS.md` 导入本文；其它 AI 工具直接读本文。项目门面见 [README.md](README.md)，详细架构见 [doc/architecture/](doc/architecture/)。
>
> 维护本文请遵守 [.claude/rules/doc-maintenance.md](.claude/rules/doc-maintenance.md) 的防漂移约定：分层图 / 依赖方向 / 已知债表**只在本文有权威副本**，其余文档链接本文而非重述；散文不硬编码行号。

## 项目概述

**wechat-link-autogame-xcx** —— 基于图像识别的**微信小程序游戏自动化**系统（Python 3.13 + PyQt6，仅 Windows）。

本地执行引擎（模板编辑 / 图像匹配 / DPI 坐标 / DGOCR / 执行器 / 报告）+ **MCP 服务端**（供 [wechat-ilink-bot](../wechat-ilink-bot) 通过 JSON-RPC over HTTP+SSE 远程调用执行模板）。

> 远程驱动（ilink）与 LLM 自然语言编排**已迁出至 [wechat-ilink-bot](../wechat-ilink-bot)**，本项目不再包含该层。

## 技术基线（不允许擅自升级）

| 技术 | 版本 | 约束 |
|------|------|------|
| Python | 3.13 | `requires-python = ">=3.13"`；src layout，绝对 import |
| GUI | PyQt6 >=6.7,<7 | 唯一 GUI 框架 |
| 图像 | opencv-python>=4.10, scikit-image, Pillow, numpy>=2.0 | 匹配/处理 |
| OCR | onnxruntime>=1.17 + 自研 dgocr | 模型走 Git LFS，放 `models/` |
| 自动化 | pyautogui, pywin32 (Windows), psutil | 仅 Windows |
| 几何 | shapely>=2.0, pyclipper | 多边形/区域 |
| 抓包 | mitmproxy>=12.2 | 预留 |
| MCP | mcp>=1.2 | 服务端 |
| 包管理 | uv | 不用 pip 直接装；`uv sync` |
| Lint/格式 | ruff>=0.6 | line-length 100，select E/F/I/B/UP/SIM |
| 类型 | mypy>=1.10 | 渐进式（strict=false） |
| 测试 | pytest>=8.0 + pytest-qt + pytest-cov | `testpaths=["tests/unit"]` |

## 包结构

```
autogame_xcx/
├── core/                 # 业务核心：game_executor / image_matcher / template_manager /
│                         #          coordinate_converter / report_generator / process_main(CLI)
├── platform/             # Windows API 隔离：window_controller（窗口枚举/激活/缩放/截图）
├── ocr/                  # OCR：engine + dgocr/（自研 ONNX det+rec+seglink）
├── mcp/                  # MCP 服务端：server / tools / executor_bridge（→ core.GameExecutor）
├── ui/                   # PyQt6 GUI（Phase E 薄壳化已完成）：
│   ├── main_window.py    #   MainGUI 薄壳：标题栏 + 侧栏 + content_stack + 状态栏 + 5 页路由
│   ├── pages/            #   导航页：intro / management / creator / guide（+ dialogs/mcp_server_page）
│   ├── widgets/          #   可复用控件：FlowLayout / NavButton / ConsoleStatusBar / FeatureCard / StepItem / PageHeader
│   ├── controllers/      #   UI ↔ core 中介：app_controller（core 单件唯一入口）
│   ├── dialogs/          #   模态对话框：area_config / area_test / matching_test / report_viewer / template_execution / template_test / mcp_server_page
│   ├── theme.py          #   集中深色 QSS 调色板
│   └── icons.py          #   图标
└── utils/                # 通用工具：opencv(CvTool) / constants / legacy device·window
```

## 分层与依赖方向（**权威定义**；经 import 图谱核实）

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

**严格向下，严禁反向。** `core` 不得 `import ui`；`utils` 不得 `import core/ui`；`mcp` 不得 `import ui/platform`。
平台专属调用（`win32gui`/`win32api`/`win32process`/`pyautogui`/`psutil`）**只允许出现在 `platform/window_controller.py`**；`ui`/`core` 需窗口/截图能力时经 `GameWindowController`。

## 目录职责边界

| 目录 | 职责 | 禁止 |
|------|------|------|
| `core/` | 业务逻辑：执行器 / 匹配器 / 模板管理 / 坐标 / 报告 / CLI | `import PyQt6`；`import ...ui` |
| `platform/` | Windows API 隔离：窗口枚举/激活/缩放/截图 | 业务流程；非 Windows 抛 `PlatformNotSupportedError` |
| `ocr/` | OCR 引擎封装 + dgocr 内部实现 | 被 UI 直接调用（须经 core） |
| `mcp/` | MCP 服务端：工具定义 + executor 桥 + server 线程 | `import ui/platform`（只 → core） |
| `ui/` | PyQt6 界面、对话框、功能页 | 直接调 `pyautogui`/`win32gui`/`win32api`（须经 `platform.window_controller`）；页面/对话框直接 `import core`（须经 `controllers/`） |
| `utils/` | 通用工具（OpenCV 工具、legacy device/window、常量） | 业务知识；向上 import |

## 硬性规则

1. **依赖方向**：见上，严格向下，严禁反向；新增代码不得引入反向依赖。
2. **绝对 import**：所有导入走 `autogame_xcx.*` 绝对包路径；**禁止 `sys.path.insert/append` hack**。
3. **日志**：禁止 `print(...)` 做日志，用 `logging.getLogger(__name__)`（存量可渐进迁移，**新增代码不得用 print**）。
4. **平台隔离**：`ui/`、`core/` 禁止直接调 `pyautogui`/`win32gui`/`win32api`；经 `platform.window_controller`。
5. **UI 经 controller 访问 core**：页面/对话框不直接 `import core.*`，经 `ui/controllers/`。
6. **文件体量**：单文件 ≤ 500 行（已知超长例外见下表；新增文件遵守）。
7. **测试**：新功能补 `tests/unit`；`uv run pytest tests/unit` 必须通过，不得提交红测。
8. **OCR 算法区**：`ocr/dgocr/` 仅按需改推理接线，不动识别算法；模型走 Git LFS。
9. **文档同步**：代码变更后按 [.claude/rules/doc-maintenance.md](.claude/rules/doc-maintenance.md) 同步文档。

## 已知债（**权威清单**；历史遗留，不得扩大、不得效仿，重构时收敛）

> 其它文档不再各自维护"已知违规"小节，统一链接本表。AI 碰到下列位置应识别为**既有债**而非新增违规，**新代码不得照抄这些写法**。

| 位置 | 债务 | 处置 |
|------|------|------|
| `core/process_main.py` `--gui` 分支 | `from autogame_xcx.ui.template_creator import TemplateCreatorGUI`（core → ui 反向依赖） | CLI 启动 GUI 的职责应上提到入口层；入口层重构时消除 |
| `core/game_executor.py`、`core/coordinate_converter.py` | 直接 `import pyautogui` / `win32gui` / `win32api`（破坏平台隔离） | 窗口/坐标能力应经 `platform.window_controller`；重构时收敛 |
| `ocr/engine.py` | 直接 `import pyautogui` / `win32gui` | 取窗口/截图应经 platform；重构时收敛 |
| `ui/pages/creator_page.py` | 约 879 行，超单文件 ≤ 500 行规则 | Phase E3/E4 按设计稿精修后再拆；新文件不得效仿 |
| `ui/dialogs/*_dialog.py` | 直接 `import core.{image_matcher,game_executor}`（未经 controller） | UI 经 controller 访问 core 的债；重构时收敛 |
| `ui/template_creator.py` | 978 行历史上帝对象（现仅 CLI `--gui` 分支调用，主 GUI 路径已不用） | 随入口层/CLI creator 去留一并处理 |

> Phase E 已完成主 GUI 薄壳化：`ui/main_window.py` 现为约 284 行外壳（曾 2252 行）。

## 场景锚点（你要做什么 → 先看这个）

| 你要做什么 | 去哪里看 |
|-----------|---------|
| 项目门面 / 定位 | [README.md](README.md) |
| 后续路线 / 项目走向 | [doc/ROADMAP.md](doc/ROADMAP.md) |
| 理解架构分层 | [doc/architecture/overview.md](doc/architecture/overview.md) |
| 层边界 / 依赖方向 / 证据 | [doc/architecture/boundaries.md](doc/architecture/boundaries.md) |
| 现有演进规划（src layout/分层/迁移） | [doc/plans/PLAN_01_代码结构规范化.md](doc/plans/PLAN_01_代码结构规范化.md) |
| MCP 服务端 ↔ 客户端 | `src/autogame_xcx/mcp/` ↔ [../wechat-ilink-bot/docs/design/mcp-autogame.md](../wechat-ilink-bot/docs/design/mcp-autogame.md) |
| 启动 GUI | `start_main_gui.py` |
| CLI 自检 / 列模板 / 执行 | `src/autogame_xcx/core/process_main.py` |
| 图像匹配算法 | `core/image_matcher.py` |
| 模板增删改查 | `core/template_manager.py` |
| 坐标 / DPI 三态 | `core/coordinate_converter.py` |
| OCR 引擎 | `ocr/engine.py` + `ocr/dgocr/` |
| UI 重构目标 / 设计稿 | `D:\note-yym\工作笔迹\杂记\微信ilink\Qt6 桌面应用重设计\重设计方案.dc.html` |
| Python / UI / 测试 / 文档约定 | `.claude/rules/{python-conventions,ui-conventions,testing,doc-maintenance}.md` |

## 编码约定

- Python 3.13、src layout、绝对 import（`from autogame_xcx.<pkg>.<mod> import ...`）
- ruff：line-length 100，规则集 E/F/I/B/UP/SIM；格式化用 `ruff format`
- 包管理统一用 uv（`uv sync` / `uv run ...`）
- 提交消息前缀：`feat:` / `fix:` / `refactor:` / `test:` / `docs:` / `chore:`
- 测试文件命名：`tests/unit/test_<主题>[_<场景>].py`

## 常用命令

```powershell
uv sync                                              # 安装依赖
python start_main_gui.py                             # 启动 GUI
python -m autogame_xcx.core.process_main --test all  # CLI 自检
uv run pytest tests/unit -v                          # 单测
uv run ruff check . && uv run ruff format .          # lint + 格式化
uv run mypy src                                      # 类型检查
```

> 行为指南（Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution）由根级 [../CLAUDE.md](../CLAUDE.md)（wechat-ilink 仓库根）统一定义，此处不重复。
