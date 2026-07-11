# ROADMAP

> 本项目演进路线。详细执行计划见 [plans/](plans/)，代码结构规范化基线见 [plans/PLAN_01_代码结构规范化.md](plans/PLAN_01_代码结构规范化.md)。

## 已完成

- **Phase 0 ~ 1（历史）**：基础指令系统 → 指令调度器 → 大模型编排 → GUI 集成 → 大模型识别（见 [archive/](archive/)）。
- **PLAN_01 代码结构规范化**：src layout + 分层包（core/platform/ocr/ui/mcp/utils）+ uv/ruff/mypy/pytest 工具链，已落地。
- **范围收缩**：远程驱动（ilink）与 LLM 编排迁出至 wechat-ilink-bot；本项目聚焦本地执行 + MCP 服务端。

## 进行中（地基：harness + 文档）

| 阶段 | 内容 | 状态 |
|------|------|------|
| **A** 对齐现实 | 核查导入/测试/入口；修 README 与现状一致 | ✅ |
| **B** 记忆层 | CLAUDE.md 契约 + AGENTS.md + `.claude/rules/` + `doc/architecture/` + ROADMAP（对标 wechat-ilink-bot） | ✅ |
| **C** harness | `.claude/settings.json` 权限 + hooks（PostToolUse ruff format/check） | ✅ |

## 待办（后续）

### Phase D：测试 harness（重构兜底网）✅
- `tests/unit/conftest.py` 共享 fixture：`sample_template`、`tmp_templates`（重定向模板目录到临时路径）。
- 纯逻辑核心单测（新，真断言）：`test_coordinate_converter.py`、`test_template_manager.py`、`test_image_matcher.py`。
- MainGUI 导航契约特征化测试：`test_main_window_contract.py`（锁定 5 页导航 = Phase E 护栏）。
- `uv run pytest tests/unit` = **68 passed, 2 skipped**；`QT_QPA_PLATFORM=offscreen` 同样通过。
- ⚠️ 隔离 2 个**预存崩溃**测试（非本次引入）：`test_enhanced_gui_features`（`TemplateCreatorGUI()` 构造）、`test_template_list_display`（`MainGUI()+show()`）在多 GUI 测试累积下触发 Qt access violation → 已 `@pytest.mark.skip`，待后续排查（Phase E 已收尾，未触及此项）。
- ⚠️ 现有若干 GUI 测试是"吞异常+零断言"脚本（`test_intro_page_fix` / `test_intro_simple_fix` / `test_template_features` 等），清理候选，本次未动（surgical）。

### Phase E：UI 重构（像素级 1:1 深色控制台）
- 设计稿：`D:\note-yym\工作笔迹\杂记\微信ilink\Qt6 桌面应用重设计\重设计方案.dc.html`（方案 A 深色控制台）
- **E0 基建 ✅**：`ui/theme.py`（调色板+字体+QSS）+ `ui/icons.py`（30 SVG，QSvgRenderer 着色）+ `ui/widgets/`（FlowLayout/NavButton/ConsoleStatusBar）。
- **E1 外壳 ✅**：MainGUI 瘦身为深色 shell（NavSideBar 200px + 5 NavButton + ConsoleStatusBar）；删 MenuButton/get_main_stylesheet；导航契约测试绿。
- **E2 5 页迁移 ✅**：intro（FeatureCard 网格）/ guide（TOC+章节）/ mcp（端口 stepper+彩色日志终端+呼吸点）/ creator（945 行 IntegratedTemplateCreator + ClickableLabel 迁出 `pages/creator_page.py`，剥内联浅色→局部 QSS 接深色，print→logger）/ management（UI+12 个逻辑方法迁 `pages/management_page.py`，core 经 `self._main`，深色行）。**main_window.py 2198→282 行薄壳**（删 FlowLayout/create_intro/create_feature_card/create_guide 死代码）。回归：`pytest tests/unit` = 68 passed/2 skipped；offscreen 5 页可达 + 类型/索引契约稳固。
  - ⚠️ creator/management 为"剥内联样式 + 全局/局部 QSS 深色"，**非逐像素对照设计稿**（creator 复杂交互面板、management 行内 emoji 图标未全替换为 SVG）；深像素还原留待 E3/E4 控制器解耦后按设计稿精修。
- **E3 控制器解耦 ✅**：`ui/controllers/app_controller.py`（`AppController` 集中持有 core 5 单件 + list/load/delete 模板操作）。`ui/pages` 不再 `import core`——management 经 `self._main.controller`，creator 的 `IntegratedTemplateCreator` 收 `controller` 注入（顺带删死代码 `image_matcher`）；`MainGUI` 作组合根构造控制器并别名。修复 E2 潜在 bug：creator 保存后经 `MainGUI.refresh_templates()` 代理刷新管理页。新增 `test_app_controller.py`（3 用例）；全套件 71 passed/2 skipped。
- **E4 template_creator 评估 ✅（全量重构延后）**：`TemplateCreatorGUI`（978 行独立 QMainWindow）不在主 GUI 流程（MainGUI 用 IntegratedTemplateCreator），仅被 `core/process_main.py` 的 `--gui` CLI 分支（即 AGENTS.md「已知债」表登记的 core→ui 反向违规）引用；构造即崩（预存 Qt access violation）。盲改崩溃独立窗口风险高、价值低 → 评估后**延后**，留待入口层重构或确认 CLI creator 去留时处理。
- 遵守 [`.claude/rules/ui-conventions.md`](../.claude/rules/ui-conventions.md)；每步 `uv run pytest` 绿 + GUI 可启动。

### Phase F：执行 harness 加固 + harness 残项

- **F1 game_executor review ✅**：40+ 处 `print` → 分级 `logger`（info 进度 / warning 预期失败 / debug 逐步骤碎语 / exception 异常块，3 处裸 `except Exception` 改 `logger.exception` 保 traceback）；`start_main_gui.py` + `core/process_main.py` 入口加 `logging.basicConfig(level=INFO)`（否则 logger 输出会被默认丢弃）。全套件 71 passed/2 skipped 无回归。**生命周期/重试/超时**为既有行为，surgical 不重构（`execute_task` 有 max_retry+sleep(2) 重试；无步骤级超时、无中断信号——`stop_execution` 如实标注不支持）。⚠️ 残留 ruff `SIM105`（start_main_gui 有意的 DPI try/except/pass）、`F841`（test_game_executor 预存死变量）为预存，非本次引入。
- **F2 mcp/ review ✅（无需改动）**：`server.py`/`tools.py`/`executor_bridge.py` 已良好工程化——全用 `logging.getLogger`（无 print）；错误处理规范（bridge `raise ... from e`，`tools.call_tool` 兜底捕获→`{"error":...}` 不崩 server，`server.run` try/except→`server_failed`）；生命周期健全（`McpServerThread` start/`request_stop`(防 None 守卫+`call_soon_threadsafe`)/`wait`；bridge `_lock` 串行 + `_last_report` 生命周期清晰；`stop_execution` 如实标注 GameExecutor 不支持中断）。
- **F3 subagents ✅**：`.claude/agents/ui-reviewer.md`（只读审查 UI 改动 vs 设计稿 + ui-conventions/architecture，出分级清单）、`.claude/agents/explore.md`（带架构分层规则的隔离只读探索）。
- **F4 skills ✅**：`.claude/skills/run-gui/SKILL.md`（启动 GUI + 5 页截图到 `data/debug/`，含 offscreen 抓图脚本）、`.claude/skills/add-template-page/SKILL.md`（按既有约定脚手架新导航页，含契约测试同步清单）。

### Phase G：MCP 鉴权 + host 可配置 + 调用方隔离 ✅（对应 wechat-ilink-bot 迭代 C.1）

- **鉴权中间件**：`mcp/server.py` 新增 `_BearerAuthMiddleware`（`starlette.middleware.base.BaseHTTPMiddleware`），`auth_token` 非空时校验 `/sse`、`/messages` 的 `Authorization: Bearer <token>`，为空跳过（本地开发兼容）。
- **host 可配置**：`McpServerThread` 加 `auth_token` 参数；新增 `mcp/server_config.py`（读 `data/mcp_server_config.json`，缺省生成模板），`ui/main_window.py::_build_mcp_server()` 用它装配 host/token，不再硬编码 `127.0.0.1`。
- **调用方隔离**：`mcp/executor_bridge.py` 的 `ExecutorBridge` 新增 `_current_caller`；`run_template` 记录发起方，`get_status` 报告 owner，`stop_execution` 校验 owner（非本人越权请求拒绝并说明当前运行方）；`mcp/tools.py` 5 个 tool 的 `inputSchema` 都加可选 `caller` 字段并透传。
- 测试：`test_mcp_server.py`（新增，中间件 401/放行）、`test_mcp_server_config.py`（新增，配置加载/模板生成）、`test_mcp_executor_bridge.py`/`test_mcp_tools.py` 补 caller 相关用例；`uv run pytest tests/unit` = 90 passed/2 skipped，ruff 净（新增代码范围内；`executor_bridge.py`/`server.py` 各 1 处预存 lint 债未动，见既有备注）。
- **本轮不做**（留给后续）：真实跨机网络部署验证、GUI 端 host/token 可视化编辑（仍走配置文件）、`GameExecutor` 真中断（`stop_execution` 越权判断已生效，但 owner 校验通过后仍是既有 stub）。

---

## 进行中：UI 像素级精细化（对照设计稿方案 A，分两批）

用户验收 Phase E 时「看到的 UI 问题挺多」→ 本 pass 按设计稿 FRAME A/D/E/F/G 逐页像素对齐。决策：creator 全量重设计 / 分两批 / 不做自定义标题栏。

- **共享基建 ✅**：`ui/widgets/page_header.py`（PageHeader，5 页统一头部条）+ `ui/icons.py` 加 `dots-v`。
- **第一批 ✅（待用户验收）**：
  - **management（FRAME E）**：卡片列表 → 6 列 `QTableWidget` 表格（名称/游戏/任务/状态色点/最近执行/行内 4 SVG 操作图标）+ PageHeader（含 mono「N 个模板」计数）+ 工具栏（搜索 + 新建模板）。逻辑全保留，参数化为行处理器。⚠️ 数据局限：状态恒「就绪」（无运行态追踪）、最近执行用 created_time 近似。
  - **creator（FRAME D，全量重设计）**：去 QGroupBox+emoji → 扁平 mono 分区（模板信息/任务流程/标记区域/全局设置）+ 顶部 PageHeader 工具栏（截图/保存/测试，保存测试按钮注入 creator 属性）+ 右画布（标题栏 + ClickableLabel + 提示条）+ 标记色按索引交替蓝/紫。**全部 action 方法逐字保留**（仅 draw_area_markers 改交替色）。⚠️ tasks/areas 仍用 QListWidget（深色紧凑 item）保逻辑不变，非设计稿自定义序号块行。
  - 验证：`pytest tests/unit` = 71 passed/2 skipped；ruff 净；`/run-gui` 5 页截图生成（`data/debug/page_*.png`，12-17KB 非空）。
- **第二批（待启动，用户验收第一批后）**：intro/guide 加 PageHeader、mcp 收敛；FeatureCard desc 行高微调；可选 statusbar `set_context` 扩展。对照 FRAME A/F/G。

### Phase H：多 bot 队列化调度 ✅（A 路线：严格串行 + 排队可见 + 真取消超时保护）

现状问题（起因）：`mcp/executor_bridge.py::ExecutorBridge` 曾用单个 `threading.Lock` 把"整次模板执行"（截图→匹配→点击→报告）串成临界区，多个 bot 并发调用 `run_template` 时第二个请求裸阻塞、无排队感知；`core/game_executor.py::execute_task`/`execute_template` 无取消检查点，`stop_execution` 是 stub。存在风险：bot 端（wechat-ilink-bot）`McpClient` 的 `tools/call` 有 600s 硬超时，超时后清理 pending Future，但 Python 侧已拿到锁的执行不会收到取消信号，会继续跑到底——可能出现"bot 侧显示超时失败，但游戏内操作已真实发生且报告无人接收"的静默丢单/影子执行问题，且后续排队的其他 bot 会被这个卡住的任务一直堵住。

决策（2026-07-11）：走 **A. 严格串行 + 排队可见 + 真取消超时保护**（不做真并发/多窗口路由，那是 B 路线，见下方「待办优化建议」）。

实现：
- **`core/game_executor.py`**：新增 `ExecutionCancelledError` + `_sleep_or_cancel` helper；`execute_template`/`execute_task` 签名加可选 `cancel_event: threading.Event | None`，在任务间/重试间/步骤间循环顶部和 `time.sleep` 调用处加检查点，`cancel_event.is_set()` 时立即抛出，向上传播、不吞。未传 `cancel_event`（`None`）时行为与改动前完全一致（向后兼容 `core/process_main.py` 等既有直接调用点）。
- **`mcp/executor_bridge.py`**：用 `threading.Condition` 守护的 `deque[_QueueEntry]` FIFO 队列替换原 `threading.Lock` + 单值字段模型；新增 `QueueFullError`/`DuplicateCallerError`/`QueueWaitTimeoutError`/`EntryCancelledError`/`ExecutionOverdueError`。`run_template` 入队→排队等待（超时摘除）→提交唯一 `ThreadPoolExecutor(max_workers=1)` 执行（超时立即 `cancel_event.set()` + 提前返回 `ExecutionOverdueError`，后台线程在下一个检查点真正停止、清理逻辑写在 worker 自身 `finally` 里，不依赖前台是否还在等待）。`get_status(caller)` 新增 `queue_length`/`queue_position`/`overdue` 字段。`stop_execution(caller)` 从"不支持中断"的 stub 升级为真取消：排队中直接摘除，执行中发送取消信号（下一个安全检查点生效）。
- **`mcp/server_config.py`**：`McpServerConfig` 新增 `queue_capacity`（默认 2）、`queue_wait_timeout_seconds`（默认 300s）、`execution_timeout_seconds`（默认 480s，`<=0` 表示禁用该超时）。
- **`mcp/tools.py`**：`get_status` 补上此前遗漏的 `caller` 透传；新增 4 个新异常的 `except` 分支，返回结构化 `reason`（如 `queue_full`/`duplicate_caller`）；5 个 tool 的 description 补充排队/超时/真取消语义说明。
- **`ui/main_window.py::_build_mcp_server()`**：把新增的三个配置项传给 `ExecutorBridge`。
- 测试：新增 `test_game_executor_cancel.py`（cancel_event 检查点特征化）、`test_mcp_executor_bridge_queue.py`（排队位置/容量拒绝/排队超时/执行超时+overdue可见+最终清理/取消排队中任务/取消执行中任务，均用 `threading.Event` 驱动的假 executor + 毫秒级超时阈值，不真 sleep 300s/480s）；更新 `test_mcp_executor_bridge.py`（`stop_execution` 同 caller/空闲两个用例改为新行为）、`test_mcp_server_config.py`（新增字段加载/默认值/`0`=禁用）、`test_mcp_tools.py`（get_status caller 透传、新异常结构化返回）。`uv run pytest tests/unit` = 114 passed/2 skipped（较 Phase G 的 90 passed 新增 24 个用例），ruff 净（新增代码范围内；`game_executor.py`/`executor_bridge.py` 各 1 处预存 lint 债未动）。
- **本轮不做**（留给后续，见下方「待办优化建议」）：真并发/多窗口路由（B 路线）；已排队/执行中任务的重试逻辑独立超时展示；`estimated_wait_seconds` 预估等待时长（无历史耗时统计，暂不做虚假精确度）。

### Phase H 待办优化建议（未排期，先记录）

**路线 B：真并发**（多个任务真正同时执行，各自操作各自窗口）——需拆出独立 `GameExecutor`/`GameWindowController` 实例、hwnd 显式穿透 mcp tool→bridge→executor→controller 四层、解决 `pyautogui.click`（系统唯一鼠标光标）与 `win32gui.SetForegroundWindow`（系统唯一前台窗口）的物理互斥、`ImageGrab.grab` 屏幕区域截图在窗口重叠时读错画面的问题。架构级改造，工作量与风险显著更高，且 autogame-xcx 当前仍是"仅 OCR、未完善 RPA/协议自动化"的半成品阶段，不适合现在投入。暂不启动；待"协议自动化 + RPA 完善"这条长期主线方向明确后一并评估启动时机。

## 不在范围内

- 远程驱动（ilink 指令编排）/ LLM 编排：归 wechat-ilink-bot。MCP server 自身的鉴权/host 配置已落地本仓库（见 Phase G），不算"远程驱动"。
- `core/process_main.py` 反向 import ui 的彻底消除：随 Phase E 入口层重构一并处理。
