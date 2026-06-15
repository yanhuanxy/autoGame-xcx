"""Python 实现 Java 的 OnMessageListener 接口。

SDK 在 JVM 线程回调 onMessages，不能直接操作 QWidget，
必须通过 pyqtSignal 转主线程。

Spike 发现（§2.4 发现 4）：@JImplements 类不能继承 QObject（元类冲突），
所以信号必须放在独立的 _SignalCarrier 里。
"""
from __future__ import annotations

import logging

from jpype import JImplements, JOverride
from PyQt6.QtCore import QObject, pyqtSignal

from autogame_xcx.remote.ilink.converters import weixin_to_python

logger = logging.getLogger(__name__)


class _SignalCarrier(QObject):
    """单独的 QObject 持有信号。

    @JImplements 修饰的类不能多继承（元类冲突），
    所以 listener 内部持有这个 carrier，外部订阅 carrier 的信号即可。
    """

    message_received = pyqtSignal(dict)
    message_error = pyqtSignal(str)


@JImplements(
    "com.github.wechat.ilink.sdk.core.listener.OnMessageListener",
    deferred=True,
)
class PythonMessageListener:
    """实现 Java 的 OnMessageListener 接口。

    用法：
        listener = PythonMessageListener()
        listener.message_received.connect(your_qt_slot)  # 主线程订阅
        builder.onMessage(listener)
    """

    def __init__(self):
        self._carrier = _SignalCarrier()
        self.message_received = self._carrier.message_received
        self.message_error = self._carrier.message_error

    @JOverride
    def onMessages(self, messages):  # noqa: N802 Java 接口名风格
        """SDK 在 JVM 线程触发，转主线程。"""
        try:
            for msg in messages:
                try:
                    py_msg = weixin_to_python(msg)
                except Exception as e:
                    logger.exception("Failed to convert WeixinMessage")
                    self.message_error.emit(f"convert error: {e}")
                    continue
                self.message_received.emit(py_msg)
        except Exception as e:
            logger.exception("PythonMessageListener.onMessages crashed")
            self.message_error.emit(f"listener error: {e}")
