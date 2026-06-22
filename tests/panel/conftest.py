"""Shared fixtures for offline panel tests (Tier 1).

Builds a real PanelState + FastAPI app wired to a MOCK Telethon client and a
MOCK AIProcessor, so we exercise the real panel code without any network.
"""

import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from telethon.tl.types import Channel, User

from src.ai.response_metadata import AIResponseMetadata
from src.panel.app import create_app
from src.panel.config import PanelConfig
from src.panel.media_cache import MediaCache
from src.panel.state import PanelState
from src.panel.throttle import Throttle

TOKEN = "test-token-123"

# Telegram write methods the panel must NEVER call.
FORBIDDEN_CLIENT_CALLS = [
    "send_message",
    "send_file",
    "edit_message",
    "forward_messages",
    "delete_messages",
    "send_read_acknowledge",
    "add_event_handler",
]


def make_message(**kw):
    """A duck-typed Telethon-ish message."""
    defaults = dict(
        id=kw.get("id", 1),
        message=kw.get("text", "hello"),
        out=kw.get("out", False),
        date=kw.get("date", datetime.datetime(2025, 1, 1, 12, 0, 0)),
        media=kw.get("media", None),
        voice=kw.get("voice", None),
        audio=kw.get("audio", None),
        document=kw.get("document", None),
        video=kw.get("video", None),
        photo=kw.get("photo", None),
        sender=kw.get("sender", None),
        sender_id=kw.get("sender_id", 999),
    )
    return SimpleNamespace(**defaults)


def make_entities():
    return [
        User(id=101, first_name="Alice", last_name="Z", username="alice", bot=False),
        User(id=102, first_name="HelpBot", username="helpbot", bot=True),
        Channel(id=201, title="Friends Group", photo=None, date=None, megagroup=True, broadcast=False),
        Channel(id=202, title="News Channel", photo=None, date=None, megagroup=False, broadcast=True),
    ]


def build_mock_client():
    client = MagicMock(name="TelethonClient")
    entities = make_entities()

    def _iter_dialogs(**kwargs):
        async def _gen():
            for ent in entities:
                yield SimpleNamespace(entity=ent)
        return _gen()

    client.iter_dialogs = MagicMock(side_effect=_iter_dialogs)

    async def _get_messages(entity_id, **kwargs):
        if "ids" in kwargs:
            return make_message(id=kwargs["ids"], voice=SimpleNamespace(), media=SimpleNamespace())
        limit = kwargs.get("limit", 30)
        return [
            make_message(id=i, text=f"message {i}", out=(i % 2 == 0))
            for i in range(1, min(limit, 5) + 1)
        ]

    client.get_messages = AsyncMock(side_effect=_get_messages)
    client.get_me = AsyncMock(return_value=SimpleNamespace(id=1, first_name="Owner", last_name="", username="owner"))
    client.get_entity = AsyncMock(side_effect=lambda x: entities[0])
    client.download_profile_photo = AsyncMock(return_value=None)
    client.download_media = AsyncMock(return_value="/tmp/panel_fake_voice.oga")
    client.is_connected = MagicMock(return_value=True)
    client.list_event_handlers = MagicMock(return_value=[])

    # Forbidden writes — present so we can assert they're never called.
    for name in FORBIDDEN_CLIENT_CALLS:
        setattr(client, name, AsyncMock())
    return client


def build_mock_ai():
    ai = MagicMock(name="AIProcessor")
    ai.is_configured = True
    ai.provider_name = "Google Gemini"
    ai.model_name = "gemini-test"
    ai.get_model_for_task = MagicMock(return_value="gemini-test-pro")

    def meta(text):
        return AIResponseMetadata(
            response_text=text, model_used="gemini-test-pro", provider_used="Google Gemini",
            latency_seconds=1.2, input_tokens=10, output_tokens=20,
        )

    ai.execute_custom_prompt = AsyncMock(return_value=meta("PROMPT_RESULT"))
    ai.translate_text_with_phonetics = AsyncMock(return_value="TRANSLATION_RESULT")
    ai.analyze_conversation_messages = AsyncMock(return_value=meta("ANALYZE_RESULT"))
    ai.answer_question_from_chat_history = AsyncMock(return_value=meta("TELLME_RESULT"))
    return ai


def build_mock_config():
    return SimpleNamespace(
        llm_provider="gemini",
        llm_fallback_provider="openrouter",
        gemini_api_keys=["k1", "k2"],
        openrouter_api_keys=["o1"],
        ffmpeg_path_resolved=None,
        gemini_tts_model="gemini-tts",
        gemini_tts_voice="Orus",
        gemini_model_web_search="gemini-2.5-flash",
        flux_worker_url="https://flux.example",
        sdxl_api_key=None,
    )


def build_state(tmp_path, *, client=None, ai=None, real_photos=False):
    from src.panel.services.dialogs_service import DialogsService
    from src.panel.services.entity_service import EntityService
    from src.panel.services.status_service import StatusService
    from src.panel.services.auth_service import AuthService
    from src.panel.services.command_service import CommandService

    settings = MagicMock()
    settings.load_user_settings = MagicMock(return_value={
        "directly_authorized_pvs": [101],
        "selected_target_group": {"id": 201, "title": "Friends Group"},
        "active_command_to_topic_map": {},
    })
    settings.save_user_settings = MagicMock()

    image_gen = MagicMock()
    image_gen.generate_with_flux = AsyncMock(return_value=(True, str(tmp_path / "img.png"), None))
    image_gen.generate_with_sdxl = AsyncMock(return_value=(True, str(tmp_path / "img.png"), None))
    (tmp_path / "img.png").write_bytes(b"\x89PNG\r\n")

    enhancer = MagicMock()
    enhancer.enhance_prompt = AsyncMock(return_value=("enhanced prompt", "gemini"))

    tts = MagicMock()
    (tmp_path / "tts.wav").write_bytes(b"RIFFxxxx")
    tts.generate_speech_file = AsyncMock(return_value=str(tmp_path / "tts.wav"))

    stt = MagicMock()
    stt.transcribe_voice_to_text = AsyncMock(return_value="TRANSCRIBED TEXT")

    verifier = MagicMock()
    verifier.verify_user_by_identifier = AsyncMock(
        return_value={"id": 555, "display_name": "New User", "username": "@newuser"}
    )

    cache = MagicMock()
    cache.load_pv_cache = MagicMock(return_value=([], None))

    pcfg = PanelConfig(token=TOKEN, real_photos=real_photos)
    state = PanelState(
        panel_config=pcfg,
        config=build_mock_config(),
        client=client,
        client_manager=None,
        ai_processor=ai or build_mock_ai(),
        stt_processor=stt,
        tts_processor=tts,
        image_generator=image_gen,
        prompt_enhancer=enhancer,
        cache_manager=cache,
        telegram_utils=MagicMock(),
        settings_manager=settings,
        user_verifier=verifier,
        throttle=Throttle(min_gap_seconds=0.0),  # no pacing delay in tests
        media_cache=MediaCache(tmp_path / "cache"),
    )
    state.dialogs = DialogsService(state)
    state.entity = EntityService(state)
    state.status = StatusService(state)
    state.auth = AuthService(state)
    state.commands = CommandService(state)
    # Audio decode needs FFmpeg + a real file; transcription is mocked, so stub
    # the WAV conversion to keep offline tests FFmpeg-free.
    state.commands._to_wav = lambda src, dst: None
    return state


@pytest.fixture
def mock_client():
    return build_mock_client()


@pytest.fixture
def panel_state(tmp_path, mock_client):
    return build_state(tmp_path, client=mock_client, ai=build_mock_ai())


@pytest.fixture
def client(panel_state):
    """Starlette TestClient over the real FastAPI app."""
    from starlette.testclient import TestClient

    app = create_app(panel_state)
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {TOKEN}"}
