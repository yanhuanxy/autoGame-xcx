"""指令调度器：单线程消费队列。

阶段 2.4 核心目的：保证同一时刻只有一个指令在执行，避免窗口操作冲突。
所有 # 指令经 CommandQueue 串行消费。

不引入 state.py（PLAN_02 §4 提到但当前阶段不需要 task_id 历史）。
按 CLAUDE.md "Simplicity First"，task_id 历史在阶段 2.5+ 真正需要时再加。
"""
from autogame_xcx.remote.scheduler.queue import CommandQueue

__all__ = ["CommandQueue"]
