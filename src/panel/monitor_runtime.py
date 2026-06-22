"""Keep the Telegram bot live while the panel runs.

This registers the same monitoring event handlers as
``src/cli/commands/monitor.py`` so that running ``sakaibot panel`` also keeps
the bot responding to chat commands. It is intentionally the ONLY place in the
panel package that touches ``add_event_handler`` (the no-send static guard
excludes this file) — these are the existing bot's handlers, not the web layer.

It carries the CORRECT ``active_command_to_topic_map`` key (the live monitor
path has a typo, ``active_command_topic_map``, which silently breaks
authorized-user categorization — FP-2 in the engineering review). The panel's
copy is fixed.
"""

from typing import Any, Dict, List, Optional, Tuple

from telethon import events

from ..utils.logging import get_logger

logger = get_logger(__name__)

OWNER_PATTERN = r"^/\w+"


def register_monitoring(
    client: Any,
    event_handlers: Any,
    *,
    selected_target_group: Any,
    active_command_to_topic_map: Dict[Any, Any],
    directly_authorized_pvs: Optional[List[int]],
    verbose: bool = False,
) -> List[Tuple[Any, Any]]:
    """Register owner + authorized-user handlers. Returns (handler, filter) pairs."""
    base_state = {
        "selected_target_group": selected_target_group,
        "active_command_to_topic_map": active_command_to_topic_map,  # correct key
        "is_monitoring_active": True,
    }
    registered: List[Tuple[Any, Any]] = []

    owner_filter = events.NewMessage(pattern=OWNER_PATTERN, outgoing=True, forwards=False)

    async def owner_handler(event: Any) -> None:
        replied = await event.message.get_reply_message() if event.message.is_reply else None
        await event_handlers.process_command_logic(
            message_to_process=event.message,
            client=client,
            current_chat_id_for_response=event.chat_id,
            is_confirm_flow=False,
            your_confirm_message=None,
            actual_message_for_categorization_content=replied,
            cli_state_ref=dict(base_state),
            is_direct_auth_user_command=False,
        )

    client.add_event_handler(owner_handler, owner_filter)
    registered.append((owner_handler, owner_filter))

    for auth_pv_id in (directly_authorized_pvs or []):
        auth_filter = events.NewMessage(
            pattern=OWNER_PATTERN, from_users=[auth_pv_id], incoming=True, forwards=False
        )

        async def auth_handler(event: Any, _state: Dict[str, Any] = base_state) -> None:
            replied = (
                await event.message.get_reply_message() if event.message.is_reply else None
            )
            await event_handlers.process_command_logic(
                message_to_process=event.message,
                client=client,
                current_chat_id_for_response=event.chat_id,
                is_confirm_flow=False,
                your_confirm_message=None,
                actual_message_for_categorization_content=replied,
                cli_state_ref=dict(_state),
                is_direct_auth_user_command=True,
            )

        client.add_event_handler(auth_handler, auth_filter)
        registered.append((auth_handler, auth_filter))

    logger.info("Panel registered %d monitoring handler(s)", len(registered))
    return registered


def unregister_monitoring(client: Any, registered: List[Tuple[Any, Any]]) -> None:
    for handler, flt in registered:
        try:
            client.remove_event_handler(handler, flt)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to remove handler: %s", exc)
