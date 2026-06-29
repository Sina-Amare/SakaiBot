"""PanelState: the dependency container shared across the web layer.

Built once by ``sakaibot panel`` (or a test) and stored on ``app.state.panel``.
Holds the SHARED Telegram client (never a new one), the existing AI core
objects, and the panel-owned throttle / caches / services.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .config import PanelConfig
from .events import EventHub
from .media_cache import MediaCache
from .throttle import Throttle


@dataclass
class PanelState:
    panel_config: PanelConfig
    config: Any                  # core src.core.config.Config
    client: Any                  # shared Telethon client (may be None -> degraded)
    client_manager: Any
    ai_processor: Any
    stt_processor: Any
    tts_processor: Any
    image_generator: Any
    prompt_enhancer: Any
    cache_manager: Any
    telegram_utils: Any
    settings_manager: Any
    user_verifier: Any
    throttle: Throttle
    media_cache: MediaCache

    # mutable runtime state
    dialogs_cache: Optional[Dict[str, Any]] = None          # {'items':[...], 'ts':float}
    result_tokens: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    events: EventHub = field(default_factory=EventHub)       # SSE pub/sub hub

    # services (attached by build_panel_state)
    dialogs: Any = None
    entity: Any = None
    status: Any = None
    auth: Any = None
    commands: Any = None
    keys: Any = None
    groups: Any = None
    messenger: Any = None
    onboarding: Any = None
    env_writer: Any = None

    def client_ready(self) -> bool:
        try:
            return self.client is not None and self.client.is_connected()
        except Exception:
            return False


def build_panel_state(
    *,
    client: Any,
    client_manager: Any,
    config: Any,
    ai_processor: Any,
    stt_processor: Any,
    tts_processor: Any,
    panel_config: PanelConfig,
) -> PanelState:
    """Construct a PanelState by wrapping existing components (no new client)."""
    # Imports are local to avoid importing heavy modules unless the panel runs.
    from ..ai.image_generator import ImageGenerator
    from ..ai.prompt_enhancer import PromptEnhancer
    from ..utils.cache import CacheManager
    from ..telegram.utils import TelegramUtils
    from ..core.settings import SettingsManager
    from ..telegram.user_verifier import TelegramUserVerifier

    from .services.dialogs_service import DialogsService
    from .services.entity_service import EntityService
    from .services.status_service import StatusService
    from .services.auth_service import AuthService
    from .services.command_service import CommandService
    from .services.keys_service import KeysService
    from .services.group_service import GroupService
    from .services.messenger_service import MessengerService
    from .env_writer import EnvWriter

    state = PanelState(
        panel_config=panel_config,
        config=config,
        client=client,
        client_manager=client_manager,
        ai_processor=ai_processor,
        stt_processor=stt_processor,
        tts_processor=tts_processor,
        image_generator=ImageGenerator(),
        prompt_enhancer=PromptEnhancer(ai_processor),
        cache_manager=CacheManager(),
        telegram_utils=TelegramUtils(),
        settings_manager=SettingsManager(),
        user_verifier=TelegramUserVerifier(client) if client is not None else None,
        throttle=Throttle(),
        media_cache=MediaCache(),
    )

    state.env_writer = EnvWriter()
    state.dialogs = DialogsService(state)
    state.entity = EntityService(state)
    state.status = StatusService(state)
    state.auth = AuthService(state)
    state.commands = CommandService(state)
    state.keys = KeysService(state)
    state.groups = GroupService(state)
    state.messenger = MessengerService(state)
    from .onboarding import OnboardingService
    state.onboarding = OnboardingService(state)
    return state


def build_setup_state(panel_config: PanelConfig) -> PanelState:
    """A minimal state for first-run onboarding (no authed client yet)."""
    from .env_writer import EnvWriter
    from .media_cache import MediaCache
    from .onboarding import OnboardingService

    state = PanelState(
        panel_config=panel_config,
        config=None,
        client=None,
        client_manager=None,
        ai_processor=None,
        stt_processor=None,
        tts_processor=None,
        image_generator=None,
        prompt_enhancer=None,
        cache_manager=None,
        telegram_utils=None,
        settings_manager=None,
        user_verifier=None,
        throttle=Throttle(),
        media_cache=MediaCache(),
    )
    state.env_writer = EnvWriter()
    state.onboarding = OnboardingService(state)
    return state
