"""session 持久化测试（阶段 2.3）。"""
from __future__ import annotations

import tempfile
from pathlib import Path

from autogame_xcx.remote.session import SessionManager


def test_default_allowed_set() -> None:
    session = SessionManager(allowed={"wxid_a"}, admins={"wxid_admin"})
    assert session.is_allowed("wxid_a")
    assert not session.is_allowed("wxid_stranger")
    assert session.is_admin("wxid_admin")
    assert not session.is_admin("wxid_a")


def test_add_user_extends_whitelist() -> None:
    session = SessionManager(allowed={"wxid_a"})
    assert not session.is_allowed("wxid_b")
    session.add_user("wxid_b")
    assert session.is_allowed("wxid_b")


def test_add_admin_extends_admins() -> None:
    session = SessionManager()
    session.add_admin("wxid_root")
    assert session.is_admin("wxid_root")


def test_save_and_reload_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "whitelist.json"
        session = SessionManager(
            allowed={"wxid_a"},
            admins={"wxid_admin"},
            whitelist_path=path,
        )
        session.add_user("wxid_b")
        session.save()

        assert path.exists()
        loaded = SessionManager.from_json(path)
        assert loaded.is_allowed("wxid_a")
        assert loaded.is_allowed("wxid_b")
        assert loaded.is_admin("wxid_admin")
        assert not loaded.is_allowed("wxid_stranger")


def test_from_json_nonexistent_path_returns_empty() -> None:
    """读取不存在的文件应得到空 SessionManager（不抛异常）。"""
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "nonexistent.json"
        session = SessionManager.from_json(path)
        assert not session.is_allowed("anyone")
        assert not session.is_admin("anyone")
