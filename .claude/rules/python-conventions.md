# Python 编码约定

## 包与导入

- **src layout + 绝对 import**：`from autogame_xcx.<pkg>.<mod> import <Name>`
- **禁止** `sys.path.insert` / `sys.path.append` / `importlib` 拼路径 hack
- 跨包导入遵守 [architecture.md](architecture.md) 的依赖方向
- 标准库 → 第三方 → 本项目，三段分组的 import 顺序（ruff `I` 强制）

## 路径

- 运行时路径基于项目根计算，**不依赖 cwd**：用 `utils/constants.py` 中的路径常量（`REFERENCE_IMAGES_PATH` / `TEMPLATES_PATH` / `REPORTS_PATH` / `DEBUG_IMAGES_PATH` 等）
- 中文路径的图像读写用 `utils.opencv.CvTool`（封装 `imread`/`imwrite` 的中文路径处理），不直接调 `cv2.imread`

## 日志

- 用 `logging.getLogger(__name__)`，**禁止 `print(...)`** 做日志
- 存量 `print` 可渐进迁移；**新增代码不得用 print**

## 格式 / Lint / 类型

- ruff：`line-length = 100`，规则集 `E, F, I, B, UP, SIM`（`E501` 忽略，由 line-length 兜底）
- 格式化统一 `ruff format`；提交前 `uv run ruff check .` 无错
- 类型标注渐进式（`mypy strict=false, ignore_missing_imports=true`）；新增公共 API 建议加类型

## 命名

- 模块/包：`snake_case`；类：`PascalCase`；常量：`UPPER_SNAKE`
- 测试文件：`tests/unit/test_<主题>[_<场景>].py`

## 依赖与打包

- 包管理统一 `uv`（`uv sync` / `uv add` / `uv run`），不直接 `pip install`
- 新增/升级依赖须同步更新 `pyproject.toml` 与根 [CLAUDE.md](../../CLAUDE.md) 的技术基线表
