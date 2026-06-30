"""聊斋搜神记 WebSocket 抓包日志解析工具。

数据来源：tools/capture_liaozhai.py 在 mitmproxy addon 里写出的
data/captures/liaozhai/ws_<时间戳>.jsonl，每行一条 entry：
    {"ts": "...", "dir": "OUT|IN", "type": "binary", "len": N,
     "ws_url": "...", "hex": "00 01 00 38 7b 22 ..."}

二进制帧格式（已逆向）：前 4 字节为大端 op(2) + len(2)，其后是 JSON 文本。

子命令：
    summary     <file>   总览：ws_url 分组、IN/OUT 分布、时间范围
    op-stats    <file>   按 op 聚合统计，可选过滤 --ws / --dir，自动翻译 op 业务名
    dump        <file>   过滤后逐条解码输出，可选 --ws / --dir / --op / --time / --limit
    init-names  <file>   扫描 jsonl 生成/更新 op_names.json 模板，已标注的保留

op 名字映射：
    data/captures/liaozhai/op_names.json，扁平字典 {"0x2714": "ui_click", ...}
    用 init-names 生成模板，手工填充 value 后再跑 op-stats/dump 即可看到业务名。

示例：
    uv run python tools/parse_liaozhai_ws.py summary ws_20260623_172829.jsonl
    uv run python tools/parse_liaozhai_ws.py init-names ws_*.jsonl
    uv run python tools/parse_liaozhai_ws.py op-stats ws_*.jsonl --ws gate --dir OUT
    uv run python tools/parse_liaozhai_ws.py dump ws_*.jsonl --op 0x2714 --dir OUT --limit 20
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NAMES_PATH = PROJECT_ROOT / "data" / "captures" / "liaozhai" / "op_names.json"


@dataclass
class Frame:
    ts: str
    dir: str
    ws_url: str
    op: int
    declared_len: int
    body: bytes

    @property
    def body_text(self) -> str | None:
        try:
            return self.body.decode("utf-8")
        except UnicodeDecodeError:
            return None

    @property
    def op_hex(self) -> str:
        return f"0x{self.op:04x}"


def short_ws(ws_url: str) -> str:
    """把长 ws_url 缩成易读标签：gate:10.2.1.15:10102 / chat。"""
    p = urlparse(ws_url)
    host_first = (p.hostname or "").split(".")[0]
    prefix = host_first.split("-")[0] or "?"
    qs = parse_qs(p.query)
    if qs.get("host") and qs.get("port"):
        return f"{prefix}:{qs['host'][0]}:{qs['port'][0]}"
    return prefix


def parse_hex(hex_str: str) -> bytes:
    return bytes(int(x, 16) for x in hex_str.split())


def iter_frames(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            b = parse_hex(e["hex"]) if e.get("hex") else b""
            op = (b[0] << 8) | b[1] if len(b) >= 2 else 0
            declared = (b[2] << 8) | b[3] if len(b) >= 4 else 0
            body = b[4 : 4 + declared] if declared else b[4:]
            yield Frame(
                ts=e["ts"],
                dir=e["dir"],
                ws_url=e["ws_url"],
                op=op,
                declared_len=declared,
                body=body,
            )


def match_ws(short: str, pattern: str) -> bool:
    if pattern == "all":
        return True
    return pattern in short


def parse_op_arg(s: str) -> int | None:
    if s == "all":
        return None
    return int(s, 16) if s.lower().startswith("0x") else int(s, 16)


def parse_time_arg(s: str) -> tuple[str, str] | None:
    """形如 '17:30-17:45'，返回 ('17:30', '17:45')。"""
    if not s:
        return None
    if "-" not in s:
        sys.exit(f"无效 --time 格式：{s}（应为 HH:MM-HH:MM）")
    a, b = s.split("-", 1)
    return a.strip(), b.strip()


def in_time_range(ts: str, rng: tuple[str, str]) -> bool:
    # ts 形如 2026-06-23T17:30:15.466，取 HH:MM 比较即可
    hhmm = ts[11:16]
    return rng[0] <= hhmm <= rng[1]


def load_op_names(path: Path) -> dict[int, str]:
    """加载 op->name 映射。文件不存在/格式错误返回空 dict，不报错。"""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"warning: {path} 解析失败，忽略 op 名字映射", file=sys.stderr)
        return {}
    names: dict[int, str] = {}
    for k, v in data.items():
        try:
            op = int(k, 16)
        except (ValueError, TypeError):
            continue
        names[op] = v if isinstance(v, str) else ""
    return names


def format_op(op: int, names: dict[int, str]) -> str:
    """0x2714 或 0x2714 [ui_click]。"""
    base = f"0x{op:04x}"
    name = names.get(op)
    return f"{base} [{name}]" if name else base


def cmd_summary(args: argparse.Namespace) -> None:
    path = Path(args.file)
    total = 0
    size = path.stat().st_size
    by_ws: Counter[str] = Counter()
    by_ws_dir: dict[str, Counter[str]] = defaultdict(Counter)
    by_dir: Counter[str] = Counter()
    first_ts = last_ts = None

    for fr in iter_frames(path):
        total += 1
        tag = short_ws(fr.ws_url)
        by_ws[tag] += 1
        by_ws_dir[tag][fr.dir] += 1
        by_dir[fr.dir] += 1
        if first_ts is None:
            first_ts = fr.ts
        last_ts = fr.ts

    print(f"file:    {path}")
    print(f"size:    {size / 1024 / 1024:.1f} MB")
    print(f"entries: {total}")
    print(f"time:    {first_ts} -> {last_ts}")
    print()
    print(f"{'socket':<30} {'total':>7} {'OUT':>7} {'IN':>7}")
    print("-" * 55)
    for tag, c in by_ws.most_common():
        d = by_ws_dir[tag]
        print(f"{tag:<30} {c:>7} {d.get('OUT', 0):>7} {d.get('IN', 0):>7}")
    print("-" * 55)
    print(f"{'TOTAL':<30} {total:>7} {by_dir.get('OUT', 0):>7} {by_dir.get('IN', 0):>7}")


def cmd_op_stats(args: argparse.Namespace) -> None:
    path = Path(args.file)
    names = load_op_names(Path(args.names))
    ws_pat = args.ws
    dir_pat = args.dir
    rng = parse_time_arg(args.time) if args.time else None

    counts: Counter[int] = Counter()
    in_out: dict[int, Counter[str]] = defaultdict(Counter)
    samples: dict[int, Frame] = {}

    for fr in iter_frames(path):
        if not match_ws(short_ws(fr.ws_url), ws_pat):
            continue
        if dir_pat != "all" and fr.dir != dir_pat:
            continue
        if rng and not in_time_range(fr.ts, rng):
            continue
        counts[fr.op] += 1
        in_out[fr.op][fr.dir] += 1
        if fr.op not in samples:
            samples[fr.op] = fr

    if not counts:
        print("没有匹配的帧。", file=sys.stderr)
        return

    print(f"{'op':<10} {'total':>7} {'OUT':>7} {'IN':>7}  {'name':<16} sample_body")
    print("-" * 106)
    for op, c in counts.most_common():
        d = in_out[op]
        sample = samples[op]
        text = sample.body_text
        body_preview = (text if text is not None else f"<binary {sample.body[:16].hex()}>")[:60]
        name = names.get(op, "")
        print(f"0x{op:04x}     {c:>7} {d.get('OUT', 0):>7} {d.get('IN', 0):>7}  {name:<16} {body_preview}")


def cmd_dump(args: argparse.Namespace) -> None:
    path = Path(args.file)
    names = load_op_names(Path(args.names))
    ws_pat = args.ws
    dir_pat = args.dir
    op_filter = parse_op_arg(args.op)
    rng = parse_time_arg(args.time) if args.time else None
    limit = args.limit
    shown = 0

    for fr in iter_frames(path):
        if shown >= limit:
            break
        if not match_ws(short_ws(fr.ws_url), ws_pat):
            continue
        if dir_pat != "all" and fr.dir != dir_pat:
            continue
        if op_filter is not None and fr.op != op_filter:
            continue
        if rng and not in_time_range(fr.ts, rng):
            continue

        body_repr = fr.body_text
        if body_repr is None:
            body_repr = "<binary " + fr.body[:32].hex(" ") + (">" if len(fr.body) <= 32 else " ...>")

        ts_short = fr.ts[11:]
        print(f"[{ts_short}] {fr.dir:<3} {short_ws(fr.ws_url):<24} {format_op(fr.op, names)} len={fr.declared_len:>4} {body_repr}")
        shown += 1

    if shown == 0:
        print("没有匹配的帧。", file=sys.stderr)


def cmd_init_names(args: argparse.Namespace) -> None:
    """扫描 jsonl 收集所有 op，合并已有 names（保留已标注），写出模板。"""
    path = Path(args.file)
    names_path = Path(args.names)
    existing = load_op_names(names_path)

    seen: set[int] = set()
    for fr in iter_frames(path):
        seen.add(fr.op)

    out: dict[str, str] = {}
    for op in sorted(seen | set(existing.keys())):
        key = f"0x{op:04x}"
        out[key] = existing.get(op, "")

    names_path.parent.mkdir(parents=True, exist_ok=True)
    names_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    labeled = sum(1 for v in out.values() if v)
    print(f"写入 {names_path}")
    print(f"共 {len(out)} 个 op，已标注 {labeled} 个，待标注 {len(out) - labeled} 个")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--names",
        default=str(DEFAULT_NAMES_PATH),
        help=f"op 名字映射 JSON（默认 {DEFAULT_NAMES_PATH}）",
    )

    s = sub.add_parser("summary", help="总览：ws_url 分组 / IN/OUT 分布 / 时间范围")
    s.add_argument("file")
    s.set_defaults(func=cmd_summary)

    o = sub.add_parser("op-stats", help="按 op 聚合统计", parents=[common])
    o.add_argument("file")
    o.add_argument("--ws", default="all", help="socket 关键字过滤：gate / chat / all（默认 all）")
    o.add_argument("--dir", default="all", choices=["all", "OUT", "IN"], help="方向过滤（默认 all）")
    o.add_argument("--time", default=None, help="时间范围 HH:MM-HH:MM")
    o.set_defaults(func=cmd_op_stats)

    d = sub.add_parser("dump", help="过滤后逐条解码输出", parents=[common])
    d.add_argument("file")
    d.add_argument("--ws", default="all", help="socket 关键字过滤：gate / chat / all")
    d.add_argument("--dir", default="all", choices=["all", "OUT", "IN"])
    d.add_argument("--op", default="all", help="op 码过滤：0x2714 / 2714 / all")
    d.add_argument("--time", default=None, help="时间范围 HH:MM-HH:MM")
    d.add_argument("--limit", type=int, default=50, help="最多输出条数（默认 50）")
    d.set_defaults(func=cmd_dump)

    n = sub.add_parser("init-names", help="扫描 jsonl 生成/更新 op 名字映射模板", parents=[common])
    n.add_argument("file")
    n.set_defaults(func=cmd_init_names)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
#  uv run python tools/parse_liaozhai_ws.py dump data/captures/liaozhai/ws_20260623_172829.jsonl
#  uv run python tools/parse_liaozhai_ws.py op-stats data/captures/liaozhai/ws_20260623_172829.json
#  uv run python tools/parse_liaozhai_ws.py summary data/captures/liaozhai/ws_20260623_172829.jsonl