# UI 编码约定

> 目标设计稿：`D:\note-yym\工作笔迹\杂记\微信ilink\Qt6 桌面应用重设计\重设计方案.dc.html`（方案 A 深色控制台：侧栏导航壳 + 5 页）。
> Phase E 薄壳化**已完成**：`ui/main_window.py` 现为约 284 行外壳（曾 2252 行）。剩余历史债（`ui/template_creator.py` 978 行、`ui/pages/creator_page.py` 879 行等）见 [AGENTS.md 「已知债」表](../../AGENTS.md)。

## 当前结构（Phase E 已落地）

```
ui/
├── main_window.py        # 窗口外壳：标题栏 + 侧栏 + content_stack + 状态栏 + 5 页路由
├── pages/                # 导航页：intro / management / creator / guide（+ dialogs/mcp_server_page）
├── widgets/              # 可复用控件：FlowLayout / NavButton / ConsoleStatusBar / FeatureCard / StepItem / PageHeader
├── controllers/          # UI ↔ core 中介：app_controller（core 单件唯一入口）
├── dialogs/              # 模态对话框
├── theme.py              # 集中深色 QSS 调色板
└── icons.py              # 图标
```

## 硬性约定

1. **UI 不直接调 `pyautogui`/`win32gui`/`win32api`**；窗口/截图经 `platform.window_controller`（见 [architecture.md](architecture.md)）。
2. **UI 经 controller 访问 core**：页面/对话框不直接 `import core.*`，经 `controllers/` 中介。
   - ⚠️ `ui/dialogs/*_dialog.py` 仍有直接 `import core` 的历史债（见 AGENTS.md 已知债表），重构时收敛，新代码不得效仿。
3. **单文件 ≤ 500 行**：`main_window.py` 只做外壳与路由；每页一个文件；超长对话框拆 widgets。已知超长例外（`creator_page.py` 879 行等）见 AGENTS.md。
4. **QSS 主题集中**：深色调色板（`#0d1117` / `#161b22` / `#21262d` / `#4493f8` / `#e6edf3` 等）集中在 `ui/theme.py`，不在控件上散落内联颜色。
5. **状态栏技术信息用等宽字体**（`QFontDatabase.Monospace`），承载版本/端口/运行状态。

## 重构守则

- **特征化先行**：继续动 `main_window.py` 等历史债前，先在 `tests/unit` 补/复用特征化测试（快照当前行为）作安全网（见 [testing.md](testing.md)）。
- **surgical**：逐页迁移/精修，每步 `uv run pytest tests/unit` 保持绿；不一次性大改。
- 全程保持 `python start_main_gui.py` 可启动、各页可达。
