"""ilink SDK 集成的运行时配置。

不引入 pydantic-settings / yaml 等抽象（CLAUDE.md: Simplicity First）。
后续阶段如需 GUI 配置面板，再抽到 autogame_xcx.config 子包。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def _default_sdk_root() -> Path:
    """ilink SDK 工程根目录（同级目录推断）。

    __file__ = <wechat-ilink>/wechat-link-autogame-xcx/src/autogame_xcx/remote/ilink/_config.py
    parents[5] = <wechat-ilink>
    """
    return Path(__file__).resolve().parents[5] / "wechat-ilink-sdk-java"


@dataclass(frozen=True)
class ILinkSdkConfig:
    """ilink SDK 加载所需的路径与 JVM 参数。"""

    jar_path: Path
    deps_dir: Path
    jvm_args: tuple[str, ...] = ("-Djava.awt.headless=true",)

    @classmethod
    def default(cls, sdk_root: Path | None = None) -> ILinkSdkConfig:
        """从 SDK 工程根目录推断 jar + deps。

        Args:
            sdk_root: wechat-ilink-sdk-java 工程根目录。
                      None 时使用 _default_sdk_root() 推断同级目录。
        """
        root = sdk_root or _default_sdk_root()
        target = root / "target"
        # 优先 SNAPSHOT 版本（开发期），否则取最新非 SNAPSHOT
        jar = _pick_jar(target, prefer_snapshot=True)
        return cls(
            jar_path=jar,
            deps_dir=target / "dependency",
        )


def _pick_jar(target_dir: Path, prefer_snapshot: bool = True) -> Path:
    """从 target/ 下选 SDK jar。"""
    if not target_dir.exists():
        raise FileNotFoundError(
            f"ilink SDK target 目录不存在: {target_dir}\n"
            f"请先在 wechat-ilink-sdk-java/ 下执行 mvn package"
        )
    candidates = sorted(target_dir.glob("wechat-ilink-sdk-*.jar"))
    # 过滤 sources / javadoc
    candidates = [c for c in candidates if "-sources" not in c.name and "-javadoc" not in c.name]
    if not candidates:
        raise FileNotFoundError(f"未在 {target_dir} 找到 wechat-ilink-sdk-*.jar")

    if prefer_snapshot:
        for c in candidates:
            if "SNAPSHOT" in c.name:
                return c
    return candidates[-1]
