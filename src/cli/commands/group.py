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
    confirm_action, console
)

@click.group()
def group():
    """Manage groups and categorization."""
    pass

@group.command()
@click.option('--refresh', is_flag=True, help='Refresh cache before listing')
@click.option('--all', 'show_all', is_flag=True, help='Show all groups (not just admin)')
def list(refresh, show_all):
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

async def _manage_mappings(action: str):
    """Manage mappings implementation."""
    try:
        settings_manager = await get_settings_manager()
        settings = settings_manager.load_user_settings()
        
        group_id = settings.get('selected_target_group')
        if not group_id and action != 'list':
            display_error("No target group set. Use 'sakaibot group set' first.")
            return
        
        # For backward compatibility, convert old format to new format if needed
        old_mappings = settings.get('active_command_to_topic_map', {})
        # Ensure mappings is a dict to prevent type errors
        mappings = old_mappings if isinstance(old_mappings, dict) else {}
        
        # Double-check that mappings is a dict to prevent type errors
        if not isinstance(mappings, dict):
            mappings = {}
        
        # Check if we have old format (command -> topic_id) or new format (topic_id -> [commands])
        has_old_format = False
        if mappings and len(mappings) > 0:
            try:
                # Get first value to check format
                first_value = next(iter(mappings.values()))
                # Check if the value is a simple type (int or None) indicating old format
                if first_value is None or isinstance(first_value, int):
                    # Old format: command_name -> topic_id
                    has_old_format = True
            except StopIteration:
                # This shouldn't happen since we check len(mappings) > 0, but just in case
                pass
            except TypeError:
                # Handle edge case where there's an issue with type checking
                pass
        
        if has_old_format:
            # Convert old format (command -> topic_id) to new format (topic_id -> [commands])
            new_format = {}
            for command, topic_id in mappings.items():
                if topic_id not in new_format:
                    new_format[topic_id] = []
                new_format[topic_id].append(command)
            settings['active_command_to_topic_map'] = new_format
            mappings = new_format
        
        if action == 'list':
            if not mappings:
                display_info("No command mappings defined.")
                return
            
            # Display mappings with a numbered index for consistency
            table = Table(title="Command Mappings", show_header=True, header_style="bold cyan")
            table.add_column("#", style="dim", width=6)
            table.add_column("Commands", style="cyan", width=30)
            table.add_column("Target", style="green", width=40)
            
            for idx, (topic_id, commands) in enumerate(mappings.items(), 1):
                if topic_id is None:
                    target = "Main Group Chat"
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
            command = prompt_text("Enter command (without /)")
            if not command:
                display_error("Command cannot be empty")
                return
            
            # Check if command already exists
            existing_topic = None
            try:
                for topic_id, commands in mappings.items():
                    if commands and isinstance(commands, list) and command in commands:
                        existing_topic = topic_id
                        break
            except TypeError:
                # Handle case where isinstance receives invalid arguments
                display_warning("Invalid mapping data detected, resetting mappings")
                mappings = {}
            
            if existing_topic is not None:
                if existing_topic is None:
                    target = "Main Group Chat"
                else:
                    target = f"Topic ID {existing_topic}"
                display_warning(f"Command /{command} already maps to {target}. It will be updated.")
            
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
            try:
                for existing_topic_id, commands in mappings.items():
                    if commands and isinstance(commands, list) and command in commands:
                        commands.remove(command)
                        # Remove the topic key if it has no commands left
                        if not commands:
                            del mappings[existing_topic_id]
                        break
            except TypeError:
                # Handle case where isinstance receives invalid arguments
                display_warning("Invalid mapping data detected during cleanup, resetting mappings")
                mappings = {}
            
            # Add command to the selected topic
            if topic_id not in mappings:
                mappings[topic_id] = []
            mappings[topic_id].append(command)
            
            settings['active_command_to_topic_map'] = mappings
            settings_manager.save_user_settings(settings)
            
            target = "Main Group Chat" if topic_id is None else f"Topic ID {topic_id}"
            display_success(f"Mapping added: /{command} → {target}")
            
        elif action == 'remove':
            if not mappings:
                display_info("No mappings to remove.")
                return
            
            # Flatten the mappings to show all command-topic pairs for selection
            all_mappings = []
            for topic_id, commands in mappings.items():
                if commands and isinstance(commands, list):
                    for command in commands:
                        if command is not None:  # Check if command is not None
                            if topic_id is None:
                                target = "Main Group Chat"
                            else:
                                target = f"Topic ID: {topic_id}"
                            all_mappings.append(f"/{command} → {target}")
            
            if not all_mappings:
                display_info("No mappings to remove.")
                return
            
            selection = prompt_choice("Select mapping to remove:", all_mappings)
            
            # Find the command and topic to remove
            for topic_id, commands in mappings.items():
                if commands and isinstance(commands, list):
                    for command in commands:
                        if command is not None:
                            if topic_id is None:
                                target = "Main Group Chat"
                            else:
                                target = f"Topic ID: {topic_id}"
                            
                            if f"/{command} → {target}" == selection:
                                commands.remove(command)
                                # Remove the topic key if it has no commands left
                                if not commands:
                                    del mappings[topic_id]
                                break
                    else:
                        continue
                    break
            
            settings['active_command_to_topic_map'] = mappings
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
