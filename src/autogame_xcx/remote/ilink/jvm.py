"""JVM 生命周期管理。

基于阶段 2.1 spike 验证过的实现（scripts/spike_jpype_ilink.py）。
关键点（详见 doc/plans/PLAN_02 §2.4 Spike 发现）：
- find_jvm_dll 三级 fallback（JAVA_HOME → java -XshowSettings → 默认）
- start() 必须把 deps_dir/*.jar 全部加入 classpath（避免 NoClassDefFoundError）
- 全局单例 + 线程安全
"""
from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
from shutil import which

import jpype

from autogame_xcx.remote.ilink._config import ILinkSdkConfig


def find_jvm_dll() -> str:
    """探测 jvm.dll 路径。

    Spike 发现：jpype.getDefaultJVMPath() 在 Windows 上仅查注册表 + JAVA_HOME，
    Microsoft JDK 用 .msi 装可能不写注册表，导致 JVMNotFoundException。
    """
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / "server" / "jvm.dll"
        if candidate.exists():
            return str(candidate)

    java_exe = (
        str(Path(java_home) / "bin" / "java.exe")
        if java_home
        else which("java")
    )
    if java_exe:
        try:
            out = subprocess.check_output(
                [java_exe, "-XshowSettings:properties", "-version"],
                stderr=subprocess.STDOUT,
                text=True,
                timeout=10,
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
    """全局唯一 JVM 实例，懒加载，PyQt 退出时优雅关闭。"""

    _instance: JVMManager | None = None
    _lock = threading.Lock()

    def __init__(self, config: ILinkSdkConfig):
        self.config = config
        self._started = False

    @classmethod
    def get(cls, config: ILinkSdkConfig | None = None) -> JVMManager:
        with cls._lock:
            if cls._instance is None:
                if config is None:
                    raise RuntimeError(
                        "JVM not initialized; config required on first call"
                    )
                cls._instance = cls(config)
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """测试用：清空单例（不会真关闭 JVM，JVM 一旦关闭无法在同一进程重启）。"""
        with cls._lock:
            cls._instance = None

    def start(self) -> None:
        if self._started:
            return
        if not self.config.jar_path.exists():
            raise FileNotFoundError(f"ilink SDK jar 不存在: {self.config.jar_path}")
        if not self.config.deps_dir.exists():
            raise FileNotFoundError(
                f"ilink SDK 依赖目录不存在: {self.config.deps_dir}\n"
                f"请在 wechat-ilink-sdk-java/ 下执行:\n"
                f"  mvn dependency:copy-dependencies "
                f"-DoutputDirectory=target/dependency -DincludeScope=runtime"
            )
        dep_jars = sorted(self.config.deps_dir.glob("*.jar"))
        if not dep_jars:
            raise FileNotFoundError(f"依赖目录为空: {self.config.deps_dir}")
        classpath = [str(self.config.jar_path)] + [str(p) for p in dep_jars]
        jpype.startJVM(
            find_jvm_dll(),
            *self.config.jvm_args,
            classpath=classpath,
            convertStrings=True,
        )
        self._started = True

    def shutdown(self) -> None:
        if self._started and jpype.isJVMStarted():
            jpype.shutdownJVM()
            self._started = False

    @property
    def is_started(self) -> bool:
        return self._started
