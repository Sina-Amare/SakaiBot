"""Provider keys + model management for the panel.

Lets the user view (masked) / add / replace / remove API keys, switch the
primary/fallback provider, set per-task model overrides, and TEST a key with a
real minimal call. All changes are written atomically to .env and applied by
hot-reloading the AIProcessor into PanelState (no restart). Never sends to
Telegram; never logs secret values.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from ...utils.logging import get_logger
from ...utils.security import mask_api_key
from ..errors import PanelError

logger = get_logger(__name__)

PROVIDERS = ("gemini", "openrouter")

# Only these .env keys may be written via set_models (allow-list).
MODEL_ENV_ALLOW = set()
for _p in ("GEMINI", "OPENROUTER"):
    for _t in ("PRO", "FLASH", "PROMPT", "ANALYZE", "TELLME", "TRANSLATE", "VOICE_SUMMARY"):
        MODEL_ENV_ALLOW.add(f"{_p}_MODEL_{_t}")


class KeysService:
    def __init__(self, state: Any) -> None:
        self.state = state
        self._reload_lock = asyncio.Lock()

    # ---------- helpers ----------
    @staticmethod
    def _vp(provider: str) -> str:
        provider = (provider or "").strip().lower()
        if provider not in PROVIDERS:
            raise PanelError(f"Unknown provider '{provider}'. Use gemini or openrouter.")
        return provider

    def _slot_value(self, provider: str, index: int) -> Optional[str]:
        return getattr(self.state.config, f"{provider}_api_key_{index}", None)

    # ---------- view ----------
    def list_keys(self) -> Dict[str, Any]:
        from ...ai.api_key_manager import get_api_key_manager

        cfg = self.state.config
        providers: List[Dict[str, Any]] = []
        for prov in PROVIDERS:
            slots = []
            for i in range(1, 5):
                v = self._slot_value(prov, i)
                slots.append({"index": i, "present": bool(v), "masked": mask_api_key(v) if v else None})
            providers.append({
                "provider": prov,
                "is_primary": cfg.llm_provider == prov,
                "is_fallback": (getattr(cfg, "llm_fallback_provider", None) == prov),
                "configured_keys": len(getattr(cfg, f"{prov}_api_keys", []) or []),
                "slots": slots,
            })
        mgr = get_api_key_manager()
        return {
            "ok": True,
            "providers": providers,
            "primary": cfg.llm_provider,
            "fallback": getattr(cfg, "llm_fallback_provider", None),
            "live": mgr.get_status() if mgr else None,
        }

    # ---------- mutations ----------
    async def _write_and_reload(self, updates: Dict[str, Optional[str]]) -> Dict[str, Any]:
        self.state.env_writer.set_many(updates)
        await self.reload_ai()
        return {"ok": True}

    async def add_key(self, provider: str, key: str) -> Dict[str, Any]:
        provider = self._vp(provider)
        key = (key or "").strip()
        if len(key) < 10:
            raise PanelError("That key looks too short.")
        for i in range(1, 5):
            if not self._slot_value(provider, i):
                return await self.set_key(provider, i, key)
        raise PanelError("All 4 key slots are full for this provider — remove one first.")

    async def set_key(self, provider: str, index: int, key: str) -> Dict[str, Any]:
        provider = self._vp(provider)
        index = int(index)
        if not 1 <= index <= 4:
            raise PanelError("Key slot must be 1–4.")
        key = (key or "").strip()
        if len(key) < 10:
            raise PanelError("That key looks too short.")
        return await self._write_and_reload({f"{provider.upper()}_API_KEY_{index}": key})

    async def remove_key(self, provider: str, index: int) -> Dict[str, Any]:
        provider = self._vp(provider)
        index = int(index)
        if not 1 <= index <= 4:
            raise PanelError("Key slot must be 1–4.")
        return await self._write_and_reload({f"{provider.upper()}_API_KEY_{index}": None})

    async def set_provider(self, primary: Optional[str] = None, fallback: Optional[str] = None) -> Dict[str, Any]:
        updates: Dict[str, Optional[str]] = {}
        if primary is not None:
            updates["LLM_PROVIDER"] = self._vp(primary)
        if fallback is not None:
            fb = (fallback or "").strip().lower()
            updates["LLM_FALLBACK_PROVIDER"] = "none" if fb in ("", "none") else self._vp(fb)
        if not updates:
            raise PanelError("Nothing to change.")
        return await self._write_and_reload(updates)

    async def set_models(self, overrides: Dict[str, Optional[str]]) -> Dict[str, Any]:
        clean: Dict[str, Optional[str]] = {}
        for k, v in (overrides or {}).items():
            ku = str(k).strip().upper()
            if ku not in MODEL_ENV_ALLOW:
                raise PanelError(f"Not an allowed model setting: {k}")
            clean[ku] = (str(v).strip() if v else None)
        if not clean:
            raise PanelError("No model overrides provided.")
        return await self._write_and_reload(clean)

    # ---------- test ----------
    async def test_key(
        self, provider: str, key: Optional[str] = None, index: Optional[int] = None
    ) -> Dict[str, Any]:
        provider = self._vp(provider)
        if key is None and index is not None:
            key = self._slot_value(provider, int(index))
        if not key:
            raise PanelError("No key to test (provide a key or a configured slot).")
        started = time.monotonic()
        try:
            if provider == "gemini":
                await self._gemini_ping(key)
            else:
                await self._openrouter_ping(key)
            return {"ok": True, "provider": provider, "latency_ms": int((time.monotonic() - started) * 1000)}
        except Exception as exc:  # noqa: BLE001 - report any failure to the UI
            return {
                "ok": False,
                "provider": provider,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "error": str(exc)[:240],
            }

    async def _gemini_ping(self, key: str) -> None:
        from google import genai

        client = genai.Client(api_key=key)
        # Listing models needs only a valid key (no generation quota).
        pager = client.aio.models.list()
        if hasattr(pager, "__aiter__"):
            async for _ in pager:
                break
        else:
            await pager

    async def _openrouter_ping(self, key: str) -> None:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
        try:
            await client.models.list()
        finally:
            await client.close()

    # ---------- hot reload ----------
    async def reload_ai(self) -> None:
        """Rebuild config + AIProcessor from the new .env and swap into state.

        The swap is a set of plain assignments with no awaits between them, so a
        concurrent request never observes a half-updated state. A lock serializes
        concurrent reloads. The old processor is closed in the background.
        """
        async with self._reload_lock:
            from ...core import config as cfgmod
            from ...ai.processor import AIProcessor
            from ...ai.prompt_enhancer import PromptEnhancer
            from ...ai.image_generator import ImageGenerator

            cfgmod.settings = None
            new_config = cfgmod.get_settings()
            new_ai = AIProcessor(new_config)

            old_ai = self.state.ai_processor
            self.state.config = new_config
            self.state.ai_processor = new_ai
            self.state.prompt_enhancer = PromptEnhancer(new_ai)
            self.state.image_generator = ImageGenerator()

            async def _close(old: Any) -> None:
                try:
                    await old.close()
                except Exception:  # noqa: BLE001
                    pass

            if old_ai is not None and old_ai is not new_ai:
                asyncio.create_task(_close(old_ai))
            logger.info("AI processor hot-reloaded (provider=%s)", new_config.llm_provider)
