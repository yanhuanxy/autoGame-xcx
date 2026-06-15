# PLAN_03：协议化接入（H5 + Canvas 游戏）

> 项目：`wechat-link-autogame-xcx`
> 方向：从图像识别升级为协议直连 + JS 注入，针对微信小程序内的 H5 + Canvas 渲染游戏
> 预计周期：7 阶段 = 约 3~6 周
> 前置依赖：方向 1 完成（包结构稳定）

---

## 1. Context（为什么做）

当前项目是"截图 + 图像匹配 + 鼠标点击"的**外部黑盒自动化**，根本局限：

- **延迟下限**：图像匹配 ~300ms/步，OCR 单次推理 1~3s，无法做"毫秒级响应"（如 BOSS 技能闪避）
- **能力盲区**：游戏内部数据（CD、伤害数值、物品掉落）无法直接读取，只能 OCR 反推，错误率高
- **抗干扰弱**：游戏任何 UI 改版（按钮移动、字体变化、动画帧）都会让模板失效
- **资源消耗大**：每秒多次截图 + 图像匹配，CPU/内存占用高

如果游戏是微信小程序内的 **H5 + Canvas 渲染**游戏，那么**底层必然依赖 HTTP/WebSocket 协议**——前端画 Canvas，后端返回游戏状态。**协议化**就是绕过 UI 直接与服务器对话。

### 1.1 目标游戏特性（Canvas 关键影响）

| 维度 | 传统 DOM 游戏 | **Canvas 游戏（本项目目标）** |
|---|---|---|
| UI 元素可见性 | HTML 元素可被 DevTools 检查 | **整个画面是位图，DOM 层看不到游戏内 UI** |
| 传统 H5 自动化（Selenium/Puppeteer） | 可用 | **完全失效**——无法 click Canvas 内部按钮 |
| 图像识别可行性 | 可行但通常没必要 | 可行（当前项目能力），但慢且对画面变化敏感 |
| **协议直连价值** | 中等 | **极高**——Canvas 渲染使得"协议"几乎是唯一高效自动化路径 |
| **JS 层 Hook 价值** | 中等 | **极高**——所有绘制必经 `fillText/drawImage`，可截获文本/图像/坐标 |

**结论**：Canvas 渲染**不影响协议层**（HTTP/WS 通信依然存在），但**大幅扩展了逆向手段**——除了协议直连，还能通过 JS 注入 Hook Canvas API 拿到精确数据。

### 1.2 法律与合规警示

⚠️ **协议化逆向存在法律风险**：
- 可能违反游戏服务条款（ToS）
- 可能违反《计算机信息网络国际联网安全保护管理办法》
- 商业化运营可能涉及刑事责任

**本项目承诺**：
- 仅用于个人技术研究与学习
- 不公开发布逆向工具
- 不商业化运营
- 保留免责声明
- 优先寻求厂商授权合作

---

## 2. 现状盘点

### 2.1 当前能力（方向 1 完成后）

| Python 资产 | 路径 | 用途 |
|---|---|---|
| `ImageMatcher` | `core/matcher.py` | 5 种图像匹配算法 |
| `GameExecutor` | `core/executor.py` | 触发模板执行 |
| `DGOCR` | `ocr/dgocr/` | 文字识别 |
| `GameWindowController` | `platform/window_controller.py` | 微信窗口控制 |

### 2.2 能力缺口

| 缺口 | 解决方案 |
|---|---|
| 无网络通信层 | 新增 `protocol/` 包（httpx + websockets） |
| 无加密算法实现 | 新增 `protocol/crypto/`（Hook 后 Python 复刻） |
| 无协议客户端 | 新增 `protocol/client.py` + `packet/` |
| 无 JS 注入能力 | 新增 `js_inject/` 包（CDP + 注入脚本） |
| 无逆向工具 | 新增 `reverse/` 包（mitmproxy/frida 脚本 + 反编译笔记） |
| 无风控对抗 | 新增 `anti_detect/` 包（rate_limiter + 行为模拟） |
| 无策略抽象 | 新增 `core/execution_strategy.py`（Strategy Pattern） |

---

## 3. 协议栈与渲染层分析

```
┌─────────────────────────────────────────────────────────────┐
│  [微信小程序容器]                                           │
│    └─ [小程序前端 JS / wxapkg 解包后]                       │
│         │                                                   │
│         ├─ 网络通信层 ← 抓包目标（mitmproxy）                │
│         │   ├─ HTTP/HTTPS API（登录/配置/资源）              │
│         │   └─ WebSocket（实时战斗/消息推送）                │
│         │       └─ TLS 1.2/1.3                              │
│         │           └─ 业务加密（sign/token/aes）           │
│         │               └─ 业务协议（json/protobuf/自定义） │
│         │                                                   │
│         └─ Canvas 渲染层 ← JS Hook 目标                     │
│             ├─ ctx.fillText(text, x, y)  → 文本数据         │
│             ├─ ctx.drawImage(img, ...)   → 图像资源 URL     │
│             ├─ ctx.setTransform/translate → 变换矩阵        │
│             ├─ canvas.onclick/onTouch     → 点击坐标        │
│             └─ fetch / WebSocket.send     → 原始网络包      │
│                 （在加密前/解密后拦截，避开 SSL Pinning）    │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 关键观察

1. **协议层与渲染层并行存在**：抓包拿加密流量，JS Hook 拿明文流量，二者互补
2. **Canvas Hook 能拿到 OCR 拿不到的东西**：CD 时间戳、伤害数值、内部 ID
3. **网络 Hook 在加密前拦截**：如果加解密在 JS 层（小程序常见），直接拿明文，避开逆向加密算法
4. **灰盒路径**：如果游戏暴露 `window.GameAPI`，可直接调内部函数，绕过 UI 与网络

---

## 4. 四条候选逆向路径

### 4.1 路径对比

| 路径 | 难度 | 数据精度 | 风控对抗 | 开发成本 | 适用阶段 |
|---|---|---|---|---|---|
| **A. 纯协议直连** | ★★★★ | 100%（直读服务器数据） | 需深度伪造（指纹/频率） | 高 | 终极目标 |
| **B. JS 注入 + Canvas Hook** | ★★★ | 高（fillText 直读文本） | 中等 | 中 | **推荐先做** |
| **C. 图像识别 + Canvas 文本截获**（混合） | ★★ | 中（受分辨率影响） | 低 | 低 | 与现有能力对接 |
| **D. JS 直接调游戏内部函数**（灰盒） | ★★★★★ | 100% | 高（在游戏上下文执行） | 极高 | 进阶 |

### 4.2 推荐策略

**先 B 后 A，C 作为兜底**：
1. **B（JS 注入）先做**：难度可控、能拿到游戏内文本与原始网络包（含加密前后对比）
2. **B 的产出喂给 A**：通过 hook_network.js 拿到的"加密前后明文对照"极大降低加密算法逆向难度
3. **C 持续保留**：现有图像识别能力作为 fallback，协议/Hook 失效时降级
4. **D 视情况**：如果游戏在 window 上暴露 API（部分 H5 游戏会），值得投入

### 4.3 路径间产出关系

```
[B. JS 注入]
  ├─→ hook_network.js → 网络明文 → [A. 协议直连] 准备数据
  ├─→ hook_canvas.js  → 游戏文本/坐标 → 独立可用的 JsInjectStrategy
  └─→ hook_game_api.js → window.GameAPI → [D. 灰盒调用]

[A. 协议直连]
  └─→ ProtocolBasedStrategy（终极方案）

[C. 图像识别]（现有）
  └─→ ImageBasedStrategy（fallback）
```

---

## 5. 目标目录结构（在方向 1 基础上增量）

```
src/autogame_xcx/
├── core/
│   ├── execution_strategy.py              # ★ 新增：ExecutionStrategy 抽象基类
│   │   # ImageBasedStrategy（封装现有 GameExecutor 逻辑）
│   │   # ProtocolBasedStrategy（新增，路径 A）
│   │   # JsInjectStrategy（新增，路径 B）
│   └── executor.py                        # GameExecutor 改为持有 StrategyContext
│
├── protocol/                              # ★ 新增：协议层（路径 A）
│   ├── __init__.py
│   ├── client.py                          # ProtocolClient（统一 login/send/subscribe）
│   ├── http_client.py                     # httpx async 封装（登录态、重试、限流）
│   ├── ws_client.py                       # websockets 封装（心跳、重连、消息分发）
│   ├── crypto/                            # 加密算法（Hook 后 Python 复刻）
│   │   ├── __init__.py
│   │   ├── sign.py                        # 请求签名（HMAC-MD5 / AES / 自定义）
│   │   ├── token.py                       # token 刷新逻辑
│   │   └── keys.py                        # 密钥管理（从 Hook 提取）
│   ├── packet/                            # 数据包定义（按业务域分组）
│   │   ├── __init__.py
│   │   ├── base.py                        # Packet 基类（seq / endpoint / serialize）
│   │   ├── auth.py                        # 登录/心跳/会话包
│   │   ├── combat.py                      # 战斗相关包
│   │   └── inventory.py                   # 背包/物品包
│   ├── codec.py                           # JSON/Protobuf/自定义二进制编解码
│   └── fingerprint.py                     # 客户端指纹伪造（device_id / version / sdk_int）
│
├── js_inject/                             # ★ 新增：JS 注入与 Canvas Hook（路径 B/D）
│   ├── __init__.py
│   ├── bridge.py                          # 与小程序 WebView 的桥接（CDP / 微信开发者工具）
│   ├── scripts/                           # 注入到游戏 WebView 的 JS 脚本（作为资源加载）
│   │   ├── hook_canvas.js                 # Hook fillText/drawImage/setTransform
│   │   ├── hook_network.js                # Hook fetch/XMLHttpRequest/WebSocket
│   │   ├── hook_game_api.js               # 定位并暴露游戏内部函数（路径 D）
│   │   └── rpc.js                         # Python ↔ JS 双向 RPC（postMessage/CDP）
│   ├── canvas_extractor.py                # 从 Hook 数据重建"虚拟 DOM"（文本+坐标）
│   └── game_state.py                      # 从 JS 推送的状态对象（比 OCR 精确）
│
├── reverse/                               # ★ 新增：逆向工程辅助（不进生产构建）
│   ├── __init__.py
│   ├── mitmproxy_scripts/                 # mitmproxy addon 脚本
│   │   ├── capture_flow.py                # 自动捕获 + 分类请求
│   │   └── replay.py                      # 流量回放
│   ├── frida_scripts/                     # Frida JS 脚本
│   │   ├── hook_crypto.js                 # Hook AES/HMAC 等加密函数
│   │   ├── hook_sign.js                   # Hook 请求签名入口
│   │   └── dump_keys.js                   # Dump 内存中的密钥
│   ├── wxapkg_unpacker_notes.md           # 小程序解包笔记
│   └── decompile_notes/                   # 反编译笔记（MD 格式）
│       ├── api_endpoints.md               # 接口列表
│       ├── sign_algorithm.md              # 签名算法说明
│       ├── packet_format.md               # 包格式说明
│       └── canvas_draw_calls.md           # Canvas 绘制调用映射
│
├── anti_detect/                           # ★ 新增：风控对抗（谨慎使用）
│   ├── __init__.py
│   ├── rate_limiter.py                    # 频率限制（模拟人类操作间隔）
│   ├── jitter.py                          # 时间抖动（避免规律性）
│   ├── behavior_simulator.py              # 行为模式模拟
│   └── proxy_pool.py                      # 代理 IP 池（可选）
│
└── ui/
    └── dialogs/
        └── strategy_selector.py           # ★ 新增：策略切换 UI（图像/协议/JS 注入）
```

### 5.1 模块职责边界

| 模块 | 职责 | 禁止 |
|---|---|---|
| `core/execution_strategy.py` | 策略抽象与切换 | 业务实现细节 |
| `protocol/` | 协议直连（路径 A） | 直接操作 UI |
| `js_inject/` | JS 注入与 Canvas Hook（路径 B/D） | 直接操作 UI |
| `reverse/` | 逆向辅助工具与笔记 | 进入生产构建（仅开发时使用） |
| `anti_detect/` | 风控对抗 | 业务知识 |

### 5.2 依赖方向

```
ui  →  core (execution_strategy)
       ↓
       ImageBasedStrategy   →  core (matcher) + platform (window_controller)
       ProtocolBasedStrategy →  protocol/ + anti_detect/
       JsInjectStrategy     →  js_inject/ + anti_detect/
```

---

## 6. 关键模块设计

### 6.1 `core/execution_strategy.py`：策略抽象

```python
"""把 GameExecutor 的"执行一个任务"抽象为可替换的策略。
现有图像执行逻辑封装为 ImageBasedStrategy；协议执行为 ProtocolBasedStrategy；
JS 注入执行为 JsInjectStrategy。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class StepResult:
    success: bool
    score: float = 0.0
    error: Optional[str] = None
    payload: Optional[dict] = None


class ExecutionStrategy(ABC):
    """执行策略抽象基类。"""

    @abstractmethod
    def initialize(self, template: dict) -> bool:
        """初始化策略（图像策略查找窗口；协议策略登录游戏；JS 策略注入脚本）。"""
        ...

    @abstractmethod
    def execute_step(self, step: dict, context: dict) -> StepResult:
        """执行单步。"""
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """清理资源。"""
        ...


class ImageBasedStrategy(ExecutionStrategy):
    """现有 GameExecutor.execute_step 的逻辑搬到这里，算法逐字保留。"""
    def __init__(self, matcher, window_controller):
        self.matcher = matcher
        self.window = window_controller

    def initialize(self, template):
        return self.window.find_and_activate()

    def execute_step(self, step, context):
        # 截图 + 匹配 + 点击（与现有 GameExecutor.execute_step 一致）
        ...


class ProtocolBasedStrategy(ExecutionStrategy):
    """协议化执行策略。"""
    def __init__(self, protocol_client):
        self.client = protocol_client

    def initialize(self, template):
        return self.client.login()

    def execute_step(self, step, context):
        action_map = {
            "combat_attack": lambda s: self.client.send(packet.combat.Attack(target=s["target_id"])),
            "inventory_use_item": lambda s: self.client.send(packet.inventory.UseItem(item_id=s["item_id"])),
        }
        handler = action_map.get(step.get("protocol_action"))
        if not handler:
            return StepResult(success=False, error=f"unknown protocol action: {step.get('protocol_action')}")
        resp = handler(step)
        return StepResult(success=resp.ok, payload=resp.data)


class JsInjectStrategy(ExecutionStrategy):
    """JS 注入执行策略（路径 B）。通过 Canvas Hook 定位元素 + JS RPC 触发点击。"""
    def __init__(self, bridge, canvas_extractor):
        self.bridge = bridge
        self.extractor = canvas_extractor

    def initialize(self, template):
        return self.bridge.inject_script("hook_canvas.js")

    def execute_step(self, step, context):
        # step 示例：{"js_action": "click_text", "pattern": "签到"}
        action = step.get("js_action")
        if action == "click_text":
            ok = self.extractor.click_text(step["pattern"])
            return StepResult(success=ok)
        # 其他 action...
        return StepResult(success=False, error=f"unknown js_action: {action}")


class StrategyContext:
    """GameExecutor 持有此对象，根据配置切换策略。"""
    def __init__(self, strategy: ExecutionStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: ExecutionStrategy):
        if self._strategy:
            self._strategy.shutdown()
        self._strategy = strategy

    def initialize(self, template):
        return self._strategy.initialize(template)

    def execute_step(self, step, context):
        return self._strategy.execute_step(step, context)
```

### 6.2 `protocol/client.py`：协议客户端

```python
"""统一对外暴露 login/send/subscribe 接口，内部组合 HttpClient + WsClient。"""
import asyncio
from typing import Callable
from autogame_xcx.protocol.http_client import HttpClient
from autogame_xcx.protocol.ws_client import WsClient
from autogame_xcx.protocol.crypto.sign import Signer
from autogame_xcx.config.protocol import ProtocolConfig


class ProtocolClient:
    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.http = HttpClient(config.http)
        self.ws = WsClient(config.ws)
        self.crypto = Signer(config.crypto)
        self._seq = 0
        self._session = None

    async def login(self) -> bool:
        # 1. 获取验证码 / 设备指纹
        # 2. 用账号密码 + 加密签名请求登录接口
        # 3. 拿到 token，存入 session
        # 4. 建立 WebSocket 长连接（接收推送事件）
        ...

    async def send(self, packet) -> dict:
        self._seq += 1
        signed = self.crypto.sign(packet.serialize(), seq=self._seq)
        if packet.transport == "http":
            response = await self.http.post(packet.endpoint, data=signed)
        else:
            response = await self.ws.send(packet.endpoint, data=signed)
        return packet.parse_response(response)

    async def subscribe(self, event: str, handler: Callable):
        """订阅服务器推送事件（例如 BOSS 刷新）。"""
        await self.ws.subscribe(event, handler)

    async def close(self):
        await self.ws.close()
        await self.http.close()
```

### 6.3 `protocol/crypto/sign.py`：签名算法

```python
"""把 Frida Hook 出来的签名算法用 Python 复刻。
这里只是骨架，实际算法需要根据 reverse/decompile_notes/sign_algorithm.md 实现。"""
import hashlib
import hmac
from typing import Optional


class Signer:
    def __init__(self, secret: bytes, algorithm: str = "hmac-md5"):
        self.secret = secret
        self.algorithm = algorithm

    def sign(self, payload: bytes, salt: Optional[bytes] = None) -> str:
        if self.algorithm == "hmac-md5":
            data = payload + (salt or b"")
            return hmac.new(self.secret, data, hashlib.md5).hexdigest()
        elif self.algorithm == "aes-ecb":
            # 实际可能更复杂（参考反编译笔记）
            raise NotImplementedError("AES 复刻需参考反编译笔记")
        else:
            raise ValueError(f"unsupported algorithm: {self.algorithm}")
```

### 6.4 `js_inject/scripts/hook_canvas.js`：核心 Canvas Hook

```javascript
// 截获所有文本绘制——比 OCR 准确，能拿到游戏内部状态字符串
(function() {
    if (window.__autogame_canvas_hooked) return;
    window.__autogame_canvas_hooked = true;
    window.__autogame_canvas_texts = [];
    window.__autogame_canvas_images = [];
    window.__autogame_transform_stack = [];  // 维护变换矩阵栈

    // Hook fillText——拿到文本与绘制坐标
    const originalFillText = CanvasRenderingContext2D.prototype.fillText;
    CanvasRenderingContext2D.prototype.fillText = function(text, x, y, ...rest) {
        // 应用当前变换矩阵还原真实屏幕坐标
        const m = this.getTransform();
        const realX = m.a * x + m.c * y + m.e;
        const realY = m.b * x + m.d * y + m.f;
        window.__autogame_canvas_texts.push({
            text: String(text),
            x: realX, y: realY,
            font: this.font,
            fillStyle: this.fillStyle,
            t: Date.now()
        });
        // 滚动窗口防止内存爆炸（保留最近 1000 条）
        if (window.__autogame_canvas_texts.length > 1000) {
            window.__autogame_canvas_texts.shift();
        }
        return originalFillText.apply(this, [text, x, y, ...rest]);
    };

    // Hook drawImage——拿到所有 UI 资源 URL
    const originalDrawImage = CanvasRenderingContext2D.prototype.drawImage;
    CanvasRenderingContext2D.prototype.drawImage = function(img, ...args) {
        if (img && img.src) {
            window.__autogame_canvas_images.push({
                src: img.src,
                width: img.naturalWidth || img.width,
                height: img.naturalHeight || img.height,
                t: Date.now()
            });
            if (window.__autogame_canvas_images.length > 500) {
                window.__autogame_canvas_images.shift();
            }
        }
        return originalDrawImage.apply(this, [img, ...args]);
    };

    // 暴露查询接口给 Python（通过 CDP/Runtime.evaluate）
    window.__autogame_get_canvas_texts = function(sinceTs) {
        sinceTs = sinceTs || 0;
        return window.__autogame_canvas_texts.filter(t => t.t > sinceTs);
    };
    window.__autogame_get_canvas_images = function() {
        return window.__autogame_canvas_images;
    };

    // 派发点击事件到 Canvas（替代 pyautogui）
    window.__autogame_dispatch_click = function(x, y) {
        const canvas = document.querySelector('canvas') || window.__game_canvas;
        if (!canvas) return false;
        const rect = canvas.getBoundingClientRect();
        const event = new MouseEvent('click', {
            clientX: rect.left + x,
            clientY: rect.top + y,
            bubbles: true
        });
        canvas.dispatchEvent(event);
        return true;
    };
})();
```

### 6.5 `js_inject/scripts/hook_network.js`：网络层 Hook

```javascript
// 截获原始网络包，补充 mitmproxy 抓不到的（明文 + 加密前数据）
(function() {
    if (window.__autogame_network_hooked) return;
    window.__autogame_network_hooked = true;
    window.__autogame_network = [];  // HTTP 请求/响应
    window.__autogame_ws_in = [];    // WebSocket 接收帧
    window.__autogame_ws_out = [];   // WebSocket 发送帧

    // Hook fetch——能看到加密前/解密后的明文
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        const reqUrl = typeof args[0] === 'string' ? args[0] : args[0].url;
        const reqMethod = (args[1] && args[1].method) || 'GET';
        const reqBody = args[1] && args[1].body;
        const t0 = Date.now();
        try {
            const response = await originalFetch.apply(this, args);
            // clone 后异步读取 body，不影响原始响应
            const clone = response.clone();
            clone.text().then(text => {
                window.__autogame_network.push({
                    type: 'fetch',
                    url: reqUrl,
                    method: reqMethod,
                    requestBody: typeof reqBody === 'string' ? reqBody : null,
                    status: response.status,
                    responseBody: text,
                    durationMs: Date.now() - t0,
                    t: t0
                });
                if (window.__autogame_network.length > 500) {
                    window.__autogame_network.shift();
                }
            }).catch(() => {});
            return response;
        } catch (err) {
            window.__autogame_network.push({
                type: 'fetch_error',
                url: reqUrl, method: reqMethod,
                error: String(err), t: t0
            });
            throw err;
        }
    };

    // Hook XMLHttpRequest
    const OriginalXHR = window.XMLHttpRequest;
    const originalOpen = OriginalXHR.prototype.open;
    const originalSend = OriginalXHR.prototype.send;
    OriginalXHR.prototype.open = function(method, url, ...rest) {
        this.__autogame_meta = { method, url, t0: Date.now() };
        return originalOpen.apply(this, [method, url, ...rest]);
    };
    OriginalXHR.prototype.send = function(body) {
        if (this.__autogame_meta) {
            this.__autogame_meta.requestBody = typeof body === 'string' ? body : null;
            this.addEventListener('loadend', () => {
                window.__autogame_network.push({
                    type: 'xhr',
                    ...this.__autogame_meta,
                    status: this.status,
                    responseBody: this.responseText,
                    durationMs: Date.now() - this.__autogame_meta.t0,
                    t: this.__autogame_meta.t0
                });
                if (window.__autogame_network.length > 500) {
                    window.__autogame_network.shift();
                }
            });
        }
        return originalSend.apply(this, [body]);
    };

    // Hook WebSocket——能看到所有 WS 帧（加密前/解密后）
    const OriginalWS = window.WebSocket;
    window.WebSocket = class extends OriginalWS {
        constructor(...args) {
            super(...args);
            this.addEventListener('message', e => {
                let data = e.data;
                if (data instanceof ArrayBuffer) {
                    data = new TextDecoder().decode(data);
                } else if (data instanceof Blob) {
                    data.text().then(t => {
                        window.__autogame_ws_in.push({data: t, t: Date.now()});
                    });
                    return;
                }
                window.__autogame_ws_in.push({data, t: Date.now()});
            });
        }
        send(data) {
            let strData = data;
            if (data instanceof ArrayBuffer) {
                strData = new TextDecoder().decode(data);
            } else if (typeof data !== 'string') {
                strData = String(data);
            }
            window.__autogame_ws_out.push({data: strData, t: Date.now()});
            return super.send(data);
        }
    };

    // 暴露查询接口
    window.__autogame_get_network = function(sinceTs) {
        sinceTs = sinceTs || 0;
        return window.__autogame_network.filter(n => n.t > sinceTs);
    };
    window.__autogame_get_ws = function(sinceTs) {
        sinceTs = sinceTs || 0;
        return {
            incoming: window.__autogame_ws_in.filter(w => w.t > sinceTs),
            outgoing: window.__autogame_ws_out.filter(w => w.t > sinceTs)
        };
    };
})();
```

### 6.6 `js_inject/canvas_extractor.py`：Python 端消费

```python
"""从 JS Hook 推送的绘制数据重建"虚拟 DOM"。
比图像识别快 10 倍以上，且无 OCR 错误。"""
import re
from typing import Optional
from autogame_xcx.js_inject.bridge import Bridge


class CanvasExtractor:
    def __init__(self, bridge: Bridge):
        self.bridge = bridge
        self._last_ts = 0

    async def get_visible_texts(self) -> list[dict]:
        """返回 [{text, x, y, font, fillStyle, t}, ...]——游戏当前画面上所有文本及坐标。"""
        result = await self.bridge.evaluate(
            f"window.__autogame_get_canvas_texts({self._last_ts})"
        )
        if result:
            self._last_ts = max(t["t"] for t in result)
        return result or []

    async def find_text(self, pattern: str) -> Optional[dict]:
        """按正则查找游戏内文本，返回坐标——替代图像匹配定位按钮。"""
        texts = await self.get_visible_texts()
        regex = re.compile(pattern)
        for t in texts:
            if regex.search(t["text"]):
                return t
        return None

    async def click_text(self, pattern: str) -> bool:
        """通过 JS 直接派发 click 事件到游戏（绕过 pyautogui）。"""
        target = await self.find_text(pattern)
        if not target:
            return False
        return await self.bridge.evaluate(
            f"window.__autogame_dispatch_click({target['x']}, {target['y']})"
        )

    async def get_image_urls(self) -> list[str]:
        """提取所有 drawImage 的图片 URL，可用于离线下载 UI 资源。"""
        result = await self.bridge.evaluate("window.__autogame_get_canvas_images()")
        return [img["src"] for img in (result or []) if img.get("src")]
```

### 6.7 `js_inject/bridge.py`：CDP 桥接

```python
"""与小程序 WebView 的桥接，基于 Chrome DevTools Protocol (CDP)。
微信开发者工具提供 CDP 调试端口，Python 通过 pychrome 或原始 CDP 协议连接。"""
import asyncio
import json
import logging
from typing import Any
import pychrome  # pip install pychrome

logger = logging.getLogger(__name__)


class Bridge:
    """Python ↔ JS 双向 RPC。"""

    def __init__(self, cdp_endpoint: str = "http://127.0.0.1:9222"):
        self.cdp_endpoint = cdp_endpoint
        self._browser = None
        self._tab = None

    async def connect(self) -> None:
        """连接到微信开发者工具的 CDP 端口。"""
        # 在独立线程运行 pychrome（同步 API）
        loop = asyncio.get_event_loop()
        self._browser = await loop.run_in_executor(None, pychrome.Browser, self.cdp_endpoint)
        tabs = await loop.run_in_executor(None, lambda: self._browser.list_tab())
        # 找到游戏 WebView 所在的 tab
        self._tab = next((t for t in tabs if "game" in t.get("url", "")), tabs[0] if tabs else None)
        if self._tab:
            await loop.run_in_executor(None, self._tab.start)

    async def inject_script(self, script_name: str) -> bool:
        """注入 scripts/ 目录下的 JS 脚本。"""
        from importlib.resources import files
        script_content = (files("autogame_xcx.js_inject") / "scripts" / script_name).read_text(
            encoding="utf-8"
        )
        result = await self.evaluate(script_content)
        return result is not None

    async def evaluate(self, expression: str) -> Any:
        """在游戏 WebView 中执行 JS 表达式，返回结果。"""
        if not self._tab:
            raise RuntimeError("Bridge not connected")
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._tab.Runtime.evaluate(
                    expression=expression,
                    returnByValue=True,
                    awaitPromise=True,
                )
            )
            return result.get("result", {}).get("value")
        except Exception as e:
            logger.exception("CDP evaluate failed")
            return None

    async def disconnect(self) -> None:
        if self._tab:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._tab.stop)
```

### 6.8 `anti_detect/rate_limiter.py`：人类化频率

```python
"""避免请求频率过于规律被风控识别。"""
import random
import time
import asyncio
from collections import deque


class HumanLikeRateLimiter:
    def __init__(self, min_interval_ms: int = 800, max_interval_ms: int = 2500):
        self.min = min_interval_ms / 1000
        self.max = max_interval_ms / 1000
        self.history = deque(maxlen=20)

    async def wait(self) -> None:
        # 1. 基础间隔随机
        delay = random.uniform(self.min, self.max)
        # 2. 每 10 次插入一次"长思考"（模拟人离开）
        if len(self.history) >= 10 and random.random() < 0.1:
            delay += random.uniform(5, 15)
        await asyncio.sleep(delay)
        self.history.append(time.time())
```

### 6.9 `protocol/packet/base.py`：数据包基类

```python
"""Packet 基类，每个业务包继承实现 serialize/parse_response。"""
from dataclasses import dataclass
from typing import Literal


@dataclass
class Packet:
    endpoint: str
    transport: Literal["http", "ws"] = "http"
    method: str = "POST"

    def serialize(self) -> bytes:
        """子类实现：把参数编码为字节流（JSON / Protobuf）。"""
        raise NotImplementedError

    def parse_response(self, raw: bytes) -> dict:
        """子类实现：把响应解码为 Python dict。"""
        raise NotImplementedError
```

---

## 7. 迁移路径（分 7 阶段）

### 阶段 3.1：抓包与环境搭建（2~3 天）

**动作**：
1. 安装 mitmproxy：`uv add mitmproxy`
2. 配置微信客户端走代理（Windows proxy 设置 + 信任 mitmproxy CA）
3. 微信开发者工具代理设置（指向 mitmproxy）
4. 在 `reverse/mitmproxy_scripts/capture_flow.py` 写 addon，自动把 `*.qq.com` / `*.weixin.qq.com` 的请求分类存到 `data/captures/{date}/`
5. 手动玩一局游戏（登录、签到、一次战斗），收集流量样本

**验证**：
- `mitmdump -s reverse/mitmproxy_scripts/capture_flow.py`，访问游戏后 `data/captures/` 出现 50+ JSON 流量文件
- 能用 `mitmproxy` UI 看到游戏 API 调用列表

### 阶段 3.2：API 端点梳理（2~3 天）

**动作**：
1. 分析抓包数据，在 `reverse/decompile_notes/api_endpoints.md` 整理：
   - 域名列表（登录、业务、CDN）
   - 每个端点的请求方法、参数、响应 schema
   - 鉴权字段（token / sign / seq）
2. 识别哪些请求有加密签名（看请求头/参数中是否有 `sign=xxx`、`_t=xxx`）

**验证**：
- 文档中至少识别 10 个核心 API
- 能复现"无签名请求被拒绝"的现象

### 阶段 3.3：★ JS 注入与 Canvas Hook（路径 B，新增 3~5 天）

**这是 Canvas 游戏特有的关键阶段，必须在路径 A 之前完成。**

**动作**：
1. 用微信开发者工具打开游戏，找到游戏 WebView 的 CDP 调试端口
2. 反编译 wxapkg（用 `wxappUnpacker` 或 `unveilr`），定位游戏 JS 源码
3. 编写 `js_inject/scripts/hook_canvas.js`（按 6.4 节模板）
4. 编写 `js_inject/scripts/hook_network.js`（按 6.5 节模板）
5. 实现 `js_inject/bridge.py`（CDP 连接）
6. 实现 `js_inject/canvas_extractor.py`（消费 Hook 数据）
7. 通过微信开发者工具 Sources 面板或 CDP 注入脚本

**验证**：
- Python 能通过 CDP 连接到游戏 WebView
- 注入 hook_canvas.js 后，能拿到游戏内所有 fillText 文本（含坐标）
- 注入 hook_network.js 后，能拿到所有 fetch/XHR/WebSocket 数据（含加密前后对比）
- `CanvasExtractor.find_text("签到")` 返回坐标，`click_text("签到")` 触发签到

### 阶段 3.4：Frida Hook 加密算法（路径 A 准备，5~10 天）

**最难的阶段。利用阶段 3.3 的产出大幅降低难度。**

**动作**：
1. 用 jadx 反编译微信小程序容器 APK（或小程序的 wxapkg 解包后用 wxappUnpacker 反编译前端 JS）
2. 在反编译代码中搜索 `Cipher.getInstance`、`Mac.getInstance`、`MessageDigest` 等加密 API 调用点
3. 在 `reverse/frida_scripts/hook_crypto.js` 写 Frida 脚本，Hook 这些 API，dump 出算法类型、密钥、明文、密文
4. **关键技巧**：用阶段 3.3 的 `hook_network.js` 拿到的"加密前后明文"对照 mitmproxy 抓到的"加密后密文"，**直接定位签名算法**，无需逐函数 Hook
5. Hook 到 `sign` 字段的生成函数，定位完整签名算法
6. 在 `reverse/decompile_notes/sign_algorithm.md` 文档化算法（输入、密钥派生、哈希链、输出格式）

**验证**：
- Frida 脚本能稳定 hook 到加密函数（不崩溃）
- 给定输入能复现密文（与抓包对照）

### 阶段 3.5：Python 协议客户端（路径 A 实现，3~5 天）

**动作**：
1. 根据阶段 3.4 的算法文档，在 `protocol/crypto/sign.py` 用 Python 复刻签名算法
2. 实现 `protocol/http_client.py`（httpx async），处理登录、token 刷新、自动重试
3. 实现 `protocol/ws_client.py`（websockets），心跳、重连
4. 实现 `protocol/packet/auth.py`（登录包）、`protocol/packet/combat.py`（至少一个业务包作为 PoC）

**验证**：
- Python 客户端能成功登录游戏服务器（拿到 token）
- 能发送一个业务包（例如查询背包）并正确解析响应
- 签名验证通过（不被服务器拒绝）

### 阶段 3.6：策略切换整合（1~2 天）

**动作**：
1. 实现 `core/execution_strategy.py`（按 6.1 节）
2. `GameExecutor` 重构为持有 `StrategyContext`，根据模板配置选择策略：
   ```json
   {
     "template_info": {
       "execution_mode": "protocol",
       "protocol_config": {...}
     }
   }
   ```
3. UI 增加"执行策略"下拉框（图像/协议/JS 注入），运行时可切换
4. 实现 `JsInjectStrategy`（封装阶段 3.3 的能力）

**验证**：
- 同一份模板，切换"图像 / 协议 / JS 注入"模式都能跑（步骤映射可能不同）
- 协议模式下，单步执行延迟 < 50ms（vs 图像模式 300ms+）
- JS 注入模式下，定位元素延迟 < 20ms（vs 图像匹配 300ms+）

### 阶段 3.7：风控对抗与稳定性（持续）

**动作**：
1. 实现 `anti_detect/rate_limiter.py`（按 6.8 节），强制人类化请求间隔
2. 监控账号是否被封（登录失败、业务包返回风控码），自动降级回图像模式
3. 每次协议变更（游戏更新）后重新跑阶段 3.1~3.3，更新签名算法

**验证**：
- 连续运行 1 小时不被封
- 游戏更新后 24h 内能恢复协议模式（依赖逆向响应速度）

---

## 8. 关键风险与对策

### 8.1 法律与合规风险

| 风险 | 对策 |
|---|---|
| 违反游戏 ToS | 仅个人研究，不公开发布，不商业 |
| 法律追责 | 保留免责声明；优先厂商授权合作 |
| 账号封禁 | 用小号测试；监控异常及时止损 |

### 8.2 技术风险（Canvas 特有）

| 风险 | 影响 | 对策 |
|---|---|---|
| Canvas 多层叠加（背景层+UI 层+特效层） | fillText Hook 数据噪声大 | 按绘制顺序与图层 z-index 过滤；按文本样式（字体/颜色）聚类 |
| 游戏使用 WebGL 而非 Canvas 2D | fillText Hook 失效 | 探测 `canvas.getContext('webgl')` 走 WebGL Hook 路径（截获纹理/着色器） |
| Canvas 文本绘制位置受变换矩阵影响 | 坐标计算错误 | Hook `setTransform/translate/scale`，维护变换栈还原真实坐标（已在 hook_canvas.js 实现） |
| 游戏反调试（debugger 语句无限触发） | DevTools 无法工作 | Hook `Function.prototype.constructor` 屏蔽 debugger；用 RID（Reflective Injection）模式 |
| JS 代码强混淆/控制流平坦化 | 静态分析定位加密函数困难 | 优先用阶段 3.3 的运行时 Hook 反推调用栈；AST 反混淆工具（webcrack/deobfuscator） |
| 游戏更新时 wxapkg 包结构变 | 解包失效 | wxapkg 解包工具版本化；监控游戏版本号自动重新解包 |
| 微信小程序 WebView 沙箱限制注入 | 油猴脚本无效 | 用微信开发者工具 + Sources 面板注入；或 CDP 远程调试真机 WebView |
| CDP 连接不稳定 | Bridge 断开 | 自动重连 + 心跳检测；失败时降级到 ImageBasedStrategy |

### 8.3 协议层风险

| 风险 | 影响 | 对策 |
|---|---|---|
| 签名算法升级 | 协议失效 | 算法版本化（`Signer` 子类），自动检测失效时降级到图像模式 |
| WebSocket 心跳复杂 | 连接不稳定 | 抓包分析心跳间隔，用 asyncio 精确控制；心跳失败自动重连 + 重新登录 |
| 多账号并发封号 | 批量封号 | 单账号单进程；代理 IP 池；设备指纹随机化 |
| 白盒密码学（密钥混淆在算法里） | Frida 无效 | 走"灰盒"——直接调用游戏内函数（不提取密钥），通过阶段 3.3 的网络 Hook 验证 |
| HTTPS 抓不到（SSL Pinning） | 抓包失败 | Frida Hook OkHttp/SSLContext bypass cert pinning；或用 objection 自动 patch |

---

## 9. Canvas 渲染特有的优化机会

### 9.1 虚拟 DOM 重建

通过 fillText Hook 数据构建"游戏内文本 + 坐标"映射，等价于一个虚拟 DOM——可以直接 `find_text("签到").click()`，比图像匹配快 10~50 倍。

```python
# 传统图像识别（300ms+）
template = load_image("signin_button.png")
position = matcher.find_in_screenshot(template)

# Canvas Hook（<20ms）
position = await extractor.find_text("签到")
await extractor.click_at(position.x, position.y)
```

### 9.2 资源 URL 提取

drawImage Hook 拿到所有 UI 图像 URL，下载后可离线分析（替代当前 `data/reference_images/` 的手动截图）。

```python
urls = await extractor.get_image_urls()
for url in urls:
    if not (reference_dir / Path(url).name).exists():
        download(url, reference_dir)
```

### 9.3 网络明文 dump

fetch/WebSocket Hook 在加密前/解密后拦截，**避开 SSL Pinning 和加密算法逆向**——如果游戏在 JS 层做加解密，直接拿到明文。

### 9.4 灰盒调用

找到游戏暴露在 window 上的对象（如 `window.GameAPI`），Python 通过 JS RPC 直接调用业务方法，完全绕过 UI 与网络：

```javascript
// hook_game_api.js
window.__autogame_game_api = {
    signIn: () => window.GameAPI.signIn(),
    getInventory: () => window.GameAPI.getInventory(),
    useItem: (id) => window.GameAPI.useItem(id),
};
```

```python
# Python 调用
result = await bridge.evaluate("window.__autogame_game_api.signIn()")
```

---

## 10. 依赖工具链

| 工具 | 版本 | 用途 | 阶段 |
|---|---|---|---|
| mitmproxy | >=10.0 | HTTPS/WS 抓包 | 3.1 |
| 微信开发者工具 | latest | 小程序调试、Network/Sources 面板、wxapkg 解密 | 3.1, 3.3 |
| wxappUnpacker / unveilr | latest | 小程序 wxapkg 解包（拿到游戏 JS 源码） | 3.3 |
| jadx | latest | Java/Android 反编译（如需看小程序容器） | 3.4 |
| frida + frida-tools | >=16.0 | 运行时 Hook native 加密 | 3.4 |
| pychrome | latest | Python 控制 CDP，连接 WebView | 3.3 |
| webcrack / deobfuscator | latest | JS 反混淆（控制流平坦化还原） | 3.3 |
| httpx | >=0.27 | 异步 HTTP 客户端 | 3.5 |
| websockets | >=12.0 | WebSocket 客户端 | 3.5 |
| （可选）protobuf | latest | 若协议用 Protobuf | 3.5 |
| （可选）objection | latest | Frida 封装，自动 bypass cert pinning | 3.4 |

---

## 11. 验证方式

| 阶段 | 命令 | 预期 |
|---|---|---|
| 3.1 | `mitmdump -s reverse/mitmproxy_scripts/capture_flow.py` | 玩游戏后 `data/captures/` 收集 50+ 流量 |
| 3.2 | 检查 `reverse/decompile_notes/api_endpoints.md` | 至少 10 个核心 API + 鉴权字段识别 |
| 3.3 | `uv run python tests/manual/test_js_inject.py` | CDP 连接成功 + 能拿到 fillText 文本与坐标 |
| 3.3 | `uv run python tests/manual/test_click_text.py` | `click_text("签到")` 触发签到功能 |
| 3.4 | `frida -U -l reverse/frida_scripts/hook_crypto.js` | 稳定输出加密函数的输入输出，与抓包对照能复现 |
| 3.5 | `uv run python -m autogame_xcx.protocol.client --login` | 成功登录并打印 token |
| 3.5 | `uv run python -m autogame_xcx.protocol.client --action query_inventory` | 返回物品列表 |
| 3.6 | GUI 中切换"协议"模式 | 跑一个简单模板，日志显示 `[strategy=protocol]` 标记，延迟 <50ms/步 |
| 3.6 | GUI 中切换"JS 注入"模式 | 跑一个简单模板，日志显示 `[strategy=js_inject]`，延迟 <20ms/步 |
| 3.7 | 连续运行 1 小时 | 无封号；游戏更新后 24h 内恢复协议模式 |

---

## 12. 与方向 1/2 的关系

- **依赖方向 1**：包结构稳定后才好引入 `protocol/` + `js_inject/` + `reverse/` + `anti_detect/` 等新模块
- **正交于方向 2**：方向 2 是远程触发通道，方向 3 是本地执行能力升级。方向 2 的 `#run <模板名>` 指令内部可以选择执行策略（图像/协议/JS 注入）
- **三策略并存**：
  - `ImageBasedStrategy`（现有，稳定但慢）
  - `ProtocolBasedStrategy`（终极目标，最快但需持续对抗）
  - `JsInjectStrategy`（折中方案，Canvas Hook 能拿到精确数据，开发成本中等）
- **降级路径**：协议失效 → 自动降级到 JS 注入；JS 注入失效 → 降级到图像识别

---

## 13. 实施建议

### 13.1 优先级排序

1. **方向 3.3（JS 注入）**：先做。难度可控、产出高、对协议直连有反哺作用
2. **方向 3.1~3.2（抓包 + API 梳理）**：与 3.3 并行
3. **方向 3.6（策略切换）**：做完 3.3 后立即接入，让 JsInjectStrategy 可用
4. **方向 3.4~3.5（协议直连）**：作为长期目标，可独立小团队推进

### 13.2 团队配置建议

- **1 人**：抓包 + API 梳理 + 协议客户端（路径 A，3~6 周）
- **1 人**：JS 注入 + Canvas Hook（路径 B，1~2 周）
- **共享**：策略切换整合 + 风控对抗

### 13.3 验收标准

**最小可用 PoC**（4 周内）：
- 路径 B（JS 注入）完整可用，能完成签到任务
- 路径 A（协议直连）至少能登录 + 1 个业务包

**生产可用**（6 周内）：
- 三种策略可切换
- 风控对抗机制就位
- 连续运行 1 小时不被封
