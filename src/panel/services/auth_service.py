"""Authorized-users service.

The ONLY thing the panel ever writes is the ``directly_authorized_pvs`` list in
``settings.json`` (via the existing SettingsManager). It NEVER writes to
Telegram. Note: a newly added user's commands are routed by the monitoring
handlers, which bind ``from_users=[id]`` at registration — so a new id takes
effect on the next ``panel``/``monitor`` start (same as the existing /auth).
"""

from typing import Any, Dict, List, Optional

from ...utils.logging import get_logger
from ..errors import PanelError

logger = get_logger(__name__)


class AuthService:
    def __init__(self, state: Any) -> None:
        self.state = state

    def _resolve_name(self, user_id: int) -> Dict[str, Optional[str]]:
        # Best-effort, cache-only (no Telegram RPC -> ban-safe).
        row = self.state.dialogs.find(user_id) if self.state.dialogs else None
        if row:
            return {"display_name": row.get("display_name"), "username": row.get("username")}
        try:
            pvs, _ = self.state.cache_manager.load_pv_cache()
            for pv in pvs or []:
                if pv.get("id") == user_id:
                    return {"display_name": pv.get("display_name"), "username": pv.get("username")}
        except Exception:  # noqa: BLE001
            pass
        return {"display_name": None, "username": None}

    def list_authorized(self) -> Dict[str, Any]:
        settings = self.state.settings_manager.load_user_settings()
        ids = settings.get("directly_authorized_pvs", []) or []
        items: List[Dict[str, Any]] = []
        for uid in ids:
            try:
                uid_int = int(uid)
            except (TypeError, ValueError):
                continue
            resolved = self._resolve_name(uid_int)
            items.append({"id": uid_int, **resolved})
        return {"ok": True, "items": items}

    async def add(self, identifier: str) -> Dict[str, Any]:
        identifier = (identifier or "").strip()
        if not identifier:
            raise PanelError("Provide a @username or numeric user id.")
        if self.state.user_verifier is None:
            raise PanelError("Telegram client unavailable.", status_code=503)

        info = await self.state.throttle.tg_read(
            lambda: self.state.user_verifier.verify_user_by_identifier(identifier)
        )
        if not info:
            raise PanelError(f"No Telegram user found for '{identifier}'.", status_code=404)

        user_id = int(info["id"])
        settings = self.state.settings_manager.load_user_settings()
        ids = list(settings.get("directly_authorized_pvs", []) or [])
        if user_id not in ids:
            ids.append(user_id)
            settings["directly_authorized_pvs"] = ids
            self.state.settings_manager.save_user_settings(settings)
        return {
            "ok": True,
            "added": {
                "id": user_id,
                "display_name": info.get("display_name"),
                "username": info.get("username"),
            },
            "note": "Saved. Command routing for this user applies on next panel/monitor start.",
        }

    def remove(self, user_id: int) -> Dict[str, Any]:
        settings = self.state.settings_manager.load_user_settings()
        ids = list(settings.get("directly_authorized_pvs", []) or [])
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            raise PanelError("Invalid user id.")
        if user_id in ids:
            ids.remove(user_id)
            settings["directly_authorized_pvs"] = ids
            self.state.settings_manager.save_user_settings(settings)
            return {"ok": True, "removed": user_id}
        return {"ok": True, "removed": None, "note": "User was not in the list."}
