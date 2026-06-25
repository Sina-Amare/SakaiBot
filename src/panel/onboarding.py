"""First-run onboarding for self-host: collect Telegram credentials, log in
(code / 2FA) in-panel, collect + write LLM keys to .env — all without a
terminal. Mirrors the proven terminal auth in TelegramClientManager._authenticate.

Used by ``sakaibot setup``. In a normal (already-authorized) ``sakaibot panel``
run, ``status().needs_setup`` is False and the wizard never appears.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.logging import get_logger
from .errors import PanelError

logger = get_logger(__name__)


class OnboardingService:
    def __init__(self, state: Any) -> None:
        self.state = state
        self._client = None
        self._api_id: Optional[int] = None
        self._api_hash: Optional[str] = None
        self._phone: Optional[str] = None
        self._phone_code_hash: Optional[str] = None
        self._authorized = False

    # ---------- status ----------
    def status(self) -> Dict[str, Any]:
        # In an authed panel run the shared client is connected -> no setup.
        live = bool(self.state.client is not None and self.state.client_ready())
        env_ok = bool(os.environ.get("TELEGRAM_API_ID")) and Path(".env").exists()
        needs = not (live or self._authorized)
        return {"ok": True, "needs_setup": needs, "authorized": self._authorized, "env": env_ok}

    # ---------- telegram login ----------
    async def start(self, api_id: Any, api_hash: str, phone: str) -> Dict[str, Any]:
        from telethon import TelegramClient
        from ..core.constants import SYSTEM_VERSION

        try:
            api_id = int(api_id)
        except (TypeError, ValueError):
            raise PanelError("API ID must be a number (from my.telegram.org).")
        if not api_hash or len(api_hash) < 10:
            raise PanelError("API hash looks invalid.")
        phone = (phone or "").strip()
        if not phone.startswith("+"):
            raise PanelError("Phone must include the country code, e.g. +98...")

        session_name = os.environ.get("TELEGRAM_SESSION_NAME", "sakaibot_session")
        Path("data").mkdir(parents=True, exist_ok=True)
        session_path = str(Path("data") / session_name)

        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:  # noqa: BLE001
                pass
        self._client = TelegramClient(
            session_path, api_id, api_hash, system_version=SYSTEM_VERSION
        )
        try:
            await self._client.connect()
        except Exception as exc:  # noqa: BLE001
            raise PanelError(
                f"Could not reach Telegram ({str(exc)[:120]}). If you're in a "
                f"blocked region, deploy on a server outside it or enable the proxy."
            )

        self._api_id, self._api_hash, self._phone = api_id, api_hash, phone
        if await self._client.is_user_authorized():
            self._authorized = True
            return {"ok": True, "authorized": True}
        sent = await self._client.send_code_request(phone)
        self._phone_code_hash = sent.phone_code_hash
        return {"ok": True, "code_sent": True}

    async def submit_code(self, code: str) -> Dict[str, Any]:
        from telethon.errors import SessionPasswordNeededError

        if self._client is None:
            raise PanelError("Enter your Telegram credentials first.")
        code = (code or "").strip()
        if not code:
            raise PanelError("Enter the code Telegram sent you.")
        try:
            await self._client.sign_in(
                self._phone, code, phone_code_hash=self._phone_code_hash
            )
        except SessionPasswordNeededError:
            return {"ok": True, "needs_password": True}
        except Exception as exc:  # noqa: BLE001
            raise PanelError(f"Code verification failed: {str(exc)[:160]}")
        self._authorized = True
        return {"ok": True, "authorized": True}

    async def submit_password(self, password: str) -> Dict[str, Any]:
        if self._client is None:
            raise PanelError("Enter your Telegram credentials first.")
        try:
            await self._client.sign_in(password=password)
        except Exception as exc:  # noqa: BLE001
            raise PanelError(f"2FA password failed: {str(exc)[:120]}")
        self._authorized = True
        return {"ok": True, "authorized": True}

    # ---------- finalize ----------
    async def finalize(self, llm: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self._authorized:
            raise PanelError("Finish the Telegram login first.")
        updates: Dict[str, Optional[str]] = {
            "TELEGRAM_API_ID": str(self._api_id),
            "TELEGRAM_API_HASH": self._api_hash,
            "TELEGRAM_PHONE_NUMBER": self._phone,
        }
        llm = llm or {}
        provider = (llm.get("provider") or "gemini").lower()
        if provider not in ("gemini", "openrouter"):
            provider = "gemini"
        updates["LLM_PROVIDER"] = provider
        if provider == "gemini":
            updates["LLM_FALLBACK_PROVIDER"] = "openrouter"
        keys: List[str] = [k for k in (llm.get("keys") or []) if k and k.strip()]
        prefix = "GEMINI" if provider == "gemini" else "OPENROUTER"
        for i, key in enumerate(keys[:4], 1):
            updates[f"{prefix}_API_KEY_{i}"] = key.strip()

        self.state.env_writer.set_many(updates)
        # Release the session so a subsequent `sakaibot panel` can open it.
        try:
            if self._client is not None:
                await self._client.disconnect()
        except Exception:  # noqa: BLE001
            pass
        logger.info("Onboarding finalized; .env written.")
        return {"ok": True, "done": True}
