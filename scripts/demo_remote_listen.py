"""阶段 2.2 验证脚本：消息接收通道完整链路。

两种运行模式：

1. dry-run（不调 executeLogin，不触发网络）：
   uv run python scripts/demo_remote_listen.py --dry-run
   验证：模块装配、JVM 启动、client 构造、优雅关闭。

2. 完整登录（需要专用测试微信号扫码）：
   uv run python scripts/demo_remote_listen.py [--qr-out path/to/qr.png]
   流程：启动 JVM → executeLogin 拿二维码 → 控制台打印二维码 URL
        → 用户扫码 → 登录成功后开始监听消息
        → 从手机发消息 → 控制台实时打印
        → Ctrl+C 退出（JVM 优雅关闭）

注意：监听器用 pyqtSignal 转主线程，所以需要 QApplication 事件循环。
"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from autogame_xcx.remote.ilink import ILinkClient, ILinkSdkConfig
from autogame_xcx.remote.ilink.client import save_qr_to_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("demo_remote_listen")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="阶段 2.2 ilink 消息接收通道 demo")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅验证 JVM 启动 + client 构造 + 优雅关闭，不下到 executeLogin",
    )
    parser.add_argument(
        "--qr-out",
        type=Path,
        default=Path("data/logs/ilink_qr.png"),
        help="二维码图片保存路径（默认 data/logs/ilink_qr.png）",
    )
    parser.add_argument(
        "--sdk-root",
        type=Path,
        default=None,
        help="wechat-ilink-sdk-java 工程根目录（默认自动推断）",
    )
    return parser.parse_args()


def _format_message(py_msg: dict) -> str:
    """格式化收到的消息为可读字符串。"""
    ts = datetime.fromtimestamp(py_msg["create_time_ms"] / 1000).strftime("%H:%M:%S") \
        if py_msg.get("create_time_ms") else "??:??:??"
    sender = py_msg.get("from_user_id", "<unknown>")
    items_text = []
    for item in py_msg.get("items", []):
        t = item.get("type")
        if t == 1 and "text" in item:
            items_text.append(f"text={item['text']!r}")
        elif t == 2:
            items_text.append(f"image(media={item['image']['media'][:16]}...)")
        elif t == 3:
            items_text.append(f"voice({item['voice']['playtime_ms']}ms)")
        elif t == 4:
            items_text.append(f"file({item['file']['file_name']})")
        elif t == 5:
            items_text.append(f"video({item['video']['play_length_ms']}ms)")
        else:
            items_text.append(f"type={t}")
    return f"[{ts}] {sender}: {', '.join(items_text) if items_text else '(empty)'}"


class DemoWindow(QMainWindow):
    """极简 demo 窗口：显示二维码、最近 10 条消息。"""

    def __init__(self, client: ILinkClient):
        super().__init__()
        self.client = client
        self.setWindowTitle("ilink 消息接收 demo (阶段 2.2)")
        self.resize(640, 480)

        central = QWidget()
        layout = QVBoxLayout(central)

        self.status_label = QLabel("等待登录...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold; padding: 8px;")
        layout.addWidget(self.status_label)

        self.qr_label = QLabel("（未启动）")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setMinimumSize(240, 240)
        self.qr_label.setStyleSheet("border: 1px solid #ccc; background: #f9f9f9;")
        layout.addWidget(self.qr_label)

        self.messages_label = QLabel("最近消息：")
        self.messages_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_label.setWordWrap(True)
        self.messages_label.setStyleSheet("padding: 8px; background: #fafafa;")
        layout.addWidget(self.messages_label, stretch=1)

        self.setCentralWidget(central)

        # 订阅信号
        client.message_listener.message_received.connect(self._on_message)
        client.message_listener.message_error.connect(self._on_error)
        client.login_listener.login_success.connect(self._on_login_success)
        client.login_listener.login_failure.connect(self._on_login_failure)

        self._messages: list[str] = []

    def _on_message(self, py_msg: dict) -> None:
        text = _format_message(py_msg)
        logger.info("RECV: %s", text)
        self._messages.append(text)
        del self._messages[:-10]
        self.messages_label.setText("最近消息：\n\n" + "\n".join(self._messages))

    def _on_error(self, err: str) -> None:
        logger.error("listener error: %s", err)
        self.messages_label.setText(self.messages_label.text() + f"\n[ERR] {err}")

    def _on_login_success(self, _ctx) -> None:
        self.status_label.setText("✓ 登录成功，开始监听消息")
        self.status_label.setStyleSheet(
            "font-weight: bold; padding: 8px; color: #4CAF50;"
        )

    def _on_login_failure(self, msg: str) -> None:
        self.status_label.setText(f"✗ 登录失败：{msg}")
        self.status_label.setStyleSheet(
            "font-weight: bold; padding: 8px; color: #f44336;"
        )

    def show_qr(self, qr_bytes: bytes) -> None:
        """显示二维码图片（直接从字节加载）。"""
        try:
            img = QImage.fromData(qr_bytes)
            if img.isNull():
                self.qr_label.setText("(二维码解码失败，请用 --qr-out 路径手动打开)")
                return
            pixmap = QPixmap.fromImage(img).scaled(
                240, 240, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.qr_label.setPixmap(pixmap)
        except Exception as e:
            self.qr_label.setText(f"(二维码显示失败：{e})")


def run_dry_run(args: argparse.Namespace) -> int:
    """模式 1：仅验证装配，不触发登录。"""
    print(">>> 模式：dry-run（不下到 executeLogin）")

    config = ILinkSdkConfig.default(sdk_root=args.sdk_root)
    print(f"  jar_path = {config.jar_path}")
    print(f"  deps_dir = {config.deps_dir}")
    if not config.jar_path.exists():
        print(f"FATAL: jar 不存在: {config.jar_path}", file=sys.stderr)
        return 2
    if not config.deps_dir.exists():
        print(
            f"FATAL: 依赖目录不存在: {config.deps_dir}\n"
            f"请先在 wechat-ilink-sdk-java/ 执行:\n"
            f"  mvn dependency:copy-dependencies "
            f"-DoutputDirectory=target/dependency -DincludeScope=runtime",
            file=sys.stderr,
        )
        return 2

    # PyQt 需要 QApplication 才能让 pyqtSignal 工作（即使 dry-run 也要构造）
    # app 引用必须保留，否则 GC 会清理导致后续 dry-run 跑不通
    app = QApplication.instance() or QApplication([])  # noqa: F841

    client = ILinkClient(config)
    print(">>> 启动 JVM + 构造 ILinkClient...")
    client.jvm.start()

    # 不调 executeLogin，但构造底层 client 验证 builder 链
    if client._client is None:
        client._client = client._build_client()
    print(f"  Java client 类型: {client._client.getClass().getName()}")
    print(f"  isLoggedIn: {client.is_logged_in()}")
    print(f"  getConfig: {client._client.getConfig() is not None}")

    print(">>> 优雅关闭...")
    client.stop()
    client.jvm.shutdown()
    print(">>> SPIKE PASSED — dry-run 验证通过")
    return 0


def run_full(args: argparse.Namespace) -> int:
    """模式 2：完整登录 + 消息监听（需要扫码）。"""
    print(">>> 模式：完整登录（请准备扫码）")

    config = ILinkSdkConfig.default(sdk_root=args.sdk_root)
    app = QApplication.instance() or QApplication([])  # noqa: F841
    client = ILinkClient(config)
    # 必须先启动 JVM 再访问 listener（@JImplements deferred=True 在实例化时校验）
    client.jvm.start()
    window = DemoWindow(client)
    window.show()

    # Ctrl+C 处理（Qt 默认不响应）
    def _on_sigint(*_):
        print("\n>>> Ctrl+C received, shutting down...")
        window.close()
    signal.signal(signal.SIGINT, _on_sigint)

    # 关闭时清理
    def _on_about_to_quit():
        client.stop()
        client.jvm.shutdown()
    app.aboutToQuit.connect(_on_about_to_quit)

    # 启动 + executeLogin
    print(">>> 启动 JVM + executeLogin（拉二维码）...")
    try:
        qr_content = client.start()
    except Exception as e:
        print(f"FATAL: executeLogin 失败: {e}", file=sys.stderr)
        return 2

    # 保存并显示二维码
    qr_path = save_qr_to_file(qr_content.encode("utf-8"), args.qr_out)
    print(f">>> 二维码已保存: {qr_path}")
    print(">>> 请用手机微信扫码登录，登录成功后从手机发消息测试")
    window.status_label.setText(f"请扫码登录（二维码已存: {qr_path}）")
    window.show_qr(qr_content.encode("utf-8"))

    # 启动事件循环（保持 JVM 线程能触发回调）
    return app.exec()


def main() -> int:
    args = parse_args()
    if args.dry_run:
        return run_dry_run(args)
    return run_full(args)


if __name__ == "__main__":
    sys.exit(main())
