"""wechat-link-autogame-xcx：微信小程序游戏自动化系统。

三层架构：
    - 本地执行层（core/ + platform/ + ocr/）：图像匹配 + DPI 自适应坐标转换 + DGOCR
    - 远程驱动层（remote/ilink + remote/commands + remote/scheduler）：JPype1 集成 ilink SDK，
      `#指令` 解析 + 串行调度
    - LLM 编排层（remote/llm + remote/llm_config）：自然语言 → 指令队列（白名单校验）

入口：
    - GUI: `python start_main_gui.py`
    - CLI: `python -m autogame_xcx.core.process_main --test all`
"""

__version__ = "0.2.0"
