# CLAUDE.md — wechat-link-autogame-xcx

> 本项目契约的**唯一真相源是 [AGENTS.md](AGENTS.md)**；下方 `@AGENTS.md` 已将其全量导入。
> 本文件只承载 Claude Code 专属补充（skills / subagents / hooks）。修改契约请改 AGENTS.md，不要在此另起副本。

@AGENTS.md

## Claude Code 专属

### Skills（按需调用）

- `add-template-page` —— 按现有约定脚手架新增一个主导航页（侧栏导航 + content_stack + 控制器 + 契约测试，保持索引顺序）。
- `run-gui` —— 启动 GUI 并对 5 个导航页逐一截图到 `data/debug/`，用于对照设计稿、排查渲染、验证 UI 改动（无显示器走 offscreen）。

### Subagents（隔离只读，返回结论 + `file:line`）

- `explore` —— 定位代码 / 追踪调用链 / 核实依赖方向；回答"X 在哪 / 谁调用 Y / 是否违反依赖方向"。
- `ui-reviewer` —— 审查 `ui/` 改动是否符合设计稿（方案 A 深色控制台）与 UI 约定，出分级问题清单。每次改 `ui/` 后调用。

### Hooks

- `PostToolUse(Edit|Write|MultiEdit)` → `.claude/hooks/format_on_edit.py`：编辑后自动 ruff 格式化（配置见 `.claude/settings.json`）。

> 行为指南（Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution）见根 [../CLAUDE.md](../CLAUDE.md)。
