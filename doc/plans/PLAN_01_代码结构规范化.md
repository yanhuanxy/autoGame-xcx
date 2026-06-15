# PLAN_01：代码结构规范化

> 项目：`wechat-link-autogame-xcx`（微信小程序游戏自动化）
> 方向：引入 src layout + 分层包 + 现代工具链，解决现有工程债
> 预计周期：5 阶段 × 2~3 天 = 约 2 周
> 前置依赖：无（方向 1 是方向 2/3 的前置）

---

## 1. Context（为什么做）

当前项目"能跑"建立在 `sys.path.insert` hack 之上，导致：

- **IDE 跳转失败**：必须把根目录 mark as root 才识别 `from gui.core.X`，新成员上手困难。
- **打包发布失败**：`pyproject.toml` 没声明包，`pip install` 后 import 路径全错。
- **测试 import 失败**：`test/test_template_list.py` 自己复制了一份 `sys.path.insert` 才能跑。
- **分层倒挂**：`gui/core/` 包含 6 个与 GUI 无关的业务模块（game_executor / image_matcher / template_manager 等），GUI 反过来寄生在 core 上。
- **构建配置冲突**：`pyproject.toml`（项目名 `autogame-xcx`，Python>=3.13）与 `setup.py`（项目名 `autoGame-xcx`，Python>=3.7）双重存在，依赖描述不一致。
- **测试无序**：`test/` 下 18 个文件命名风格混杂（`test_*` / `demo_*` / `verify_*` / `basic_*`），无 unit/integration 分类，pytest 默认无法良好收集。
- **基础设施缺失**：无标准化 logging、配置中心、统一异常体系、类型检查、lint。

不解决结构问题，方向 2（ilink 远程驱动）和方向 3（协议化）都会在导入、依赖、打包上反复踩坑。**方向 1 是方向 2 和 3 的前置条件**。

---

## 2. 现状盘点

### 2.1 已实现并需保留的核心资产（迁移时逐字保留算法）

| 当前路径 | 类/函数 | 价值 | 迁移目标 | 迁移注意 |
|---|---|---|---|---|
| `gui/core/game_executor.py` | `GameExecutor` | 业务核心调度器，三层结构（execute_template/task/step） | `core/executor.py` | 后续方向 3 会抽象为 StrategyContext，方向 1 阶段不动 |
| `gui/core/image_matcher.py` | `ImageMatcher`（template/ssim/feature/histogram/hybrid） | 5 种匹配算法成熟 | `core/matcher.py` | `print` → `logger`，算法不动 |
| `gui/core/template_manager.py` | `TemplateManager` | JSON 模板增删改查 + 校验 | `core/template_manager.py` | 路径常量从 `util.constants` 改引 `core.paths` |
| `gui/core/coordinate_converter.py` | `CoordinateConverter` | DPI awareness 三态处理 | `core/coordinate_converter.py` | `ctypes` 调 `shcore/user32` 是 Windows 专属，平台层条件导入 |
| `gui/core/window_controller.py` | `GameWindowController` | 微信窗口枚举/激活/缩放/截图 | `platform/window_controller.py` | `win32gui`/`pyautogui`/`psutil` 全部 Windows 专属 |
| `gui/core/report_generator.py` | `ReportGenerator` | HTML + JSON 报告 | `core/report_generator.py` | 模板字符串很长但无外部依赖 |
| `gui/core/process_main.py` | CLI 入口 | 命令行执行入口 | `core/process_main.py` | 改为通过 `[project.scripts]` 注册 |
| `util/opencv_util.py` | `CvTool` | 中文路径 `imwrite/imread`（关键工具） | `utils/opencv.py` | 已 staticmethod 化，迁移零成本 |
| `util/ocr.py` + `dgocr/` | `DGOCR` | 自研 OCR（det + rec + seglink） | `ocr/engine.py` + `ocr/dgocr/` | 模型走 Git LFS；`dgocr.py` 删除 `sys.path.append(".")` |
| `util/constants.py` | 路径常量 + `ele_coords` 字典 | 路径常量散落、`ele_coords` 是 Phase 1 遗留 | 拆分：路径→`core/paths.py`，`ele_coords`→`utils/constants.py` | 拆分时注意 device.py 依赖 |
| `util/device.py` / `util/window.py` | 低层窗口/点击 | Phase 1 遗留，main_gui 之外无人引用 | `utils/device.py` / `utils/window.py` | 保留为 legacy 一个版本 |
| `gui/main_gui.py`（2219 行） | `MainGUI` + `FlowLayout` | PyQt6 GUI 主入口 | `ui/main_window.py` | 体量大，迁移到 `ui/`；FlowLayout 抽出 `ui/widgets/flow_layout.py` |
| `gui/template_creator_gui.py`（1401 行） | 模板创建器 | UI 体量大 | `ui/template_creator.py` | 同上 |
| `gui/dialog/*.py`（7 个对话框） | 各功能对话框 | UI 子模块 | `ui/dialogs/`（去掉 `_dialog` 后缀） | 同上 |

### 2.2 已确认的工程债清单

| 工程债 | 当前症状 | 解决方案 |
|---|---|---|
| 双构建配置 | `pyproject.toml` 与 `setup.py` 冲突 | 统一为 `pyproject.toml`，删除 `setup.py` |
| sys.path hack | `start_main_gui.py` 用 `sys.path.insert(0, gui_dir)` | 改为正规包 + `[project.scripts]` 控制台入口 |
| 分层倒挂 | `gui/core/` 寄生 GUI 下的业务核心 | 业务核心上提到顶层包 `core/` |
| util 单数命名 | 违反 PEP8 习惯 | 重命名 `utils/`（复数） |
| 测试无序 | `test/` 命名混杂无分类 | 改为 `tests/{unit,integration,e2e,manual}/` + pytest 收集规则 |
| 无标准化 logging | 全局 print 输出 | 引入 `config/logging.py` 统一 logger 工厂 |
| 路径常量散落 + cwd 依赖 | `REFERENCE_IMAGES_PATH='data/reference_images'` 相对路径 | 改为 `core/paths.py`，基于项目根的绝对路径 |
| 无类型检查/lint | 无 ruff/mypy | 加入工具链配置 |
| 无 CI | 无 `.github/workflows` | 方向 1 验证阶段引入（可选） |

---

## 3. 目标目录结构（src layout + 分层包）

```
wechat-link-autogame-xcx/
├── pyproject.toml                          # 唯一构建配置，删除 setup.py
├── uv.lock                                 # UV 锁定文件
├── README.md
├── LICENSE
├── CLAUDE.md
├── .python-version                         # 3.13
├── .gitignore
│
├── src/                                    # ★ 引入 src layout
│   └── autogame_xcx/                       # 顶级包（PEP 8 模块名：小写下划线）
│       ├── __init__.py                     # 暴露 __version__
│       ├── _cli.py                         # ★ 新增：控制台入口点
│       │
│       ├── core/                           # 业务核心层（迁自 gui/core/）
│       │   ├── __init__.py
│       │   ├── executor.py                 # ← game_executor.py
│       │   ├── matcher.py                  # ← image_matcher.py（ImageMatcher）
│       │   ├── template_manager.py         # ← template_manager.py
│       │   ├── coordinate_converter.py     # ← coordinate_converter.py
│       │   ├── report_generator.py         # ← report_generator.py
│       │   ├── process_main.py             # ← process_main.py（CLI 入口）
│       │   └── paths.py                    # ★ 新增：基于项目根的路径常量
│       │
│       ├── platform/                       # ★ 新增：平台抽象层（Windows API 隔离）
│       │   ├── __init__.py
│       │   ├── window_controller.py        # ← gui/core/window_controller.py
│       │   ├── win32_api.py                # ★ 抽出自 window_controller 的 win32gui/win32process
│       │   └── _windows.py                 # 平台探测与条件导入
│       │
│       ├── ocr/                            # ★ 新增：OCR 子包（封装 dgocr）
│       │   ├── __init__.py
│       │   ├── engine.py                   # ← util/ocr.py，封装为 OCREngine 类
│       │   └── dgocr/                      # ← 迁自 dgocr/（保持原结构作为内部实现）
│       │       ├── __init__.py
│       │       ├── det.py / det_seglink.py
│       │       ├── rec.py
│       │       ├── dgocr.py
│       │       ├── utils.py / utils_seglink.py
│       │       ├── visual.py
│       │       └── AlibabaPuHuiTi-3-45-Light.ttf
│       │
│       ├── ui/                             # PyQt6 GUI 层（迁自 gui/）
│       │   ├── __init__.py
│       │   ├── main_window.py              # ← main_gui.py 的 MainGUI
│       │   ├── template_creator.py         # ← template_creator_gui.py
│       │   ├── widgets/
│       │   │   └── flow_layout.py          # ← 抽自 main_gui.py 的 FlowLayout
│       │   └── dialogs/                    # ← 迁自 gui/dialog/（去掉 _dialog 后缀）
│       │       ├── area_config.py
│       │       ├── area_test.py
│       │       ├── matching_test.py
│       │       ├── report_viewer.py
│       │       ├── template_execution.py
│       │       └── template_test.py
│       │
│       ├── utils/                          # ← 迁自 util/（重命名为 utils）
│       │   ├── __init__.py
│       │   ├── opencv.py                   # ← opencv_util.py（CvTool）
│       │   ├── device.py                   # ← device.py（保留 legacy）
│       │   ├── window.py                   # ← window.py（保留 legacy）
│       │   └── constants.py                # ← constants.py（仅 ele_coords，路径常量搬到 core/paths.py）
│       │
│       ├── config/                         # ★ 新增：配置中心
│       │   ├── __init__.py
│       │   ├── settings.py                 # Pydantic Settings，加载 .env / config.yaml
│       │   └── logging.py                  # 日志配置（dictConfig 模板）
│       │
│       └── exceptions.py                   # ★ 新增：统一异常体系
│           # AutogameError / ExecutorError / TemplateError / MatchError
│           # WindowNotFoundError / OCRError / PlatformNotSupportedError
│
├── tests/                                  # ★ 重构 test/，按粒度分目录
│   ├── conftest.py                         # 共享 fixture（fake window / sample template）
│   ├── unit/
│   │   ├── test_matcher.py
│   │   ├── test_template_manager.py
│   │   ├── test_coordinate_converter.py
│   │   └── test_report_generator.py
│   ├── integration/
│   │   ├── test_executor.py                # 真实窗口或 mock window_controller
│   │   └── test_ocr_engine.py
│   ├── e2e/
│   │   └── test_full_template_run.py
│   └── manual/                             # demo_/verify_/basic_ 类手动脚本（pytest 默认不收集）
│
├── scripts/                                # ★ 新增：辅助启动脚本
│   ├── run_main_gui.py                     # ← 迁自 start_main_gui.py（去 sys.path hack）
│   └── run_template_creator.py             # ← 迁自 start_gui.py
│
├── data/                                   # 运行时数据（保留相对位置）
│   ├── reference_images/
│   ├── debug_images/
│   ├── test_images/
│   ├── demo_images/
│   ├── reports/
│   ├── templates/
│   ├── captures/                           # ★ 方向 3 预留（抓包数据）
│   └── logs/                               # ★ 新增：日志输出目录
│
├── models/                                 # OCR 模型（Git LFS）
│   └── duguang-ocr-onnx-v2/
│
├── doc/
│   ├── PRD_游戏自动化系统.md
│   ├── design.md
│   ├── requirements.md
│   └── plans/                              # ★ 本文件所在目录
│       ├── PLAN_01_代码结构规范化.md
│       ├── PLAN_02_ilink远程驱动.md
│       └── PLAN_03_协议化接入.md
│
└── .github/workflows/ci.yml                # ★ 可选：CI（方向 1 验证阶段引入）
```

### 3.1 目录职责边界（强约束）

| 目录 | 职责边界 | 禁止事项 |
|---|---|---|
| `core/` | 业务逻辑（执行器、匹配器、模板管理、坐标、报告、路径） | 禁止 `import PyQt6` / `import win32gui` |
| `platform/` | 平台 API 隔离（窗口控制、Win32 API 封装） | 禁止定义业务流程；非 Windows 平台抛 `PlatformNotSupportedError` |
| `ocr/` | OCR 引擎封装 + dgocr 内部实现 | 不允许直接被 UI 调用，必须经 `core` |
| `ui/` | PyQt6 界面、对话框、widgets | 禁止直接调 `pyautogui` / `win32gui`，必须经 `core/executor` |
| `utils/` | 通用工具（OpenCV 工具、legacy device/window） | 禁止业务知识 |
| `config/` | 配置加载、日志配置 | 禁止业务逻辑 |
| `tests/` | 测试代码，按粒度分目录 | 禁止写业务实现 |
| `scripts/` | 启动脚本 | 仅做启动，不写业务逻辑 |
| `data/` | 运行时产物（截图、报告、模板、日志） | 禁止放代码 |
| `models/` | 模型文件（Git LFS） | 禁止放代码 |
| `doc/` | 文档 | 禁止放代码 |

### 3.2 依赖方向（强约束）

```
ui  →  core  →  utils
       ↓
     platform  →  utils
       ↓
       ocr  →  utils
       
config ← 被 core/ui/utils 引用（不被引）
```

**禁止反向依赖**：`core` 不允许 `import ui`；`utils` 不允许 `import core`。

---

## 4. 关键模块设计

### 4.1 `core/paths.py`（替代 `util/constants.py` 的路径部分）

```python
"""集中管理所有路径常量，基于项目根计算，消除 cwd 依赖。"""
from pathlib import Path

# src/autogame_xcx/core/paths.py → 项目根（向上 3 级）
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
REFERENCE_IMAGES_PATH = DATA_DIR / "reference_images"
DEBUG_IMAGES_PATH = DATA_DIR / "debug_images"
TEST_IMAGES_PATH = DATA_DIR / "test_images"
DEMO_IMAGES_PATH = DATA_DIR / "demo_images"
REPORTS_PATH = DATA_DIR / "reports"
TEMPLATES_PATH = DATA_DIR / "templates"
LOGS_PATH = DATA_DIR / "logs"
MODELS_DIR = PROJECT_ROOT / "models"

def ensure_runtime_dirs() -> None:
    """启动时调用，确保所有 data 子目录存在。"""
    for d in (REFERENCE_IMAGES_PATH, DEBUG_IMAGES_PATH, REPORTS_PATH,
              TEMPLATES_PATH, LOGS_PATH):
        d.mkdir(parents=True, exist_ok=True)
```

### 4.2 `exceptions.py`（统一异常体系）

```python
"""所有业务异常继承自 AutogameError，便于上层分级处理 + GUI 错误弹窗。"""


class AutogameError(Exception):
    """所有项目异常的基类。"""


class WindowNotFoundError(AutogameError):
    """微信/目标窗口未找到。"""


class TemplateError(AutogameError):
    """模板加载/校验/保存失败。"""


class MatchError(AutogameError):
    """图像匹配执行失败（非"未匹配"，而是算法异常）。"""


class OCRError(AutogameError):
    """OCR 引擎加载或推理失败。"""


class ExecutorError(AutogameError):
    """GameExecutor 执行流程错误。"""


class PlatformNotSupportedError(AutogameError):
    """当前平台不支持该操作（如非 Windows 调用 win32gui）。"""
```

### 4.3 `config/logging.py`（统一日志）

```python
"""用 logging.config.dictConfig 配置 root logger；模块用 logging.getLogger(__name__)。"""
import logging.config
from pathlib import Path
from autogame_xcx.core.paths import LOGS_PATH

LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "filename": str(LOGS_PATH / "autogame.log"),
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
}

def setup_logging() -> None:
    LOGS_PATH.mkdir(parents=True, exist_ok=True)
    logging.config.dictConfig(LOG_CONFIG)
```

### 4.4 `_cli.py`（控制台入口点）

```python
"""取代散落的 if __name__ == '__main__'，统一启动入口。"""
import sys
from autogame_xcx.config.logging import setup_logging
from autogame_xcx.core.paths import ensure_runtime_dirs


def launch_main_gui() -> int:
    """启动主 GUI。"""
    setup_logging()
    ensure_runtime_dirs()
    from PyQt6.QtWidgets import QApplication
    from autogame_xcx.ui.main_window import MainGUI
    app = QApplication(sys.argv)
    window = MainGUI()
    window.show()
    return app.exec()


def launch_template_creator() -> int:
    """启动模板创建器。"""
    setup_logging()
    ensure_runtime_dirs()
    from PyQt6.QtWidgets import QApplication
    from autogame_xcx.ui.template_creator import TemplateCreator
    app = QApplication(sys.argv)
    window = TemplateCreator()
    window.show()
    return app.exec()
```

### 4.5 `core/executor.py`（保留 `GameExecutor` 类签名，仅改 import）

迁移规则（**surgical**，参考 CLAUDE.md 第 3 条）：
1. import 路径：`from gui.core.X` → `from autogame_xcx.core.X`
2. `from util.constants import REPORTS_PATH` → `from autogame_xcx.core.paths import REPORTS_PATH`
3. `print(...)` → `logger.info/debug/error(...)`
4. **不修改** execute_template/execute_task/execute_step 的算法逻辑

### 4.6 `pyproject.toml`（重写）

```toml
[project]
name = "autogame-xcx"
version = "0.1.0"
description = "WeChat mini-program game automation via image recognition"
readme = "README.md"
requires-python = ">=3.13"
license = "MIT"
authors = [{ name = "yanhuanxy" }]
dependencies = [
    "PyQt6==6.6.1",
    "opencv-python==4.10.0.84",
    "numpy>=2.0,<3.0",
    "Pillow>=11.0",
    "scikit-image>=0.21",
    "pyautogui>=0.9.54",
    "pywin32>=310; platform_system=='Windows'",
    "psutil>=6.0",
    "onnxruntime>=1.17",
    "pydantic>=2.5",
    "pydantic-settings>=2.1",
]

[project.scripts]
autogame-gui = "autogame_xcx._cli:launch_main_gui"
autogame-creator = "autogame_xcx._cli:launch_template_creator"
autogame-run = "autogame_xcx.core.process_main:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/autogame_xcx"]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-qt>=4.4",
    "pytest-cov>=5.0",
    "ruff>=0.6",
    "mypy>=1.10",
]

[[tool.uv.index]]
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
default = true

[tool.ruff]
line-length = 100
target-version = "py313"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.13"
strict = false
ignore_missing_imports = true  # cv2/win32gui 等无 stub

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-ra --strict-markers"
markers = [
    "integration: requires real WeChat window",
    "e2e: full template execution",
    "gui: requires PyQt6 display",
]
```

---

## 5. 迁移路径（分 5 阶段）

> 原则：CLAUDE.md 第 3 条 surgical changes。每阶段只移动文件 + 改 import，**不动算法逻辑、不动 GUI 行为**。

### 阶段 1.1：构建配置统一化（半天）

**动作**：
1. 删除 `setup.py`
2. 重写 `pyproject.toml`（按 4.6 节模板）
3. `uv sync` 重新生成 `uv.lock`
4. 安装 dev 依赖：`uv sync --all-extras`

**验证**：
- `uv run python -c "import sys; print(sys.path)"` 输出包含 `src/`
- `uv pip list` 中应能看到所有 dev 依赖（pytest/ruff/mypy）
- `uv run ruff check .` 不报致命错误

### 阶段 1.2：包结构搬迁（1 天）

**动作**：
1. 在 `src/autogame_xcx/` 下创建子包目录，每个目录加空 `__init__.py`
2. 用 `git mv`（不是 cp）逐个迁移文件（保留 git 历史）：
   - `gui/core/*.py → src/autogame_xcx/core/`（保留原文件名）
   - `gui/dialog/*.py → src/autogame_xcx/ui/dialogs/`（去掉 `_dialog` 后缀）
   - `gui/main_gui.py → src/autogame_xcx/ui/main_window.py`
   - `gui/template_creator_gui.py → src/autogame_xcx/ui/template_creator.py`
   - `util/*.py → src/autogame_xcx/utils/`（`opencv_util.py → opencv.py`）
   - `dgocr/ → src/autogame_xcx/ocr/dgocr/`
3. 批量改 import 路径：
   - `from gui.core.X import Y` → `from autogame_xcx.core.X import Y`
   - `from util.X import Y` → `from autogame_xcx.utils.X import Y`（注意 `opencv_util→opencv`）
   - `from util.constants import REPORTS_PATH` → `from autogame_xcx.core.paths import REPORTS_PATH`
   - `import dgocr.dgocr` → `from autogame_xcx.ocr.dgocr.dgocr import DGOCR`
4. 新建 `core/paths.py` / `exceptions.py` / `config/logging.py` / `config/settings.py` / `_cli.py`
5. 拆 `util/constants.py`：路径常量搬到 `core/paths.py`，`ele_coords` 留 `utils/constants.py`

**验证**：
- `uv run python -c "from autogame_xcx.core.executor import GameExecutor; print(GameExecutor)"` 输出类对象
- `uv run python -c "from autogame_xcx.ocr.dgocr.dgocr import DGOCR; print(DGOCR)"` 同上
- `uv run python -c "from autogame_xcx.ui.main_window import MainGUI; print(MainGUI)"` 同上

### 阶段 1.3：删除 `sys.path.insert` hack（半天）

**动作**：
1. 在 `src/autogame_xcx/_cli.py` 实现 `launch_main_gui()` / `launch_template_creator()`
2. 把 `start_main_gui.py` / `start_gui.py` 重写为 4 行：`from autogame_xcx._cli import launch_main_gui; sys.exit(launch_main_gui())`（或直接删除，使用控制台命令）
3. 用 `[project.scripts]` 注册 console entry

**验证**：
- `uv run autogame-gui` 启动主窗口（与原 `python start_main_gui.py` 行为一致）
- `grep -r "sys.path.insert" src/ scripts/` 输出为空
- `data/logs/autogame.log` 出现并写入启动日志

### 阶段 1.4：测试目录重构（半天）

**动作**：
1. `test/ → tests/`，按命名前缀分发到四个子目录：
   - `test_*` → `tests/unit/` 或 `tests/integration/`（按是否需要真实窗口判断）
   - `demo_*` / `verify_*` / `basic_*` → `tests/manual/`（手动验证脚本，pytest 默认不收集）
2. 删除每个文件顶部的 `sys.path.insert`，改用 `[tool.pytest.ini_options] pythonpath=["src"]`
3. 编写 `tests/conftest.py`：共享 fixture（mock 窗口、样例模板）

**验证**：
- `uv run pytest tests/unit --collect-only` 显示分类清晰
- `uv run pytest tests/unit -v` 至少能收集所有 unit 测试（即使有些需要 Qt 环境会 skip）
- 不修改测试内容，只调整位置和 import

### 阶段 1.5：日志/异常/路径渐进替换（持续，不阻塞前 4 阶段）

**动作**：每次 surgical 修改某模块时，把该模块内的：
- `print(...)` 替换为 `logger.info/debug/error(...)`
- `return False` 升级为 `raise XxxError + 兼容层`

**验证**：
- `ruff check src/ --statistics` 的 print 使用数量随时间下降
- 业务行为不变（旧测试仍通过）

---

## 6. 关键风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| `dgocr.py` 内部 `sys.path.append(".")` 干扰导入 | OCR 引擎加载失败 | 删除该 hack；dgocr 已用相对导入（`.rec` / `.det`），安全 |
| `util/constants.py` 中 `ele_coords` 被 `util/device.py` 引用，device.py 又被 legacy 引用 | 循环依赖 | 拆 `constants.py`：`ele_coords` 留 `utils/constants.py`；路径常量搬到 `core/paths.py` |
| PyQt6 类无法在 headless CI 跑 | CI 红 | pytest-qt + `QT_QPA_PLATFORM=offscreen` 环境变量；标记 GUI 测试为 `@pytest.mark.gui` |
| `win32gui` 在 Linux 上 import 失败 | 跨平台打包失败 | `platform/_windows.py` 做条件导入；非 Windows 平台抛 `PlatformNotSupportedError` |
| 模型走 Git LFS，新克隆未 pull LFS 时 OCR 加载失败 | CI/新成员环境异常 | `models/.gitattributes` 已存在；CI 加 `git lfs pull`；启动时若 onnx 不存在则禁用 OCR 而非崩溃 |
| 大量 `print` 替换为 logger 时漏掉关键流程 | 日志变少 | 阶段 1.5 用 grep 监控 `print` 数量，不要求一次到位 |
| `main_gui.py` 2219 行直接迁移可能引入隐性 bug | GUI 行为变化 | 阶段 1.2 仅做 `git mv` + import 改写，**不重构 FlowLayout 抽离**（留作独立 PR） |
| `dgocr/dgocr.py` 引用字体文件用相对路径 | 迁移后字体找不到 | 改用 `importlib.resources` 或基于 `__file__` 计算路径 |

---

## 7. 依赖工具链

| 工具 | 版本 | 用途 | 加入位置 |
|---|---|---|---|
| hatchling | latest | PEP 621 构建后端 | `pyproject.toml [build-system]` |
| ruff | >=0.6 | Lint + format（取代 black + isort + flake8） | `[tool.ruff]` |
| mypy | >=1.10 | 渐进式类型检查 | `[tool.mypy]` |
| pytest | >=8.0 | 测试框架 | `[tool.pytest.ini_options]` |
| pytest-qt | >=4.4 | PyQt 测试 | dev-deps |
| pytest-cov | >=5.0 | 覆盖率 | dev-deps |
| pydantic | >=2.5 | 数据模型 | deps |
| pydantic-settings | >=2.1 | 配置中心（`.env` / yaml 加载） | deps |
| pre-commit（可选） | latest | 提交前跑 ruff/mypy | `.pre-commit-config.yaml` |

---

## 8. 验证方式

### 8.1 阶段性验证

| 阶段 | 命令 | 预期 |
|---|---|---|
| 1.1 | `uv sync && uv run ruff --version && uv run pytest --version` | 工具链可用 |
| 1.2 | `uv run python -c "from autogame_xcx.core.executor import GameExecutor; from autogame_xcx.ui.main_window import MainGUI; from autogame_xcx.ocr.dgocr.dgocr import DGOCR; print('all imports ok')"` | 三类核心导入成功 |
| 1.3 | `uv run autogame-gui` | 主窗口弹出；`grep -rn "sys.path.insert" src/ scripts/` 输出空 |
| 1.4 | `uv run pytest tests/unit --collect-only \| head -30` | 分类清晰，无 sys.path.insert 残留 |
| 1.5 | `uv run pytest tests/ -v` | 全部通过或 skip（无 fail） |

### 8.2 整体回归

完成阶段 1.5 后，运行原有 `gui/core/process_main.py --test all` 等价命令 `uv run autogame-run --test all`，输出与原版一致。

### 8.3 跨平台验证（可选）

- Windows 11：`uv run autogame-gui` 启动正常
- Linux WSL：`QT_QPA_PLATFORM=offscreen uv run pytest tests/unit` 通过（验证 win32gui 条件导入）

---

## 9. 与方向 2/3 的关系

方向 1 完成后，方向 2/3 可以基于稳定的包结构增量引入：

- **方向 2（ilink 远程驱动）**：新增 `src/autogame_xcx/remote/` 包（ilink 集成 + 指令系统 + 调度器 + LLM 编排），通过 `core/executor` 触发模板执行。
- **方向 3（协议化接入）**：新增 `src/autogame_xcx/protocol/` + `js_inject/` + `reverse/` + `anti_detect/`，通过 `core/execution_strategy.py` 抽象与现有 `ImageBasedStrategy` 并存。

**禁止**方向 2/3 在方向 1 完成前启动，否则会反复触发 import 重构。
