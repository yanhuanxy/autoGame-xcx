# 项目设计文档: autoGame-LZ

## 1. 概述

本文档基于《项目需求文档》，旨在为 `autoGame-LZ` 项目提供技术实现层面的设计方案。项目将采用模块化、分层化的结构，以提高代码的可读性、可维护性和可扩展性。

## 2. 系统架构

项目将遵循以下分层和模块化的文件结构：

```
autoGame-LZ/
│
├── core/                  # 核心功能模块
│   ├── __init__.py
│   ├── window.py          # 窗口管理 (查找、激活)
│   ├── ocr.py             # 文字识别 (OCR)
│   ├── device.py          # 设备控制 (鼠标点击、键盘输入)
│   └── constants.py       # 存储静态数据 (如坐标)
│
├── modules/               # 业务逻辑模块
│   ├── __init__.py
│   ├── trial.py           # 试炼模块
│   ├── boss.py            # BOSS模块
│   ├── experience.py      # 历练模块
│   ├── spacetime.py       # 时空模块
│   └── daily.py           # 日常模块 (待实现)
│
├── doc/                   # 文档目录
│   ├── requirements.md
│   └── design.md
│
├── venv/                  # Python虚拟环境
├── main.py                # 主程序入口
├── requirements.txt       # 依赖列表
└── README.md              # 项目说明
```

## 3. 核心模块设计 (`core/`)

### 3.1. 窗口管理 (`core/window.py`)

-   **`find_target_window(name)`**: 接收一个 `name` 参数，遍历系统窗口，返回标题或进程名与 `name` 匹配的窗口句柄 (`hwnd`)。
-   **`activate_window(hwnd)`**: 接收一个 `hwnd` 参数，将对应窗口置于前台并激活。

### 3.2. 文字识别 (`core/ocr.py`)

-   **`find_text_in_window(text, hwnd)`**:
    -   **输入**: 目标文字 `text`，窗口句柄 `hwnd`。
    -   **处理**:
        1.  根据 `hwnd` 获取窗口的精确位置和大小 (`left, top, width, height`)。
        2.  使用 `pyautogui.screenshot(region=...)` 对该窗口区域进行截图。
        3.  将截图对象传递给 `pytesseract.image_to_data(..., output_type=Output.DICT)`，获取详细的OCR结果，包含每个识别出的文字及其坐标。
        4.  在结果中搜索与 `text` 参数匹配的字符串。
    -   **输出**: 如果找到，返回该文字在窗口内的中心点坐标 `(x, y)`；如果未找到，返回 `None`。
    -   **备注**: 此功能主要用于各模块内部的二级界面操作，主界面的导航将使用基于静态坐标的路由功能。

### 3.3. 设备控制 (`core/device.py`)

-   **`click(x, y)`**: 接收屏幕绝对坐标 `(x, y)`，使用 `pyautogui.click()` 执行鼠标左键单击。
-   **`click_in_window(x, y, hwnd)`**: 接收窗口内相对坐标 `(x, y)` 和窗口句柄 `hwnd`，将其转换为屏幕绝对坐标后，再调用 `click()` 执行点击。
-   **`click_element_by_name(name, hwnd)`**: 
    -   **输入**: 目标元素的名称 `name` (如 "试炼")，窗口句柄 `hwnd`。
    -   **处理**:
        1.  从 `core.constants` 导入 `ele_coords` 坐标数据。
        2.  遍历 `ele_coords` 中的所有分组，查找键为 `name` 的元素。
        3.  如果找到，从其坐标列表（多边形）计算中心点 `(x, y)`。
        4.  调用 `click_in_window(x, y, hwnd)` 执行点击。
    -   **输出**: 成功点击返回 `True`，未找到元素返回 `False`。

### 3.4. 静态数据 (`core/constants.py`)

-   该文件包含项目所需的静态数据。
-   **`ele_coords`**: 一个字典，存储了在《需求文档》附录中定义的UI元素坐标。

## 4. 业务模块设计 (`modules/`)

-   每个模块（如 `trial.py`）都将包含一个 `run(hwnd)` 函数作为该模块任务的入口。
-   `run` 函数将优先使用 `core.device.click_element_by_name` 进行导航。
-   **示例: `modules/trial.py`**
    ```python
    from core import device, ocr

    def run(hwnd):
        print("开始执行[试炼]模块...")
        # 1. 点击"试炼"按钮
        if device.click_element_by_name("试炼", hwnd):
            # (可能需要短暂延时等待界面切换)
            # 2. 查找"鬼影迷境"
            dungeon_coords = ocr.find_text_in_window("鬼影迷境", hwnd)
            if dungeon_coords:
                print("  成功找到[鬼影迷境]")
                # ... 后续点击操作 ...
                return True
        print("  [试炼]模块执行失败")
        return False
    ```

## 5. 主程序流程 (`main.py`)

1.  **初始化**:
    -   定义目标应用程序名称 `TARGET_APP_NAME = "聊斋搜神记"`。
2.  **窗口获取**:
    -   调用 `core.window.find_target_window(TARGET_APP_NAME)` 获取窗口句柄。
    -   如果失败，打印错误信息并退出。
    -   调用 `core.window.activate_window(hwnd)` 激活窗口。
3.  **任务调度**:
    -   按顺序调用 `modules.trial.run(hwnd)`、`modules.boss.run(hwnd)` 等，执行各个模块的任务。
    -   未来可扩展为根据用户输入或配置文件来选择执行哪些模块。 