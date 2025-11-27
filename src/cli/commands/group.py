"""Group management commands."""

import click
import asyncio
from rich import print as rprint
from rich.table import Table
from typing import Optional, Dict, Any, List
from ..utils import (
    get_telegram_client, get_cache_manager, get_settings_manager,
    format_group_table, display_error, display_success, display_info,
    display_warning, ProgressSpinner, prompt_choice, prompt_text,
    confirm_action, normalize_command_mappings, console
)

@click.group()
def group():
    """Manage groups and categorization."""
    pass

@group.command(name='list')
@click.option('--refresh', is_flag=True, help='Refresh cache before listing')
@click.option('--all', 'show_all', is_flag=True, help='Show all groups (not just admin)')
def list_groups(refresh, show_all):
    """List all groups where you have admin rights."""
    asyncio.run(_list_groups(refresh, show_all))

async def _list_groups(refresh: bool, show_all: bool):
    """List groups implementation."""
    try:
        client, client_manager = await get_telegram_client()
        if not client:
            return
        
        cache_manager = await get_cache_manager()
        from src.telegram.utils import TelegramUtils
        telegram_utils = TelegramUtils()
        
        with ProgressSpinner("Fetching groups...") as spinner:
            if refresh:
                spinner.update("Refreshing group cache from Telegram...")
            
            groups = await cache_manager.get_groups(
                client=client,
                telegram_utils=telegram_utils,
                force_refresh=refresh,
                require_admin_rights=not show_all
            )
        
        if not groups:
            display_info("No groups found.")
            return
        
        # Display groups
        table = format_group_table(groups)
        console.print(table)
        
        display_success(f"Listed {len(groups)} groups")
        
    except Exception as e:
        display_error(f"Failed to list groups: {e}")
    finally:
        if client_manager:
            await client_manager.disconnect()

@group.command(name='set')
@click.argument('identifier', required=False)
@click.option('--clear', is_flag=True, help='Clear the target group')
def set_target(identifier, clear):
    """Set target group for message categorization."""
    asyncio.run(_set_target_group(identifier, clear))

async def _set_target_group(identifier: Optional[str], clear: bool):
    """Set target group implementation."""
    try:
        settings_manager = await get_settings_manager()
        settings = settings_manager.load_user_settings()
        
        if clear:
            settings['selected_target_group'] = None
            settings_manager.save_user_settings(settings)
            display_success("Target group cleared")
            return
        
        # Get groups
        cache_manager = await get_cache_manager()
        groups, _ = cache_manager.load_group_cache()
        
        if not groups:
            display_error("No group cache found. Run 'sakaibot group list --refresh' first.")
            return
        
        selected_group = None
        
        if identifier:
            # Search for group
            identifier_lower = identifier.lower()
            matches = []
            for group in groups:
                if (str(group['id']) == identifier or 
                    identifier_lower in group.get('title', '').lower()):
                    matches.append(group)
            
            if not matches:
                display_error(f"No group found matching '{identifier}'")
                return
            
            if len(matches) == 1:
                selected_group = matches[0]
            else:
                # Multiple matches
                choices = [f"{g['title']} ({'Forum' if g.get('is_forum') else 'Regular'})" for g in matches]
                selection = prompt_choice("Multiple groups found. Select one:", choices)
                selected_group = matches[choices.index(selection)]
        else:
            # Interactive selection
            choices = [f"{g['title']} ({'Forum' if g.get('is_forum') else 'Regular'})" for g in groups]
            selection = prompt_choice("Select target group:", choices)
            selected_group = groups[choices.index(selection)]
        
        # Save selection
        settings['selected_target_group'] = selected_group['id']
        settings_manager.save_user_settings(settings)
        
        group_type = "Forum" if selected_group.get('is_forum') else "Regular"
        display_success(f"Target group set to: {selected_group['title']} ({group_type})")
        
        if selected_group.get('is_forum'):
            display_info("This is a forum group. Use 'sakaibot group map' to map commands to topics.")
        
    except Exception as e:
        display_error(f"Failed to set target group: {e}")

@group.command()
def topics():
    """List topics in the selected forum group."""
    asyncio.run(_list_topics())

async def _list_topics():
    """List topics implementation."""
    try:
        settings_manager = await get_settings_manager()
        settings = settings_manager.load_user_settings()
        
        group_id = settings.get('selected_target_group')
        if not group_id:
            display_error("No target group set. Use 'sakaibot group set' first.")
            return
        
        # Get group details
        cache_manager = await get_cache_manager()
        groups, _ = cache_manager.load_group_cache()
        
        selected_group = None
        for group in groups or []:
            if group['id'] == group_id:
                selected_group = group
                break
        
        if not selected_group:
            display_error(f"Target group (ID: {group_id}) not found in cache.")
            return
        
        if not selected_group.get('is_forum'):
            display_info(f"'{selected_group['title']}' is not a forum group (no topics).")
            return
        
        # Get topics
        client, client_manager = await get_telegram_client()
        if not client:
            return
        
        try:
            from src.telegram.utils import TelegramUtils
            telegram_utils = TelegramUtils()
            
            with ProgressSpinner(f"Fetching topics for '{selected_group['title']}'..."):
                topics = await telegram_utils.get_forum_topics(client, group_id)
            
            # Ensure topics is a list to prevent NoneType errors
            if not topics: # This check handles both None and empty list
                display_info("No topics found in this forum.")
                return
            
            # Display topics
            table = Table(title=f"Topics in '{selected_group['title']}'",
                         show_header=True, header_style="bold cyan")
            table.add_column("#", style="dim", width=6)
            table.add_column("Topic Title", style="cyan", width=40)
            table.add_column("Topic ID", style="yellow", width=15)
            
            # At this point, 'topics' should be a non-empty list, but let's verify
            for idx, topic in enumerate(topics, 1):
                if topic and isinstance(topic, dict) and 'title' in topic and 'id' in topic:
                    table.add_row(str(idx), topic['title'], str(topic['id']))
            
            console.print(table)
            display_success(f"Found {len(topics) if topics else 0} topics")
            
        finally:
            if client_manager:
                await client_manager.disconnect()
        
    except Exception as e:
        display_error(f"Failed to list topics: {e}")

@group.command()
@click.option('--add', 'action', flag_value='add', help='Add a new mapping')
@click.option('--remove', 'action', flag_value='remove', help='Remove a mapping')
@click.option('--clear', 'action', flag_value='clear', help='Clear all mappings')
@click.option('--list', 'action', flag_value='list', default=True, help='List mappings')
def map(action):
    """Manage command to topic/group mappings."""
    asyncio.run(_manage_mappings(action))

async def _load_and_normalize_mappings() -> tuple[dict, 'SettingsManager']:
    """Load settings and normalize mappings, handling potential data corruption."""
    settings_manager = await get_settings_manager()
    settings = settings_manager.load_user_settings()
    
    raw_mappings = settings.get('active_command_to_topic_map', {})
    
    # The normalize_command_mappings function now handles TypeError internally
    # and returns an empty dict if the data is invalid.
    from ..utils import normalize_command_mappings
    mappings = normalize_command_mappings(raw_mappings)
    
    # If normalization cleared the mappings, it implies the data was corrupt.
    # Save the cleaned (empty) mappings back to the settings file.
    if not mappings and raw_mappings:
        display_warning("Invalid mapping data detected; mappings have been reset.")
        settings['active_command_to_topic_map'] = {}
        settings_manager.save_user_settings(settings)
        
    return mappings, settings_manager

async def _manage_mappings(action: str):
    """Manage mappings implementation."""
    try:
        mappings, settings_manager = await _load_and_normalize_mappings()
        settings = settings_manager.load_user_settings()

        group_id = settings.get('selected_target_group')
        if not group_id and action not in ['list']:
            display_error("No target group set. Use 'sakaibot group set' first.")
            return

        if action == 'list':
            if not mappings:
                display_info("No command mappings defined.")
                return
            
            # Fetch topic names if target group is a forum
            topic_id_to_name = {}
            if group_id:
                try:
                    client, client_manager = await get_telegram_client()
                    if client:
                        # Get forum topics using TelegramUtils (already tested and working)
                        try:
                            from src.telegram.utils import TelegramUtils
                            telegram_utils = TelegramUtils()
                            topics = await telegram_utils.get_forum_topics(client, group_id)
                            
                            # Build topic_id to name mapping
                            if topics:
                                for topic in topics:
                                    if topic and isinstance(topic, dict) and 'id' in topic and 'title' in topic:
                                        topic_id_to_name[topic['id']] = topic['title']
                        except Exception as e:
                            # Not a forum or can't fetch topics, continue without names
                            # Silently ignore to avoid disrupting the display
                            pass
                        finally:
                            if client_manager:
                                await client_manager.disconnect()
                except Exception:
                    # If we can't get client, continue without topic names
                    pass
            
            # Display mappings with a numbered index for consistency
            table = Table(title="Command Mappings", show_header=True, header_style="bold cyan")
            table.add_column("#", style="dim", width=6)
            table.add_column("Commands", style="cyan", width=30)
            table.add_column("Target", style="green", width=40)
            
            for idx, (topic_id, commands) in enumerate(mappings.items(), 1):
                if topic_id is None:
                    target = "Main Group Chat"
                else:
                    # Show topic name if available
                    topic_name = topic_id_to_name.get(topic_id)
                    if topic_name:
                        target = f"Topic ID: {topic_id} ({topic_name})"
                    else:
                        target = f"Topic ID: {topic_id}"
                
                # Safely join commands, handling potential None values
                if commands and isinstance(commands, list):
                    command_list = ", ".join([f"/{cmd}" for cmd in commands if cmd is not None])
                else:
                    command_list = "No commands"
                table.add_row(str(idx), command_list, target)
            
            console.print(table)
            
        elif action == 'add':
            # Add new mapping
            command_input = prompt_text("Enter command (without /)")
            if not command_input:
                display_error("Command cannot be empty")
                return
            canonical_command = command_input.strip().lower().lstrip('/')
            if not canonical_command:
                display_error("Command cannot be empty")
                return
            
            # Check if command already exists
            existing_topic = None
            for topic_id, commands in mappings.items():
                if commands and isinstance(commands, list) and canonical_command in commands:
                    existing_topic = topic_id
                    break
            
            if existing_topic is not None:
                if existing_topic is None:
                    target = "Main Group Chat"
                else:
                    target = f"Topic ID {existing_topic}"
                display_warning(f"Command /{canonical_command} already maps to {target}. It will be updated.")
            
            # Check if forum group
            cache_manager = await get_cache_manager()
            groups, _ = cache_manager.load_group_cache()
            
            is_forum = False
            for group in groups or []:
                if group['id'] == group_id:
                    is_forum = group.get('is_forum', False)
                    break
            
            topic_id = None
            if is_forum:
                # Get topics and let user choose
                client, client_manager = await get_telegram_client()
                if not client:
                    return
                
                try:
                    from src.telegram.utils import TelegramUtils
                    telegram_utils = TelegramUtils()
                    
                    topics = await telegram_utils.get_forum_topics(client, group_id)
                    # Ensure topics is a list to prevent NoneType errors in subsequent logic
                    if not topics: # This handles both None and empty list
                        display_info("No topics found in this forum. Command will map to main group chat.")
                        # topic_id remains None, which maps to main group chat
                    else:
                        # At this point, 'topics' is a guaranteed non-empty list with valid entries
                        valid_topics = [t for t in topics if t and isinstance(t, dict) and 'title' in t and 'id' in t]
                        if not valid_topics:
                            display_info("No valid topics found in this forum. Command will map to main group chat.")
                        else:
                            choices = ["Main Group Chat"] + [t['title'] for t in valid_topics]
                            selection = prompt_choice("Select target for this command:", choices)
                            
                            if selection != "Main Group Chat":
                                topic_idx = choices.index(selection) - 1
                                topic_id = valid_topics[topic_idx]['id']
                finally:
                    if client_manager:
                        await client_manager.disconnect()
            
            # Remove command from any existing topic if it exists
            for existing_topic_id, commands in list(mappings.items()):
                if not commands or not isinstance(commands, list):
                    continue
                if canonical_command in commands:
                    commands[:] = [cmd for cmd in commands if cmd != canonical_command]
                    if not commands:
                        mappings.pop(existing_topic_id, None)
                    break

            # Add command to the selected topic
            # Ensure the key exists before appending
            mappings.setdefault(topic_id, []).append(canonical_command)

            normalized_mappings = normalize_command_mappings(mappings)
            settings['active_command_to_topic_map'] = normalized_mappings
            settings_manager.save_user_settings(settings)
            
            target = "Main Group Chat" if topic_id is None else f"Topic ID {topic_id}"
            display_success(f"Mapping added: /{canonical_command} -> {target}")
            
        elif action == 'remove':
            if not mappings:
                display_info("No mappings to remove.")
                return
            
            mapping_entries: List[Dict[str, Any]] = []
            for topic_id, commands in mappings.items():
                if not commands or not isinstance(commands, list):
                    continue
                for command in commands:
                    if not isinstance(command, str) or not command:
                        continue
                    target_label = "Main Group Chat" if topic_id is None else f"Topic ID {topic_id}"
                    mapping_entries.append({
                        "topic_id": topic_id,
                        "command": command,
                        "label": f"/{command} -> {target_label}"
                    })
            
            if not mapping_entries:
                display_info("No mappings to remove.")
                return
            
            selection = prompt_choice(
                "Select mapping to remove:",
                [entry["label"] for entry in mapping_entries]
            )
            
            selected_entry = next((entry for entry in mapping_entries if entry["label"] == selection), None)
            if not selected_entry:
                display_warning("Selected mapping could not be found. No changes made.")
                return
            
            topic_id = selected_entry["topic_id"]
            command_to_remove = selected_entry["command"]
            command_list = mappings.get(topic_id, [])
            if isinstance(command_list, list):
                command_list[:] = [cmd for cmd in command_list if cmd != command_to_remove]
                if not command_list:
                    mappings.pop(topic_id, None)
            
            normalized_mappings = normalize_command_mappings(mappings)
            settings['active_command_to_topic_map'] = normalized_mappings
            settings_manager.save_user_settings(settings)
            
            display_success(f"Mapping removed: {selection}")
            
        elif action == 'clear':
            if not mappings:
                display_info("No mappings to clear.")
                return
            
            # Count total commands across all topics, handling potential None values in commands lists
            total_commands = 0
            for commands_list in mappings.values():
                if commands_list and isinstance(commands_list, list):
                    total_commands += len([cmd for cmd in commands_list if cmd is not None])
            
            if confirm_action(f"Clear all {total_commands} mappings?"):
                settings['active_command_to_topic_map'] = {}
                settings_manager.save_user_settings(settings)
                display_success("All mappings cleared")
            else:
                display_info("Operation cancelled")
            
    except Exception as e:
        display_error(f"Failed to manage mappings: {e}")
