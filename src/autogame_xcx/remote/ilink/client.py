"""Python 端的 ilink 客户端门面。

封装 ILinkClientBuilder + ILinkClient，提供 Python 友好的 API。
不直接暴露 Java 对象；发送消息时用 Python 类型，接收消息通过 listener 信号。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from autogame_xcx.remote.ilink._config import ILinkSdkConfig
from autogame_xcx.remote.ilink.jvm import JVMManager
from autogame_xcx.remote.ilink.login_listener import PythonLoginListener
from autogame_xcx.remote.ilink.message_listener import PythonMessageListener

logger = logging.getLogger(__name__)


class ILinkClient:
    """ilink 客户端门面（Python 视角）。

    生命周期：
        client = ILinkClient()              # 配置默认从同级 SDK 工程推断
        client.start()                      # 启动 JVM + 构造 client + 执行登录
        # 订阅信号必须在 start() 之后（listener 实例化要求 JVM 已启动）
        client.message_listener.message_received.connect(slot)
        client.send_text(user_id, "hello")
        client.stop()                       # 关闭 SDK client（JVM 由 JVMManager 管理）
    """

    def __init__(self, config: ILinkSdkConfig | None = None):
        self.config = config or ILinkSdkConfig.default()
        self.jvm = JVMManager.get(self.config)
        # listener 延迟创建：@JImplements deferred=True 在实例化时校验接口，
        # 实例化要求 JVM 已启动。所以放 lazy property 里。
        self._message_listener: PythonMessageListener | None = None
        self._login_listener: PythonLoginListener | None = None
        self._client: Any = None  # com.github.wechat.ilink.sdk.ILinkClient

    @property
    def message_listener(self) -> PythonMessageListener:
        if self._message_listener is None:
            if not self.jvm.is_started:
                raise RuntimeError(
                    "JVM not started; call start() before accessing message_listener"
                )
            self._message_listener = PythonMessageListener()
        return self._message_listener

    @property
    def login_listener(self) -> PythonLoginListener:
        if self._login_listener is None:
            if not self.jvm.is_started:
                raise RuntimeError(
                    "JVM not started; call start() before accessing login_listener"
                )
            self._login_listener = PythonLoginListener()
        return self._login_listener

    @property
    def java_client(self) -> Any:
        """直接访问底层 Java ILinkClient（高级用法）。"""
        return self._client

    def start(self) -> str:
        """启动 JVM + 构造 client + 执行登录，返回二维码内容（base64 image content）。

        Raises:
            FileNotFoundError: jar 或依赖目录不存在
            RuntimeError: Java 端构造/登录失败
        """
        self.jvm.start()
        # 触发 listener lazy init（JVM 已启动，可安全创建）
        _ = self.message_listener
        _ = self.login_listener
        if self._client is None:
            self._client = self._build_client()
        qr_content = self._client.executeLogin()
        logger.info("ilink client started, QR content returned (len=%d)", len(str(qr_content)))
        return str(qr_content)

    def request_qr_code(self) -> tuple[str, bytes]:
        """仅请求二维码不进入登录轮询（用于"先展示二维码再决定扫码"场景）。

        Returns:
            (qr_url, qr_image_bytes)
        """
        self.jvm.start()
        _ = self.message_listener
        _ = self.login_listener
        if self._client is None:
            self._client = self._build_client()
        response = self._client.requestQRCode()
        qr_url = str(response.getQrcode())
        # QRCodeResponse.getQrcodeImgContent() 返回二维码图片字节
        img_bytes = bytes(response.getQrcodeImgContent())
        return qr_url, img_bytes

    def send_text(self, user_id: str, text: str) -> None:
        """发送文本消息。

        Raises:
            RuntimeError: client 未启动
            java.io.IOException: SDK 端发送失败（会被 JPype 转为 Python 异常）
        """
        if self._client is None:
            raise RuntimeError("Client not started; call start() first")
        self._client.sendText(user_id, text)

    def send_image(
        self,
        user_id: str,
        image_bytes: bytes,
        file_name: str = "image.jpg",
        caption: str = "",
    ) -> None:
        """发送图片消息。"""
        if self._client is None:
            raise RuntimeError("Client not started; call start() first")
        self._client.sendImage(user_id, image_bytes, file_name, caption)

    def send_file(
        self,
        user_id: str,
        file_bytes: bytes,
        file_name: str,
        caption: str = "",
    ) -> None:
        """发送文件消息。"""
        if self._client is None:
            raise RuntimeError("Client not started; call start() first")
        self._client.sendFile(user_id, file_bytes, file_name, caption)

    def is_logged_in(self) -> bool:
        """是否已登录。"""
        return bool(self._client.isLoggedIn()) if self._client else False

    def cancel_login(self) -> None:
        """取消正在进行的登录轮询。"""
        if self._client is not None:
            self._client.cancelLogin()

    def stop(self) -> None:
        """优雅停止 client（关闭长轮询、清理上下文）。

        注意：JVM 本身由 JVMManager 管理，不在这里关闭。
        GUI 退出时通过 JVMManager.shutdown() 关。
        """
        if self._client is not None:
            try:
                self._client.close()
                logger.info("ilink client closed")
            except Exception as e:
                logger.warning("ilink client close error: %s", e)
            self._client = None

    def _build_client(self) -> Any:
        """构造 ILinkClient Java 实例（链式 builder）。"""
        from jpype import JClass

        builder_cls = JClass("com.github.wechat.ilink.sdk.ILinkClientBuilder")
        return (
            builder_cls()
            .onMessage(self.message_listener)
            .onLogin(self.login_listener)
            .build()
        )


def save_qr_to_file(qr_image_bytes: bytes, output_path: Path | str) -> Path:
    """把二维码字节流写入文件（方便用户扫码）。

    ilink SDK 的 executeLogin() 返回的是 base64 编码的图片内容（data URI），
    需要先解码。本函数处理两种格式：
    - "data:image/png;base64,..."  → 去掉前缀后 base64 解码
    - 直接二进制 → 原样写入
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    content = qr_image_bytes
    if isinstance(content, str):
        content = content.encode("utf-8")

    # 检测 data URI 前缀
    if content.startswith(b"data:") and b"base64," in content:
        import base64
        payload = content.split(b"base64,", 1)[1]
        output_path.write_bytes(base64.b64decode(payload))
    else:
        # 可能本身是 base64（无 data URI 前缀）
        try:
            import base64
            decoded = base64.b64decode(content, validate=True)
            # 用解码后大小判断：PNG 头是 \x89PNG
            if decoded[:4] == b"\x89PNG":
                output_path.write_bytes(decoded)
                return output_path
        except Exception:
            pass
        output_path.write_bytes(content)
    return output_path
