# README_Phase1 / Phase2 完成度验证 与 改进方案

> **状态：已归档（仅作历史追溯，勿当现状）。** 生成于 2026-06-23 的快照：本文所列断点 bug A1–A5（process_main 导入、report_generator TypeError、game_executor 调试写入、ocr/engine 半成品）均已于 Phase F / "添加大模型识别" 修复；A1 的 `remote_llm.json` 已删除、`remote/` 模块已整体迁出至 wechat-ilink-bot。第 3/7 节描述的 `remote/` 能力在本仓库已不存在。当前契约真相源见 [AGENTS.md](../../AGENTS.md)。
>
> 生成日期：2026-06-23
> 范围：对照 `README_Phase1.md`、`README_Phase2.md` 核验项目实际状态，并提出改进方案
> 结论速览：Phase 1 ~90%、Phase 2 ~85%，项目实际能力已远超两份 README 承诺（已完成 PLAN_01 重构 + PLAN_02 ilink 远程驱动 + LLM 编排），但文档严重过时且代码有多处断点 bug 与安全隐患。

---

## 1. Phase 1 核验：计划 vs 实际（完成度 ~90%）

| 计划项 | 计划承诺 | 实际情况 | 评级 |
|---|---|---|---|
| `find_wechat_window` | 自动检测微信窗口 | `platform/window_controller.py:28` 硬编码匹配 `"聊斋搜神记"`，不是通用微信 | ⚠️ 偏离承诺 |
| `activate_window` | 激活窗口 | `window_controller.py:52` 正常实现 | ✅ |
| `capture_window_screenshot` | 窗口截图 | `window_controller.py:129` 正常实现 | ✅ |
| `resize_window` | 调整窗口大小 | `window_controller.py:98` 正常实现 | ✅ |
| 图像匹配 4 算法 | template_matching/ssim/feature_matching/hybrid | `core/image_matcher.py:15` 实际有 **5 种**（多一个 histogram），超额完成 | ✅ 超额 |
| `convert_coordinates` | 区域坐标转换 | `core/coordinate_converter.py:149` 实现，且包含完整 DPI 三态处理（unaware / system_aware / per_monitor_aware），远超 Phase 1 文档 | ✅ 超额 |
| `convert_click_point` | 点击坐标转换 | `coordinate_converter.py:179` 正常 | ✅ |
| `is_resolution_match` | 分辨率匹配 | `coordinate_converter.py:205` 正常 | ✅ |
| 模板增删改查 + 校验 | JSON CRUD | `core/template_manager.py` 完整实现 `create / add_task / add_step / save / load / validate / list` | ✅ |
| 执行引擎 | 加载→转换→截图→比对→操作 | `core/game_executor.py:134` 正常，但 `game_executor.py:280-281` 残留调试代码 `CvTool.imwrite('./data/test.png', reference_image)` / `'./data/test1.png', current_image_cv`，每步执行都覆盖 | ⚠️ 调试遗留 |
| `process_main.py --test` | 支持 `window / image / coordinate / template / all` | `core/process_main.py:277` 参数齐全 | ✅ |
| `--list-templates` / `--execute` | CLI 命令 | `process_main.py:279-280` 实现 | ✅ |
| `process_main.py --gui` | 启动 GUI | `process_main.py:310` `from template_creator_gui import main as gui_main` —— 模块早已重命名为 `autogame_xcx.ui.template_creator`，**导入必失败** | ❌ Bug |
| `process_main.py --report` | 生成报告 | `process_main.py:318` `from report_generator import ReportGenerator` —— 路径错误，**导入必失败** | ❌ Bug |
| `process_main.py` 截图 | 保存截图 | `process_main.py:59` 调用 `CvTool.imwrite` 但**未 import**，会抛 `NameError` | ❌ Bug |
| 文档承诺的 `main.py` | `python main.py --test all` | 项目中没有 `main.py`，实际入口是 `process_main.py` | ❌ 文档错误 |

**Phase 1 结论**：核心算法与数据结构 100% 完成且超额（5 算法 + DPI 三态），但 CLI 入口 `process_main.py` 有 3 处断点级 bug，README 承诺的 `main.py` 不存在。

---

## 2. Phase 2 核验：计划 vs 实际（完成度 ~85%）

| 计划项 | 计划承诺 | 实际情况 | 评级 |
|---|---|---|---|
| PyQt6 可视化模板创建 | 拖拽标记、任务管理、保存 | 同时存在两套实现：<br>• `ui/template_creator.py` (1401 行) `TemplateCreatorGUI`（旧版 / 独立窗口）<br>• `ui/main_window.py` (2266 行) `MainGUI`（新版 / 主导，含远程驱动集成） | ⚠️ 重复实现 |
| 区域配置对话框 | `AreaConfigDialog` | `ui/dialogs/area_config_dialog.py:10`（180 行，独立）<br>**同时** `ui/template_creator.py:145` 内部又重复定义了一份 `AreaConfigDialog`（156 行） | ❌ 代码重复 |
| 高级匹配测试 | `MatchingTestDialog` 算法选择 / 连续测试 / 差异分析 | `ui/dialogs/matching_test_dialog.py:14`（436 行，功能完整：算法选择 / 阈值 / 次数 / 连续测试 / diff 图）<br>**同时** `ui/template_creator.py:301` 内部又重复定义了一份 `MatchingTestDialog`（425 行） | ❌ 代码重复 |
| 模板测试对话框 | 完整 / 单任务 / 匹配三模式 + 模拟运行 | `ui/dialogs/template_test_dialog.py:10`（360 行，完整实现 `run_full_test` / `run_single_task_test` / `run_match_test` + `dry_run_check`） | ✅ |
| 区域测试对话框 | 区域测试 | `ui/dialogs/area_test_dialog.py:10`（215 行） | ✅ |
| 模板执行对话框 | 执行模板 | `ui/dialogs/template_execution_dialog.py:9`（78 行，较薄） | ✅ |
| 报告查看器 | 浏览历史报告 | `ui/dialogs/report_viewer_dialog.py:50` 只 `os.listdir(REPORTS_PATH)` 不递归；但 `report_generator.py:29` 把报告写到 `REPORTS_PATH/<template_info>/` 子目录（dict 当 str 用，**TypeError 必崩**），两者契约不一致 | ❌ 双 Bug |
| HTML 报告 | 美观可视化 | `core/report_generator.py:25` 完整实现（CSS+JS+可折叠），但 `report_generator.py:29` 路径拼接 bug | ⚠️ Bug |
| JSON / 文本 报告 | 三种格式 | `report_generator.py:561 / 589` 正常 | ✅ |
| `start_gui.py` 快速启动 | GUI 启动器 | `start_gui.py:9` 启动旧版 `TemplateCreatorGUI`<br>`start_main_gui.py:21` 启动新版 `MainGUI`<br>**两个启动器并存**，且 `start_gui.py` 引用的 `TemplateCreatorGUI` 已是遗留代码 | ⚠️ 冗余 |
| Phase 2 README 承诺的「template_creator_gui.py」 | 模块名 | 实际已重命名为 `ui/template_creator.py`，README 未同步 | ❌ 文档过时 |

**Phase 2 结论**：所有对话框功能都已实现且功能丰富，但 `report_generator.py:29` 有断点级 bug（template_info 是 dict 当 str 用），两套 GUI 实现并存导致代码重复约 1000 行，两个启动器造成入口混乱。

---

## 3. Phase 1/2 之外的新能力（PLAN_01 / 02 / 03 演进）

| 模块 | 路径 | 用途 | 完成度 |
|---|---|---|---|
| DGOCR（自研 OCR） | `src/autogame_xcx/ocr/dgocr/` | ONNX 文字识别（det + rec + seglink） | ✅ 模型完整 |
| OCR Engine | `src/autogame_xcx/ocr/engine.py` | 文字查找接口 | ❌ **半成品**：`do_handle_image(image, type)` 需 2 参但 L64 只传 1 参；L67-71 还按 pytesseract 格式访问 `ocr_data['level'] / ['text'] / ['conf'] / ['left'] / ['width']`，而 DGOCR 返回 `list[dict]`，结构完全不匹配 |
| ilink 客户端 | `remote/ilink/client.py` | JPype1 集成 Java SDK，executeLogin / sendText / sendImage | ✅ 完整 |
| JVM 管理 | `remote/ilink/jvm.py` | JVM 生命周期 | ✅ |
| 登录 / 消息监听 | `remote/ilink/login_listener.py` / `message_listener.py` | SDK listener → Qt 信号桥 | ✅ |
| 指令系统 | `remote/commands/{base,parser,registry,dispatcher}.py` + `definitions/` | `#help / #list / #run / #status / #stop / #report` 6 个指令 | ✅ 42 / 42 单测通过 |
| 任务调度器 | `remote/scheduler/queue.py` | 串行执行避免窗口冲突 | ✅ |
| LLM 编排 | `remote/llm/orchestrator.py` + `anthropic_provider.py` + `openai_provider.py` + `prompt_templates.py` | 自然语言 → 指令队列（JSON 解析 + 白名单校验） | ✅ 29 / 29 单测通过 |
| RemoteDriver | `remote/driver.py` | QObject 集成层（QThread worker + 状态机） | ✅ 19 / 19 单测通过 |
| LLM 配置 | `remote/llm_config.py` + `data/config/remote_llm.json` | provider / api_key / model / base_url 持久化 | ✅ 功能正常 |
| PLAN_03 协议化 | — | HTTP / WS 协议直连 + JS 注入 | ❌ **完全未启动** |

**演进结论**：项目已从 Phase 1/2 的"单机图像自动化"演进为"远程指令驱动 + LLM 编排 + 单机执行"三层架构。PLAN_01 完成 ~95%（src layout 已切换、分层清晰，但 `utils/constants.py` 仍是相对路径，PLAN_01 承诺的 `core/paths.py` 绝对路径未落地）。PLAN_02 完成 100%（6 个阶段全部 ✅）。PLAN_03 完成 0%。

---

## 4. 关键问题清单（按严重性排序）

### 🔴 严重（断点 / 安全）

1. **API key 明文泄露**：`data/config/remote_llm.json` 含 GLM / 智谭真实 key，已提交到 git history。`.gitignore` 未覆盖该文件。
2. **`core/process_main.py` 三处导入 / 名称错误**：
   - L59 `CvTool.imwrite` 未 import → NameError
   - L310 `from template_creator_gui import main as gui_main` → 模块已重命名
   - L318 `from report_generator import ReportGenerator` → 路径错
3. **`core/report_generator.py:29` 类型错误**：`os.path.join(self.reports_dir, template_info, html_filename)` —— `template_info` 是 dict，必抛 TypeError，HTML 报告根本无法生成。
4. **`ocr/engine.py` 半成品**：`do_handle_image` 调用签名不匹配、按 pytesseract 格式访问 DGOCR 结果，一旦调用必崩。

### 🟠 中等（可维护性）

5. **UI 代码重复 ~1000 行**：`template_creator.py` 内嵌的 `AreaConfigDialog`(156 行) / `MatchingTestDialog`(425 行) 与 `ui/dialogs/` 下独立版本并存，维护时易遗漏其中一处。
6. **两套 GUI 主窗口 + 两个启动器**：`TemplateCreatorGUI`(1401 行) vs `MainGUI`(2266 行)，`start_gui.py` vs `start_main_gui.py`。
7. **路径管理不统一**：`utils/constants.py:52-60` 所有路径都是相对路径（`'data/reference_images'`），违反 PLAN_01 承诺的「`core/paths.py` 基于项目根的绝对路径」；工作目录变化时全部失效。
8. **`window_controller.find_wechat_window` 硬编码游戏名**："聊斋搜神记" 写死在代码里，Phase 1 README 承诺的"自动检测微信窗口"未落地，其他游戏复用需要改源码。
9. **调试代码遗留**：`game_executor.py:280-281` 每次执行都把参考图和截图强制写到 `./data/test.png`、`./data/test1.png`。

### 🟡 低（文档 / 规范）

10. **三份 README 全部过时**：
    - `README.md` 还叫 `autoGame-LZ`，引用 `requirements.txt`（已删）、`venv`（已改 uv）、`images/`（不存在）、`process_main.py`（实际入口名对但路径错）
    - `README_Phase1.md` 提到的 `main.py` 不存在
    - `README_Phase2.md` 提到的 `template_creator_gui.py` 已重命名
    - 均未提及 ilink / LLM / scheduler / RemoteDriver / PLAN_02 / PLAN_03
11. **`autogame_xcx/__init__.py` 空文件**：PLAN_01 §3 承诺「暴露 `__version__`」未落地。
12. **`pyproject.toml` 构建后端**：声明 `setuptools` 但实际用 `uv`，可换 `hatchling`。

---

## 5. 改进方案（推荐执行顺序）

### 阶段 A：止血（0.5 天）

**目标：修掉断点级 bug + 处理安全问题，让现有功能能跑起来。**

| 编号 | 动作 | 文件 |
|---|---|---|
| A1 | 把 `data/config/remote_llm.json` 加入 `.gitignore`；改为从环境变量 `AUTOGAME_LLM_API_KEY` 读取；提供 `data/config/remote_llm.example.json` 模板；**git history 中的 key 视为已泄露，提醒用户在 GLM 控制台立刻吊销并重新生成** | `.gitignore`、`remote/llm_config.py` |
| A2 | 修 `process_main.py` 三处 bug：①文件顶部 `from autogame_xcx.utils.opencv import CvTool`；②`--gui` 改为 `from autogame_xcx.ui.template_creator import TemplateCreatorGUI` + 调用；③`--report` 改为 `from autogame_xcx.core.report_generator import ReportGenerator` | `core/process_main.py:59,308-333` |
| A3 | 修 `report_generator.py:29` —— `template_info` 当 str 用是设计错误。改为：reports_dir 下不按 template_info 分子目录，直接 `os.path.join(self.reports_dir, html_filename)`；`ReportViewerDialog.refresh_reports()` 已经是 listdir 一层，契约一致。同步删除 `report_generator.py:29` 的 `template_info` 参数在路径拼接中的使用 | `core/report_generator.py:25-42` |
| A4 | 删除 `game_executor.py:280-281` 两行调试 `CvTool.imwrite` 调用 | `core/game_executor.py:280-281` |
| A5 | 修 `ocr/engine.py`：`do_handle_image` 改为单参 `do_handle_image(image)`（type 参数本来就没用）；调用处 L64 保持单参；把 L66-77 按 pytesseract 格式的访问改成遍历 DGOCR 返回的 `list[dict]`，从每个 dict 里取 `text / bbox / confidence` | `ocr/engine.py:64,67-77,87` |

**验证命令**：

```bash
python -m autogame_xcx.core.process_main --test all      # 4 项测试全通过
python -m autogame_xcx.core.process_main --list-templates
python start_main_gui.py                                  # 启动 MainGUI 不报错
python -c "from autogame_xcx.core.report_generator import ReportGenerator; ReportGenerator().generate_html_report({'summary':{}},{'name':'t'})"
```

### 阶段 B：收敛（1 天）

**目标：消除重复实现，统一入口。**

| 编号 | 动作 | 说明 |
|---|---|---|
| B1 | **废弃 `start_gui.py`**，README 与文档统一推荐 `start_main_gui.py`；或把 `start_gui.py` 改为 thin wrapper（直接 `from start_main_gui import main; main()`）避免维护两份 | 项目根 |
| B2 | **删除 `ui/template_creator.py` 内部重复的 `MatchingTestDialog`(原 L301-725)**，改为从 `ui.dialogs` import（424 行 → 0 行）；`AreaConfigDialog` API 与 `dialogs/` 版不兼容（`get_config` vs `get_area_data` / `action_type` vs `action_combo`），保留内嵌版避免破坏 `TemplateCreatorGUI` | `ui/template_creator.py` |
| B3 | **`utils/constants.py` 的路径常量改为绝对路径**：基于 `pathlib.Path(__file__).resolve().parents[N]` 推算项目根，所有 `*_PATH` 改为绝对 Path 对象；`CvTool` / `TemplateManager` 等使用方无需改 | `utils/constants.py:52-60` |
| B4 | **`find_wechat_window` 参数化**：接受 `window_title_keyword: str = "微信"` 参数，默认匹配微信；当前硬编码的"聊斋搜神记"改为由 `data/config/window.json` 读取或 CLI 参数覆盖 | `platform/window_controller.py:24-35` |
| B5 | **`autogame_xcx/__init__.py` 暴露 `__version__ = "0.2.0"`**（pyproject.toml 同步改）；`pyproject.toml` 构建后端从 setuptools 切到 hatchling（与 uv 工作流更搭） | `__init__.py`、`pyproject.toml` |

**验证命令**：

```bash
pytest tests/unit -v                # 42+29+24+19 所有单测仍通过
ruff check src tests                # 无新增告警
python -c "import autogame_xcx; print(autogame_xcx.__version__)"
```

### 阶段 C：文档对齐（0.5 天）

**目标：让文档反映项目真实状态。**

| 编号 | 动作 |
|---|---|
| C1 | 归档 `README_Phase1.md`、`README_Phase2.md` 到 `doc/archive/`，顶部加「**历史文档，已过时**」警告头；或直接删除 |
| C2 | 把 `README.md` 重写为：项目当前能力（本地自动化 + ilink 远程驱动 + LLM 编排）、安装（uv）、启动（`start_main_gui.py`）、配置（`data/config/remote_llm.json`）、链接到 `doc/plans/PLAN_01..03` |
| C3 | 新建 `doc/verification_report.md`：本文件内容（Phase 1 / 2 核验表 + 问题清单 + 改进方案）作为交付物 |

### 阶段 D：启动 PLAN_03（可选，不在本次范围）

PLAN_03（协议化接入）完全未启动。若后续要做，先在 `doc/plans/` 下补 `PLAN_03_协议化接入.md` 的阶段拆分（当前文件只是方向性 RFC）。

---

## 6. 关键文件路径速查（供执行时引用）

- `src/autogame_xcx/core/process_main.py` — Phase 1 CLI 入口（3 处 bug）
- `src/autogame_xcx/core/report_generator.py` — HTML / JSON 报告（L29 类型 bug）
- `src/autogame_xcx/core/game_executor.py` — 执行引擎（L280-281 调试遗留）
- `src/autogame_xcx/ocr/engine.py` — OCR 接口（签名 + 格式 bug）
- `src/autogame_xcx/platform/window_controller.py:24-35` — 硬编码游戏名
- `src/autogame_xcx/ui/template_creator.py:145,301` — 重复对话框
- `src/autogame_xcx/utils/constants.py:52-60` — 相对路径
- `src/autogame_xcx/__init__.py` — 空，应暴露 `__version__`
- `data/config/remote_llm.json` — **明文 key**
- `start_gui.py` / `start_main_gui.py` — 双启动器
- `README.md` / `README_Phase1.md` / `README_Phase2.md` — 三份过时文档

---

## 7. 可复用的现有能力（不要重造）

- `CvTool.imread / imwrite`（`utils/opencv.py`）—— 中文路径友好，所有图像 IO 走它
- `CommandRegistry.build_default_registry()`（`remote/commands/registry.py`）—— 6 个默认指令已注册
- `LlmConfig.validate()`（`remote/llm_config.py`）—— provider / api_key / model 校验
- `ReportGenerator._create_*_section`（`core/report_generator.py`）—— HTML 报告分节构造
- `FlowLayout`（`ui/main_window.py:23`）—— Qt 流式布局
- 单元测试基线：`tests/unit/test_remote_*.py`（registry / parser / router / session / commands / llm / driver 共 130+ 用例）

---

## 8. 最终交付物

| 产出 | 状态 |
|---|---|
| 新建 `doc/verification_report.md`（本文件） | ✅ |
| 重写 `README.md` | 待执行（阶段 C2） |
| 归档 `README_Phase1.md` / `README_Phase2.md` 到 `doc/archive/` | 待执行（阶段 C1） |
| 修复 A1-A5 五个断点 bug（5 个文件） | 待执行 |
| 收敛 B1-B5 五处重复 / 冗余（6 个文件） | 待执行 |
| PLAN_03 启动 | 不在本次范围 |

预计总工作量：**2 天**（A 0.5 + B 1 + C 0.5）。

---

## 9. 验证步骤（阶段 A + B + C 全部完成后）

```bash
# 1. 单元测试全绿
pytest tests/unit -v --tb=short

# 2. CLI 冒烟
python -m autogame_xcx.core.process_main --test all
python -m autogame_xcx.core.process_main --list-templates

# 3. GUI 冒烟
python start_main_gui.py

# 4. 报告生成冒烟
python -c "from autogame_xcx.core.report_generator import ReportGenerator; \
           r = ReportGenerator(); \
           r.generate_html_report({'summary': {'total_tasks':1,'completed':1,'failed':0,'success_rate':'100%'}, 'tasks': []}, {'name':'smoke'}); \
           print('OK')"

# 5. LLM 配置不再含明文 key
grep -R "b7a2ad9ce23841e1b4b4b70b8303c900" . --exclude-dir=.git --exclude-dir=.venv
# 应返回空

# 6. 文档检查
ls doc/archive/README_Phase1.md doc/archive/README_Phase2.md
ls doc/verification_report.md
```
