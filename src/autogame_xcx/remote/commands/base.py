"""Command 抽象基类、上下文、结果。

按 CLAUDE.md "Simplicity First"：不引入 exceptions.py，用 RuntimeError。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol


class _Sender(Protocol):
    """发送回执的最小协议。

    实际实现是 ILinkClient（remote/ilink/client.py）或测试 mock。
    """

    def send_text(self, user_id: str, text: str) -> None: ...


@dataclass
class CommandContext:
    """指令执行的上下文。

    指令通过这个对象访问本地能力（执行器 / 模板管理 / 报告）与远程通道（sender）。
    """

    user_id: str                            # 微信发送者 ID
    raw_text: str                           # 原始消息文本（含 # 前缀）
    executor: Any                           # GameExecutor 实例
    template_manager: Any                   # TemplateManager 实例
    sender: _Sender                         # 回传通道（ILinkClient.send_text）
    state: dict[str, Any] = field(default_factory=dict)  # 跨指令共享状态


@dataclass
class CommandResult:
    """指令执行结果。

    success=True 时 message 是给用户的回复；
    success=False 时 message 是错误描述（同样回传给用户）。
    payload 仅供日志/调度器使用，不直接发给用户。
    """

    success: bool
    message: str = ""
    payload: dict[str, Any] | None = None


class Command(ABC):
    """指令基类。

    子类必须设置类属性 name / aliases / description / usage，
    并实现 execute(ctx, args)。
    """

    name: str = ""                # 规范指令名（如 RUN_TEMPLATE）
    aliases: list[str] = []       # 别名（如 "run"、"执行"）
    description: str = ""
    usage: str = ""
    queued_dispatch: bool = False  # True=走调度器串行队列（长任务，如 #run）；
                                   # False=router 直接 dispatch（控制类指令如 #status/#stop）

    @abstractmethod
    def execute(self, ctx: CommandContext, args: str) -> CommandResult:
        """执行指令。

        Args:
            ctx: 指令上下文。
            args: #command 后面的所有文本（已 strip，可能为空字符串）。
        """
        ...

    @classmethod
    def help_text(cls) -> str:
        """生成给用户的帮助文本。"""
        aliases = "/".join(["#" + a for a in cls.aliases]) if cls.aliases else ""
        line = f"{aliases}  {cls.description}" if aliases else cls.description
        if cls.usage:
            line += f"\n  用法：{cls.usage}"
        return line
