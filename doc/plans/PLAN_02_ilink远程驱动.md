# PLAN_02：ilink SDK 远程驱动

> 项目：`wechat-link-autogame-xcx`
> 方向：通过 JPype1 集成 `wechat-ilink-sdk-java`，建立"远程用户微信 ↔ Python 自动化"双向通道
> 预计周期：6 阶段 = 约 2 周（核心链路） + 后续 LLM 编排迭代
> 前置依赖：方向 1 完成（包结构稳定）

> **进度状态**：
> - ✅ 阶段 2.1 JPype Spike（2026-06-15 完成，17/17 检查通过）
> - ✅ 阶段 2.2 消息接收通道（完成）
> - ✅ 阶段 2.3 基础指令系统（完成，单元测试 42/42）
> - ✅ 阶段 2.4 指令调度器（完成，24/24 检查通过）
> - ✅ 阶段 2.5 大模型编排（2026-06-16 完成，29/29 单元测试 + 24/24 演示脚本）
> - ⬜ 阶段 2.6 GUI 集成与稳定性

---

## 1. Context（为什么做）

当前项目是单机本地 PyQt6 自动化工具——用户必须在运行 GUI 的电脑前手动操作。这限制了使用场景：

- 出门时无法远程触发自动化
- 长时间任务跑完无法及时收到通知
- 多台机器分别跑不同账号时无法统一调度
- 无法利用大模型做语义化的任务编排（"帮我把日常任务做完"）

父目录 `D:\IDEAGithubWork\wechat-ilink\wechat-ilink-sdk-java` 是一个完整的 ilink 通信 SDK（包名 `com.github.wechat.ilink.sdk`），可以让程序以"机器人"身份登录微信，**接收用户消息**（`OnMessageListener`）并**回发消息**（`MessageService.sendText/sendImage/...`）。

本方向目标：**Python 项目通过 JPype1 集成 ilink SDK jar**，让远程用户在微信中发指令（结构化 `#指令` 或自然语言），Python 解析后调用本地自动化能力（图像/协议策略）执行，结果回传微信。后续接入大模型，把自然语言拆解为指令队列顺序执行。

### 1.1 边界澄清

同级目录的 `wechat-ilink-game`、`wechat-ilink-imoney` 是**与当前项目同级的独立项目**，本规划**不复用其代码**：
- `wechat-ilink-game`：基于 SDK 的 Java 机器人后端（已有 command 系统、LLM 路由，但是 Java 实现）
- `wechat-ilink-imoney`：Spring 业务服务（含 imai AI 模块）

当前 Python 项目**只引用** `wechat-ilink-sdk-java` 的 jar 作为通信通道，**自己实现**指令解析、调度、LLM 编排。

### 1.2 应用场景示意

```
[远程用户手机微信]
  ↓ 发送 "#run 签到模板"
[ilink Java SDK] (长轮询接收)
  ↓ OnMessageListener.onMessages 回调
[Python 远程驱动层]
  ├── 解析指令 (#run → 触发模板执行)
  ├── 调度器入队 (顺序执行避免窗口冲突)
  ├── 本地执行 (调 core/executor)
  └── 结果回传
  ↓ MessageService.sendText
[远程用户手机微信] 收到 "签到完成：金币+100"

[大模型介入（后续阶段）]
用户发自然语言："帮我把签到和领体力做了"
  ↓ LLM 分析
LLM 拆解为 [#run 签到, #run 领体力]
  ↓ 顺序执行
汇总报告 → 微信回发
```

---

## 2. 现状盘点

### 2.1 ilink SDK 已有能力（仅引用，不修改）

| SDK 组件 | 包路径 | 用途 |
|---|---|---|
| `ILinkClientBuilder` | `com.github.wechat.ilink.sdk` | Builder 模式构造 client（config / loginContext / onLogin / onMessage 等） |
| `ILinkClient` | `com.github.wechat.ilink.sdk` | 客户端实例，`executeLogin()` 返回二维码，`sendText(userId, text)` 发消息 |
| `MessageService` | `com.github.wechat.ilink.sdk.service` | 消息发送：`sendText / sendImage / sendVoice / sendVideo / sendFile` |
| `OnMessageListener` | `com.github.wechat.ilink.sdk.core.listener` | 消息接收回调接口：`void onMessages(List<WeixinMessage>)` |
| `OnLoginListener` | 同上 | 登录结果回调 |
| `OnHeartbeatListener` | 同上 | 心跳回调 |
| `OnDisconnectListener` | 同上 | 断线回调 |
| `WeixinMessage` | `com.github.wechat.ilink.sdk.core.model` | 消息模型：`message_id / message_type / from_user_id / to_user_id / create_time_ms / context_token / item_list` |
| `MessageItem` | 同上 | 消息内容（text_item / image_item / voice_item / video_item / file_item） |
| `LoginContext` | `com.github.wechat.ilink.sdk.core.login` | 登录上下文（持久化用） |
| `ResumeContext` | `com.github.wechat.ilink.sdk.core.context` | 服务重启后恢复客户端实例 |

### 2.2 当前 Python 项目能力（复用对象）

| Python 资产 | 路径（方向 1 后） | 用途 |
|---|---|---|
| `GameExecutor` | `core/executor.py` | 触发模板执行的统一入口 |
| `TemplateManager` | `core/template_manager.py` | 列出/查询可用模板 |
| `ReportGenerator` | `core/report_generator.py` | 生成执行报告 |
| `MainGUI` | `ui/main_window.py` | 主窗口（pyqtSignal 信号体系） |

### 2.3 待补足能力

| 能力缺口 | 解决方案 |
|---|---|
| Python 调 Java | 引入 JPype1（同进程 JNI） |
| 接收 SDK 消息回调 | `@JImplements("...OnMessageListener")` 让 Python 类实现 Java 接口 |
| 跨线程通信（JVM 线程 → Qt 主线程） | pyqtSignal 转发 |
| 指令解析 | 新增 `remote/commands/` 子包 |
| 顺序执行（避免窗口冲突） | 新增 `remote/scheduler/` 子包 |
| 自然语言编排 | 新增 `remote/llm/` 子包（后续阶段） |

### 2.4 Spike 实战发现（2026-06-15，阶段 2.1 产出）

阶段 2.1 完成时，spike 脚本 `scripts/spike_jpype_ilink.py` 揭示了 4 个原文档未覆盖的问题。这些发现已回写到本规划相关章节，并对后续阶段（2.2~2.6）的实现有直接影响。

#### 发现 1：JPype API 名是 `JImplements`（带 s），不是 `JImplement`

**原文档错误**：所有出现 `@JImplement` 的地方都写错（共 8 处）。

**正确写法**：
```python
from jpype import JImplements, JOverride

@JImplements("com.github.wechat.ilink.sdk.core.listener.OnMessageListener")
class PythonMessageListener:
    @JOverride
    def onMessages(self, messages): ...
```

**修复状态**：✅ 文档已全文替换（§2.3、§3.1、§3.2、§4 目录注释、§5.2 代码示例）。

#### 发现 2：ilink jar 单独加载会 `NoClassDefFoundError`，必须加 14 个依赖 jar

**症状**：
```
java.lang.NoClassDefFoundError: org/slf4j/LoggerFactory
    at JClass("com.github.wechat.ilink.sdk.ILinkClient")
```

**原因**：SDK 的 pom.xml 声明了 okhttp / jackson-databind / slf4j-api / logback-classic / kotlin-stdlib 等 14 个 runtime 依赖，但 jar 文件本身没 shade 它们。Maven 构建只把 SDK 自己的 class 打进 jar，依赖 jar 在用户工程里解析。

**解决**：在 ilink SDK 工程下跑一次：
```bash
cd ../wechat-ilink-sdk-java
mvn dependency:copy-dependencies \
    -DoutputDirectory=target/dependency \
    -DincludeScope=runtime
```

产出 14 个 jar 在 `target/dependency/`：
```
annotations-13.0.jar           kotlin-stdlib-common-1.9.10.jar
jackson-annotations-2.17.2.jar kotlin-stdlib-jdk7-1.8.21.jar
jackson-core-2.17.2.jar        kotlin-stdlib-jdk8-1.8.21.jar
jackson-databind-2.17.2.jar    kotlin-stdlib-1.8.21.jar
logback-classic-1.5.8.jar      okhttp-4.12.0.jar
logback-core-1.5.8.jar         okio-jvm-3.6.0.jar
                                okio-3.6.0.jar
                                slf4j-api-2.0.13.jar
```

**JVMManager 适配**：`start()` 必须把整个 `deps_dir/*.jar` 加到 classpath（详见 §5.1 修订后的实现）。

**对 config/ilink.py 的影响**：必须新增 `deps_dir: Path` 字段（不仅 `jar_path`）。

**后续阶段注意事项**：
- 阶段 2.6 用 PyInstaller 打包时，`--add-data` 要带 jar + 整个 deps 目录
- ilink SDK 版本升级后，依赖列表会变，要重跑 `copy-dependencies`
- 建议在 `_cli.py` 启动时探测 `deps_dir` 是否存在，缺失则提示用户执行 mvn 命令

#### 发现 3：JVM 路径探测必须 fallback

**症状**：
```
JVMNotFoundException: No JVM shared library file (jvm.dll) found.
Try setting up the JAVA_HOME environment variable properly.
```

**原因**：JPype 1.7.1 在 Windows 上不查 PATH 上的 java，只查注册表 + JAVA_HOME。Microsoft JDK 用 .msi 安装可能不写注册表。

**解决**：`find_jvm_dll()` 函数实现三级 fallback（详见 §5.1）：
1. `JAVA_HOME/bin/server/jvm.dll`
2. 调 `java -XshowSettings:properties` 拿 `java.home`，组合 `lib/server/jvm.dll` 或 `bin/server/jvm.dll`
3. 退化到 `jpype.getDefaultJVMPath()`（让上层报清晰错误）

**当前环境**：实际探测到 `D:\jdk\jdk-17.0.18.8-hotspot\bin\server\jvm.dll`。

#### 发现 4：JPype 桥接层 Python 写法陷阱

JPype 的 Python ↔ Java 代理桥接有几个非直觉行为，直接影响 listener 等核心代码的写法：

| Python 写法 | 行为 | 正确做法 |
|---|---|---|
| `isinstance(py_obj, java_interface)` | 永远 `False`（Python 的 isinstance 不能判 Java 接口） | 用 Java 反射：`OnMessageListener.class_.isInstance(py_obj)` |
| `proxy_a is proxy_b`（同一 Java 对象的两个 Python 引用） | 永远 `False`（JPype 每次返回新 Python 代理） | 用 Java 端 identity：`int(a.hashCode()) == int(b.hashCode())` |
| `messages: list[WeixinMessage]` 类型注解 | JPype 内部 List 类型不能直接当 Python list | 用 `for msg in messages:` 迭代即可，不要尝试 `list(messages)` 或 `messages[0]` |
| `@JImplements` 类继承 `QObject` | 失败（JPype 元类冲突） | 用单独的 `_SignalCarrier(QObject)` 持有 pyqtSignal，listener 持有 carrier（详见 §5.2） |

**对实现的影响**：
- `message_listener.py` 的 listener 类不能继承 QObject（信号必须放独立 carrier）
- 单元测试里检查"listener 是否实现了接口"要用 `class_.isInstance()`，不能用 `isinstance()`
- 阶段 2.4 的 CommandQueue 单元测试也要避免 `is` 比较 Java 对象

### 2.5 阶段 2.5 实战发现（2026-06-16）

阶段 2.5 完成时发现原文档 §5.11 的设计在落地时有 4 处需要修订。这些发现已回写到相关章节。

#### 发现 1：LLM 输出经常违反"只输出 JSON"约束，必须容错解析

**症状**：即使用 system prompt 强约束"只输出 JSON 数组、不要解释"，主流 LLM（Claude / GPT-4o / DeepSeek）仍会在 ~10% 调用中：
- 把 JSON 包在 ```` ```json ... ``` ```` 围栏里
- 在 JSON 前后加"好的，输出如下："/"以上是建议"等口水
- 直接返回自然语言（"对不起，我无法处理这个请求"）

**解决**：在 `orchestrator.py` 加 `_extract_json_array(text)` 辅助函数：
1. 剥离 ``` 围栏
2. 取首个 `[` 到末尾 `]` 之间的子串
3. 找不到方括号 → 返回 None，上层报"格式异常"
4. 找到 → `json.loads`；解析失败 → 报"JSON 解析失败"

**对单元测试的影响**：`test_extract_json_array` 参数化覆盖 7 种输入（含围栏、含口水、纯自然语言、空串、单对象），见 `tests/unit/test_remote_llm.py`。

**对 §5.11 的回写**：原 `orchestrator._parse_response` 直接 `json.loads(response)`，已修订为先走 `_extract_json_array` 容错。

#### 发现 2：白名单二次校验必须"整批拒绝"，不能"跳过未知项"

**症状**：原 §5.11 暗示 LLM 输出 `[{"action":"run","args":"签到"},{"action":"delete_database","args":"all"}]` 时跳过 delete_database、保留 run 签到。

**问题**：LLM 一次输出多个指令表示"批量规划"，半执行状态难以回滚——用户看到"签到完成 + delete 被拒"会误以为意图没完整传达，反复重发反而触发更多签到。

**解决**：`orchestrator._parse_and_validate` 校验任何一项失败（解析错误、字段缺失、action 不在 registry）→ **整批拒绝**、不入队任何指令、回执错误描述。单测覆盖 `test_orchestrator_rejects_unknown_action` / `test_orchestrator_rejects_missing_action` / `test_orchestrator_rejects_non_string_args`。

**对 §7 风险表的影响**：原 "LLM 拆解指令失败/越界" 对策 "JSON Schema 校验 + 指令白名单二次验证" 已细化为"白名单二次校验 + **整批拒绝**策略"。

#### 发现 3：`anthropic` / `openai` 不能进核心 `dependencies`

**症状**：在 `pyproject.toml [project].dependencies` 里写 `anthropic` / `openai` 会导致：
- 所有用户都被强制安装 ~50MB 的 SDK，即使用户不需要 LLM 编排
- 离线部署时这两个包会拖慢 `uv sync`

**解决**：新增 `[project.optional-dependencies].llm`：
```toml
[project.optional-dependencies]
llm = ["anthropic>=0.40", "openai>=1.50"]
```
用户按需 `uv pip install autogame-xcx[llm]`。

**AnthropicProvider / OpenAIProvider 的 import 策略**：
- 不在 `remote/llm/__init__.py` 里 import 它们（否则 import 包就触发 ImportError）
- 子模块内 `def __init__` 才 `import anthropic` / `import openai`，未安装时报清晰错误：
  > `anthropic 包未安装；请运行 uv pip install anthropic 或 uv pip install autogame-xcx[llm]`

**对 §8 依赖工具链的影响**：原表把 anthropic/openai 列为常规依赖；已修订为 optional `[llm]` extras。

#### 发现 4：单元测试用 `MockLlmProvider` 桩，不调真实 API

**症状**：原 §5.11 暗示 orchestrator 测试要 mock LLM 调用，但没明确桩的形态。

**问题**：真实 API 调用需要 key + 网络 + 速率限制 + 输出不确定性，无法纳入 `pytest tests/unit/`。

**解决**：`remote/llm/provider.py` 内置 `MockLlmProvider`：
- 接收预设响应队列 `responses: list[str]`
- `chat()` 每次出队一个；耗尽后返回 `""`（不抛 IndexError，便于后续断言）
- 记录 `calls: list[list[dict]]` 让测试断言 prompt 内容

**对 §9 验证方式的影响**：阶段 2.5 增加了两层验证：
- 单元测试：`pytest tests/unit/test_remote_llm.py`（29/29 通过，用 MockLlmProvider）
- 演示脚本：`uv run python scripts/demo_remote_llm.py`（24/24 通过，6 个场景覆盖 happy path / 越权 / 乱码 / 围栏 / router 集成 / provider 异常）

真实 LLM 链路（用户配置 API key 后手动验证）作为阶段 2.6 GUI 集成时的端到端检查项。

---

## 3. 集成方式选型

### 3.1 五方案对比矩阵

| 方案 | 启动开销 | 调用延迟 | 双向回调 | 部署复杂度 | 适用性 |
|---|---|---|---|---|---|
| **JPype1** ★推荐 | ~1.5s（一次） | 微秒级（同进程 JNI） | 强（`@JImplements` 直接实现 Java 监听器） | 单进程需 JDK | ✅ 完美匹配 |
| Py4J（备选） | ~3s（独立进程） | 毫秒级（socket） | 中（需 callback server） | 独立 Java 进程 | ⚠️ 进程隔离需求时 |
| subprocess + CLI | ~1s/次 | 秒级 | 无 | 极低 | ❌ 无法长轮询接收消息 |
| gRPC | ~2s | 毫秒级 | 强 | 需 Java 端开发 server | ❌ SDK 是客户端不是 server |
| HTTP/REST | ~3s | 毫秒级 | 中 | 需 Java Web 框架 | ❌ SDK 不是 Web 应用 |

### 3.2 推荐 JPype1 理由

1. **完美匹配 SDK 模式**：ilink SDK 本质是"长连接客户端 + 监听器回调"，需要 Python 实现 `OnMessageListener` 接收消息——JPype 的 `@JImplements` 让 Python 类直接实现 Java 接口，**是唯一原生支持此模式的方案**。
2. **零网络开销**：同进程 JNI，消息回调延迟可控在毫秒级。
3. **PyQt6 共存稳定**：单进程模型，JVM 启动后常驻，与 Qt 事件循环无冲突。
4. **依赖最小**：仅一个 `jpype1` pip 包；SDK jar 直接通过 classpath 加载，无需 Java 端额外改造。

### 3.3 备选 Py4J 场景

- SDK 频繁崩溃会拖垮 PyQt 应用（JPype 同进程无法隔离）
- 多 Python 进程需要共享同一个 Java client
- 团队对 JNI 不信任

---

## 4. 目标目录结构（在方向 1 基础上增量）

```
src/autogame_xcx/
├── remote/                              # ★ 新增：远程驱动层（核心）
│   ├── __init__.py
│   ├── ilink/                           # ilink SDK 集成
│   │   ├── __init__.py
│   │   ├── jvm.py                       # JVM 生命周期（懒加载、atexit 关闭）
│   │   ├── client.py                    # ILinkClient 包装（登录、sendText 等）
│   │   ├── message_listener.py          # @JImplements 实现 OnMessageListener
│   │   ├── login_listener.py            # @JImplements 实现 OnLoginListener
│   │   └── converters.py                # WeixinMessage/MessageItem ↔ Python dict
│   │
│   ├── commands/                        # 指令系统
│   │   ├── __init__.py
│   │   ├── parser.py                    # 文本 → ParsedCommand（# 前缀 + 别名表）
│   │   ├── registry.py                  # 指令注册表 + 别名解析
│   │   ├── dispatcher.py                # 分发到执行器，结果回传
│   │   ├── base.py                      # Command 抽象基类 + CommandContext + CommandResult
│   │   └── definitions/                 # 具体指令实现
│   │       ├── __init__.py
│   │       ├── run_template.py          # #run <模板名> 触发模板执行
│   │       ├── status.py                # #status 查询执行状态
│   │       ├── stop.py                  # #stop 停止当前任务
│   │       ├── list_templates.py        # #list 列出可用模板
│   │       └── report.py                # #report <task_id> 查询报告
│   │
│   ├── scheduler/                       # 指令调度
│   │   ├── __init__.py
│   │   ├── queue.py                     # 顺序执行队列（线程安全）
│   │   ├── executor.py                  # 出队执行 + 状态追踪
│   │   └── state.py                     # 执行状态机（pending/running/done/failed）
│   │
│   ├── llm/                             # 大模型编排（后续阶段，预留接口）
│   │   ├── __init__.py
│   │   ├── provider.py                  # LlmProvider 抽象基类
│   │   ├── anthropic_provider.py        # Claude 实现
│   │   ├── openai_provider.py           # OpenAI 兼容实现
│   │   ├── orchestrator.py              # 自然语言 → 指令队列编排
│   │   └── prompt_templates.py          # 系统提示词（含可用指令清单）
│   │
│   ├── router.py                        # 消息路由（# 指令 / 自然语言分发）
│   └── session.py                       # 远程会话（用户白名单、最近上下文）
│
├── config/
│   ├── ilink.py                         # ★ 新增：ilink SDK 配置（jar 路径、登录凭证、心跳）
│   ├── remote.py                        # ★ 新增：远程控制配置（白名单、指令前缀、超时）
│   └── llm.py                           # ★ 新增：LLM 配置（API key、模型、温度）
│
└── ui/dialogs/
    ├── remote_status.py                 # ★ 新增：远程连接状态指示灯 + 最近消息
    └── command_console.py               # ★ 新增：指令执行日志（线程安全显示）
```

### 4.1 模块职责边界

| 模块 | 职责 | 禁止 |
|---|---|---|
| `remote/ilink/` | SDK 集成（JVM 管理、消息收发） | 业务知识 |
| `remote/commands/` | 指令解析、注册、分发 | 直接操作 SDK 对象（经 ilink/client 抽象） |
| `remote/scheduler/` | 顺序执行、状态追踪 | 业务逻辑（只调度，不实现） |
| `remote/llm/` | 自然语言 → 指令队列编排 | 直接执行游戏操作（只生成指令） |
| `remote/router.py` | 消息分发（指令 vs 自然语言） | 业务实现 |
| `remote/session.py` | 用户白名单、最近上下文 token | 业务知识 |

### 4.2 依赖方向

```
ui  →  remote  →  core (executor/template_manager)
              ↓
          config (ilink/remote/llm)
              ↓
            utils (logger)
```

---

## 5. 关键模块设计

### 5.1 `remote/ilink/jvm.py`：JVM 生命周期管理

```python
"""全局唯一 JVM 实例，懒加载，PyQt 退出时优雅关闭。"""
import os
import subprocess
import threading
from pathlib import Path
from typing import Optional
import jpype
import jpype.imports  # noqa: F401

from autogame_xcx.config.ilink import ILinkConfig
from autogame_xcx.exceptions import AutogameError


def find_jvm_dll() -> str:
    """从 JAVA_HOME 或 PATH 上的 java 探测 jvm.dll。

    Spike 实战发现：jpype.getDefaultJVMPath() 在 Windows 上不查 PATH，
    仅靠注册表 + JAVA_HOME；Microsoft JDK 用 .msi 装可能不写注册表，
    导致 JVMNotFoundException。本函数显式 fallback：
      1. JAVA_HOME/bin/server/jvm.dll
      2. java -XshowSettings:properties 拿 java.home，再 lib/server 或 bin/server
      3. 退化到 jpype.getDefaultJVMPath()（让上层报清晰错误）
    """
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / "server" / "jvm.dll"
        if candidate.exists():
            return str(candidate)

    from shutil import which
    java_exe = os.environ.get("JAVA_HOME")
    if java_exe:
        java_exe = str(Path(java_exe) / "bin" / "java.exe")
    else:
        java_exe = which("java")
    if java_exe:
        try:
            out = subprocess.check_output(
                [java_exe, "-XshowSettings:properties", "-version"],
                stderr=subprocess.STDOUT, text=True, timeout=10,
            )
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("java.home ="):
                    home = Path(line.split("=", 1)[1].strip())
                    for sub in ("lib/server", "bin/server"):
                        dll = home / sub / "jvm.dll"
                        if dll.exists():
                            return str(dll)
        except Exception:
            pass

    return jpype.getDefaultJVMPath()


class JVMManager:
    _instance: Optional["JVMManager"] = None
    _lock = threading.Lock()

    def __init__(self, config: ILinkConfig):
        self.config = config
        self._started = False

    @classmethod
    def get(cls, config: Optional[ILinkConfig] = None) -> "JVMManager":
        with cls._lock:
            if cls._instance is None:
                if config is None:
                    raise AutogameError("JVM not initialized; config required on first call")
                cls._instance = cls(config)
            return cls._instance

    def start(self) -> None:
        if self._started:
            return
        if not self.config.jar_path.exists():
            raise AutogameError(f"ilink SDK jar not found: {self.config.jar_path}")
        if not self.config.deps_dir.exists():
            raise AutogameError(
                f"ilink SDK dependencies not found: {self.config.deps_dir}\n"
                f"Run: mvn dependency:copy-dependencies "
                f"-DoutputDirectory=target/dependency -DincludeScope=runtime "
                f"in wechat-ilink-sdk-java/"
            )
        # Spike 实战发现：单独加载 SDK jar 会 NoClassDefFoundError: org/slf4j/LoggerFactory
        # 必须把 14 个运行时依赖 jar（okhttp/jackson/slf4j/logback/kotlin-stdlib 等）一起加入
        dep_jars = sorted(self.config.deps_dir.glob("*.jar"))
        classpath = [str(self.config.jar_path)] + [str(p) for p in dep_jars]
        jpype.startJVM(
            find_jvm_dll(),
            *self.config.jvm_args,
            classpath=classpath,
            convertStrings=True,  # Java String 自动转 Python str
        )
        self._started = True

    def shutdown(self) -> None:
        if self._started and jpype.isJVMStarted():
            jpype.shutdownJVM()
            self._started = False

    @property
    def is_started(self) -> bool:
        return self._started
```

> **关键配置字段（`config/ilink.py`）**：
> ```python
> @dataclass(frozen=True)
> class ILinkConfig:
>     jar_path: Path       # wechat-ilink-sdk-java/target/wechat-ilink-sdk-X.Y.Z.jar
>     deps_dir: Path       # wechat-ilink-sdk-java/target/dependency/  (14 个 jar)
>     jvm_args: list[str]  # 默认 ["-Djava.awt.headless=true"]
>     # ... 登录凭证 / 心跳 / channelVersion 等
> ```

### 5.2 `remote/ilink/message_listener.py`：核心回调实现

```python
"""Python 实现 Java 的 OnMessageListener 接口。
SDK 在 JVM 线程回调 onMessages，不能直接操作 QWidget，
必须通过 pyqtSignal 转主线程。"""
from PyQt6.QtCore import QObject, pyqtSignal
from jpype import JImplements, JOverride

from autogame_xcx.remote.ilink import converters


class _SignalCarrier(QObject):
    """单独的 QObject 持有信号（JImplements 类不能多继承）。"""
    message_received = pyqtSignal(dict)
    message_error = pyqtSignal(str)


# ⚠️ deferred=True 必须加：
# @JImplements 装饰类时会立即校验 Java 接口可解析，但此时 JVM 可能还没启动，
# 会导致 JVMNotRunning 异常。deferred=True 把校验延后到首次实例化，
# 这样模块可以在 JVM 未启动时被 import，只要在使用前调用 jvm.start() 即可。
@JImplements(
    "com.github.wechat.ilink.sdk.core.listener.OnMessageListener",
    deferred=True,
)
class PythonMessageListener:
    """实现 Java 接口，注册到 ILinkClientBuilder.onMessage()。

    实例化要求 JVM 已启动（client.py 里通过 lazy property 保证）。"""

    def __init__(self):
        self._carrier = _SignalCarrier()
        self.message_received = self._carrier.message_received
        self.message_error = self._carrier.message_error

    @JOverride
    def onMessages(self, messages):  # List<WeixinMessage>
        import logging
        logger = logging.getLogger(__name__)
        try:
            for msg in messages:
                py_msg = converters.weixin_to_python(msg)
                self.message_received.emit(py_msg)
        except Exception as e:
            logger.exception("Failed to handle incoming messages")
            self.message_error.emit(str(e))
```

> **`deferred=True` 的关键作用**（阶段 2.2 实战发现）：
>
> - 不加 `deferred=True`：`@JImplements(...)` 在 import 模块时立即调用 `JClass(interface_name)`，此时 JVM 还没启动 → `JVMNotRunning: Java Virtual Machine is not running`
> - 加 `deferred=True`：类定义时只标记"待绑定接口"，首次实例化时才真正解析接口
> - 配合 `ILinkClient.message_listener` 的 lazy property（在 `jvm.start()` 之后才实例化），可保证 JVM 启动顺序正确
> - `login_listener.py` 的 `PythonLoginListener` 同理

### 5.3 `remote/ilink/client.py`：ILinkClient 包装

```python
"""封装 ILinkClientBuilder + ILinkClient，提供 Python 友好的 API。"""
import logging
from typing import Optional
from autogame_xcx.remote.ilink.jvm import JVMManager
from autogame_xcx.remote.ilink.message_listener import PythonMessageListener
from autogame_xcx.remote.ilink.login_listener import PythonLoginListener
from autogame_xcx.config.ilink import ILinkConfig

logger = logging.getLogger(__name__)


class ILinkClient:
    """Python 端的 ilink 客户端门面。"""

    def __init__(self, config: ILinkConfig):
        self.config = config
        self.jvm = JVMManager.get(config)
        self.message_listener = PythonMessageListener()
        self.login_listener = PythonLoginListener()
        self._client = None

    def start(self) -> str:
        """启动 JVM + 构造 client + 执行登录，返回二维码内容。"""
        self.jvm.start()
        if self._client is None:
            from com.github.wechat.ilink.sdk import ILinkClientBuilder
            self._client = (
                ILinkClientBuilder()
                .config(self.config.to_java())
                .onMessage(self.message_listener)
                .onLogin(self.login_listener)
                .build()
            )
        qr_content = self._client.executeLogin()
        logger.info("ilink client started, QR content returned")
        return str(qr_content)

    def send_text(self, user_id: str, text: str) -> None:
        if self._client is None:
            raise RuntimeError("Client not started")
        self._client.sendText(user_id, text)

    def send_image(self, user_id: str, image_bytes: bytes, caption: str = "") -> None:
        if self._client is None:
            raise RuntimeError("Client not started")
        self._client.sendImage(user_id, image_bytes, "img.jpg", caption)

    def stop(self) -> None:
        """优雅停止 client（关闭长轮询）。"""
        # SDK 暂无显式 stop 方法，shutdownJVM 时自然清理
        # 后续 SDK 升级提供 stop 时在此调用
        pass
```

### 5.4 `remote/ilink/converters.py`：消息对象转换

```python
"""Java WeixinMessage/MessageItem ↔ Python dict 转换。"""
from typing import Any


def weixin_to_python(msg: Any) -> dict:
    """转换 com.github.wechat.ilink.sdk.core.model.WeixinMessage 为 dict。"""
    return {
        "message_id": int(msg.getMessage_id()) if msg.getMessage_id() else None,
        "message_type": int(msg.getMessage_type()) if msg.getMessage_type() else None,
        "from_user_id": str(msg.getFrom_user_id()),
        "to_user_id": str(msg.getTo_user_id()),
        "create_time_ms": int(msg.getCreate_time_ms()) if msg.getCreate_time_ms() else None,
        "context_token": str(msg.getContext_token()) if msg.getContext_token() else None,
        "items": [message_item_to_python(item) for item in (msg.getItem_list() or [])],
    }


def message_item_to_python(item: Any) -> dict:
    """转换 MessageItem，提取文本/图像/语音/视频内容。"""
    result = {"type": int(getattr(item, "getType", lambda: 0)() or 0)}
    if item.getText_item() is not None:
        result["text"] = str(item.getText_item().getText())
    if item.getImage_item() is not None:
        result["image"] = {"media": str(item.getImage_item().getMedia())}
    # 其他类型（voice/video/file）按需扩展
    return result
```

### 5.5 `remote/commands/base.py`：Command 抽象

```python
"""Command 抽象基类、上下文、结果。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CommandContext:
    """指令执行的上下文。"""
    user_id: str                         # 微信发送者 ID
    raw_text: str                        # 原始消息文本
    executor: Any                        # GameExecutor 实例（用于触发模板）
    template_manager: Any                # 模板管理器（用于查询可用模板）
    sender: Any                          # ILinkClient.send_text 回传通道
    state: dict = field(default_factory=dict)  # 共享状态（如当前 task_id）


@dataclass
class CommandResult:
    """指令执行结果。"""
    success: bool
    message: str = ""                    # 回传给用户的文本
    payload: Optional[dict] = None       # 结构化数据（日志/报告用）


class Command(ABC):
    """指令基类。每个具体指令（#run / #status / ...）实现一个子类。"""
    name: str = ""                       # 指令规范名（如 RUN_TEMPLATE）
    aliases: list[str] = []              # 别名（如 "run"、"执行"）
    description: str = ""
    usage: str = ""                      # 用法说明

    @abstractmethod
    def execute(self, ctx: CommandContext, args: str) -> CommandResult:
        """执行指令。args 是 #command 后面的所有文本（已 trim）。"""
        ...
```

### 5.6 `remote/commands/parser.py`：文本解析

```python
"""纯文本解析，与 Java 端逻辑解耦。"""
import re
from dataclasses import dataclass
from typing import Optional
from autogame_xcx.remote.commands.registry import CommandRegistry


@dataclass
class ParsedCommand:
    name: str                            # 解析后的规范指令名（如 RUN_TEMPLATE）
    args: str                            # 指令参数（"" 表示无参数）
    raw: str                             # 原始文本


class CommandParser:
    PREFIX = "#"

    def __init__(self, registry: CommandRegistry):
        self.registry = registry

    def parse(self, text: str) -> Optional[ParsedCommand]:
        if not text or not text.startswith(self.PREFIX):
            return None  # 不是指令，可能走 LLM
        body = text[len(self.PREFIX):].strip()
        if not body:
            return None
        parts = body.split(maxsplit=1)
        command_alias = parts[0]
        args = parts[1].strip() if len(parts) > 1 else ""
        canonical_name = self.registry.resolve_alias(command_alias)
        if canonical_name is None:
            return ParsedCommand(name="UNKNOWN", args=body, raw=text)
        return ParsedCommand(name=canonical_name, args=args, raw=text)
```

### 5.7 `remote/commands/registry.py`：注册表

```python
"""指令注册表 + 别名解析。"""
from typing import Optional
from autogame_xcx.remote.commands.base import Command


class CommandRegistry:
    def __init__(self):
        self._commands: dict[str, Command] = {}
        self._alias_to_name: dict[str, str] = {}

    def register(self, command: Command) -> None:
        self._commands[command.name] = command
        # 注册规范名本身作为别名（大小写不敏感）
        self._alias_to_name[command.name.lower()] = command.name
        for alias in command.aliases:
            self._alias_to_name[alias.lower()] = command.name

    def resolve_alias(self, alias: str) -> Optional[str]:
        return self._alias_to_name.get(alias.lower())

    def find(self, name: str) -> Optional[Command]:
        return self._commands.get(name)

    def all_commands(self) -> list[Command]:
        return list(self._commands.values())
```

### 5.8 `remote/commands/dispatcher.py`：分发

```python
"""分发指令到具体 Command 实现，结果回传微信。"""
import logging
from autogame_xcx.remote.commands.base import CommandContext, CommandResult
from autogame_xcx.remote.commands.registry import CommandRegistry
from autogame_xcx.exceptions import AutogameError

logger = logging.getLogger(__name__)


class CommandDispatcher:
    def __init__(self, registry: CommandRegistry):
        self.registry = registry

    def dispatch(self, ctx: CommandContext, parsed) -> CommandResult:
        if parsed.name == "UNKNOWN":
            return CommandResult(
                success=False,
                message=f"未知指令：{parsed.args}\n输入 #help 查看可用指令",
            )
        command = self.registry.find(parsed.name)
        if command is None:
            return CommandResult(success=False, message=f"指令未注册：{parsed.name}")
        try:
            result = command.execute(ctx, parsed.args)
            return result
        except AutogameError as e:
            logger.warning("Command %s failed: %s", parsed.name, e)
            return CommandResult(success=False, message=f"执行失败：{e}")
        except Exception as e:
            logger.exception("Command %s crashed", parsed.name)
            return CommandResult(success=False, message=f"内部错误：{e}")
```

### 5.9 `remote/scheduler/queue.py`：顺序执行

```python
"""单线程消费的指令队列，保证同一时刻只有一个 GameExecutor 实例在跑。
避免多个远程指令同时触发模板执行导致微信窗口操作冲突。"""
import threading
import logging
from collections import deque
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class CommandQueue:
    def __init__(self, consumer: Callable):
        """consumer: 接收 (user_id, parsed_cmd) 并执行。"""
        self._q: deque = deque()
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._running = True
        self._current: Optional[tuple] = None
        self._consumer = consumer
        self._worker = threading.Thread(target=self._loop, daemon=True, name="cmd-queue")

    def start(self) -> None:
        self._worker.start()

    def enqueue(self, user_id: str, parsed_cmd) -> int:
        """入队，返回当前队列长度（含本次）。"""
        with self._cv:
            self._q.append((user_id, parsed_cmd))
            length = len(self._q)
            self._cv.notify()
        logger.info("Enqueued command from %s, queue length=%d", user_id, length)
        return length

    def stop(self) -> None:
        with self._cv:
            self._running = False
            self._cv.notify_all()

    def _loop(self) -> None:
        while self._running:
            with self._cv:
                while self._running and not self._q:
                    self._cv.wait()
                if not self._running:
                    return
                self._current = self._q.popleft()
            user_id, parsed_cmd = self._current
            try:
                self._consumer(user_id, parsed_cmd)
            except Exception:
                logger.exception("Queue consumer crashed on %s", parsed_cmd)
            finally:
                self._current = None

    @property
    def queue_length(self) -> int:
        with self._lock:
            return len(self._q)

    @property
    def current_running(self) -> Optional[tuple]:
        return self._current
```

### 5.10 `remote/router.py`：消息路由

```python
"""消息路由：# 前缀走指令系统；非 # 走 LLM（后续阶段）。"""
import logging
from autogame_xcx.remote.commands.parser import CommandParser
from autogame_xcx.remote.scheduler.queue import CommandQueue
from autogame_xcx.remote.session import SessionManager

logger = logging.getLogger(__name__)


class MessageRouter:
    def __init__(
        self,
        parser: CommandParser,
        scheduler: CommandQueue,
        session: SessionManager,
        llm_orchestrator=None,  # 阶段 2.5 注入
    ):
        self.parser = parser
        self.scheduler = scheduler
        self.session = session
        self.llm_orchestrator = llm_orchestrator

    def route(self, user_id: str, text: str) -> None:
        if not self.session.is_allowed(user_id):
            logger.info("Ignored message from non-whitelisted user: %s", user_id)
            return
        if text.startswith("#"):
            parsed = self.parser.parse(text)
            if parsed is None:
                return
            self.scheduler.enqueue(user_id, parsed)
        else:
            # 后续阶段：交给 LLM orchestrator 拆解为指令队列
            if self.llm_orchestrator is None:
                logger.info("LLM not configured, ignored natural language from %s", user_id)
                return
            self.llm_orchestrator.handle_natural_language(user_id, text)
```

### 5.11 `remote/llm/orchestrator.py`：自然语言编排

> **阶段 2.5 实战修订**（详见 §2.5）：原 sketch 有 4 处偏差已修订：
> 1. 增加返回类型 `OrchestrationResult`（含 success / message / commands），便于单测断言
> 2. `_parse_and_validate` 走 `_extract_json_array` 容错（容忍 LLM 输出围栏 / 口水）
> 3. 白名单二次校验**整批拒绝**（任一项失败 → 全部不入队）
> 4. 单测用 `MockLlmProvider` 桩，不调真实 API

```python
"""自然语言 → 指令队列编排。
用户发"帮我把签到和领体力都做了"
  ↓ LLM 分析
LLM 拆解为 [#run 签到, #run 领体力]
  ↓ 顺序执行
汇总报告 → 微信回发
"""
import json
import logging
from dataclasses import dataclass

from autogame_xcx.remote.commands.parser import ParsedCommand
from autogame_xcx.remote.commands.registry import CommandRegistry
from autogame_xcx.remote.llm.prompt_templates import build_orchestration_prompt
from autogame_xcx.remote.llm.provider import LlmProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrchestrationResult:
    success: bool
    message: str
    commands: list[ParsedCommand]


class LLMOrchestrator:
    def __init__(
        self,
        provider: LlmProvider,
        registry: CommandRegistry,
        scheduler,
        sender,
    ) -> None:
        self.provider = provider
        self.registry = registry
        self.scheduler = scheduler
        self.sender = sender

    def handle_natural_language(
        self, user_id: str, text: str
    ) -> OrchestrationResult:
        """编排 + 校验 + 入队 + 回执；返回 OrchestrationResult 用于断言。"""
        messages = build_orchestration_prompt(text, self.registry.all_commands())
        try:
            raw_response = self.provider.chat(messages)
        except Exception as e:
            logger.exception("LLM provider.chat crashed")
            return self._fail(user_id, f"AI 调用失败：{e}", [])

        commands, parse_error = self._parse_and_validate(raw_response)
        if parse_error is not None:
            logger.warning("LLM response rejected: %s; raw_head=%r",
                           parse_error, raw_response[:200])
            return self._fail(user_id, parse_error, [])

        if not commands:
            return self._fail(user_id,
                              "未能理解您的请求；输入 #help 查看可用指令", [])

        for cmd in commands:
            try:
                self.scheduler.enqueue(user_id, cmd)
            except Exception as e:
                logger.exception("scheduler.enqueue crashed")
                return self._fail(user_id, f"指令入队失败：{e}", [])

        msg = f"已为您规划 {len(commands)} 个指令，正在顺序执行..."
        self._reply(user_id, msg)
        return OrchestrationResult(success=True, message=msg, commands=list(commands))

    def _parse_and_validate(
        self, raw_response: str
    ) -> tuple[list[ParsedCommand], str | None]:
        """解析 + 白名单校验；任一项失败整批拒绝。"""
        json_str = _extract_json_array(raw_response)
        if json_str is None:
            return [], "AI 输出格式异常（未找到 JSON 数组），请改用 # 指令"
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return [], f"AI 输出 JSON 解析失败：{e}"
        if not isinstance(data, list):
            return [], "AI 输出应为 JSON 数组"

        commands: list[ParsedCommand] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                return [], f"AI 输出第 {i + 1} 项不是对象"
            action = item.get("action")
            args = item.get("args", "")
            if not isinstance(action, str) or not action.strip():
                return [], f"AI 输出第 {i + 1} 项缺少 action 字段"
            if not isinstance(args, str):
                return [], f"AI 输出第 {i + 1} 项 args 必须是字符串"
            canonical = self.registry.resolve_alias(action)
            if canonical is None:
                return [], f"AI 输出指令不在白名单：#{action}"
            commands.append(ParsedCommand(
                name=canonical, args=args, raw=f"#{action} {args}".strip(),
            ))
        return commands, None

    def _fail(self, user_id, message, commands) -> OrchestrationResult:
        self._reply(user_id, message)
        return OrchestrationResult(success=False, message=message, commands=commands)

    def _reply(self, user_id: str, text: str) -> None:
        try:
            self.sender.send_text(user_id, text)
        except Exception:
            logger.exception("Failed to send reply to %s", user_id)


def _extract_json_array(text: str) -> str | None:
    """从 LLM 文本中抽取首个 JSON 数组（容错：剥离围栏、取首 [ 末 ]）。"""
    text = (text or "").strip()
    if not text:
        return None
    if text.startswith("```"):  # 剥离 Markdown 围栏
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]
```

### 5.12 `remote/commands/definitions/run_template.py`：示例指令

> **阶段 2.3 实战修订**：原假设的 `template_manager.find_by_name()` / `list_names()` 在现有 `core/template_manager.py` 中**不存在**。实际可用 API：
> - `manager.list_templates()` → `list[dict]`，元素含 `{filename, filepath, name, version, game_name, created_time}`
> - `executor.execute_template(filepath)` → `bool`
> - `executor.execution_report` → `dict`（含 start_time/end_time/tasks/summary）
>
> 下面的示例已改用真实 API。`_find_template_by_name()` 是本指令私有辅助，从 `list_templates()` 结果按 name 过滤。

```python
"""#run <模板名>：触发本地模板执行。"""
from autogame_xcx.remote.commands.base import Command, CommandContext, CommandResult


class RunTemplateCommand(Command):
    name = "RUN_TEMPLATE"
    aliases = ["run", "执行", "运行"]
    description = "触发指定模板的自动化执行"
    usage = "#run <模板名>  例如：#run 签到"

    def execute(self, ctx: CommandContext, args: str) -> CommandResult:
        template_name = args.strip()
        if not template_name:
            return CommandResult(success=False, message="用法：" + self.usage)
        # 用现有 list_templates() 按 name 过滤（find_by_name 在源码中不存在）
        match = _find_template_by_name(ctx.template_manager, template_name)
        if match is None:
            available = [t["name"] for t in ctx.template_manager.list_templates()]
            return CommandResult(
                success=False,
                message=f"模板不存在：{template_name}\n可用模板：{', '.join(available) or '(无)'}",
            )
        # 触发执行（execute_template 返回 bool）
        ctx.sender.send_text(ctx.user_id, f"开始执行模板：{template_name}")
        success = ctx.executor.execute_template(match["filepath"])
        if success:
            summary = ctx.executor.execution_report.get("summary", {})
            return CommandResult(
                success=True,
                message=(
                    f"模板执行完成：{template_name}\n"
                    f"任务 {summary.get('completed', 0)}/{summary.get('total_tasks', 0)} 成功 "
                    f"（成功率 {summary.get('success_rate', '?')}）"
                ),
                payload={"template": template_name, "filepath": match["filepath"]},
            )
        return CommandResult(success=False, message=f"模板执行失败：{template_name}")


def _find_template_by_name(manager, name: str):
    """从 manager.list_templates() 按 name 精确匹配。"""
    for t in manager.list_templates():
        if t["name"] == name:
            return t
    return None
```

---

## 6. 迁移路径（分 6 阶段）

### 阶段 2.1：JPype Spike（半天）✅ 已完成（2026-06-15）

**目标**：验证 JPype1 在 Python 3.13 + Windows 环境下能正常启动 JVM 并加载 ilink SDK jar。

**动作**：
1. `uv add jpype1`（实际版本 1.7.1）
2. 从 `D:\IDEAGithubWork\wechat-ilink\wechat-ilink-sdk-java\target\` 取构建好的 jar（先 `mvn package`）
3. **必须**额外跑 `mvn dependency:copy-dependencies -DoutputDirectory=target/dependency -DincludeScope=runtime` 拷 14 个依赖 jar（详见 §2.4 Spike 发现）
4. spike 脚本：`scripts/spike_jpype_ilink.py`（不在 `tests/` 下，因为 `.gitignore` 屏蔽了 `tests/`）
5. spike 验证项（不下到 executeLogin，不触发网络请求）：
   - JVM 启动 + jvm.dll 自动探测
   - 14 个 jar 加载到 classpath
   - `JClass` 访问 4 个关键类（ILinkClient / ILinkClientBuilder / OnMessageListener / WeixinMessage）
   - `@JImplements` 实现 OnMessageListener（**API 名带 s**）
   - `ILinkClient.builder().onMessage(listener).build()` 链式构造
   - `client.getConfig()` 不发请求验证
   - `client.close()` + `jpype.shutdownJVM()` 优雅退出

**验证结果**：17/17 项检查通过，输出 `SPIKE PASSED`。

**实际发现**：见 §2.4 Spike 实战发现。

### 阶段 2.2：消息接收通道（1~2 天）

**目标**：Python 能通过 SDK 接收微信消息并通过 pyqtSignal 暴露给上层（GUI / 调度器订阅）。本阶段不集成到主 GUI（那是阶段 2.6 的事），仅产出独立可运行的 demo 脚本验证完整链路。

**动作**：
1. 实现 `remote/ilink/jvm.py`（JVMManager + find_jvm_dll，按 §5.1 修订后的版本）
2. 实现 `remote/ilink/converters.py`（WeixinMessage / MessageItem → Python dict）
3. 实现 `remote/ilink/message_listener.py`（PythonMessageListener + `_SignalCarrier`，按 §5.2 + §2.4 发现 4）
4. 实现 `remote/ilink/login_listener.py`（PythonLoginListener，处理 onLoginSuccess / onLoginFailure）
5. 实现 `remote/ilink/client.py`（ILinkClient Python 门面，start/send_text/stop）
6. 写 `scripts/demo_remote_listen.py`：启动 JVM → 执行登录 → 显示二维码（控制台 base64 或落盘）→ 监听消息 → 控制台打印

**验证（不实测扫码场景，留待用户提供测试号）**：
- `python scripts/demo_remote_listen.py --dry-run`：仅启动 JVM + 构造 client + 优雅关闭（不下到 executeLogin），验证模块装配无 import 错误
- `python scripts/demo_remote_listen.py`：实际跑 executeLogin，扫码登录后从手机发消息，控制台打印 `收到：xxx from <user_id>`
- `data/logs/autogame.log` 记录所有收到的消息

**已完成依赖**：阶段 2.1 spike 脚本（`scripts/spike_jpype_ilink.py`）已验证 JVM/类加载/`@JImplements` 实现，本阶段复用 spike 的 `find_jvm_dll` 实现。

### 阶段 2.3：基础指令系统（1~2 天）

**目标**：5 个基础指令可用，远程触发本地模板执行。

**动作**：
1. 实现 `remote/commands/base.py`（Command 抽象）
2. 实现 `remote/commands/registry.py`（注册表）
3. 实现 `remote/commands/parser.py`（解析器）
4. 实现 `remote/commands/dispatcher.py`（分发）
5. 实现 5 个具体指令：
   - `#run <模板名>` → 触发 `GameExecutor.execute_template`
   - `#list` → 列出可用模板（调 `TemplateManager.list_names`）
   - `#status` → 查询当前执行状态
   - `#stop` → 停止当前任务
   - `#report <task_id>` → 查询报告（调 `ReportGenerator`）
6. 实现 `remote/session.py`（用户白名单）
7. 实现 `remote/router.py`（消息路由）

**验证**：
- 手机发 `#list`，Python 回发可用模板列表
- 手机发 `#run 签到模板`，本地执行，执行完回发"签到完成"
- 非白名单用户发消息被忽略

### 阶段 2.4：指令调度器（1 天）

**目标**：多指令顺序执行，避免窗口冲突。

**动作**：
1. 实现 `remote/scheduler/queue.py`（CommandQueue 单线程消费）
2. 实现 `remote/scheduler/state.py`（执行状态机）
3. router 中接入 scheduler，所有指令经队列消费
4. 指令开始/结束时通过 `sender.send_text` 通知用户

**验证**：
- 连续发 3 个 `#run` 指令，依次执行不冲突
- `#status` 能返回当前正在执行的指令 + 队列剩余数量

### 阶段 2.5：大模型编排（2~3 天，可独立迭代）✅ 已完成（2026-06-16）

**目标**：自然语言指令被 LLM 拆解为指令队列。

**动作**：
1. ✅ 实现 `remote/llm/provider.py`（抽象 `LlmProvider` Protocol + `MockLlmProvider` 桩）
2. ✅ 实现 `remote/llm/anthropic_provider.py`（Claude，可选依赖 `anthropic` 包）
3. ✅ 实现 `remote/llm/openai_provider.py`（OpenAI 兼容，可选依赖 `openai` 包）
4. ✅ 实现 `remote/llm/prompt_templates.py`（含可用指令清单 + JSON 输出格式约束 + 示例）
5. ✅ 实现 `remote/llm/orchestrator.py`（编排 + JSON 容错解析 + 白名单二次校验 + 整批拒绝）
6. ✅ router 中接入 orchestrator，非 `#` 消息转 LLM（`router.llm_orchestrator` 已预留钩子）

**验证（已完成）**：
- ✅ 单元测试：`uv run pytest tests/unit/test_remote_llm.py` — 29/29 通过
- ✅ 演示脚本：`uv run python scripts/demo_remote_llm.py` — 24/24 通过（6 场景：happy path / 越权拒绝 / 乱码拒绝 / Markdown 围栏容错 / router 集成 / provider 异常隔离）

**验证（用户配置 API key 后手动跑真实链路）**：
- 安装 optional 依赖：`uv pip install autogame-xcx[llm]`
- 配置 `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY`
- 在 `scripts/demo_remote_llm.py` 末尾加一段：把 `MockLlmProvider` 换成真实 provider，跑同样的场景
- 手机发"帮我把签到和领体力都做了"，LLM 拆解为 `[#run 签到, #run 领体力]`，依次执行后回发汇总
- 手机发含未知动作的自然语言，orchestrator 整批拒绝并回执"AI 输出指令不在白名单"

### 阶段 2.6：GUI 集成与稳定性（1 天）

**目标**：远程驱动完整集成到 GUI，关闭时优雅退出。

**动作**：
1. 实现 `ui/dialogs/remote_status.py`（连接状态指示灯 + 二维码显示）
2. 实现 `ui/dialogs/command_console.py`（指令执行日志，线程安全显示）
3. 在 `MainGUI` 添加"远程驱动"菜单项
4. `QApplication.aboutToQuit` 信号触发 `client.stop()` + `jvm.shutdown()`
5. 白名单配置 UI（持久化到 `config/remote.yaml`）

**验证**：
- GUI 中"远程驱动"菜单可打开配置面板
- 关闭 GUI 后 `tasklist | findstr java` 输出为空（JVM 干净退出）
- 启动时如未配置远程，不阻塞 GUI

---

## 7. 关键风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| JVM 启动慢（1~2s）阻塞 GUI 主线程 | UI 卡顿 | JVM 在独立 QThread 启动，启动信号通过 pyqtSignal 回主线程 |
| OnMessageListener 在 JVM 线程回调 | 直接操作 QWidget 崩溃 | pyqtSignal 转主线程，listener 仅做 emit |
| SDK 长轮询阻塞 JVM 关闭 | GUI 退出挂起 | `aboutToQuit` 信号触发 `client.stop` → `jpype.shutdownJVM` |
| Python 3.13 + JPype 兼容性问题 | import 失败 | ✅ Spike 已验证（jpype1 1.7.1 + Python 3.13 通过） |
| 微信账号封禁（机器人行为特征） | 账号失效 | 用专用测试号；控制消息频率；模拟真人节奏（消息间隔 800~2500ms 随机） |
| 远程指令注入（任意人发消息触发自动化） | 安全风险 | 用户白名单（from_user_id 校验）；指令权限分级（admin / user） |
| ilink SDK 升级破坏 Python 集成 | 调用失败 | SDK 版本锁定到 `config/ilink.py`；启动时探测版本不匹配告警 |
| 同一窗口并发执行（多指令并发触发） | 自动化混乱 | CommandQueue 单线程消费，强制串行 |
| LLM 拆解指令失败/越界 | 执行错误指令 | LLM 输出 JSON 容错解析（`_extract_json_array`）+ 白名单二次校验 + **整批拒绝**策略（详见 §2.5 发现 1/2、§5.11） |
| SDK jar 路径错误或缺失 | 启动崩溃 | `JVMManager.start` 显式检查 jar 存在，缺失时报清晰错误 |
| Java 异常丢失堆栈 | 调试困难 | `send_text` 等方法外层 try/except，把 `java.lang.Throwable` 转为 `AutogameError` 并保留 cause |
| SDK 内部 AWT 线程与 PyQt6 冲突 | GUI 死锁 | JVM 启动参数加 `-Djava.awt.headless=true`（SDK 不需要 GUI） |
| 失败指令重复触发（用户重发） | 资源浪费 | 短时间内相同指令去重（基于 user_id + command_hash） |
| **ilink jar 单独加载缺依赖**（Spike 发现） | `NoClassDefFoundError: org/slf4j/LoggerFactory` | `JVMManager.start` 把 `deps_dir/*.jar` 全部加入 classpath（详见 §2.4 发现 2、§5.1） |
| **JAVA_HOME 未设导致找不到 jvm.dll**（Spike 发现） | `JVMNotFoundException` | `find_jvm_dll()` 三级 fallback：JAVA_HOME → `java -XshowSettings` → 默认（§5.1） |
| **Python `isinstance`/`is` 在 JPype 桥接失效**（Spike 发现） | listener 注册校验误报失败 | 用 Java 反射 `class_.isInstance()` / `hashCode()` 比较（§2.4 发现 4） |

---

## 8. 依赖工具链

| 工具 | 版本 | 用途 | 阶段 |
|---|---|---|---|
| jpype1 | >=1.5 | Python 调 Java 的核心库 | 2.1 |
| JDK | 17+ | JVM（用户机预装） | 2.1 |
| wechat-ilink-sdk-java jar | 跟随上游 | 远程通信 SDK（从 ilink 项目取或 mvn install） | 2.1 |
| anthropic | >=0.40 | Claude API SDK（阶段 2.5 二选一；**optional**，需 `uv pip install autogame-xcx[llm]`） | 2.5 |
| openai | >=1.50 | OpenAI 兼容 API SDK（阶段 2.5 二选一；**optional**，同上） | 2.5 |
| PyInstaller | >=6.0 | 打包含 jar（`--add-data "lib/ilink-sdk.jar;lib"`） | 发布 |

> **阶段 2.5 实战发现**：`anthropic` / `openai` 不进核心 `[project].dependencies`，而是放 `[project.optional-dependencies].llm`——避免所有用户都被迫安装 ~50MB SDK。详见 §2.5 发现 3。

---

## 9. 验证方式

| 阶段 | 命令 | 预期 |
|---|---|---|
| 2.1 | `uv run python tests/manual/test_jpype_spike.py` | 输出 `JVM started, currentTimeMillis=...` |
| 2.2 | `uv run autogame-gui` 启动后扫码，手机发 `#test` | GUI 显示 `收到：#test from <user_id>` |
| 2.3 | `uv run pytest tests/unit/test_remote_commands.py tests/unit/test_remote_parser.py tests/unit/test_remote_registry.py tests/unit/test_remote_session.py tests/unit/test_remote_router.py` | 全部通过（42 用例） |
| 2.3 | 手机发 `#list` | Python 回发可用模板列表 |
| 2.3 | 手机发 `#run 签到模板` | 本地执行签到，完成后回发"签到完成：金币+100" |
| 2.4 | `uv run python scripts/demo_remote_scheduler.py` | 输出 24/24 checks passed |
| 2.4 | 连发 3 个 `#run` | `#status` 返回 "队列中：2，正在执行：第1个" |
| 2.5 | `uv run pytest tests/unit/test_remote_llm.py` | 29/29 通过（含 prompt / mock / orchestrator 解析+校验 / router 集成） |
| 2.5 | `uv run python scripts/demo_remote_llm.py` | 24/24 checks passed（6 场景，用 MockLlmProvider 不调真实 API） |
| 2.5 | 手机发"帮我把签到和领体力做了"（用户配置 API key 后真实链路） | LLM 拆解为 2 个指令顺序执行，完成后回发汇总报告 |
| 2.6 | 关闭 GUI | `tasklist \| findstr java` 输出为空（JVM 干净退出） |

---

## 10. 与方向 1/3 的关系

- **依赖方向 1**：包结构稳定后才好引入 `remote/` 包。方向 1 完成前启动会反复触发 import 重构。
- **正交于方向 3**：方向 3 升级"本地执行能力"（协议策略），方向 2 提供"远程触发通道"。两者协同：远程指令（`#run`）触发执行，执行内部可走图像或协议策略。
- **LLM 编排（阶段 2.5）可独立迭代**：不阻塞核心远程驱动链路，可后期补充。
