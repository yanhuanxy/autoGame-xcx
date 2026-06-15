"""远程会话：用户白名单 + 最近上下文 token。

阶段 2.3 实现：
- is_allowed(user_id)：白名单校验
- 持久化到 JSON 文件（默认 data/config/remote_whitelist.json）

阶段 2.4+ 可能扩展：admin/user 角色分级、最近 N 条上下文 token 缓存。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SessionConfig:
    """远程控制配置。"""

    allowed_users: set[str] = field(default_factory=set)
    admin_users: set[str] = field(default_factory=set)
    whitelist_path: Path | None = None  # None 时不持久化

    def is_allowed(self, user_id: str) -> bool:
        """是否在白名单（普通或管理员）。"""
        return user_id in self.allowed_users or user_id in self.admin_users

    def is_admin(self, user_id: str) -> bool:
        return user_id in self.admin_users


class SessionManager:
    """白名单管理 + 可选 JSON 持久化。

    用法：
        # 内存模式（白名单通过参数注入，不持久化）
        session = SessionManager(allowed={"wxid_1", "wxid_2"})

        # 持久化模式（白名单存到 JSON，运行时可加可删）
        session = SessionManager.from_json(Path("data/config/remote_whitelist.json"))
        session.add_user("wxid_3")
        session.save()
    """

    def __init__(
        self,
        allowed: set[str] | None = None,
        admins: set[str] | None = None,
        whitelist_path: Path | None = None,
    ) -> None:
        self._config = SessionConfig(
            allowed_users=set(allowed or []),
            admin_users=set(admins or []),
            whitelist_path=whitelist_path,
        )

    @classmethod
    def from_json(cls, path: Path) -> SessionManager:
        """从 JSON 加载白名单。

        JSON 格式：
            {"allowed": ["wxid_1", ...], "admins": ["wxid_admin", ...]}
        """
        if not path.exists():
            logger.info("Whitelist not found, starting empty: %s", path)
            return cls(whitelist_path=path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load whitelist %s: %s", path, e)
            return cls(whitelist_path=path)
        return cls(
            allowed=set(data.get("allowed", [])),
            admins=set(data.get("admins", [])),
            whitelist_path=path,
        )

    def is_allowed(self, user_id: str) -> bool:
        return self._config.is_allowed(user_id)

    def is_admin(self, user_id: str) -> bool:
        return self._config.is_admin(user_id)

    def add_user(self, user_id: str) -> None:
        self._config.allowed_users.add(user_id)

    def add_admin(self, user_id: str) -> None:
        self._config.admin_users.add(user_id)

    def remove_user(self, user_id: str) -> None:
        self._config.allowed_users.discard(user_id)
        self._config.admin_users.discard(user_id)

    def save(self) -> None:
        """持久化到 JSON（whitelist_path 为 None 时是 no-op）。"""
        path = self._config.whitelist_path
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "allowed": sorted(self._config.allowed_users),
            "admins": sorted(self._config.admin_users),
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Whitelist saved to %s", path)

    def all_users(self) -> dict[str, list[str]]:
        """返回 {allowed: [...], admins: [...]}（用于 UI 显示）。"""
        return {
            "allowed": sorted(self._config.allowed_users),
            "admins": sorted(self._config.admin_users),
        }
