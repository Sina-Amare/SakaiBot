"""Helpers for the LIVE panel E2E tests (real Telegram + real LLM + real server).

These start the REAL panel runtime: a real connected Telethon client + a real
``AIProcessor`` + a real uvicorn server on the SAME event loop (exactly like
production), then exercise it over HTTP. Gated by ``SAKAIBOT_RUN_LIVE_TESTS=1``.

Ban-safety: tiny volume, throttled through the panel, and all chat-targeting
tests use Saved Messages (``me``) or ``SAKAIBOT_TEST_CHAT`` — never a third
party. The panel sends nothing.
"""

import contextlib
import os
from pathlib import Path

import pytest

LIVE = os.getenv("SAKAIBOT_RUN_LIVE_TESTS") == "1"
TEST_PORT = int(os.getenv("PANEL_TEST_PORT", "8791"))
TEST_CHAT = os.getenv("SAKAIBOT_TEST_CHAT", "me")
LIVE_TOKEN = "live-test-token"

skip_unless_live = pytest.mark.skipif(
    not LIVE, reason="Set SAKAIBOT_RUN_LIVE_TESTS=1 (real creds + session) to run."
)


@contextlib.asynccontextmanager
async def live_panel():
    """Yield (state, base_url, client) for a fully real, running panel."""
    from telethon import TelegramClient

    from src.core.config import load_config
    from src.core.constants import SYSTEM_VERSION
    from src.ai.processor import AIProcessor
    from src.ai.stt import SpeechToTextProcessor
    from src.ai.tts import TextToSpeechProcessor
    from src.panel.config import PanelConfig
    from src.panel.runner import start_panel
    from src.panel.state import build_panel_state

    config = load_config()
    session_path = str(Path("data") / config.telegram_session_name)
    client = TelegramClient(
        session_path,
        config.telegram_api_id,
        config.telegram_api_hash,
        system_version=SYSTEM_VERSION,
    )
    try:
        await client.connect()
    except Exception as exc:  # e.g. database is locked (bot already running)
        pytest.skip(f"Could not open Telegram session (is the bot running?): {exc}")
    if not await client.is_user_authorized():
        await client.disconnect()
        pytest.skip("No authorized Telegram session; run `sakaibot panel` once to log in.")

    ai = AIProcessor(config)
    stt = SpeechToTextProcessor()
    tts = TextToSpeechProcessor()
    pcfg = PanelConfig(port=TEST_PORT, token=LIVE_TOKEN)
    state = build_panel_state(
        client=client,
        client_manager=None,
        config=config,
        ai_processor=ai,
        stt_processor=stt,
        tts_processor=tts,
        panel_config=pcfg,
    )
    handle = await start_panel(state)
    base = f"http://{pcfg.host}:{pcfg.port}"
    try:
        yield state, base, client
    finally:
        await handle.stop()
        await client.disconnect()


def auth_header():
    return {"Authorization": f"Bearer {LIVE_TOKEN}"}


@contextlib.asynccontextmanager
async def setup_panel():
    """Serve the panel in first-run SETUP mode (no Telegram client/creds)."""
    from src.panel.config import PanelConfig
    from src.panel.runner import start_panel
    from src.panel.state import build_setup_state

    pcfg = PanelConfig(port=TEST_PORT + 1, token="setup-token")
    state = build_setup_state(pcfg)
    handle = await start_panel(state)
    base = f"http://{pcfg.host}:{pcfg.port}"
    try:
        yield state, base
    finally:
        await handle.stop()
