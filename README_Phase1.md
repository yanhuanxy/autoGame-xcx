# 游戏自动化系统 - Phase 1 核心验证版本

## 项目概述

这是基于OCR和图像识别的小程序游戏自动化系统的第一个版本，主要用于核心技术验证。

### 核心特性

- ✅ **窗口检测与控制**：自动检测微信窗口，支持窗口激活和截图
- ✅ **图像匹配引擎**：支持多种图像相似度算法（模板匹配、SSIM、特征匹配、混合匹配）
- ✅ **坐标转换系统**：支持不同分辨率下的坐标自动转换
- ✅ **模板管理系统**：JSON格式的模板创建、保存、加载和验证
- ✅ **基础执行引擎**：基于图像比对的自动化任务执行

## 技术架构

```
src/
├── window_controller.py    # 窗口检测和控制
├── image_matcher.py        # 图像匹配算法
├── coordinate_converter.py # 坐标转换
├── template_manager.py     # 模板管理
├── game_executor.py        # 执行引擎
└── main.py                # 主程序和测试工具
```

## 环境要求

- **Python**: 3.13
- **操作系统**: Windows 10/11
- **微信客户端**: 最新版本

## 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd autoGame-xcx
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **验证安装**
```bash
cd src
python process_main.py --test all
```

## 使用方法

### 1. 系统测试

```bash
cd src

# 运行完整测试
python process_main.py --test all

# 单独测试各个模块
python process_main.py --test window      # 窗口检测测试
python process_main.py --test image       # 图像匹配测试
python process_main.py --test coordinate  # 坐标转换测试
python process_main.py --test template    # 模板管理测试
```

### 2. 模板管理

```bash
# 列出所有可用模板
python process_main.py --list-templates

# 执行指定模板
python process_main.py --execute templates/your_template.json
```

### 3. 单独测试各模块

```bash
# 测试窗口控制
python window_controller.py

# 测试图像匹配
python image_matcher.py

# 测试坐标转换
python coordinate_converter.py

# 测试模板管理
python template_manager.py
```

## 核心功能说明

### 1. 窗口检测与控制 (window_controller.py)

- **功能**：检测微信窗口、激活窗口、获取窗口信息、截图
- **核心方法**：
  - `find_wechat_window()`: 查找微信窗口
  - `activate_window()`: 激活窗口
  - `capture_window_screenshot()`: 截取窗口截图
  - `resize_window()`: 调整窗口大小

### 2. 图像匹配引擎 (image_matcher.py)

- **功能**：多种图像相似度算法，用于模板匹配
- **支持算法**：
  - `template_matching`: 模板匹配（快速，适合精确匹配）
  - `ssim`: 结构相似性（适合光照变化）
  - `feature_matching`: 特征点匹配（适合形状识别）
  - `hybrid`: 混合匹配（推荐使用）

### 3. 坐标转换系统 (coordinate_converter.py)

- **功能**：处理不同分辨率下的坐标转换
- **核心方法**：
  - `convert_coordinates()`: 转换区域坐标
  - `convert_click_point()`: 转换点击坐标
  - `is_resolution_match()`: 检查分辨率匹配

### 4. 模板管理系统 (template_manager.py)

- **功能**：JSON模板的创建、保存、加载和验证
- **模板结构**：
  ```json
  {
    "template_info": {
      "name": "模板名称",
      "version": "v1.0_20241217_143022",
      "template_resolution": {"width": 1920, "height": 1080}
    },
    "tasks": [...],
    "global_settings": {...}
  }
  ```

### 5. 执行引擎 (game_executor.py)

- **功能**：基于图像比对的自动化任务执行
- **执行流程**：
  1. 加载模板 → 2. 初始化环境 → 3. 坐标转换 → 4. 区域截图 → 5. 图像比对 → 6. 执行操作

## 测试结果示例

运行 `python main.py --test all` 后的预期输出：

```
==================================================
测试窗口检测功能
==================================================
1. 查找微信窗口...
✓ 找到微信窗口: 微信
  进程名: WeChat.exe

2. 激活窗口...
✓ 窗口激活成功

3. 获取窗口信息...
✓ 窗口位置: x=100, y=100
  窗口大小: 1200x800
✓ 当前分辨率: 1200x800
✓ 系统DPI: 96x96

4. 截取窗口截图...
✓ 截图成功，尺寸: (800, 1200, 3)
✓ 截图已保存: test_screenshot_20241217_143022.png

窗口检测测试: 通过
```

## 已知限制

### Phase 1 版本限制：
- ❌ 没有可视化模板创建工具（需要手动创建JSON）
- ❌ 没有GUI界面（仅命令行）
- ❌ 游戏区域定位较简单（需要手动调整）
- ❌ 错误处理不够完善
- ❌ 性能未优化

### 技术限制：
- 仅支持Windows系统
- 需要微信客户端运行
- 图像识别受光照和界面变化影响
- 坐标转换在极端分辨率差异下可能不准确

## 下一步计划 (Phase 2)

1. **PyQt6可视化模板创建工具**
2. **完善的执行报告系统**
3. **更智能的游戏区域定位**
4. **错误处理和重试机制优化**
5. **性能优化和稳定性提升**

## 故障排除

### 常见问题：

1. **找不到微信窗口**
   - 确保微信客户端已启动
   - 检查微信窗口标题是否包含"微信"

2. **图像匹配失败**
   - 检查参考图像是否存在
   - 调整匹配阈值（降低threshold值）
   - 尝试不同的匹配算法

3. **坐标转换不准确**
   - 确保模板分辨率信息正确
   - 检查系统DPI设置
   - 尝试强制调整窗口大小

4. **截图失败**
   - 确保窗口没有被遮挡
   - 检查窗口是否最小化
   - 尝试重新激活窗口

## 开发者信息

- **产品设计师**: Anna
- **Python开发工程师**: Noma
- **版本**: Phase 1 - 核心验证版本
- **创建时间**: 2024-12-17

## 联系方式

如有问题或建议，请及时反馈以便改进系统。
