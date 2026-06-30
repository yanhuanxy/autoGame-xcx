# 测试约定

## 框架与布局

- pytest，`testpaths = ["tests/unit"]`，`pythonpath = ["src"]`
- 目录按粒度分：`tests/unit/`（默认收集）、`tests/manual/`（demo/verify 脚本，默认不收集）、`tests/integration|e2e`（需真实环境，标 mark）

## 标记（`--strict-markers`）

| mark | 含义 | 用法 |
|------|------|------|
| `integration` | 需真实微信窗口 | `@pytest.mark.integration` |
| `e2e` | 完整模板执行 | `@pytest.mark.e2e` |
| `gui` | 需 PyQt6 显示 | `@pytest.mark.gui` |

无标记 = 纯逻辑单测，必须能在无窗口环境跑过。

## GUI 测试

- 用 `pytest-qt`；无显示环境设 `QT_QPA_PLATFORM=offscreen`
- GUI 类冒烟（能实例化 `MainGUI` / 各 dialog 不崩）标 `@pytest.mark.gui`
- CI/无头：`QT_QPA_PLATFORM=offscreen uv run pytest tests/unit`

## Fixture

- 共享 fixture 放 `tests/unit/conftest.py`（样例模板、假窗口、临时 `data/` 目录等）
- 需要图像/模板的测试用 fixture 提供最小样本，不依赖真实游戏截图

## 红线

- `uv run pytest tests/unit` 必须全绿才能提交
- 新功能/bugfix 先写测试再改代码（Goal-Driven）：`"fix bug" → 写复现测试 → 让它过`
- 重构前对目标模块补**特征化测试**（characterization）锁定现有行为
