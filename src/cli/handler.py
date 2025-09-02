"""Main CLI handler for SakaiBot."""

import asyncio
import functools
from typing import Dict, Any, List, Optional

from telethon import TelegramClient, events

from ..core.settings import SettingsManager
from ..utils.cache import CacheManager
from ..telegram.utils import TelegramUtils
from ..telegram.handlers import EventHandlers
from ..utils.logging import get_logger
from .state import CLIState
from .interface import CLIInterface


class CLIHandler:
    """Handles the main CLI interface and user interactions."""
    
    def __init__(
        self,
        cache_manager: CacheManager,
        telegram_utils: TelegramUtils,
        settings_manager: SettingsManager,
        event_handlers: EventHandlers
    ) -> None:
        self._cache_manager = cache_manager
        self._telegram_utils = telegram_utils
        self._settings_manager = settings_manager
        self._event_handlers = event_handlers
        self._interface = CLIInterface()
        self._logger = get_logger(self.__class__.__name__)
        
        self._cli_state = CLIState()
    
    @property
    def cli_state(self) -> CLIState:
        """Get the current CLI state."""
        return self._cli_state
    
    async def display_main_menu_loop(self, client: TelegramClient) -> None:
        """Display the main menu and handle user interactions."""
        self._logger.info("CLI Handler started")
        
        # Load user settings
        await self._load_user_settings()
        
        # Pre-fetch topics for forum groups
        await self._prefetch_forum_topics(client)
        
        self._logger.info("Displaying main menu")
        running = True
        
        while running:
            self._interface.display_main_menu(self._cli_state)
            choice = await self._interface.get_user_choice("Enter your choice: ", expect_int=True)
            
            if choice == -1:
                await self._interface.wait_for_continue()
                continue
            
            try:
                if choice == 1:
                    await self._handle_list_cached_pvs(client)
                elif choice == 2:
                    await self._handle_refresh_pvs(client)
                elif choice == 3:
                    await self._handle_search_pvs(client)
                elif choice == 4:
                    await self._handle_set_default_pv_context(client)
                elif choice == 5:
                    await self._handle_set_target_group(client)
                elif choice == 6:
                    await self._handle_manage_command_mappings(client)
                elif choice == 7:
                    await self._handle_toggle_monitoring(client)
                elif choice == 8:
                    await self._handle_manage_authorized_pvs(client)
                elif choice == 0:
                    await self._handle_exit(client)
                    running = False
                else:
                    self._logger.warning(f"Invalid menu choice: {choice}")
                    print("Invalid choice. Please try again.")
            
            except Exception as e:
                self._logger.error(f"Error handling menu choice {choice}: {e}", exc_info=True)
                print(f"An error occurred: {e}")
            
            if choice != 0:
                await self._interface.wait_for_continue()
        
        self._logger.info("CLI Handler finished")
    
    async def _load_user_settings(self) -> None:
        """Load user settings and update CLI state."""
        try:
            loaded_settings = self._settings_manager.load_user_settings()
            self._cli_state.load_from_settings(loaded_settings)
            
            auth_pvs = self._cli_state.directly_authorized_pvs
            self._logger.info(f"Loaded authorized PVs: {[pv.get('id') for pv in auth_pvs]}")
        
        except Exception as e:
            self._logger.error(f"Error loading user settings: {e}", exc_info=True)
            print("Warning: Could not load user settings. Using defaults.")
    
    async def _prefetch_forum_topics(self, client: TelegramClient) -> None:
        """Pre-fetch topics for forum groups."""
        if (self._cli_state.selected_target_group and 
            self._cli_state.selected_target_group.get('is_forum')):
            
            group_title = self._cli_state.selected_target_group.get('title', 'N/A')
            group_id = self._cli_state.selected_target_group['id']
            
            self._logger.info(f"Pre-fetching topics for forum group '{group_title}'")
            
            try:
                topics, _ = await self._telegram_utils.get_group_topics(client, group_id)
                self._cli_state.current_group_topics_cache = topics
                self._logger.info(f"Cached {len(topics)} topics for group '{group_title}'")
            except Exception as e:
                self._logger.error(f"Failed to pre-fetch topics: {e}")
                self._cli_state.current_group_topics_cache = []
        else:
            self._cli_state.current_group_topics_cache = []
    
    async def _handle_list_cached_pvs(self, client: TelegramClient) -> None:
        """Handle listing cached PVs."""
        print("\nFetching your cached PV list...")
        
        try:
            pvs = await self._cache_manager.get_pvs(
                client, self._telegram_utils, force_refresh=False
            )
            
            if not pvs:
                print("Your PV cache is currently empty.")
                print("You might want to use 'Refresh/Update PV List from Telegram' (Option 2) to populate it.")
            else:
                self._interface.display_entity_list(
                    pvs, "All Your Cached Private Chats (PVs)", entity_type="PV", show_numbers=True
                )
        
        except Exception as e:
            self._logger.error(f"Error listing cached PVs: {e}", exc_info=True)
            print("Error fetching PV list. Check logs for details.")
    
    async def _handle_refresh_pvs(self, client: TelegramClient) -> None:
        """Handle refreshing PV list from Telegram."""
        print("\nRefreshing PV list from Telegram (this may take a moment)...")
        
        try:
            refreshed_pvs = await self._cache_manager.get_pvs(
                client, self._telegram_utils, force_refresh=True
            )
            
            print(f"PV list refreshed. Total PVs in cache: {len(refreshed_pvs)}.")
            self._interface.display_entity_list(
                refreshed_pvs, "Updated PV List (Cache)", entity_type="PV", show_numbers=False
            )
        
        except Exception as e:
            self._logger.error(f"Error refreshing PVs: {e}", exc_info=True)
            print("Failed to refresh PV list. Check logs for details.")
    
    async def _handle_search_pvs(self, client: TelegramClient) -> List[Dict[str, Any]]:
        """Handle searching PVs."""
        search_query = await self._interface.get_user_choice(
            "Enter search term (User ID, @Username, or Name): ", expect_int=False
        )
        
        if not search_query:
            print("Search term cannot be empty.")
            return []
        
        print(f"\nSearching your cached PVs for '{search_query}'...")
        
        try:
            all_cached_pvs = await self._cache_manager.get_pvs(
                client, self._telegram_utils, force_refresh=False
            )
            
            if not all_cached_pvs:
                print("PV cache is empty. Try refreshing the PV list first (Option 2).")
                return []
            
            search_results = self._cache_manager.search_pvs(all_cached_pvs, search_query)
            
            if search_results:
                self._interface.display_entity_list(
                    search_results,
                    f"PV Search Results for '{search_query}' (from cache)",
                    entity_type="PV",
                    show_numbers=True
                )
            else:
                print(f"No PVs found in cache matching '{search_query}'.")
            
            return search_results
        
        except Exception as e:
            self._logger.error(f"Error searching PVs: {e}", exc_info=True)
            print("An error occurred during PV search. Check logs for details.")
            return []
    
    async def _handle_set_default_pv_context(self, client: TelegramClient) -> None:
        """Handle setting default PV context."""
        self._interface.print_header("Set Default PV Context (e.g., for /analyze)")
        print("1. List all cached PVs to select from")
        print("2. Search cached PVs (by ID, Username, or Name) to select from")
        print("9. Clear Default PV Context")
        print("0. Back to main menu")
        
        choice = await self._interface.get_user_choice("Choose an option: ", expect_int=True)
        
        if choice == 9:
            self._cli_state.selected_pv_for_categorization = None
            self._logger.info("Default PV context cleared")
            print("Default PV context has been cleared.")
            return
        elif choice == 0:
            return
        
        pvs_to_select_from = []
        if choice == 1:
            await self._handle_list_cached_pvs(client)
            pvs_to_select_from = await self._cache_manager.get_pvs(
                client, self._telegram_utils, force_refresh=False
            )
        elif choice == 2:
            pvs_to_select_from = await self._handle_search_pvs(client)
        else:
            print("Invalid option. Returning to main menu.")
            return
        
        if not pvs_to_select_from:
            print("No PVs available to select from.")
            return
        
        await self._select_pv_from_list(pvs_to_select_from, "default context")
    
    async def _select_pv_from_list(
        self, pvs_list: List[Dict[str, Any]], purpose: str
    ) -> Optional[Dict[str, Any]]:
        """Select a PV from a list."""
        while True:
            pv_number = await self._interface.get_user_choice(
                f"Enter the number of the PV for {purpose} (1-{len(pvs_list)}), or 0 to cancel: ",
                expect_int=True
            )
            
            if pv_number == -1:
                continue
            if pv_number == 0:
                print("Selection cancelled.")
                return None
            
            if 1 <= pv_number <= len(pvs_list):
                selected_pv = pvs_list[pv_number - 1]
                
                if purpose == "default context":
                    self._cli_state.selected_pv_for_categorization = selected_pv
                    self._logger.info(
                        f"Default PV context set to: ID={selected_pv['id']}, "
                        f"Name='{selected_pv['display_name']}'"
                    )
                    print(f"\nSuccessfully set default PV context to: '{selected_pv['display_name']}' (ID: {selected_pv['id']}).")
                
                return selected_pv
            else:
                print(f"Invalid number. Please enter a number between 1 and {len(pvs_list)} or 0.")
    
    async def _handle_set_target_group(self, client: TelegramClient) -> None:
        """Handle setting target group for categorization."""
        self._interface.print_header("Set/Change Categorization Target Group")
        print("Fetching your groups (admins/owners of supergroups), please wait...")
        
        try:
            user_groups = await self._cache_manager.get_groups(
                client, self._telegram_utils, force_refresh=False, require_admin_rights=True
            )
            
            if not user_groups:
                print("No supergroups found where you are an admin/owner.")
                return
            
            self._interface.display_entity_list(
                user_groups, "Your Qualifying Supergroups", entity_type="Group", show_numbers=True
            )
            
            await self._select_target_group(client, user_groups)
        
        except Exception as e:
            self._logger.error(f"Error setting target group: {e}", exc_info=True)
            print("Could not fetch your groups. Please try again later.")
    
    async def _select_target_group(
        self, client: TelegramClient, groups_list: List[Dict[str, Any]]
    ) -> None:
        """Select target group from list."""
        while True:
            group_number = await self._interface.get_user_choice(
                f"Enter the number of the group to select (1-{len(groups_list)}), or 0 to cancel: ",
                expect_int=True
            )
            
            if group_number == -1:
                continue
            if group_number == 0:
                print("Target group selection cancelled.")
                return
            
            if 1 <= group_number <= len(groups_list):
                chosen_group = groups_list[group_number - 1]
                
                print(f"\nVerifying group '{chosen_group['title']}' and fetching topics if it's a forum...")
                
                try:
                    topics, is_forum = await self._telegram_utils.get_group_topics(
                        client, chosen_group['id']
                    )
                    
                    # Check if target group changed
                    if (self._cli_state.selected_target_group and 
                        self._cli_state.selected_target_group['id'] != chosen_group['id']):
                        self._logger.info("Target group changed. Clearing command-topic map and topic cache")
                        self._cli_state.clear_command_mappings()
                    
                    # Update target group info
                    self._cli_state.selected_target_group = {
                        'id': chosen_group['id'],
                        'title': chosen_group['title'],
                        'is_forum': is_forum
                    }
                    
                    self._cli_state.current_group_topics_cache = topics if is_forum else []
                    
                    self._logger.info(
                        f"Target group set: ID={chosen_group['id']}, "
                        f"Title='{chosen_group['title']}', Is Forum: {is_forum}"
                    )
                    
                    print(f"\nSuccessfully set target group: '{chosen_group['title']}'.")
                    
                    if is_forum:
                        print("This group is a forum.")
                        if topics:
                            self._interface.display_topic_list(
                                topics, chosen_group['title'], show_numbers=False
                            )
                        else:
                            print(f"No topics found for forum '{chosen_group['title']}'.")
                    else:
                        print(f"This group is not a forum. Messages will be sent to the main group chat.")
                    
                    print("\nNext, please use 'Manage Command Mappings' (Option 6).")
                    return
                
                except Exception as e:
                    self._logger.error(f"Error verifying group: {e}", exc_info=True)
                    print(f"Error verifying group: {e}")
            else:
                print("Invalid number.")
    
    async def _handle_manage_command_mappings(self, client: TelegramClient) -> None:
        """Handle managing command-topic mappings."""
        if not self._cli_state.selected_target_group:
            print("Please set a target group first (Main Menu - Option 5).")
            return
        
        group_id = self._cli_state.selected_target_group['id']
        group_title = self._cli_state.selected_target_group['title']
        is_forum = self._cli_state.selected_target_group.get('is_forum', False)
        
        self._interface.print_header(f"Manage Mappings for Group: '{group_title}' (Categorization)")
        
        # Ensure we have topics for forum groups
        if is_forum and not self._cli_state.current_group_topics_cache:
            print(f"Fetching topics for forum '{group_title}', please wait...")
            try:
                topics, _ = await self._telegram_utils.get_group_topics(client, group_id)
                self._cli_state.current_group_topics_cache = topics
            except Exception as e:
                self._logger.error(f"Could not fetch topics for group {group_id}: {e}", exc_info=True)
                print(f"Error: Could not fetch topics for group '{group_title}'.")
                self._cli_state.current_group_topics_cache = []
        
        await self._command_mapping_menu_loop(client, group_title, is_forum)
    
    async def _command_mapping_menu_loop(
        self, client: TelegramClient, group_title: str, is_forum: bool
    ) -> None:
        """Handle the command mapping menu loop."""
        while True:
            print("\nCategorization Command Mapping Menu:")
            print("1. View current categorization mappings")
            
            if is_forum:
                print("2. Add new categorization command (select topic from list)")
                print("3. Add new categorization command (manual Topic ID entry)")
            else:
                print("2. Add new categorization command (will send to main group chat)")
            
            print("4. Remove a categorization mapping")
            print("0. Back to main menu")
            
            choice = await self._interface.get_user_choice("Mapping choice: ", expect_int=True)
            
            if choice == -1:
                continue
            elif choice == 0:
                break
            elif choice == 1:
                self._view_current_mappings(is_forum)
            elif choice == 2:
                await self._add_command_mapping(client, group_title, is_forum, manual_topic=False)
            elif choice == 3 and is_forum:
                await self._add_command_mapping(client, group_title, is_forum, manual_topic=True)
            elif choice == 3 and not is_forum:
                print("Option 3 (manual Topic ID) is not applicable for non-forum groups.")
            elif choice == 4:
                self._remove_command_mapping(is_forum)
            else:
                print("Invalid choice. Please try again.")
    
    def _view_current_mappings(self, is_forum: bool) -> None:
        """View current command mappings."""
        self._interface.display_command_mappings(
            self._cli_state.active_command_to_topic_map,
            self._cli_state.current_group_topics_cache,
            is_forum
        )
    
    async def _add_command_mapping(
        self, client: TelegramClient, group_title: str, is_forum: bool, manual_topic: bool
    ) -> None:
        """Add a new command mapping."""
        command_name = await self._interface.get_user_choice(
            "Enter new categorization command name (no '/'): ", expect_int=False
        )
        
        if not command_name:
            print("Invalid command.")
            return
        
        command_name = command_name.strip().lower().replace(" ", "_")
        if not command_name:
            print("Command name empty.")
            return
        
        if is_forum:
            if manual_topic:
                await self._add_manual_topic_mapping(client, command_name, group_title)
            else:
                await self._add_topic_from_list_mapping(command_name, group_title)
        else:
            # Non-forum group
            self._cli_state.active_command_to_topic_map[command_name] = None
            self._logger.info(
                f"Mapped categorization command '/{command_name}' to main chat of group '{group_title}'"
            )
            print(f"Categorization command '/{command_name}' will send to main chat of '{group_title}'.")
    
    async def _add_topic_from_list_mapping(self, command_name: str, group_title: str) -> None:
        """Add mapping by selecting topic from list."""
        if not self._cli_state.current_group_topics_cache:
            print(f"No topics found for '{group_title}'. Add manually.")
            return
        
        displayed = self._interface.display_topic_list(
            self._cli_state.current_group_topics_cache, group_title, show_numbers=True
        )
        
        if not displayed:
            print(f"No topics to select in '{group_title}'.")
            return
        
        topic_number = await self._interface.get_user_choice(
            f"Topic number for '/{command_name}': ", expect_int=True
        )
        
        if topic_number == -1:
            return
        
        if 1 <= topic_number <= len(self._cli_state.current_group_topics_cache):
            selected_topic = self._cli_state.current_group_topics_cache[topic_number - 1]
            self._cli_state.active_command_to_topic_map[command_name] = selected_topic['id']
            
            self._logger.info(
                f"Mapped categorization command '/{command_name}' to Topic ID {selected_topic['id']}"
            )
            print(f"Categorization command '/{command_name}' mapped to '{selected_topic['title']}'.")
        else:
            print("Invalid topic number.")
    
    async def _add_manual_topic_mapping(
        self, client: TelegramClient, command_name: str, group_title: str
    ) -> None:
        """Add mapping by manually entering topic ID."""
        manual_topic_id_str = await self._interface.get_user_choice(
            f"Numeric ID of topic for '/{command_name}': ", expect_int=False
        )
        
        try:
            manual_topic_id = int(manual_topic_id_str)
        except ValueError:
            print("Invalid Topic ID (must be number).")
            return
        
        print(f"Verifying Topic ID {manual_topic_id} in '{group_title}'...")
        
        try:
            topic_info = await self._telegram_utils.get_topic_info_by_id(
                client, self._cli_state.selected_target_group['id'], manual_topic_id
            )
            
            if topic_info:
                print(f"Verified Topic: Title='{topic_info['title']}', ID={topic_info['id']}")
                
                confirm = await self._interface.get_user_choice(
                    f"Map '/{command_name}'? (yes/no): ", expect_int=False
                )
                
                if confirm.lower() == 'yes':
                    self._cli_state.active_command_to_topic_map[command_name] = topic_info['id']
                    
                    self._logger.info(
                        f"Manually mapped categorization command '/{command_name}' to Topic ID {topic_info['id']}"
                    )
                    print(f"Categorization command '/{command_name}' mapped to '{topic_info['title']}'.")
                    
                    # Add to cache if not present
                    if not any(t['id'] == topic_info['id'] for t in self._cli_state.current_group_topics_cache):
                        self._cli_state.current_group_topics_cache.append(topic_info)
                else:
                    print("Mapping cancelled.")
            else:
                print(f"Could not verify Topic ID {manual_topic_id} in '{group_title}'.")
        
        except Exception as e:
            self._logger.error(f"Error verifying topic: {e}", exc_info=True)
            print(f"Error verifying topic: {e}")
    
    async def _remove_command_mapping(self, is_forum: bool) -> None:
        """Remove a command mapping."""
        if not self._cli_state.active_command_to_topic_map:
            print("\nNo categorization mappings to remove.")
            return
        
        self._interface.print_header("Current Categorization Mappings (for removal)")
        
        mappings_list = list(self._cli_state.active_command_to_topic_map.items())
        self._interface.display_command_mappings(
            self._cli_state.active_command_to_topic_map,
            self._cli_state.current_group_topics_cache,
            is_forum,
            show_numbers=True
        )
        
        # Use async method properly
        async def get_removal_choice():
            return await self._interface.get_user_choice(
                f"Number of mapping to remove (1-{len(mappings_list)}), or 0 to cancel: ",
                expect_int=True
            )
        
        # Run the async function
        # Direct async call since this function is already async
        map_number = await get_removal_choice()
        
        if map_number == -1 or map_number == 0:
            print("Removal cancelled.")
            return
        
        if 1 <= map_number <= len(mappings_list):
            command_to_remove, _ = mappings_list[map_number - 1]
            del self._cli_state.active_command_to_topic_map[command_to_remove]
            
            self._logger.info(f"Removed categorization mapping for '/{command_to_remove}'")
            print(f"Categorization mapping for '/{command_to_remove}' removed.")
        else:
            print("Invalid number for removal.")
    
    async def _handle_manage_authorized_pvs(self, client: TelegramClient) -> None:
        """Handle managing authorized PVs."""
        self._interface.print_header("Manage Directly Authorized PVs")
        
        while True:
            print("\nAuthorized PVs Menu:")
            print("1. View authorized PVs")
            print("2. Authorize a new PV (List all cached PVs)")
            print("3. Authorize a new PV (Search cached PVs)")
            print("4. De-authorize a PV")
            print("0. Back to main menu")
            
            choice = await self._interface.get_user_choice("Auth PV choice: ", expect_int=True)
            
            if choice == -1:
                continue
            elif choice == 0:
                break
            elif choice == 1:
                self._view_authorized_pvs()
            elif choice == 2:
                await self._authorize_pv_from_list(client)
            elif choice == 3:
                await self._authorize_pv_from_search(client)
            elif choice == 4:
                await self._deauthorize_pv()
            else:
                print("Invalid choice. Please try again.")
    
    def _view_authorized_pvs(self) -> None:
        """View currently authorized PVs."""
        if not self._cli_state.directly_authorized_pvs:
            print("\nNo PVs are currently authorized for direct commands.")
        else:
            self._interface.display_entity_list(
                self._cli_state.directly_authorized_pvs,
                "Directly Authorized PVs",
                entity_type="PV",
                show_numbers=False
            )
    
    async def _authorize_pv_from_list(self, client: TelegramClient) -> None:
        """Authorize a PV by selecting from the full cached list."""
        print("\nSelect a PV to authorize for direct commands (from cached PVs):")
        await self._handle_list_cached_pvs(client)
        
        try:
            pvs_list = await self._cache_manager.get_pvs(
                client, self._telegram_utils, force_refresh=False
            )
            await self._authorize_pv_from_selection(pvs_list)
        except Exception as e:
            self._logger.error(f"Error authorizing PV from list: {e}", exc_info=True)
            print("Error authorizing PV. Check logs for details.")
    
    async def _authorize_pv_from_search(self, client: TelegramClient) -> None:
        """Authorize a PV by searching the cached list."""
        print("\nSelect a PV to authorize for direct commands (search cached PVs):")
        search_results = await self._handle_search_pvs(client)
        await self._authorize_pv_from_selection(search_results)
    
    async def _authorize_pv_from_selection(self, pvs_list: List[Dict[str, Any]]) -> None:
        """Authorize a PV from a selection list."""
        if not pvs_list:
            print("No PVs available to select from.")
            print("You may need to refresh the PV list first (Main Menu - Option 2).")
            return
        
        pv_number = await self._interface.get_user_choice(
            f"Enter number of PV to authorize (1-{len(pvs_list)}), or 0 to cancel: ",
            expect_int=True
        )
        
        if pv_number == -1 or pv_number == 0:
            print("Authorization cancelled.")
            return
        
        if 1 <= pv_number <= len(pvs_list):
            pv_to_authorize = pvs_list[pv_number - 1]
            
            if self._cli_state.add_authorized_pv(pv_to_authorize):
                self._logger.info(
                    f"Authorized PV for direct commands: {pv_to_authorize['display_name']} "
                    f"(ID: {pv_to_authorize['id']})"
                )
                print(f"PV '{pv_to_authorize['display_name']}' is now authorized for direct commands.")
            else:
                print(f"PV '{pv_to_authorize['display_name']}' is already authorized.")
        else:
            print("Invalid selection.")
    
    async def _deauthorize_pv(self) -> None:
        """De-authorize a PV."""
        if not self._cli_state.directly_authorized_pvs:
            print("\nNo PVs are currently authorized to de-authorize.")
            return
        
        print("\nSelect an authorized PV to de-authorize:")
        self._interface.display_entity_list(
            self._cli_state.directly_authorized_pvs,
            "Currently Authorized PVs",
            entity_type="PV",
            show_numbers=True
        )
        
        pv_number = await self._interface.get_user_choice(
            f"Enter number of PV to de-authorize (1-{len(self._cli_state.directly_authorized_pvs)}), or 0 to cancel: ",
            expect_int=True
        )
        
        if pv_number == -1 or pv_number == 0:
            print("De-authorization cancelled.")
            return
        
        if 1 <= pv_number <= len(self._cli_state.directly_authorized_pvs):
            pv_to_remove = self._cli_state.directly_authorized_pvs[pv_number - 1]
            removed_pv = self._cli_state.remove_authorized_pv(pv_to_remove['id'])
            
            if removed_pv:
                self._logger.info(
                    f"De-authorized PV: {removed_pv['display_name']} (ID: {removed_pv['id']})"
                )
                print(f"PV '{removed_pv['display_name']}' is no longer authorized for direct commands.")
        else:
            print("Invalid selection for de-authorization.")
    
    async def _handle_toggle_monitoring(self, client: TelegramClient) -> None:
        """Handle toggling monitoring on/off."""
        if self._cli_state.is_monitoring_active:
            await self._stop_monitoring(client)
        else:
            await self._start_monitoring(client)
    
    async def _start_monitoring(self, client: TelegramClient) -> None:
        """Start global monitoring."""
        if not self._cli_state.can_start_monitoring:
            print("Cannot start GLOBAL monitoring. Requirements not met:")
            if not self._cli_state.can_categorize:
                print("   - For categorization: Set target group (Opt 5) AND define command mappings (Opt 6).")
            if not self._cli_state.can_use_ai:
                print("   - For AI features: Ensure OpenRouter API key is set in config.")
            return
        
        try:
            # Setup owner handler
            owner_handler = functools.partial(
                self._event_handlers.categorization_reply_handler_owner,
                client=client,
                cli_state_ref=self._cli_state
            )
            owner_filter = events.NewMessage(outgoing=True)
            
            # Setup authorized user handler
            auth_handler = functools.partial(
                self._event_handlers.authorized_user_command_handler,
                client=client,
                cli_state_ref=self._cli_state
            )
            
            auth_pv_ids = [pv['id'] for pv in self._cli_state.directly_authorized_pvs]
            auth_filters = []
            
            if auth_pv_ids:
                auth_filter = events.NewMessage(incoming=True, chats=auth_pv_ids)
                auth_filters.append(auth_filter)
            
            # Register event handlers
            client.add_event_handler(owner_handler, owner_filter)
            self._logger.info("Owner's event handler added for NewMessage(outgoing=True)")
            
            if auth_filters:
                for auth_filter in auth_filters:
                    client.add_event_handler(auth_handler, auth_filter)
                    self._logger.info(
                        f"Authorized user event handler added for NewMessage(incoming=True, chats={auth_filter.chats})"
                    )
            
            # Update state
            self._cli_state.registered_handler_info = (
                owner_handler, owner_filter, auth_handler, auth_filters
            )
            self._cli_state.is_monitoring_active = True
            
            self._logger.info("GLOBAL monitoring started")
            print("GLOBAL monitoring started.")
            print("SakaiBot will now process your commands and commands from authorized PVs.")
        
        except Exception as e:
            self._logger.error(f"Error starting monitoring: {e}", exc_info=True)
            print("Error starting GLOBAL monitoring. Check logs.")
    
    async def _stop_monitoring(self, client: TelegramClient) -> None:
        """Stop global monitoring."""
        if not self._cli_state.registered_handler_info:
            self._logger.warning("Attempted to stop monitoring, but no handler info was stored")
            self._cli_state.is_monitoring_active = False
            return
        
        try:
            owner_handler, owner_filter, auth_handler, auth_filters = self._cli_state.registered_handler_info
            
            # Remove handlers
            if owner_handler and owner_filter:
                client.remove_event_handler(owner_handler, owner_filter)
                self._logger.info("Owner's event handler removed")
            
            if auth_handler and auth_filters:
                for auth_filter in auth_filters:
                    client.remove_event_handler(auth_handler, auth_filter)
                self._logger.info("Authorized users' event handlers removed")
            
            # Update state
            self._cli_state.is_monitoring_active = False
            self._cli_state.registered_handler_info = None
            
            print("GLOBAL monitoring (for categorization & AI) stopped.")
            self._logger.info("GLOBAL monitoring stopped")
        
        except Exception as e:
            self._logger.error(f"Error stopping monitoring: {e}", exc_info=True)
            print("Error stopping monitoring. Check logs.")
    
    async def _handle_exit(self, client: TelegramClient) -> None:
        """Handle CLI exit with cleanup."""
        self._logger.info("Exiting SakaiBot CLI (Option 0). Performing cleanup...")
        
        # Save settings
        try:
            settings_to_save = self._cli_state.to_settings_dict()
            self._settings_manager.save_user_settings(settings_to_save)
            self._cli_state.settings_saved_on_cli_exit = True
            print("Settings saved.")
        except Exception as e:
            self._logger.error(f"Error saving settings on exit: {e}", exc_info=True)
            print(f"Warning: Could not save settings: {e}")
        
        # Stop monitoring if active
        if self._cli_state.is_monitoring_active:
            try:
                await self._stop_monitoring(client)
                print("Monitoring stopped.")
            except Exception as e:
                self._logger.error(f"Could not stop monitoring on exit: {e}")
        
        print("Exiting SakaiBot CLI...")
