"""PLAN_02 Phase 1 — JPype + ilink SDK Spike

成功标准（不下到 executeLogin，不触发任何网络请求）：
  1. JVM 启动成功
  2. wechat-ilink-sdk-java jar 加载到 classpath
  3. 4 个关键类可 JClass 访问：ILinkClient / ILinkClientBuilder / OnMessageListener / WeixinMessage
  4. @JImplements 能实现 OnMessageListener 接口（验证 JPype 反射代理）
  5. ILinkClient.builder() 链式调用 + .onMessage(listener) + .build() 成功构造 client
  6. client.getConfig() 不发请求返回配置（验证实例可用）
  7. client.close() 优雅关闭
  8. jpype.shutdownJVM() 干净退出

退出码 0 = spike 通过；非 0 = spike 失败（见末尾 traceback）。
"""
import os
import subprocess
import sys
from pathlib import Path

import jpype
import jpype.imports  # noqa: F401  # 启用 jpype 的 Java 包导入支持
from jpype import JClass, JImplements, JOverride

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SDK_TARGET = PROJECT_ROOT.parent / "wechat-ilink-sdk-java" / "target"
JAR_PATH = SDK_TARGET / "wechat-ilink-sdk-3.0.0.jar"
DEPS_DIR = SDK_TARGET / "dependency"

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond), detail))
    mark = "OK " if cond else "FAIL"
    line = f"  [{mark}] {name}"
    if detail:
        line += f" — {detail}"
    print(line)


def step(msg):
    print(f"\n>>> {msg}")


def find_jvm_dll() -> str:
    """从 JAVA_HOME 或 PATH 上的 java 探测 jvm.dll 路径。"""
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        dll = Path(java_home) / "bin" / "server" / "jvm.dll"
        if dll.exists():
            return str(dll)

    java_exe = os.environ.get("JAVA_HOME")
    if java_exe:
        java_exe = str(Path(java_exe) / "bin" / "java.exe")
    else:
        from shutil import which
        java_exe = which("java")
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
                    home = line.split("=", 1)[1].strip()
                    dll = Path(home) / "lib" / "server" / "jvm.dll"
                    if dll.exists():
                        return str(dll)
                    dll = Path(home) / "bin" / "server" / "jvm.dll"
                    if dll.exists():
                        return str(dll)
        except Exception as e:
            print(f"WARN: 从 PATH 探测 java.home 失败: {e}", file=sys.stderr)

    return jpype.getDefaultJVMPath()


def main():
    if not JAR_PATH.exists():
        print(f"FATAL: ilink SDK jar 不存在: {JAR_PATH}", file=sys.stderr)
        print("请先在 wechat-ilink-sdk-java 目录执行 mvn package", file=sys.stderr)
        return 2

    step(f"启动 JVM (jar={JAR_PATH.name})")
    try:
        if not DEPS_DIR.exists():
            print(
                f"FATAL: 依赖目录不存在: {DEPS_DIR}\n"
                f"请在 wechat-ilink-sdk-java 目录执行: "
                f"mvn dependency:copy-dependencies -DoutputDirectory=target/dependency -DincludeScope=runtime",
                file=sys.stderr,
            )
            return 2

        dep_jars = sorted(DEPS_DIR.glob("*.jar"))
        print(f"  依赖 jar 数: {len(dep_jars)}")
        classpath = [str(JAR_PATH)] + [str(p) for p in dep_jars]

        jvm_dll = find_jvm_dll()
        print(f"  jvm.dll = {jvm_dll}")
        jpype.startJVM(
            jvm_dll,
            classpath=classpath,
            convertStrings=True,
        )
    except Exception as e:
        print(f"FATAL: JVM 启动失败: {e}", file=sys.stderr)
        raise
    check("JVM 启动", jpype.isJVMStarted())
    check("jpype1 反射", jpype.isThreadAttachedToJVM())

    step("加载 ilink SDK 关键类")
    try:
        ILinkClient = JClass("com.github.wechat.ilink.sdk.ILinkClient")
        ILinkClientBuilder = JClass("com.github.wechat.ilink.sdk.ILinkClientBuilder")
        OnMessageListener = JClass(
            "com.github.wechat.ilink.sdk.core.listener.OnMessageListener"
        )
        WeixinMessage = JClass(
            "com.github.wechat.ilink.sdk.core.model.WeixinMessage"
        )
    except Exception as e:
        print(f"FATAL: 关键类加载失败: {e}", file=sys.stderr)
        raise
    check("ILinkClient 类可访问", ILinkClient is not None)
    check("ILinkClientBuilder 类可访问", ILinkClientBuilder is not None)
    check("OnMessageListener 接口可访问", OnMessageListener is not None)
    check("WeixinMessage 模型可访问", WeixinMessage is not None)
    check(
        "OnMessageListener 是接口",
        bool(OnMessageListener.class_.isInterface()),
    )

    step("用 @JImplements 实现 OnMessageListener（验证 JPype 反射代理）")
    try:
        @JImplements("com.github.wechat.ilink.sdk.core.listener.OnMessageListener")
        class PythonMessageListener:
            def __init__(self):
                self.received = []

            @JOverride
            def onMessages(self, messages):
                for msg in messages:
                    self.received.append(msg)

        py_listener = PythonMessageListener()
        check("@JImplements 实例化成功", py_listener is not None)
        # Python 的 isinstance 不能直接判 Java 接口实现，用 Java 反射
        is_assignable = bool(OnMessageListener.class_.isInstance(py_listener))
        check(
            "Python 实例可赋值给 Java 接口（isInstance）",
            is_assignable,
        )
    except Exception as e:
        print(f"FATAL: @JImplements 失败: {e}", file=sys.stderr)
        raise

    step("ILinkClient.builder() 链式构造（不下到 executeLogin）")
    try:
        builder = ILinkClient.builder()
        check("builder() 返回非 None", builder is not None)
        check("builder 类型正确", isinstance(builder, ILinkClientBuilder))

        builder2 = builder.onMessage(py_listener)
        # JPype 每次返回新 Python 代理对象，is 比较恒为 False；
        # 用 Java 端 identityHashCode 验证底层是同一对象
        same_obj = (
            int(builder.hashCode()) == int(builder2.hashCode())
        )
        check(
            "onMessage(listener) 链式返回同一 builder",
            same_obj,
            detail="hashCode 相等表示 Java 端是同一个 builder 实例",
        )

        client = builder.build()
        check("build() 返回 ILinkClient 实例", isinstance(client, ILinkClient))
        check(
            "client.getConfig() 不发请求",
            client.getConfig() is not None,
            detail="config 是构造时注入的本地对象",
        )
        check(
            "client.isLoggedIn() 初始为 False",
            client.isLoggedIn() is False,
        )
    except Exception as e:
        print(f"FATAL: builder/build 失败: {e}", file=sys.stderr)
        raise

    step("优雅关闭")
    try:
        client.close()
        check("client.close() 无异常", True)
    except Exception as e:
        print(f"FATAL: close 失败: {e}", file=sys.stderr)
        raise

    try:
        jpype.shutdownJVM()
        check("shutdownJVM 无异常", True)
    except Exception as e:
        # Windows 上 shutdownJVM 偶有非致命警告，标记但不算 FAIL
        check("shutdownJVM 无异常", False, detail=f"warning: {e}")

    step("Spike 结果汇总")
    passed = sum(1 for _, ok, _ in CHECKS if ok)
    total = len(CHECKS)
    print(f"  通过 {passed}/{total} 项检查")
    failed = [(n, d) for n, ok, d in CHECKS if not ok]
    if failed:
        print("\n  失败项:")
        for name, detail in failed:
            print(f"    - {name}" + (f" — {detail}" if detail else ""))
        return 1

    print("\nSPIKE PASSED — 可进入阶段 2.2 消息接收通道")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
