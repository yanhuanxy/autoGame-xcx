"""Python 实现 Java 的 OnLoginListener 接口。

ILinkClient.executeLogin() 异步触发登录流程：
- 成功：onLoginSuccess(LoginContext)
- 失败：onLoginFailure(Throwable)

结果通过 pyqtSignal 暴露，主线程订阅后可更新 UI 状态指示灯等。
"""
from __future__ import annotations

import logging

from jpype import JImplements, JOverride
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class _LoginSignalCarrier(QObject):
    login_success = pyqtSignal(object)  # LoginContext Java 对象
    login_failure = pyqtSignal(str)     # 错误消息


@JImplements(
    "com.github.wechat.ilink.sdk.core.listener.OnLoginListener",
    deferred=True,
)
class PythonLoginListener:
    """实现 Java 的 OnLoginListener 接口。"""

    def __init__(self):
        self._carrier = _LoginSignalCarrier()
        self.login_success = self._carrier.login_success
        self.login_failure = self._carrier.login_failure

    @JOverride
    def onLoginSuccess(self, login_context):  # noqa: N802
        logger.info("ilink login success")
        self.login_success.emit(login_context)

    @JOverride
    def onLoginFailure(self, cause):  # noqa: N802
        msg = str(cause) if cause is not None else "unknown"
        logger.warning("ilink login failure: %s", msg)
        self.login_failure.emit(msg)
