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


def register_live_updates(client: Any, hub: Any, entity_service: Any) -> List[Tuple[Any, Any]]:
    """Tap Telegram's existing update stream → EventHub for the SSE channel.

    RPC-free: the handlers only read fields already on the update (incoming
    message, typing action, online flag) and enqueue a normalized dict — they
    never call back to Telegram. Like register_monitoring, this is allowed here
    because monitor_runtime is the panel's sole add_event_handler site."""

    async def on_new_message(event: Any) -> None:
        try:
            msg = event.message
            if getattr(msg, "out", False):
                return  # outgoing is already echoed by the composer
            cid = event.chat_id
            row = (entity_service.state.dialogs.find(cid) or {}) if cid else {}
            item = entity_service._format_message(
                msg, row.get("kind", "pv"), row.get("display_name", str(cid))
            )
            hub.publish({"type": "message", "entity_id": cid, "message": item})
        except Exception as exc:  # noqa: BLE001 - live tap must never crash the loop
            logger.debug("live new-message tap skipped: %s", exc)

    async def on_user_update(event: Any) -> None:
        try:
            cid = event.chat_id or event.user_id
            if getattr(event, "typing", False) or getattr(event, "uploading", False) \
                    or getattr(event, "recording", False):
                hub.publish({"type": "typing", "entity_id": cid})
                return
            online = getattr(event, "online", None)
            if online is True:
                hub.publish({"type": "presence", "entity_id": event.user_id,
                             "presence": {"state": "online"}})
            elif online is False:
                was = getattr(event, "last_seen", None)
                hub.publish({"type": "presence", "entity_id": event.user_id, "presence": {
                    "state": "offline",
                    "was_online": was.isoformat() if was else None,
                }})
        except Exception as exc:  # noqa: BLE001
            logger.debug("live user-update tap skipped: %s", exc)

    pairs = [
        (on_new_message, events.NewMessage(incoming=True)),
        (on_user_update, events.UserUpdate()),
    ]
    for handler, flt in pairs:
        client.add_event_handler(handler, flt)
    logger.info("Panel registered %d live-update tap(s) for SSE", len(pairs))
    return pairs


def unregister_monitoring(client: Any, registered: List[Tuple[Any, Any]]) -> None:
    for handler, flt in registered:
        try:
            client.remove_event_handler(handler, flt)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to remove handler: %s", exc)
