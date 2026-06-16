"""阶段 2.5 LLM 编排测试。

覆盖：
- build_orchestration_prompt：包含指令清单、用户原文、JSON 格式约束
- MockLlmProvider：按队列出响应、记录调用
- LLMOrchestrator：
  * 正常解析（2 个指令入队）
  * 单指令解析
  * JSON 解析失败（垃圾输入）
  * Markdown 围栏容错
  * action 不在白名单
  * 缺 action 字段
  * args 非 string
  * 空数组 [] → 提示"未能理解"
  * provider 异常隔离
- MessageRouter：非 # 消息 → orchestrator
"""
from __future__ import annotations

import pytest

from autogame_xcx.remote.commands import build_default_registry
from autogame_xcx.remote.commands.parser import ParsedCommand
from autogame_xcx.remote.llm import (
    MockLlmProvider,
    build_orchestration_prompt,
)
from autogame_xcx.remote.llm.orchestrator import _extract_json_array

# -------------------- prompt_templates 测试 --------------------


def test_prompt_contains_all_command_aliases() -> None:
    registry = build_default_registry()
    messages = build_orchestration_prompt("hi", registry.all_commands())
    assert messages[0]["role"] == "system"
    system = messages[0]["content"]
    # 至少 #run / #list / #status / #stop / #report / #help 都要出现
    for alias in ("#run", "#list", "#status", "#stop", "#report", "#help"):
        assert alias in system, f"prompt 缺少 {alias}"


def test_prompt_user_text_preserved_and_stripped() -> None:
    messages = build_orchestration_prompt("   帮我做签到   ", [])
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "帮我做签到"


def test_prompt_includes_json_format_constraint() -> None:
    messages = build_orchestration_prompt("hi", [])
    system = messages[0]["content"]
    assert "JSON" in system or "json" in system
    assert "数组" in system
    assert "action" in system


def test_prompt_examples_mention_run_and_status() -> None:
    messages = build_orchestration_prompt("hi", [])
    system = messages[0]["content"]
    assert "签到" in system  # 示例里出现
    assert "status" in system


# -------------------- MockLlmProvider 测试 --------------------


def test_mock_provider_returns_responses_in_order() -> None:
    provider = MockLlmProvider(responses=["first", "second"])
    assert provider.chat([{"role": "user", "content": "..."}]) == "first"
    assert provider.chat([{"role": "user", "content": "..."}]) == "second"


def test_mock_provider_returns_empty_when_responses_exhausted() -> None:
    provider = MockLlmProvider(responses=["only"])
    provider.chat([])
    assert provider.chat([]) == ""


def test_mock_provider_records_calls() -> None:
    provider = MockLlmProvider(responses=["ok"])
    provider.chat([{"role": "user", "content": "hello"}])
    assert len(provider.calls) == 1
    assert provider.calls[0][0]["content"] == "hello"


# -------------------- _extract_json_array 单元测试 --------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ('[{"action":"run"}]', '[{"action":"run"}]'),
        ('```json\n[{"action":"run"}]\n```', '[{"action":"run"}]'),
        ('好的，输出如下：\n[{"action":"run"}]\n以上', '[{"action":"run"}]'),
        ("not json at all", None),
        ("", None),
        ("   ", None),
        ("{}", None),  # 只有对象，没有数组
    ],
)
def test_extract_json_array(raw: str, expected: str | None) -> None:
    assert _extract_json_array(raw) == expected


# -------------------- LLMOrchestrator 正常路径 --------------------


def test_orchestrator_parses_two_commands_and_enqueues(make_orchestrator) -> None:  # type: ignore[no-untyped-def]
    response = (
        '[{"action": "run", "args": "签到"}, {"action": "run", "args": "领体力"}]'
    )
    orch, provider, sender, sched = make_orchestrator(responses=[response])

    result = orch.handle_natural_language("wxid_alice", "帮我把签到和领体力都做了")

    assert result.success is True
    assert len(result.commands) == 2
    assert result.commands[0].name == "RUN_TEMPLATE"
    assert result.commands[0].args == "签到"
    assert result.commands[1].args == "领体力"
    # 两条都入队
    assert len(sched.enqueued) == 2
    assert sched.enqueued[0][0] == "wxid_alice"
    # 回执包含"已规划 N 个指令"
    assert "已为您规划 2 个指令" in (sender.last_text() or "")


def test_orchestrator_single_command(make_orchestrator) -> None:  # type: ignore[no-untyped-def]
    response = '[{"action": "status", "args": ""}]'
    orch, _, sender, sched = make_orchestrator(responses=[response])

    result = orch.handle_natural_language("wxid_alice", "现在情况怎么样")

    assert result.success is True
    assert len(sched.enqueued) == 1
    user_id, parsed = sched.enqueued[0]
    assert user_id == "wxid_alice"
    assert isinstance(parsed, ParsedCommand)
    assert parsed.name == "STATUS"
    assert "已为您规划 1 个指令" in (sender.last_text() or "")


def test_orchestrator_accepts_chinese_alias(make_orchestrator) -> None:  # type: ignore[no-untyped-def]
    """LLM 用中文别名 '执行' 也应解析为 RUN_TEMPLATE。"""
    response = '[{"action": "执行", "args": "签到"}]'
    orch, _, _, sched = make_orchestrator(responses=[response])
    result = orch.handle_natural_language("wxid_alice", "做签到")
    assert result.success is True
    assert result.commands[0].name == "RUN_TEMPLATE"


# -------------------- LLMOrchestrator 错误路径 --------------------


def test_orchestrator_rejects_unknown_action(make_orchestrator) -> None:  # type: ignore[no-untyped-def]
    response = '[{"action": "delete_database", "args": "all"}]'
    orch, _, sender, sched = make_orchestrator(responses=[response])

    result = orch.handle_natural_language("wxid_alice", "清空所有数据")

    assert result.success is False
    assert len(result.commands) == 0
    assert len(sched.enqueued) == 0  # 拒绝后不入队
    reply = sender.last_text() or ""
    assert "不在白名单" in reply or "delete_database" in reply


def test_orchestrator_rejects_garbage_response(make_orchestrator) -> None:  # type: ignore[no-untyped-def]
    orch, _, sender, sched = make_orchestrator(responses=["这不是 JSON"])

    result = orch.handle_natural_language("wxid_alice", "随便说说")

    assert result.success is False
    assert len(sched.enqueued) == 0
    assert "格式异常" in (sender.last_text() or "")


def test_orchestrator_rejects_partial_json(make_orchestrator) -> None:  # type: ignore[no-untyped-def]
    """JSON 数组本身解析失败（方括号闭合但内容不合法）。"""
    response = '[this is not valid json]'  # 有 [ ] 但中间不是 JSON
    orch, _, sender, sched = make_orchestrator(responses=[response])

    result = orch.handle_natural_language("wxid_alice", "做签到")

    assert result.success is False
    assert len(sched.enqueued) == 0
    assert "JSON 解析失败" in (sender.last_text() or "")


def test_orchestrator_rejects_non_string_args(make_orchestrator) -> None:  # type: ignore[no-untyped-def]
    response = '[{"action": "run", "args": 123}]'
    orch, _, sender, sched = make_orchestrator(responses=[response])

    result = orch.handle_natural_language("wxid_alice", "做签到")

    assert result.success is False
    assert "args 必须是字符串" in (sender.last_text() or "")


def test_orchestrator_rejects_missing_action(make_orchestrator) -> None:  # type: ignore[no-untyped-def]
    response = '[{"args": "签到"}]'
    orch, _, sender, sched = make_orchestrator(responses=[response])

    result = orch.handle_natural_language("wxid_alice", "做签到")

    assert result.success is False
    assert "缺少 action" in (sender.last_text() or "")


def test_orchestrator_handles_markdown_fence(make_orchestrator) -> None:  # type: ignore[no-untyped-def]
    response = '```json\n[{"action": "run", "args": "签到"}]\n```'
    orch, _, _, sched = make_orchestrator(responses=[response])

    result = orch.handle_natural_language("wxid_alice", "做签到")

    assert result.success is True
    assert len(sched.enqueued) == 1


def test_orchestrator_empty_array_hint(make_orchestrator) -> None:  # type: ignore[no-untyped-def]
    """LLM 返回 [] 表示无法映射；应回执 #help 提示。"""
    orch, _, sender, sched = make_orchestrator(responses=["[]"])

    result = orch.handle_natural_language("wxid_alice", "讲个笑话")

    assert result.success is False
    assert len(sched.enqueued) == 0
    assert "未能理解" in (sender.last_text() or "")


def test_orchestrator_provider_exception_isolated(make_orchestrator) -> None:  # type: ignore[no-untyped-def]
    """provider.chat 抛异常 → orchestrator 捕获并回执"AI 调用失败"。"""
    orch, provider, sender, sched = make_orchestrator(responses=[])

    def _boom(_messages: list[dict]) -> str:
        raise RuntimeError("network down")

    provider.chat = _boom  # type: ignore[method-assign]
    result = orch.handle_natural_language("wxid_alice", "做签到")

    assert result.success is False
    assert len(sched.enqueued) == 0
    assert "AI 调用失败" in (sender.last_text() or "")


def test_orchestrator_sends_exactly_one_reply_on_failure(make_orchestrator) -> None:  # type: ignore[no-untyped-def]
    """失败路径只回执一次（避免多次 send_text 刷屏）。"""
    orch, _, sender, _ = make_orchestrator(responses=["not json"])
    orch.handle_natural_language("wxid_alice", "随便")
    assert len(sender.sent) == 1


# -------------------- Router 集成测试 --------------------


def test_router_dispatches_natural_language_to_orchestrator(make_orchestrator, make_router) -> None:  # type: ignore[no-untyped-def]
    """非 # 消息：router 应转给 orchestrator；orchestrator 入队 + 回执。"""
    # 先建 router 拿到共享 sender，再用同一个 sender 建 orchestrator 注入回去。
    # 真实部署里 router 和 orchestrator 共用同一个 ILinkClient sender。
    router, sender, _ = make_router()
    response = '[{"action": "list", "args": ""}]'
    orch, _, _, sched = make_orchestrator(responses=[response], sender=sender)
    router.llm_orchestrator = orch

    router.route("wxid_alice", "列出所有模板")

    # orchestrator 入队 1 条
    assert len(sched.enqueued) == 1
    # 共享 sender 上能看到回执
    assert "已为您规划 1 个指令" in (sender.last_text() or "")


def test_router_without_orchestrator_ignores_natural_language(make_router) -> None:  # type: ignore[no-untyped-def]
    """未注入 orchestrator 时，非 # 消息被静默忽略（不抛异常）。"""
    router, sender, _ = make_router()
    router.route("wxid_alice", "随便聊聊")
    assert len(sender.sent) == 0


def test_router_hash_message_bypasses_orchestrator(make_orchestrator, make_router) -> None:  # type: ignore[no-untyped-def]
    """# 消息即使注入了 orchestrator 也走指令系统，不打扰 LLM。"""
    response = '[{"action": "list", "args": ""}]'
    orch, provider, _, _ = make_orchestrator(responses=[response])
    router, sender, _ = make_router(llm_orchestrator=orch)

    router.route("wxid_alice", "#help")

    # orchestrator 没被调用（provider.calls 为空）
    assert len(provider.calls) == 0
    # 走指令系统的 #help 回执
    assert "可用指令" in (sender.last_text() or "")
