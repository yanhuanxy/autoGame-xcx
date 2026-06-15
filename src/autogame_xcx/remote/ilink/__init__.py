"""ilink SDK 集成子包（基于 JPype1）。

公共 API：
    JVMManager        — JVM 生命周期（懒加载、单例）
    ILinkClient       — Python 端门面（start / send_text / stop）
    PythonMessageListener / PythonLoginListener — Java 接口的 Python 实现
    weixin_to_python  — WeixinMessage Java 对象转 Python dict
"""
from autogame_xcx.remote.ilink._config import ILinkSdkConfig
from autogame_xcx.remote.ilink.client import ILinkClient
from autogame_xcx.remote.ilink.converters import weixin_to_python
from autogame_xcx.remote.ilink.jvm import JVMManager, find_jvm_dll
from autogame_xcx.remote.ilink.login_listener import PythonLoginListener
from autogame_xcx.remote.ilink.message_listener import PythonMessageListener

__all__ = [
    "ILinkSdkConfig",
    "JVMManager",
    "find_jvm_dll",
    "ILinkClient",
    "PythonMessageListener",
    "PythonLoginListener",
    "weixin_to_python",
]
