# 架构概述

> 项目定位见根 [README.md](../../README.md)，项目契约真相源见 [AGENTS.md](../../AGENTS.md)，后续路线见 [ROADMAP.md](../ROADMAP.md)。本文给出架构详解；**分层表/依赖方向以 AGENTS.md 为权威**。

## 定位

基于图像识别的**微信小程序游戏自动化**：本地执行引擎（模板编辑 → 图像匹配 → DPI 坐标 → OCR → 执行 → 报告）+ **MCP 服务端**（供 [wechat-ilink-bot](../../../wechat-ilink-bot) 通过 JSON-RPC over HTTP+SSE 远程调用执行模板）。

> 远程驱动（ilink）与 LLM 编排已迁出至 wechat-ilink-bot；本项目专注本地执行 + MCP 暴露。

## 分层

```
┌──────────────────────────────────────────────────────┐
│                      UI 层 (PyQt6)                     │
│  main_window · template_creator · dialogs/            │
│  （界面、对话框、功能页；经 controller/platform 访问能力）│
├──────────────────────────────────────────────────────┤
│                   MCP 服务层                           │
│  server(McpServerThread) · tools · executor_bridge    │
│  （暴露 MCP 工具 → 桥接 core.GameExecutor）            │
├──────────────────────────────────────────────────────┤
│                    Core 业务层                         │
│  game_executor · image_matcher · template_manager     │
│  coordinate_converter · report_generator · process_main│
├──────────────────────────────────────────────────────┤
│        Platform（Windows API 隔离）   ·   OCR          │
│  window_controller                    engine + dgocr/  │
├──────────────────────────────────────────────────────┤
│                       Utils                           │
│  opencv(CvTool) · constants · legacy device/window    │
└──────────────────────────────────────────────────────┘
```

**依赖方向**：UI → {Core, MCP, Platform, Utils}；MCP → Core；Core → {Platform, Utils}；Platform → Utils；OCR 自包含；Utils 不向上。详见 [boundaries.md](boundaries.md)。

## 包结构

```
autogame_xcx/
├── core/                       # 业务核心
│   ├── game_executor.py          # 模板执行引擎（execute_template/task/step 三层）
│   ├── image_matcher.py          # 图像匹配（多种算法）
│   ├── template_manager.py       # 模板 JSON 增删改查 + 校验
│   ├── coordinate_converter.py   # DPI 三态自适应坐标转换
│   ├── report_generator.py       # HTML/JSON/Text 报告
│   └── process_main.py           # CLI 入口（--test/--list-templates/--execute）
│
├── platform/                   # Windows API 隔离
│   └── window_controller.py      # 窗口枚举/激活/缩放/截图（win32gui/pyautogui/psutil）
│
├── ocr/                        # OCR
│   ├── engine.py                 # OCR 引擎封装
│   └── dgocr/                    # 自研 ONNX OCR（det + rec + seglink）
│
├── mcp/                        # MCP 服务端（供 wechat-ilink-bot 调用）
│   ├── server.py                 # McpServerThread（uvicorn 生命周期）
│   ├── tools.py                  # MCP 工具定义（list_all_tools / call_tool）
│   └── executor_bridge.py        # MCP ↔ GameExecutor 桥（仅 import core）
│
├── ui/                         # PyQt6 GUI（Phase E 薄壳化已完成）
│   ├── main_window.py            # MainGUI 薄壳（约 284 行）：标题栏+侧栏+content_stack+状态栏+5 页路由
│   ├── pages/                    # 导航页：intro / management / creator / guide
│   ├── widgets/                  # FlowLayout / NavButton / ConsoleStatusBar / FeatureCard / StepItem / PageHeader
│   ├── controllers/              # app_controller（UI ↔ core 中介，core 单件唯一入口）
│   ├── theme.py                  # 集中深色 QSS 调色板
│   ├── icons.py                  # 图标
│   ├── template_creator.py       # TemplateCreatorGUI（978 行历史债，仅 CLI --gui 路径用）
│   └── dialogs/                  # area_config / area_test / matching_test /
│                                 # report_viewer / template_execution / template_test / mcp_server_page
│
└── utils/                      # 通用工具
    ├── opencv.py                 # CvTool（中文路径 imread/imwrite）
    ├── constants.py              # 路径常量 + ele_coords
    └── device.py / window.py     # Phase 1 legacy（保留）
```

## 关键依赖关系

- `start_main_gui.py`（入口）→ `ui.main_window.MainGUI`；退出前优雅停止 `McpServerThread`
- `ui.main_window` → `core.{image_matcher,template_manager,game_executor,report_generator}` + `platform.window_controller` + `mcp.{ExecutorBridge,McpServerThread}`
- `mcp.executor_bridge` → `core.{game_executor,template_manager}`
- `core.game_executor` → `core.{image_matcher,coordinate_converter,template_manager,report_generator}` + `platform.window_controller`
- `core.process_main`（CLI）→ `core.*` + `platform.window_controller`（⚠️ 反向 import `ui.template_creator` 为已知违规）

## 外部依赖

- **PyQt6**：GUI 框架
- **opencv / scikit-image / numpy / Pillow**：图像匹配与处理
- **onnxruntime + 自研 dgocr**：文字识别（模型走 Git LFS）
- **pyautogui / pywin32 / psutil**：Windows 窗口与输入控制（隔离在 `platform/`）
- **mcp**：MCP 服务端 SDK
- **mitmproxy**：抓包（预留，方向 3）
