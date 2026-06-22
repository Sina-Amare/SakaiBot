"""Status / dashboards service: account + monitoring state, live API key-health
board, model matrix, and help. READ-ONLY."""

from typing import Any, Dict, List

from ...utils.logging import get_logger

logger = get_logger(__name__)


class StatusService:
    def __init__(self, state: Any) -> None:
        self.state = state

    async def account(self) -> Dict[str, Any]:
        client = self.state.client
        cfg = self.state.config
        settings = self.state.settings_manager.load_user_settings()

        me_name = None
        me_username = None
        me_id = None
        monitoring = False
        connected = self.state.client_ready()
        if client is not None and connected:
            try:
                me = await self.state.throttle.tg_read(lambda: client.get_me())
                if me:
                    me_name = " ".join(
                        p for p in [getattr(me, "first_name", ""), getattr(me, "last_name", "")] if p
                    ).strip()
                    me_username = f"@{me.username}" if getattr(me, "username", None) else None
                    me_id = me.id
            except Exception as exc:  # noqa: BLE001
                logger.warning("get_me failed: %s", exc)
            try:
                monitoring = len(client.list_event_handlers()) > 0
            except Exception:  # noqa: BLE001
                monitoring = False

        target = settings.get("selected_target_group")
        target_title = None
        if isinstance(target, dict):
            target_title = target.get("title")
        elif target:
            target_title = str(target)

        try:
            import psutil

            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
        except Exception:  # noqa: BLE001
            cpu = None
            mem = None

        return {
            "ok": True,
            "account": {"name": me_name, "username": me_username, "id": me_id},
            "client": "connected" if connected else "degraded",
            "monitoring": monitoring,
            "provider": cfg.llm_provider,
            "fallback_provider": getattr(cfg, "llm_fallback_provider", None),
            "ai_enabled": self.state.ai_processor.is_configured,
            "authorized_count": len(settings.get("directly_authorized_pvs", []) or []),
            "target_group": target_title,
            "mappings": len(settings.get("active_command_to_topic_map", {}) or {}),
            "system": {"cpu_percent": cpu, "mem_percent": mem},
            "panel": {"real_photos": self.state.panel_config.real_photos},
        }

    def keys(self) -> Dict[str, Any]:
        from ...ai.api_key_manager import get_api_key_manager

        cfg = self.state.config
        providers: List[Dict[str, Any]] = []

        # Config-level counts (both providers).
        try:
            providers.append(
                {
                    "name": "gemini",
                    "configured_keys": len(getattr(cfg, "gemini_api_keys", []) or []),
                    "is_primary": cfg.llm_provider == "gemini",
                }
            )
            providers.append(
                {
                    "name": "openrouter",
                    "configured_keys": len(getattr(cfg, "openrouter_api_keys", []) or []),
                    "is_primary": cfg.llm_provider == "openrouter",
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("key config read failed: %s", exc)

        # Live per-key health from the global manager (Gemini sets this).
        manager = get_api_key_manager()
        live = manager.get_status() if manager else None
        return {"ok": True, "providers": providers, "live": live}

    def models(self) -> Dict[str, Any]:
        ai = self.state.ai_processor
        cfg = self.state.config
        tasks = ["prompt", "analyze", "tellme", "translate"]
        matrix = {}
        for t in tasks:
            try:
                matrix[t] = ai.get_model_for_task(t)
            except Exception:  # noqa: BLE001
                matrix[t] = "unknown"
        return {
            "ok": True,
            "provider": ai.provider_name,
            "tasks": matrix,
            "tts_model": getattr(cfg, "gemini_tts_model", None),
            "tts_voice": getattr(cfg, "gemini_tts_voice", None),
            "web_search_model": getattr(cfg, "gemini_model_web_search", None),
            "flux_worker": bool(getattr(cfg, "flux_worker_url", None)),
            "sdxl_worker": bool(getattr(cfg, "sdxl_api_key", None)),
        }

    def help(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "commands": [
                {"cmd": "prompt", "desc": "Ask the AI anything. Flags: think, web.", "scope": "global"},
                {"cmd": "translate", "desc": "Translate text with Persian phonetics.", "scope": "global"},
                {"cmd": "analyze", "desc": "Analyze the last N messages of a chat. Modes: general, fun, romance.", "scope": "chat"},
                {"cmd": "tellme", "desc": "Answer a question from a chat's last N messages. Flags: think, web.", "scope": "chat"},
                {"cmd": "image", "desc": "Generate an image (flux / sdxl) from a prompt.", "scope": "global"},
                {"cmd": "tts", "desc": "Text-to-speech; plays inline in the panel.", "scope": "global"},
                {"cmd": "stt", "desc": "Transcribe a voice message; results stay in the panel.", "scope": "chat"},
            ],
            "note": "Results appear ONLY in this panel — nothing is ever sent to the Telegram chat.",
        }
