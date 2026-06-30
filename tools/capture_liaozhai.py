"""mitmproxy addon：聊斋搜神记请求自动分类保存。

用法：
    mitmweb -s tools/capture_liaozhai.py --listen-port 8080

抓包后请求会按 <秒>_<KEY|all>_<METHOD>_<host>_<path>.json 命名，落到
data/captures/liaozhai/ 下；KEY 前缀的包含 login/auth/signin/action/combat
等关键字，便于优先分析。
"""
import json
from datetime import datetime
from pathlib import Path

from mitmproxy import ctx, http

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DIR = PROJECT_ROOT / "data" / "captures" / "liaozhai"
CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
WS_LOG = CAPTURE_DIR / f"ws_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

INTERESTED_DOMAINS = ("szfangzhouhd.com", "fangzhouhd.com","dashscope.aliyuncs.com")
INTERESTED_PATTERNS = (
    "/login",
    "/auth",
    "/session",
    "/signin",
    "/sign/",
    "/action",
    "/combat",
    "/battle",
    "/heartbeat",
    "/hb",
)


def request(flow: http.HTTPFlow) -> None:
    if not any(d in flow.request.host for d in INTERESTED_DOMAINS):
        return
    ts = datetime.now().strftime("%H%M%S")
    is_key = any(p in flow.request.path for p in INTERESTED_PATTERNS)
    tag = "KEY" if is_key else "all"
    raw_name = f"{ts}_{tag}_{flow.request.method}_{flow.request.host}{flow.request.path[:30]}.json"
    safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in raw_name)
    payload = {
        "url": flow.request.url,
        "method": flow.request.method,
        "headers": dict(flow.request.headers),
        "body": flow.request.text,
    }
    (CAPTURE_DIR / safe_name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

def websocket_message(flow: http.HTTPFlow) -> None:
    if not any(d in flow.request.host for d in INTERESTED_DOMAINS):
        return
    assert flow.websocket is not None
    msg = flow.websocket.messages[-1]
    direction = "OUT" if msg.from_client else "IN"
    entry = {
        "ts": datetime.now().isoformat(timespec="milliseconds"),
        "dir": direction,
        "type": "text" if msg.is_text else "binary",
        "len": len(msg.content),
        "ws_url": flow.request.url,
    }
    if msg.is_text:
        entry["text"] = msg.content.decode("utf-8", errors="replace")
    else:
        entry["hex"] = msg.content.hex(" ")
    with WS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    ctx.log.info(f"[WS] {direction} {entry['type']} {entry['len']}B")