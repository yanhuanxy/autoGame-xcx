# wechat-link-autogame-xcx

> 微信小程序游戏自动化系统：本地图像识别执行引擎 + MCP 服务端

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-blue.svg)](https://learn.microsoft.com/windows/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## 能力概览

本项目是 [wechat-ilink-bot](../wechat-ilink-bot) 体系中的**本地执行 + MCP 服务端**：

| 层 | 目录 | 职责 |
|---|---|---|
| **本地执行层** | `src/autogame_xcx/core/` + `platform/` + `ocr/` | 图像匹配（多种算法）、DPI 三态自适应坐标转换、DGOCR 文字识别、模板执行引擎、HTML/JSON 报告 |
| **MCP 服务层** | `src/autogame_xcx/mcp/` | 暴露 MCP 工具（执行/列出模板、查报告等），供 wechat-ilink-bot 通过 JSON-RPC over HTTP+SSE 远程调用 |

> 远程驱动（ilink）与 LLM 自然语言编排已迁移到 [wechat-ilink-bot](../wechat-ilink-bot)，本项目不再包含该层。

## 安装

### 前置要求

- Windows 10 / 11
- Python 3.13+
- [uv](https://docs.astral.sh/uv/)（推荐）或 pip
- 微信 PC 客户端（自动化目标窗口）

### 步骤

```powershell
# 1. 克隆项目
git clone <repo-url>
cd wechat-link-autogame-xcx

# 2. 使用 uv 同步依赖
uv sync
```

### DGOCR 模型下载

本项目使用 `duguang-ocr-onnx-v2` 进行文字识别，下载下列成对模型到 `models/duguang-ocr-onnx-v2/`：

| 模型 | 模型大小 | modelscope 下载 | 个人评价 |
|---|---|---|---|
| base_seglink++ | 73.2MB+78MB | [v2 地址](https://modelscope.cn/models/mscoder/duguang-ocr-onnx-v2) | 9 分 |
| large | 73.2MB+46.4MB | [v2 地址](https://modelscope.cn/models/mscoder/duguang-ocr-onnx-v2) | 8 分 |
| small | 7.4MB+5.2MB | [v2 地址](https://modelscope.cn/models/mscoder/duguang-ocr-onnx-v2) | 5 分 |

> rec 和 det 可以自由组合使用。

## 快速开始

### GUI 模式（推荐）

```powershell
python start_main_gui.py
```

提供可视化模板编辑、匹配测试、执行监控、MCP 服务控制。

### CLI 模式

```powershell
# 自检（窗口/图像/坐标/模板四项）
python -m autogame_xcx.core.process_main --test all

# 列出已有模板
python -m autogame_xcx.core.process_main --list-templates

# 执行指定模板
python -m autogame_xcx.core.process_main --execute <template_name>
```

## 配置

### 窗口关键字

默认匹配 `"聊斋搜神记"`，其他游戏调用 `find_wechat_window(keyword=...)` 传入关键字，或修改 `GameWindowController.DEFAULT_WINDOW_KEYWORD` 类常量。

### MCP 服务

GUI 内「MCP 服务」页可启动/停止内嵌 MCP server（默认端口 `8765`）。客户端（wechat-ilink-bot）侧的接入配置见 [wechat-ilink-bot/docs/design/mcp-autogame.md](../wechat-ilink-bot/docs/design/mcp-autogame.md)。

## 项目结构

```
wechat-link-autogame-xcx/
├── src/autogame_xcx/
│   ├── core/                # 本地执行层
│   │   ├── image_matcher.py         # 多种图像匹配算法
│   │   ├── coordinate_converter.py  # DPI 三态坐标转换
│   │   ├── game_executor.py         # 模板执行引擎
│   │   ├── template_manager.py      # 模板增删改查
│   │   ├── process_main.py          # CLI 入口
│   │   └── report_generator.py      # HTML/JSON/Text 报告
│   ├── platform/            # 窗口控制 + DPI（Windows API 隔离）
│   ├── ocr/                 # DGOCR 集成
│   │   ├── engine.py
│   │   └── dgocr/           # 自研 ONNX OCR（det+rec+seglink）
│   ├── mcp/                 # MCP 服务层（供 wechat-ilink-bot 调用）
│   │   ├── server.py                # MCP server
│   │   ├── tools.py                 # MCP 工具定义
│   │   └── executor_bridge.py       # MCP ↔ GameExecutor 桥接
│   ├── ui/                  # PyQt6 GUI（Phase E 薄壳化已完成）
│   │   ├── main_window.py           # MainGUI 薄壳（外壳 + 5 页路由）
│   │   ├── pages/                   # 导航页 intro / management / creator / guide
│   │   ├── widgets/                 # 可复用控件
│   │   ├── controllers/             # UI ↔ core 中介
│   │   ├── theme.py / icons.py      # 主题与图标
│   │   ├── template_creator.py      # TemplateCreatorGUI（历史债，仅 CLI --gui 用）
│   │   └── dialogs/                 # 各类对话框 / 功能页
│   └── utils/              # 通用工具（OpenCV、legacy device/window、常量）
├── data/                    # 模板 / 配置 / 参考图 / 报告
├── doc/                     # 设计文档 + 历史计划
│   ├── architecture/                # overview / boundaries（架构详解）
│   ├── plans/                       # PLAN_01..03 演进规划
│   └── archive/                     # 历史文档（Phase 1/2、verification_report，已过时仅追溯）
├── tests/unit/              # 单元测试
├── start_main_gui.py        # GUI 入口
└── pyproject.toml
```

## 文档导航

- [AGENTS.md](AGENTS.md) — 项目契约真相源（分层 / 依赖 / 已知债 / 约定）
- [doc/architecture/](doc/architecture/) — 架构详解（overview / boundaries）
- [doc/plans/](doc/plans/) — PLAN_01..03 后续架构演进规划
- [doc/archive/](doc/archive/) — 历史文档（Phase 1/2、verification_report，已过时仅作追溯）

## 测试

```powershell
# 全量单测
uv run pytest tests/unit -v
```

## License

MIT
