"""Categorization / group-topic management for the panel.

Lets the user pick a target forum group, browse its topics, and map
command -> topic (so the live monitoring handler files replied-to messages into
the right topic). READ-ONLY on Telegram (forwarding happens only in the live
handler, never here) — it just reads groups/topics and writes settings.json.
"""

from typing import Any, Dict, List

from ...cli.utils import normalize_command_mappings
from ...utils.logging import get_logger
from ..errors import PanelError, PanelUnavailable

logger = get_logger(__name__)


class GroupService:
    def __init__(self, state: Any) -> None:
        self.state = state

    async def list_groups(self) -> Dict[str, Any]:
        data = await self.state.dialogs.list_dialogs(kind="group")
        items = [
            {
                "id": g["id"],
                "title": g["display_name"],
                "is_forum": bool(g.get("is_forum")),
                "username": g.get("username"),
            }
            for g in data["items"]
        ]
        return {"ok": True, "items": items}

    async def list_topics(self, group_id: int) -> Dict[str, Any]:
        client = self.state.client
        if client is None:
            raise PanelUnavailable()
        topics = await self.state.throttle.tg_read(
            lambda: self.state.telegram_utils.get_forum_topics(client, int(group_id))
        )
        return {"ok": True, "items": topics or []}

    # ---------- settings-backed state ----------
    def _save_map(self, settings: Dict[str, Any], mapping: Dict[Any, List[str]]) -> None:
        # JSON keys must be strings; None topic -> "None". The reader normalizes back.
        settings["active_command_to_topic_map"] = {
            ("None" if k is None else str(k)): v for k, v in mapping.items()
        }
        self.state.settings_manager.save_user_settings(settings)

    def get_state(self) -> Dict[str, Any]:
        s = self.state.settings_manager.load_user_settings()
        mapping = normalize_command_mappings(s.get("active_command_to_topic_map"))
        flat = []
        for topic_id, cmds in mapping.items():
            for c in cmds:
                flat.append({"command": c, "topic_id": topic_id})
        return {"ok": True, "target": s.get("selected_target_group"), "mappings": flat}

    def set_target(self, group_id: int) -> Dict[str, Any]:
        gid = int(group_id)
        row = self.state.dialogs.find(gid) if self.state.dialogs else None
        title = (row or {}).get("display_name", f"Group {gid}")
        s = self.state.settings_manager.load_user_settings()
        s["selected_target_group"] = {"id": gid, "title": title}
        self.state.settings_manager.save_user_settings(s)
        return {"ok": True, "target": s["selected_target_group"]}

    def add_mapping(self, command: str, topic_id: int) -> Dict[str, Any]:
        command = (command or "").strip().lstrip("/").lower()
        if not command:
            raise PanelError("A command is required.")
        topic_id = int(topic_id)
        s = self.state.settings_manager.load_user_settings()
        mapping = normalize_command_mappings(s.get("active_command_to_topic_map"))
        # a command maps to exactly one topic: drop it from any other topic first
        for tid in list(mapping.keys()):
            mapping[tid] = [c for c in mapping[tid] if c != command]
            if not mapping[tid]:
                del mapping[tid]
        mapping.setdefault(topic_id, [])
        if command not in mapping[topic_id]:
            mapping[topic_id].append(command)
        self._save_map(s, mapping)
        return {"ok": True}

    def remove_mapping(self, command: str) -> Dict[str, Any]:
        command = (command or "").strip().lstrip("/").lower()
        s = self.state.settings_manager.load_user_settings()
        mapping = normalize_command_mappings(s.get("active_command_to_topic_map"))
        for tid in list(mapping.keys()):
            mapping[tid] = [c for c in mapping[tid] if c != command]
            if not mapping[tid]:
                del mapping[tid]
        self._save_map(s, mapping)
        return {"ok": True}

    def clear(self) -> Dict[str, Any]:
        s = self.state.settings_manager.load_user_settings()
        s["active_command_to_topic_map"] = {}
        self.state.settings_manager.save_user_settings(s)
        return {"ok": True}
