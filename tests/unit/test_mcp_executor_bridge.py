"""ExecutorBridge 单元测试（Task #1）。

用最小 mock 替代 GameExecutor/TemplateManager，验证：
- list_templates 透传
- run_template 命中模板路径，串行执行，记录 last_report
- run_template 模板不存在时抛 ValueError
- get_status 在空闲时正确返回
- get_report 在未执行过时返回空 dict
"""

from __future__ import annotations

import pytest

from autogame_xcx.mcp import ExecutorBridge


class _MockTemplateManager:
    def __init__(self, templates: list[dict] | None = None) -> None:
        self._templates = templates or []

    def list_templates(self) -> list[dict]:
        return list(self._templates)


class _MockExecutor:
    def __init__(self, *, succeed: bool = True) -> None:
        self.succeed = succeed
        self.calls: list[str] = []
        self.execution_report: dict = {}

    def execute_template(self, filepath: str) -> bool:
        self.calls.append(filepath)
        self.execution_report = {
            "template_info": {"name": "签到"},
            "summary": {
                "total_tasks": 2,
                "completed": 2,
                "failed": 0,
                "success_rate": "100.0%",
            },
        }
        return self.succeed


def _make_bridge(
    templates: list[dict] | None = None, *, succeed: bool = True
) -> tuple[ExecutorBridge, _MockExecutor]:
    executor = _MockExecutor(succeed=succeed)
    tm = _MockTemplateManager(templates)
    return ExecutorBridge(executor=executor, template_manager=tm), executor


def test_list_templates_passes_through() -> None:
    bridge, _ = _make_bridge(templates=[{"name": "签到", "filepath": "/a/b.json"}])
    templates = bridge.list_templates()
    assert len(templates) == 1
    assert templates[0]["name"] == "签到"


def test_run_template_dispatches_to_executor() -> None:
    bridge, executor = _make_bridge(
        templates=[{"name": "签到", "filepath": "/tmp/qiandao.json"}],
    )
    result = bridge.run_template("签到")
    assert executor.calls == ["/tmp/qiandao.json"]
    assert result["template"] == "签到"
    assert result["success"] is True
    assert result["summary"]["completed"] == 2
    assert result["summary"]["success_rate"] == "100.0%"


def test_run_template_unknown_name_raises_value_error() -> None:
    bridge, executor = _make_bridge(templates=[{"name": "签到", "filepath": "/x.json"}])
    with pytest.raises(ValueError, match="模板不存在"):
        bridge.run_template("不存在的模板")
    assert executor.calls == []  # 不应调 executor


def test_run_template_executor_failure_propagates() -> None:
    bridge, executor = _make_bridge(templates=[{"name": "签到", "filepath": "/x.json"}])
    executor.succeed = False
    result = bridge.run_template("签到")
    assert result["success"] is False


def test_get_status_idle_initially() -> None:
    bridge, _ = _make_bridge()
    status = bridge.get_status()
    assert status["running"] is False
    assert status["current_template"] is None
    assert status["last_template"] is None


def test_get_status_after_run_records_last_template() -> None:
    bridge, _ = _make_bridge(templates=[{"name": "签到", "filepath": "/x.json"}])
    bridge.run_template("签到")
    status = bridge.get_status()
    assert status["running"] is False  # run_template 已返回，不在执行中
    assert status["last_template"] == "签到"


def test_get_report_empty_before_any_run() -> None:
    bridge, _ = _make_bridge()
    assert bridge.get_report() == {}


def test_get_report_returns_last_execution_report() -> None:
    bridge, _ = _make_bridge(templates=[{"name": "签到", "filepath": "/x.json"}])
    bridge.run_template("签到")
    report = bridge.get_report()
    assert report["template_info"]["name"] == "签到"
    assert report["summary"]["completed"] == 2


def test_stop_execution_returns_reason() -> None:
    bridge, _ = _make_bridge()
    result = bridge.stop_execution()
    assert result["stopped"] is False
    assert "reason" in result


def test_run_template_records_caller_visible_via_status_during_execution() -> None:
    """迭代C：run_template 执行期间，get_status 应能看到发起方 caller。"""
    captured: dict = {}
    bridge_ref: list = [None]

    class _ObservingExecutor(_MockExecutor):
        def execute_template(self, filepath: str) -> bool:
            captured["status"] = bridge_ref[0].get_status()
            return super().execute_template(filepath)

    executor = _ObservingExecutor()
    tm = _MockTemplateManager([{"name": "签到", "filepath": "/x.json"}])
    bridge = ExecutorBridge(executor=executor, template_manager=tm)
    bridge_ref[0] = bridge

    bridge.run_template("签到", caller="bot1")

    assert captured["status"]["running"] is True
    assert captured["status"]["caller"] == "bot1"


def test_get_status_caller_clears_after_run_completes() -> None:
    bridge, _ = _make_bridge(templates=[{"name": "签到", "filepath": "/x.json"}])
    bridge.run_template("签到", caller="bot1")
    status = bridge.get_status()
    assert status["running"] is False
    assert status["caller"] is None


def test_stop_execution_wrongCaller_duringRun_rejectedAsUnauthorized() -> None:
    """迭代C：非发起方在任务运行期间请求停止，应被拒绝（越权），而不是走"不支持中断"的通用回复。"""
    captured: dict = {}
    bridge_ref: list = [None]

    class _ObservingExecutor(_MockExecutor):
        def execute_template(self, filepath: str) -> bool:
            captured["stop_by_other"] = bridge_ref[0].stop_execution(caller="bot2")
            return super().execute_template(filepath)

    executor = _ObservingExecutor()
    tm = _MockTemplateManager([{"name": "签到", "filepath": "/x.json"}])
    bridge = ExecutorBridge(executor=executor, template_manager=tm)
    bridge_ref[0] = bridge

    bridge.run_template("签到", caller="bot1")

    assert captured["stop_by_other"]["stopped"] is False
    assert "无权" in captured["stop_by_other"]["reason"]
    assert "bot1" in captured["stop_by_other"]["reason"]


def test_stop_execution_sameCaller_duringRun_notRejectedAsUnauthorized() -> None:
    """发起方本人请求停止：越权校验放行，落到 GameExecutor 不支持中断的既有 stub 回复。"""
    captured: dict = {}
    bridge_ref: list = [None]

    class _ObservingExecutor(_MockExecutor):
        def execute_template(self, filepath: str) -> bool:
            captured["stop_by_owner"] = bridge_ref[0].stop_execution(caller="bot1")
            return super().execute_template(filepath)

    executor = _ObservingExecutor()
    tm = _MockTemplateManager([{"name": "签到", "filepath": "/x.json"}])
    bridge = ExecutorBridge(executor=executor, template_manager=tm)
    bridge_ref[0] = bridge

    bridge.run_template("签到", caller="bot1")

    assert captured["stop_by_owner"]["stopped"] is False
    assert "不支持中断" in captured["stop_by_owner"]["reason"]


def test_stop_execution_idle_ignoresCaller() -> None:
    """没有任务在跑时（owner=None），任何 caller 都不算越权，走通用 stub 回复。"""
    bridge, _ = _make_bridge()
    result = bridge.stop_execution(caller="anyone")
    assert result["stopped"] is False
    assert "不支持中断" in result["reason"]


def test_list_templates_failure_raises_runtime_error() -> None:
    class _Broken:
        def list_templates(self):
            raise OSError("disk gone")

    bridge = ExecutorBridge(executor=_MockExecutor(), template_manager=_Broken())  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="读取模板列表失败"):
        bridge.list_templates()
