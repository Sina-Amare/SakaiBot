"""LIVE end-to-end panel tests: real Telegram reads + real LLM calls + the
core 'never sends to chat' promise verified against the real account.

Run locally:  SAKAIBOT_RUN_LIVE_TESTS=1 pytest tests/live/test_panel_live.py -v
"""

import httpx
import pytest

from ._helpers import LIVE_TOKEN, TEST_CHAT, auth_header, live_panel, skip_unless_live

pytestmark = [pytest.mark.live, skip_unless_live]


@pytest.mark.asyncio
async def test_live_connected_and_dialogs():
    async with live_panel() as (state, base, client):
        async with httpx.AsyncClient(base_url=base, timeout=60) as hc:
            health = (await hc.get("/api/health")).json()
            assert health["client"] == "connected"

            status = await hc.get("/api/status", headers=auth_header())
            assert status.status_code == 200
            assert status.json()["account"]["id"]  # real account id

            dialogs = await hc.get("/api/dialogs", headers=auth_header())
            body = dialogs.json()
            assert body["total"] > 0  # real chats classified
            assert any(item["kind"] in ("pv", "group", "channel", "bot") for item in body["items"])


@pytest.mark.asyncio
async def test_live_prompt_real_llm():
    async with live_panel() as (state, base, client):
        if not state.ai_processor.is_configured:
            pytest.skip("AI provider not configured in .env")
        async with httpx.AsyncClient(base_url=base, timeout=180) as hc:
            r = await hc.post(
                "/api/cmd/prompt",
                json={"text": "Reply with exactly one word: PONG"},
                headers=auth_header(),
            )
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["kind"] == "text"
            assert data["html"].strip(), "real LLM returned empty text"


@pytest.mark.asyncio
async def test_live_results_never_reach_telegram():
    """The core promise: running panel commands creates NO message in the chat."""
    async with live_panel() as (state, base, client):
        before = await client.get_messages(TEST_CHAT, limit=1)
        before_id = before[0].id if before else 0
        entity = await client.get_entity(TEST_CHAT)

        async with httpx.AsyncClient(base_url=base, timeout=180) as hc:
            # analyze the test chat (Saved Messages) — tolerate "too few messages"
            await hc.post(
                "/api/cmd/analyze",
                json={"entity_id": entity.id, "count": 20, "mode": "general", "language": "english"},
                headers=auth_header(),
            )
            # and a plain prompt
            await hc.post("/api/cmd/prompt", json={"text": "ping"}, headers=auth_header())

        after = await client.get_messages(TEST_CHAT, limit=1)
        after_id = after[0].id if after else 0
        assert after_id == before_id, "Panel must NOT create any message in the chat"


@pytest.mark.asyncio
async def test_live_image_real_worker():
    async with live_panel() as (state, base, client):
        if not getattr(state.config, "flux_worker_url", None):
            pytest.skip("Flux worker not configured")
        async with httpx.AsyncClient(base_url=base, timeout=180) as hc:
            r = await hc.post(
                "/api/cmd/image",
                json={"model": "flux", "prompt": "a single red cube on a white background"},
                headers=auth_header(),
            )
            if r.status_code != 200:
                pytest.skip(f"Image worker unavailable: {r.text}")
            url = r.json()["media_url"]
            media = await hc.get(f"{url}?t={LIVE_TOKEN}")
            assert media.status_code == 200
            assert media.headers["content-type"] == "image/png"
            assert len(media.content) > 500  # real image bytes


@pytest.mark.asyncio
async def test_live_tts_real():
    async with live_panel() as (state, base, client):
        async with httpx.AsyncClient(base_url=base, timeout=180) as hc:
            r = await hc.post(
                "/api/cmd/tts",
                json={"text": "Hello from the SakaiBot panel live test."},
                headers=auth_header(),
            )
            if r.status_code != 200:
                pytest.skip(f"TTS unavailable: {r.text}")
            url = r.json()["media_url"]
            media = await hc.get(f"{url}?t={LIVE_TOKEN}")
            assert media.status_code == 200
            assert media.content[:4] == b"RIFF"  # WAV header


@pytest.mark.asyncio
async def test_live_stt_real_if_voice_available():
    async with live_panel() as (state, base, client):
        entity = await client.get_entity(TEST_CHAT)
        voice_msg = None
        async for m in client.iter_messages(entity, limit=50):
            if getattr(m, "voice", None) or getattr(m, "audio", None):
                voice_msg = m
                break
        if voice_msg is None:
            pytest.skip("No voice/audio message in the test chat to transcribe.")
        async with httpx.AsyncClient(base_url=base, timeout=300) as hc:
            r = await hc.post(
                "/api/cmd/stt",
                json={"entity_id": entity.id, "message_id": voice_msg.id},
                headers=auth_header(),
            )
            assert r.status_code == 200, r.text
            assert r.json()["kind"] == "text"


@pytest.mark.asyncio
async def test_live_history_pagination():
    """Scroll-up pagination: page 2 must be strictly OLDER and not overlap page 1."""
    async with live_panel() as (state, base, client):
        entity = await client.get_entity(TEST_CHAT)
        probe = await client.get_messages(entity, limit=21)
        if len(probe) < 21:
            pytest.skip("Test chat has too few messages to paginate.")
        async with httpx.AsyncClient(base_url=base, timeout=60) as hc:
            p1 = (
                await hc.get(f"/api/entity/{entity.id}/history?limit=10", headers=auth_header())
            ).json()
            assert len(p1["items"]) == 10
            oldest = p1["oldest_id"]
            assert oldest is not None

            p2 = (
                await hc.get(
                    f"/api/entity/{entity.id}/history?limit=10&before_id={oldest}",
                    headers=auth_header(),
                )
            ).json()
            assert p2["items"], "page 2 should return older messages"
            assert all(m["id"] < oldest for m in p2["items"]), "page 2 must be strictly older"
            ids1 = {m["id"] for m in p1["items"]}
            ids2 = {m["id"] for m in p2["items"]}
            assert ids1.isdisjoint(ids2), "pages must not overlap"


@pytest.mark.asyncio
async def test_live_command_fetches_full_count_regardless_of_preview():
    """The command path honors `count` (independent of the 30-msg preview).

    messages_for_ai filters to text-only, so we assert it SCALES with count
    rather than a fixed number: asking for many returns strictly more than
    asking for a few. This proves the command fetch is driven by `count`, not
    by whatever the Messages tab has loaded.
    """
    async with live_panel() as (state, base, client):
        entity = await client.get_entity(TEST_CHAT)
        probe = await client.get_messages(entity, limit=60)
        if len(probe) < 45:
            pytest.skip("Test chat has too few messages.")
        small = len(await state.entity.messages_for_ai(entity.id, 5))
        big = len(await state.entity.messages_for_ai(entity.id, 200))
        assert small <= 5, f"small count not respected: {small}"
        assert big > small, f"count not honored: big={big} small={small}"


@pytest.mark.asyncio
async def test_live_token_enforced():
    async with live_panel() as (state, base, client):
        async with httpx.AsyncClient(base_url=base, timeout=30) as hc:
            assert (await hc.get("/api/status")).status_code == 401
            assert (await hc.get("/api/health")).status_code == 200
