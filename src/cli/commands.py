"""CLI command implementations for SakaiBot.

This module contains the implementation of all CLI commands and operations,
providing the business logic for menu actions and user interactions.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple

from .models import CLIState, SelectionResult, SearchCriteria
from .menu import RichMenu
from .state import StateManager
from ..core.exceptions import CLIError, InputError, TelegramError
from ..core.constants import APP_NAME

logger = logging.getLogger(__name__)


class CLICommands:
    """Implementation of CLI commands and operations."""
    
    def __init__(
        self,
        state_manager: StateManager,
        menu: RichMenu,
        client,
        cache_manager,
        telegram_utils,
        settings_manager,
        event_handlers
    ):
        """Initialize CLI commands.
        
        Args:
            state_manager: State manager instance
            menu: Rich menu instance
            client: Telegram client
            cache_manager: Cache manager instance
            telegram_utils: Telegram utilities module
            settings_manager: Settings manager instance
            event_handlers: Event handlers module
        """
        self.state_manager = state_manager
        self.menu = menu
        self.client = client
        self.cache_manager = cache_manager
        self.telegram_utils = telegram_utils
        self.settings_manager = settings_manager
        self.event_handlers = event_handlers
    
    async def list_cached_pvs(self, show_numbers: bool = True) -> List[Dict[str, Any]]:
        """List cached private chats.
        
        Args:
            show_numbers: Whether to show row numbers
            
        Returns:
            List[Dict[str, Any]]: List of PV data
        """
        try:
            self.menu.console.print("\n[blue]Fetching cached PV list...[/blue]")
            
            # Get PVs without forcing refresh (will fetch if cache is empty)
            pvs = await self.cache_manager.get_pvs(
                self.client,
                self.telegram_utils,
                force_refresh=False
            )
            
            if not pvs:
                self.menu.display_warning(
                    "Your PV cache is currently empty",
                    "You might want to use 'Refresh/Update PV List' (Option 2) to populate it."
                )
                return []
            
            self.menu.display_entity_table(
                pvs,
                "All Your Cached Private Chats (PVs)",
                entity_type="PV",
                show_numbers=show_numbers
            )
            
            return pvs
            
        except Exception as e:
            logger.error(f"Error listing cached PVs: {e}", exc_info=True)
            self.menu.display_error("Failed to list cached PVs", str(e))
            return []
    
    async def refresh_pvs(self) -> Optional[List[Dict[str, Any]]]:
        """Refresh PV list from Telegram.
        
        Returns:
            Optional[List[Dict[str, Any]]]: Refreshed PV list or None if failed
        """
        try:
            # Show loading while refreshing
            refreshed_pvs = await self.menu.show_loading(
                "Refreshing PV list from Telegram...",
                self.cache_manager.get_pvs(
                    self.client,
                    self.telegram_utils,
                    force_refresh=True
                )
            )
            
            if refreshed_pvs is not None:
                self.menu.display_success(
                    f"PV list refreshed successfully",
                    f"Total PVs in cache: {len(refreshed_pvs)}"
                )
                
                if refreshed_pvs:
                    self.menu.display_entity_table(
                        refreshed_pvs,
                        "Updated PV List (Cache)",
                        entity_type="PV",
                        show_numbers=False
                    )
                return refreshed_pvs
            else:
                self.menu.display_error(
                    "Failed to refresh PV list",
                    "Please check logs for details"
                )
                return None
                
        except Exception as e:
            logger.error(f"Error refreshing PVs: {e}", exc_info=True)
            self.menu.display_error("PV refresh failed", str(e))
            return None
    
    async def search_pvs(self, show_numbers: bool = True) -> List[Dict[str, Any]]:
        """Search cached PVs interactively.
        
        Args:
            show_numbers: Whether to show row numbers
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        try:
            # Get all cached PVs first
            all_pvs = await self.cache_manager.get_pvs(
                self.client,
                self.telegram_utils,
                force_refresh=False
            )
            
            if not all_pvs:
                self.menu.display_warning(
                    "PV cache is empty",
                    "Try refreshing the PV list first (Option 2)"
                )
                return []
            
            # Perform search
            results = await self.menu.search_entities(all_pvs, "PV")
            return results
            
        except Exception as e:
            logger.error(f"Error searching PVs: {e}", exc_info=True)
            self.menu.display_error("PV search failed", str(e))
            return []
    
    async def set_default_pv_context(self) -> None:
        """Set default PV context for analysis commands."""
        try:
            self.menu.console.print("\n[bold]Set Default PV Context (for /analyze)[/bold]")
            
            # Show options
            options_table = Table(show_header=False, box=None)
            options_table.add_column("Option", style="cyan", width=3)
            options_table.add_column("Description", style="white")
            
            options_table.add_row("1", "List all cached PVs to select from")
            options_table.add_row("2", "Search cached PVs to select from")
            options_table.add_row("9", "Clear Default PV Context")
            options_table.add_row("0", "Back to main menu")
            
            self.menu.console.print(options_table)
            
            choice = await self.menu.get_user_choice("Choose an option", expect_int=True)
            
            if choice == 0:
                return
            elif choice == 9:
                self.state_manager.clear_default_pv()
                self.menu.display_success("Default PV context cleared")
                return
            
            # Get PVs based on choice
            pvs_to_select_from = []
            if choice == 1:
                pvs_to_select_from = await self.list_cached_pvs(show_numbers=True)
            elif choice == 2:
                pvs_to_select_from = await self.search_pvs(show_numbers=True)
            else:
                self.menu.display_error("Invalid option")
                return
            
            if not pvs_to_select_from:
                self.menu.display_warning("No PVs available for selection")
                return
            
            # Get user selection
            selection = await self.menu.get_selection_from_list(
                pvs_to_select_from,
                "Select Default PV Context",
                "PV"
            )
            
            if selection.success and selection.selected_item:
                self.state_manager.set_default_pv(selection.selected_item)
                pv_name = selection.selected_item['display_name']
                pv_id = selection.selected_item['id']
                self.menu.display_success(
                    f"Default PV context set to '{pv_name}'",
                    f"ID: {pv_id}"
                )
            elif selection.cancelled:
                self.menu.display_info("Selection cancelled")
            else:
                self.menu.display_error(selection.error_message or "Selection failed")
                
        except Exception as e:
            logger.error(f"Error setting default PV context: {e}", exc_info=True)
            self.menu.display_error("Failed to set default PV context", str(e))
    
    async def set_target_group(self) -> None:
        """Set target group for categorization."""
        try:
            self.menu.console.print("\n[bold]Set/Change Categorization Target Group[/bold]")
            
            # Fetch user groups
            user_groups = await self.menu.show_loading(
                "Fetching your groups (admin/owner supergroups)...",
                self.cache_manager.get_groups(
                    self.client,
                    self.telegram_utils,
                    force_refresh=False,
                    require_admin_rights=True
                )
            )
            
            if not user_groups:
                self.menu.display_warning(
                    "No qualifying supergroups found",
                    "You must be an admin/owner of supergroups to use categorization"
                )
                return
            
            # Get user selection
            selection = await self.menu.get_selection_from_list(
                user_groups,
                "Your Qualifying Supergroups",
                "Group"
            )
            
            if not selection.success:
                if selection.cancelled:
                    self.menu.display_info("Target group selection cancelled")
                else:
                    self.menu.display_error(selection.error_message or "Selection failed")
                return
            
            chosen_group = selection.selected_item
            
            # Verify group and fetch topics
            group_title = chosen_group['title']
            group_id = chosen_group['id']
            
            self.menu.console.print(f"\n[blue]Verifying group '{group_title}' and fetching topics...[/blue]")
            
            try:
                topics, is_forum = await self.telegram_utils.get_group_topics(self.client, group_id)
                
                updated_group_info = {
                    'id': group_id,
                    'title': group_title,
                    'is_forum': is_forum
                }
                
                # Update state
                self.state_manager.set_target_group(updated_group_info)
                self.state_manager.state.current_group_topics_cache = topics if is_forum else []
                
                # Display success and group info
                self.menu.display_success(f"Target group set to '{group_title}'")
                
                if is_forum:
                    self.menu.display_info(f"This group is a forum with {len(topics)} topics")
                    
                    if topics:
                        self.menu.display_entity_table(
                            topics,
                            f"Topics in '{group_title}'",
                            entity_type="Topic",
                            show_numbers=False
                        )
                    else:
                        self.menu.display_warning(
                            "No topics found in forum",
                            "You may need to add topics manually"
                        )
                else:
                    self.menu.display_info(
                        f"'{group_title}' is a regular group",
                        "Messages will be sent to the main group chat"
                    )
                
                self.menu.display_info(
                    "Next step: Configure command mappings",
                    "Use 'Manage Command Mappings' (Option 6)"
                )
                
            except Exception as e:
                logger.error(f"Error verifying group {group_id}: {e}", exc_info=True)
                self.menu.display_error(f"Failed to verify group '{group_title}'", str(e))
                
        except Exception as e:
            logger.error(f"Error setting target group: {e}", exc_info=True)
            self.menu.display_error("Failed to set target group", str(e))
    
    async def manage_command_mappings(self) -> None:
        """Manage command to topic mappings."""
        state = self.state_manager.state
        
        if not state.selected_target_group:
            self.menu.display_warning(
                "No target group selected",
                "Please set a target group first (Option 5)"
            )
            return
        
        group_title = state.selected_target_group['title']
        group_id = state.selected_target_group['id']
        is_forum = state.selected_target_group.get('is_forum', False)
        
        self.menu.console.print(f"\n[bold]Manage Command Mappings for: '{group_title}'[/bold]")
        
        # Ensure topics are cached for forum groups
        if is_forum and not state.current_group_topics_cache:
            try:
                topics, _ = await self.menu.show_loading(
                    f"Fetching topics for forum '{group_title}'...",
                    self.telegram_utils.get_group_topics(self.client, group_id)
                )
                state.current_group_topics_cache = topics
            except Exception as e:
                logger.error(f"Failed to fetch topics for group {group_id}: {e}", exc_info=True)
                self.menu.display_error(f"Could not fetch topics for '{group_title}'")
                state.current_group_topics_cache = []
        
        while True:
            # Display submenu
            submenu_table = Table(show_header=False, box=None)
            submenu_table.add_column("Option", style="cyan", width=3)
            submenu_table.add_column("Description", style="white")
            
            submenu_table.add_row("1", "View current command mappings")
            
            if is_forum:
                submenu_table.add_row("2", "Add new command (select topic from list)")
                submenu_table.add_row("3", "Add new command (manual Topic ID entry)")
            else:
                submenu_table.add_row("2", "Add new command (will send to main group chat)")
            
            submenu_table.add_row("4", "Remove a command mapping")
            submenu_table.add_row("0", "Back to main menu")
            
            self.menu.console.print("\nCommand Mapping Menu:")
            self.menu.console.print(submenu_table)
            
            try:
                choice = await self.menu.get_user_choice("Mapping choice", expect_int=True)
                
                if choice == 0:
                    break
                elif choice == 1:
                    self.menu.display_command_mappings(state)
                elif choice == 2:
                    await self._add_command_mapping_from_list(is_forum, group_title)
                elif choice == 3 and is_forum:
                    await self._add_command_mapping_manual(group_id, group_title)
                elif choice == 3 and not is_forum:
                    self.menu.display_warning("Manual Topic ID not applicable for non-forum groups")
                elif choice == 4:
                    await self._remove_command_mapping()
                else:
                    self.menu.display_error("Invalid choice")
                    
            except InputError:
                continue
            
            if choice != 0:
                await self.menu.wait_for_keypress()
    
    async def _add_command_mapping_from_list(
        self,
        is_forum: bool,
        group_title: str
    ) -> None:
        """Add command mapping by selecting from topic list.
        
        Args:
            is_forum: Whether target group is a forum
            group_title: Group title for display
        """
        try:
            command_name = await self.menu.get_user_choice(
                "Enter new command name (without '/')",
                expect_int=False
            )
            
            if not command_name:
                self.menu.display_error("Command name cannot be empty")
                return
            
            # Sanitize command name
            command_name = command_name.strip().lower().replace(" ", "_")
            
            if not command_name:
                self.menu.display_error("Invalid command name")
                return
            
            if is_forum:
                state = self.state_manager.state
                
                if not state.current_group_topics_cache:
                    self.menu.display_warning(
                        f"No topics found for '{group_title}'",
                        "Try manual topic ID entry instead"
                    )
                    return
                
                # Get topic selection
                selection = await self.menu.get_selection_from_list(
                    state.current_group_topics_cache,
                    f"Select Topic for '/{command_name}'",
                    "Topic"
                )
                
                if selection.success and selection.selected_item:
                    topic = selection.selected_item
                    self.state_manager.add_command_mapping(command_name, topic['id'])
                    self.menu.display_success(
                        f"Command '/{command_name}' mapped to topic '{topic['title']}'"
                    )
                elif selection.cancelled:
                    self.menu.display_info("Command mapping cancelled")
            else:
                # Non-forum group - map to main chat
                self.state_manager.add_command_mapping(command_name, None)
                self.menu.display_success(
                    f"Command '/{command_name}' will send to main chat of '{group_title}'"
                )
                
        except InputError:
            pass  # User cancelled
        except Exception as e:
            logger.error(f"Error adding command mapping: {e}", exc_info=True)
            self.menu.display_error("Failed to add command mapping", str(e))
    
    async def _add_command_mapping_manual(
        self,
        group_id: int,
        group_title: str
    ) -> None:
        """Add command mapping with manual topic ID entry.
        
        Args:
            group_id: Target group ID
            group_title: Group title for display
        """
        try:
            command_name = await self.menu.get_user_choice(
                "Enter new command name (without '/')",
                expect_int=False
            )
            
            if not command_name:
                self.menu.display_error("Command name cannot be empty")
                return
            
            # Sanitize command name
            command_name = command_name.strip().lower().replace(" ", "_")
            
            if not command_name:
                self.menu.display_error("Invalid command name")
                return
            
            topic_id = await self.menu.get_user_choice(
                f"Enter Topic ID for '/{command_name}'",
                expect_int=True
            )
            
            # Verify topic exists
            self.menu.console.print(f"\n[blue]Verifying Topic ID {topic_id} in '{group_title}'...[/blue]")
            
            topic_info = await self.telegram_utils.get_topic_info_by_id(
                self.client,
                group_id,
                topic_id
            )
            
            if topic_info:
                self.menu.console.print(
                    f"\n[green]Verified Topic:[/green] '{topic_info['title']}' (ID: {topic_info['id']})"
                )
                
                confirmed = await self.menu.confirm_action(
                    f"Map '/{command_name}' to this topic?"
                )
                
                if confirmed:
                    self.state_manager.add_command_mapping(command_name, topic_info['id'])
                    self.menu.display_success(
                        f"Command '/{command_name}' mapped to '{topic_info['title']}'"
                    )
                    
                    # Add to cache if not present
                    state = self.state_manager.state
                    if not any(t['id'] == topic_info['id'] for t in state.current_group_topics_cache):
                        state.current_group_topics_cache.append(topic_info)
                else:
                    self.menu.display_info("Mapping cancelled")
            else:
                self.menu.display_error(f"Could not verify Topic ID {topic_id} in '{group_title}'")
                
        except InputError:
            pass  # User cancelled
        except Exception as e:
            logger.error(f"Error adding manual command mapping: {e}", exc_info=True)
            self.menu.display_error("Failed to add command mapping", str(e))
    
    async def _remove_command_mapping(self) -> None:
        """Remove a command mapping."""
        state = self.state_manager.state
        
        if not state.active_command_to_topic_map:
            self.menu.display_warning("No command mappings to remove")
            return
        
        # Create table of current mappings
        mappings_list = list(state.active_command_to_topic_map.items())
        
        table = Table(
            title="Current Command Mappings (for removal)",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("No.", style="cyan", width=6)
        table.add_column("Command", style="white", width=20)
        table.add_column("Target", style="blue", width=40)
        
        is_forum = state.selected_target_group and state.selected_target_group.get('is_forum', False)
        
        for idx, (command, topic_id) in enumerate(mappings_list):
            target_description = "Main Group Chat"
            
            if topic_id is not None and is_forum:
                topic_title = next(
                    (t['title'] for t in state.current_group_topics_cache if t['id'] == topic_id),
                    f"Unknown Topic (ID: {topic_id})"
                )
                target_description = f"Topic: '{topic_title}' (ID: {topic_id})"
            elif topic_id is not None:
                target_description = f"Target ID: {topic_id} (Non-forum with topic ID)"
            
            table.add_row(
                str(idx + 1),
                f"/{command}",
                target_description
            )
        
        self.menu.console.print(table)
        
        try:
            choice = await self.menu.get_user_choice(
                f"Enter number to remove (1-{len(mappings_list)}) or 0 to cancel",
                expect_int=True
            )
            
            if choice == 0:
                self.menu.display_info("Removal cancelled")
                return
            
            if 1 <= choice <= len(mappings_list):
                command_to_remove = mappings_list[choice - 1][0]
                
                if self.state_manager.remove_command_mapping(command_to_remove):
                    self.menu.display_success(f"Command mapping '/{command_to_remove}' removed")
                else:
                    self.menu.display_error(f"Failed to remove mapping for '/{command_to_remove}'")
            else:
                self.menu.display_error("Invalid selection")
                
        except InputError:
            pass  # User cancelled
    
    async def manage_authorized_pvs(self) -> None:
        """Manage directly authorized PVs."""
        while True:
            self.menu.console.print("\n[bold]Manage Directly Authorized PVs[/bold]")
            
            # Display submenu
            submenu_table = Table(show_header=False, box=None)
            submenu_table.add_column("Option", style="cyan", width=3)
            submenu_table.add_column("Description", style="white")
            
            submenu_table.add_row("1", "View authorized PVs")
            submenu_table.add_row("2", "Authorize new PV (list all cached PVs)")
            submenu_table.add_row("3", "Authorize new PV (search cached PVs)")
            submenu_table.add_row("4", "De-authorize a PV")
            submenu_table.add_row("0", "Back to main menu")
            
            self.menu.console.print(submenu_table)
            
            try:
                choice = await self.menu.get_user_choice("Authorization choice", expect_int=True)
                
                if choice == 0:
                    break
                elif choice == 1:
                    await self._view_authorized_pvs()
                elif choice == 2:
                    await self._authorize_pv_from_list()
                elif choice == 3:
                    await self._authorize_pv_from_search()
                elif choice == 4:
                    await self._deauthorize_pv()
                else:
                    self.menu.display_error("Invalid choice")
                    
            except InputError:
                continue
            
            if choice != 0:
                await self.menu.wait_for_keypress()
    
    async def _view_authorized_pvs(self) -> None:
        """View currently authorized PVs."""
        state = self.state_manager.state
        
        if not state.directly_authorized_pvs:
            self.menu.display_info("No PVs are currently authorized for direct commands")
            return
        
        self.menu.display_entity_table(
            state.directly_authorized_pvs,
            "Directly Authorized PVs",
            entity_type="PV",
            show_numbers=False
        )
    
    async def _authorize_pv_from_list(self) -> None:
        """Authorize PV by selecting from cached list."""
        try:
            pvs = await self.list_cached_pvs(show_numbers=True)
            if not pvs:
                return
            
            selection = await self.menu.get_selection_from_list(
                pvs,
                "Select PV to Authorize",
                "PV"
            )
            
            if selection.success and selection.selected_item:
                if self.state_manager.authorize_pv(selection.selected_item):
                    pv_name = selection.selected_item['display_name']
                    self.menu.display_success(f"PV '{pv_name}' is now authorized for direct commands")
                else:
                    pv_name = selection.selected_item['display_name']
                    self.menu.display_warning(f"PV '{pv_name}' is already authorized")
            elif selection.cancelled:
                self.menu.display_info("Authorization cancelled")
            else:
                self.menu.display_error(selection.error_message or "Authorization failed")
                
        except Exception as e:
            logger.error(f"Error authorizing PV from list: {e}", exc_info=True)
            self.menu.display_error("Authorization failed", str(e))
    
    async def _authorize_pv_from_search(self) -> None:
        """Authorize PV by searching cached list."""
        try:
            search_results = await self.search_pvs(show_numbers=True)
            if not search_results:
                return
            
            selection = await self.menu.get_selection_from_list(
                search_results,
                "Select PV to Authorize",
                "PV"
            )
            
            if selection.success and selection.selected_item:
                if self.state_manager.authorize_pv(selection.selected_item):
                    pv_name = selection.selected_item['display_name']
                    self.menu.display_success(f"PV '{pv_name}' is now authorized for direct commands")
                else:
                    pv_name = selection.selected_item['display_name']
                    self.menu.display_warning(f"PV '{pv_name}' is already authorized")
            elif selection.cancelled:
                self.menu.display_info("Authorization cancelled")
            else:
                self.menu.display_error(selection.error_message or "Authorization failed")
                
        except Exception as e:
            logger.error(f"Error authorizing PV from search: {e}", exc_info=True)
            self.menu.display_error("Authorization failed", str(e))
    
    async def _deauthorize_pv(self) -> None:
        """De-authorize a PV."""
        state = self.state_manager.state
        
        if not state.directly_authorized_pvs:
            self.menu.display_info("No PVs are currently authorized to de-authorize")
            return
        
        selection = await self.menu.get_selection_from_list(
            state.directly_authorized_pvs,
            "Select PV to De-authorize",
            "PV"
        )
        
        if selection.success and selection.selected_item:
            pv_id = selection.selected_item['id']
            deauthorized = self.state_manager.deauthorize_pv(pv_id)
            
            if deauthorized:
                self.menu.display_success(
                    f"PV '{deauthorized['display_name']}' is no longer authorized"
                )
            else:
                self.menu.display_error("Failed to de-authorize PV")
        elif selection.cancelled:
            self.menu.display_info("De-authorization cancelled")
        else:
            self.menu.display_error(selection.error_message or "De-authorization failed")
    
    async def toggle_monitoring(self) -> None:
        """Toggle global monitoring on/off."""
        state = self.state_manager.state
        
        try:
            if state.is_monitoring_active:
                await self._stop_monitoring()
            else:
                await self._start_monitoring()
                
        except Exception as e:
            logger.error(f"Error toggling monitoring: {e}", exc_info=True)
            self.menu.display_error("Failed to toggle monitoring", str(e))
    
    async def _start_monitoring(self) -> None:
        """Start global monitoring."""
        state = self.state_manager.state
        
        # Check requirements
        can_start, missing_requirements = state.can_start_monitoring()
        
        if not can_start:
            self.menu.display_monitoring_requirements(missing_requirements)
            return
        
        try:
            # Set up event handlers
            import functools
            from telethon import events
            
            # Owner handler
            owner_handler = functools.partial(
                self.event_handlers.categorization_reply_handler_owner,
                client=self.client,
                cli_state_ref=state
            )
            owner_filter = events.NewMessage(outgoing=True)
            
            # Authorized user handler
            authorized_handler = functools.partial(
                self.event_handlers.authorized_user_command_handler,
                client=self.client,
                cli_state_ref=state
            )
            
            # Create filters for authorized PVs
            authorized_pv_ids = state.get_authorized_pv_ids()
            auth_filters = []
            
            if authorized_pv_ids:
                auth_filter = events.NewMessage(incoming=True, chats=authorized_pv_ids)
                auth_filters.append(auth_filter)
            
            # Register handlers
            self.client.add_event_handler(owner_handler, owner_filter)
            logger.info("Owner event handler registered")
            
            for auth_filter in auth_filters:
                self.client.add_event_handler(authorized_handler, auth_filter)
                logger.info(f"Authorized user handler registered for chats: {auth_filter.chats}")
            
            # Update state
            handler_info = (owner_handler, owner_filter, authorized_handler, auth_filters)
            self.state_manager.set_monitoring_active(True, handler_info)
            
            self.menu.display_success(
                "Global monitoring started",
                "SakaiBot will now process commands from you and authorized users"
            )
            
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}", exc_info=True)
            self.menu.display_error("Failed to start monitoring", str(e))
    
    async def _stop_monitoring(self) -> None:
        """Stop global monitoring."""
        state = self.state_manager.state
        
        if not state.registered_handler_info:
            self.menu.display_warning("No active monitoring to stop")
            state.is_monitoring_active = False
            return
        
        try:
            owner_handler, owner_filter, auth_handler, auth_filters = state.registered_handler_info
            
            # Remove handlers
            if owner_handler and owner_filter:
                self.client.remove_event_handler(owner_handler, owner_filter)
                logger.info("Owner event handler removed")
            
            if auth_handler and auth_filters:
                for auth_filter in auth_filters:
                    self.client.remove_event_handler(auth_handler, auth_filter)
                logger.info("Authorized user handlers removed")
            
            # Update state
            self.state_manager.set_monitoring_active(False, None)
            
            self.menu.display_success("Global monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}", exc_info=True)
            self.menu.display_error("Error stopping monitoring", str(e))
            # Force state update even if removal failed
            state.is_monitoring_active = False
            state.registered_handler_info = None
    
    async def exit_cli(self) -> bool:
        """Handle CLI exit with cleanup.
        
        Returns:
            bool: True if exit should proceed, False to cancel
        """
        try:
            self.menu.console.print("\n[bold]Exiting SakaiBot CLI...[/bold]")
            
            # Save settings
            await self.menu.show_loading(
                "Saving settings...",
                self.state_manager.save_settings()
            )
            
            # Stop monitoring if active
            state = self.state_manager.state
            if state.is_monitoring_active:
                self.menu.console.print("[blue]Stopping monitoring...[/blue]")
                await self._stop_monitoring()
            
            self.menu.display_success("Settings saved and cleanup completed")
            self.menu.console.print(f"\n[dim]Thank you for using {APP_NAME}![/dim]")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during CLI exit: {e}", exc_info=True)
            self.menu.display_error("Error during exit cleanup", str(e))
            
            # Ask user if they want to force exit
            force_exit = await self.menu.confirm_action(
                "Exit anyway without saving?",
                default=False
            )
            return force_exit
    
    def display_startup_check(self, health: Dict[str, Any]) -> None:
        """Display startup health check results.
        
        Args:
            health: Health check results
        """
        if health["status"] == "healthy":
            self.menu.display_success("CLI initialized successfully")
        elif health["status"] == "degraded":
            issues = health.get("issues", [])
            self.menu.display_warning(
                "CLI initialized with warnings",
                "\n".join([f"• {issue}" for issue in issues])
            )
        else:
            error_msg = health.get("error", "Unknown error")
            self.menu.display_error("CLI initialization failed", error_msg)
    
    async def display_config_wizard(self) -> None:
        """Display configuration wizard for first-time setup."""
        self.menu.console.print("\n[bold blue]Configuration Wizard[/bold blue]")
        
        wizard_text = f"""
{EMOJI['info']} Let's set up your {APP_NAME} configuration!

[bold]Step 1:[/bold] Set a target group for categorization
[bold]Step 2:[/bold] Configure command mappings
[bold]Step 3:[/bold] Start monitoring

[dim]You can run this wizard anytime by selecting the appropriate menu options.[/dim]
"""
        
        panel = Panel(
            wizard_text,
            title="Setup Wizard",
            box=box.DOUBLE,
            style="blue"
        )
        self.menu.console.print(panel)
        
        # Ask if user wants to run wizard
        if await self.menu.confirm_action("Would you like to run the setup wizard now?"):
            await self.set_target_group()
            await self.menu.wait_for_keypress("Press Enter to continue to command mapping...")
            await self.manage_command_mappings()
            await self.menu.wait_for_keypress("Press Enter to continue to monitoring setup...")
            
            state = self.state_manager.state
            can_start, _ = state.can_start_monitoring()
            if can_start:
                if await self.menu.confirm_action("Start monitoring now?"):
                    await self.toggle_monitoring()
            else:
                self.menu.display_info(
                    "Monitoring setup incomplete",
                    "You can start monitoring later using Option 7"
                )
