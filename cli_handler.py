# -*- coding: utf-8 -*-
# English comments as per our rules

import asyncio
import logging
import functools 

import settings_manager
from telethon import events 
# event_handlers module will be passed as an argument

logger = logging.getLogger(__name__)

selected_pv_for_categorization = None
selected_target_group = None 
active_command_to_topic_map = {} 
directly_authorized_pvs = [] 
current_group_topics_cache = [] 
is_monitoring_active = False
registered_handler_info = None 
OPENROUTER_API_KEY_CLI = None 
OPENROUTER_MODEL_NAME_CLI = "deepseek/chat"
MAX_ANALYZE_MESSAGES_CLI = 5000


async def async_input(prompt: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, input, prompt)

async def _get_user_choice_async(prompt="Enter your choice: ", expect_int=True):
    while True:
        try:
            choice_str = await async_input(prompt)
            if not choice_str.strip() and expect_int: # Handle empty input for int prompts
                # logger.warning("Input cannot be empty for a numeric choice.") # Already handled by print
                print("Input cannot be empty. Please enter a number.")
                continue
            if expect_int:
                return int(choice_str)
            return choice_str.strip() # Strip whitespace for string inputs
        except ValueError:
            if expect_int:
                logger.warning(f"Invalid input '{choice_str}'. Please enter a number.")
                print(f"Invalid input '{choice_str}'. Please enter a number.")
            # No specific error print for string if expect_int is False, as any string is valid.
            # The caller should handle empty strings if not desired.
        except Exception as e:
            logger.error(f"Error getting user input: {e}", exc_info=True)
            if expect_int: return -1 
            return "" # Return empty string on error for non-int expected input


def _display_main_menu():
    # ... (same as v23/v22) ...
    global selected_pv_for_categorization, selected_target_group, is_monitoring_active, directly_authorized_pvs
    print("\nSakaiBot Menu:")
    print("=" * 30)
    print("1. List all my Private Chats (PVs)")
    print("2. Search PVs (by ID, Username, or Name)") # Updated menu text
    pv_display_name = selected_pv_for_categorization['display_name'] if selected_pv_for_categorization and 'display_name' in selected_pv_for_categorization else "None (Uses current chat for /analyze)"
    pv_status = f"(Default Context PV: '{pv_display_name}')"
    group_status_text = "(No group selected for categorization)"
    if selected_target_group:
        group_type = "Forum Group" if selected_target_group.get('is_forum') else "Regular Group"
        group_status_text = f"(Categorization Target: '{selected_target_group.get('title', 'N/A')}' - {group_type})"
    print(f"3. Set Default PV Context (for /analyze) {pv_status}")
    print(f"4. Set/Change Categorization Target Group {group_status_text}")
    print("5. Manage Categorization Command Mappings") 
    print(f"7. Manage Directly Authorized PVs ({len(directly_authorized_pvs)} authorized)")
    print("-" * 30)
    print("--- Monitoring (Applies to All Chats You Use & Authorized PVs) ---") 
    monitoring_status = "Stop GLOBAL Monitoring" if is_monitoring_active else "Start GLOBAL Monitoring"
    print(f"6. {monitoring_status} (for categorization & AI commands)") 
    print("   (Bot listens to your outgoing commands AND commands from authorized PVs)")
    print("=" * 30)
    print("0. Exit (Save Settings)")


def _print_header(title: str):
    print(f"\n{'=' * 5} {title} {'=' * (40 - len(title) if len(title) < 40 else 0)}")
def _print_footer():
    print(f"{'=' * 47}")

def _display_entity_list(entity_list: list, title: str, entity_type: str = "PV", show_numbers: bool = True): 
    if not entity_list:
        print(f"\nNo {entity_type}(s) to display.")
        return False 
    _print_header(title)
    idx_width = 5 if show_numbers else 2 
    name_width = 30
    username_width = 25
    id_width = 15
    header_format_pv = "{:<{idx}} {:<{name}} {:<{uname}} {:<{id}}"
    header_format_group = "{:<{idx}} {:<{name}} {:<{type_}} {:<{id}}" 
    if entity_type == "PV":
        print(header_format_pv.format("No." if show_numbers else "", "Display Name", "Username", "User ID",idx=idx_width, name=name_width, uname=username_width, id=id_width))
    elif entity_type == "Group":
        print(header_format_group.format("No." if show_numbers else "", "Group Title", "Type", "Group ID",idx=idx_width, name=name_width, type_=username_width, id=id_width))
    print("-" * (idx_width + name_width + username_width + id_width + 3))
    for index, item in enumerate(entity_list):
        prefix = f"{index + 1}." if show_numbers else "-"
        item_id = item['id']
        if entity_type == "PV":
            display_name = item.get('display_name', 'N/A')
            username = item.get('username', "N/A") # Already handles None
            print(header_format_pv.format(
                prefix, 
                display_name[:name_width-1], 
                username[:username_width-1] if username else "N/A", # Ensure N/A if None
                str(item_id)[:id_width-1], 
                idx=idx_width, name=name_width, uname=username_width, id=id_width
            ))
        elif entity_type == "Group":
            title_name = item.get('title', 'N/A')
            is_forum_str = "Forum" if item.get('is_forum') else "Regular"
            print(header_format_group.format(
                prefix, 
                title_name[:name_width-1], 
                is_forum_str, 
                str(item_id)[:id_width-1],
                idx=idx_width, name=name_width, type_=username_width, id=id_width
            ))
    _print_footer()
    return True


async def _handle_list_all_pvs(client, cache_manager, telegram_utils_module, show_numbers=True):
    print("\nFetching your PV list, please wait...")
    pvs = []
    try:
        pvs = await cache_manager.get_pvs(client, telegram_utils_module, force_refresh=False)
        _display_entity_list(pvs, "All Your Private Chats (PVs)", entity_type="PV", show_numbers=show_numbers)
    except Exception as e:
        logger.error(f"Error handling 'List all PVs': {e}", exc_info=True)
        print("An error occurred while fetching PVs. Check logs for details.")
    return pvs

def _perform_pv_search(pvs_list: list, query: str) -> list:
    """
    Performs a case-insensitive search on the provided list of PVs
    by User ID, Username (with or without @), or Display Name.
    """
    if not query:
        logger.debug("Search query is empty in _perform_pv_search.")
        return []
    
    results = []
    query_lower = query.lower()
    
    # Try to interpret query as User ID first
    query_as_int = None
    try:
        query_as_int = int(query)
    except ValueError:
        pass # Not an integer, proceed with string search

    for pv in pvs_list:
        # 1. Search by User ID
        if query_as_int is not None and pv['id'] == query_as_int:
            results.append(pv)
            continue # Found by ID, no need for further checks on this pv

        # 2. Search by Username (case-insensitive, with or without @)
        pv_username_lower = None
        if pv['username']:
            pv_username_lower = pv['username'].lower()
            # Remove leading @ from query if present for username comparison
            search_username_query = query_lower[1:] if query_lower.startswith('@') else query_lower
            if search_username_query in pv_username_lower:
                results.append(pv)
                continue # Found by username

        # 3. Search by Display Name (case-insensitive)
        if query_lower in pv['display_name'].lower():
            results.append(pv)
            continue # Found by display name
            
    return results

async def _handle_search_pvs(client, cache_manager, telegram_utils_module, show_numbers=True): 
    search_query = await _get_user_choice_async(prompt="Enter search term (User ID, @Username, or Name): ", expect_int=False)
    search_results = []
    if not search_query: # Handles empty string from _get_user_choice_async
        print("Search term cannot be empty.")
        return search_results
    
    print(f"\nSearching PVs for '{search_query}', please wait...")
    try:
        all_pvs = await cache_manager.get_pvs(client, telegram_utils_module, force_refresh=False)
        if not all_pvs:
            print("Could not retrieve PV list to search. Try listing all PVs first or check logs.")
            return search_results
            
        search_results = _perform_pv_search(all_pvs, search_query) # Uses the enhanced search
        
        if search_results:
            _display_entity_list(search_results, f"PV Search Results for '{search_query}'", entity_type="PV", show_numbers=show_numbers)
        else:
            print(f"No PVs found matching '{search_query}'.")
            
    except Exception as e:
        logger.error(f"Error handling 'Search PVs': {e}", exc_info=True)
        print("An error occurred during PV search. Check logs for details.")
    return search_results

async def _handle_set_default_pv_context(client, cache_manager, telegram_utils_module): 
    global selected_pv_for_categorization 
    _print_header("Set Default PV Context (e.g., for /analyze)")
    print("1. List all PVs to select from")
    print("2. Search PVs (by ID, Username, or Name) to select from") # Updated prompt
    print("9. Clear Default PV Context")
    print("0. Back to main menu")
    choice_input = await _get_user_choice_async(prompt="Choose an option: ", expect_int=True)
    if choice_input == -1: return
    if choice_input == 9:
        selected_pv_for_categorization = None
        logger.info("Default PV context cleared.")
        print("Default PV context has been cleared.")
        return
    pvs_to_select_from = []
    if choice_input == 1:
        pvs_to_select_from = await _handle_list_all_pvs(client, cache_manager, telegram_utils_module, show_numbers=True) 
    elif choice_input == 2:
        pvs_to_select_from = await _handle_search_pvs(client, cache_manager, telegram_utils_module, show_numbers=True) 
    elif choice_input == 0: return
    else:
        print("Invalid option. Returning to main menu.")
        return
    if not pvs_to_select_from:
        print("No PVs available to select from based on your previous action.")
        return
    while True:
        pv_number = await _get_user_choice_async(
            prompt=f"Enter the number of the PV for default context (1-{len(pvs_to_select_from)}), or 0 to cancel: ",
            expect_int=True)
        if pv_number == -1: continue
        if pv_number == 0:
            print("Selection cancelled.")
            return
        if 1 <= pv_number <= len(pvs_to_select_from):
            selected_pv = pvs_to_select_from[pv_number - 1]
            selected_pv_for_categorization = selected_pv 
            logger.info(f"Default PV Context set to: ID={selected_pv['id']}, Name='{selected_pv['display_name']}'")
            print(f"\nSuccessfully set Default PV Context to: '{selected_pv['display_name']}' (ID: {selected_pv['id']}).")
            return
        else:
            print(f"Invalid number. Please enter a number between 1 and {len(pvs_to_select_from)} or 0.")


async def _handle_set_target_group(client, cache_manager, telegram_utils_module):
    # ... (same as v22/v19) ...
    global selected_target_group, active_command_to_topic_map, current_group_topics_cache
    _print_header("Set/Change Categorization Target Group")
    print("Fetching your groups (admins/owners of supergroups), please wait...")
    try:
        user_groups = await cache_manager.get_groups(client, telegram_utils_module, 
                                                     force_refresh=False, require_admin_rights=True)
    except Exception as e:
        logger.error(f"Failed to fetch user groups: {e}", exc_info=True)
        print("Could not fetch your groups. Please try again later.")
        return

    if not user_groups:
        print("No supergroups found where you are an admin/owner, or no supergroups were found.")
        return

    _display_entity_list(user_groups, "Your Qualifying Supergroups", entity_type="Group", show_numbers=True)

    while True:
        group_number = await _get_user_choice_async(
            prompt=f"Enter the number of the group to select (1-{len(user_groups)}), or 0 to cancel: ",
            expect_int=True)
        if group_number == -1: continue
        if group_number == 0:
            print("Target group selection cancelled.")
            return
        if 1 <= group_number <= len(user_groups):
            chosen_group_from_list = user_groups[group_number - 1]
            print(f"\nVerifying group '{chosen_group_from_list['title']}' and fetching topics if it's a forum, please wait...")
            actual_topics, is_actually_forum = await telegram_utils_module.get_group_topics(client, chosen_group_from_list['id'])
            updated_target_group_info = {
                'id': chosen_group_from_list['id'],
                'title': chosen_group_from_list['title'],
                'is_forum': is_actually_forum 
            }
            if selected_target_group and selected_target_group['id'] != updated_target_group_info['id']:
                logger.info(f"Target group changed. Clearing command-topic map and topic cache.")
                active_command_to_topic_map = {} 
            selected_target_group = updated_target_group_info 
            current_group_topics_cache = actual_topics if is_actually_forum else [] 
            logger.info(f"Target group set: ID={selected_target_group['id']}, Title='{selected_target_group['title']}', Is Forum: {selected_target_group['is_forum']}")
            print(f"\nSuccessfully set target group: '{selected_target_group['title']}'.")
            if selected_target_group['is_forum']:
                print(f"This group is a forum.")
                if current_group_topics_cache:
                    _display_topic_list(current_group_topics_cache, selected_target_group['title'], show_numbers=False)
                else:
                    print(f"No topics were found/listed for forum '{selected_target_group['title']}'. You might need to add them manually via Option 5 if they exist.")
            else:
                print(f"This group ('{selected_target_group['title']}') is not a forum. Messages will be sent to the main group chat.")
            print("\nNext, please use 'Manage Command Mappings' (Option 5).")
            return
        else:
            print(f"Invalid number.")

async def _handle_manage_command_topic_mappings(client, telegram_utils_module):
    # ... (same as v22/v19) ...
    global selected_target_group, active_command_to_topic_map, current_group_topics_cache
    if not selected_target_group:
        print("Please set a target group first (Main Menu - Option 4).")
        return
    group_id = selected_target_group['id']
    group_title = selected_target_group['title']
    is_forum_group = selected_target_group.get('is_forum', False)
    _print_header(f"Manage Mappings for Group: '{group_title}' (Categorization)")
    if is_forum_group and not current_group_topics_cache: 
        print(f"Fetching/Re-fetching topics for forum '{group_title}', please wait...")
        try:
            topics, _ = await telegram_utils_module.get_group_topics(client, group_id)
            current_group_topics_cache = topics
        except Exception as e:
            logger.error(f"Could not fetch topics for group {group_id}: {e}", exc_info=True)
            print(f"Error: Could not fetch topics for group '{group_title}'.")
            current_group_topics_cache = [] 
    if current_group_topics_cache is None: current_group_topics_cache = []
    while True:
        print("\nCategorization Command Mapping Menu:")
        print("1. View current categorization mappings")
        if is_forum_group:
            print("2. Add new categorization command (select topic from list)")
            print("3. Add new categorization command (manual Topic ID entry)")
        else: 
            print("2. Add new categorization command (will send to main group chat)")
        print("4. Remove a categorization mapping")
        print("0. Back to main menu")
        choice = await _get_user_choice_async(prompt="Mapping choice: ", expect_int=True)
        if choice == -1: continue
        if choice == 1: 
            if not active_command_to_topic_map:
                print("\nNo categorization command mappings currently defined.")
            else:
                _print_header("Current Categorization Command Mappings")
                cmd_width = 20; target_width = 45
                print(f"{'Command':<{cmd_width}} {'Target':<{target_width}}")
                print(f"{'-'*cmd_width} {'-'*target_width}")
                for command, topic_id_map in active_command_to_topic_map.items():
                    target_description = ""
                    if topic_id_map is None: target_description = "Main Group Chat"
                    elif is_forum_group:
                        topic_title = next((t['title'] for t in current_group_topics_cache if t['id'] == topic_id_map), 
                                           f"Manually Added/Unknown Topic (ID: {topic_id_map})")
                        target_description = f"Topic: '{topic_title}' (ID: {topic_id_map})"
                    else: target_description = f"Target ID: {topic_id_map} (Error: Non-forum group with topic ID)"
                    print(f"/{command:<{cmd_width-1}} {target_description:<{target_width}}")
                _print_footer()
        elif choice == 2: 
            command_name = await _get_user_choice_async(prompt="Enter new categorization command name (no '/'): ", expect_int=False)
            if not command_name or command_name == "": print("Invalid command."); continue
            command_name = command_name.strip().lower().replace(" ", "_")
            if not command_name: print("Command name empty."); continue
            if is_forum_group:
                if not current_group_topics_cache: print(f"No topics found for '{group_title}'. Add manually."); continue
                displayed_any_topic = _display_topic_list(current_group_topics_cache, group_title, show_numbers=True)
                if not displayed_any_topic: print(f"Still no topics to select in '{group_title}'."); continue
                topic_number = await _get_user_choice_async(prompt=f"Topic number for '/{command_name}': ", expect_int=True)
                if topic_number == -1: continue
                if 0 < topic_number <= len(current_group_topics_cache):
                    selected_topic_from_list = current_group_topics_cache[topic_number - 1]
                    active_command_to_topic_map[command_name] = selected_topic_from_list['id']
                    logger.info(f"Mapped categorization command '/{command_name}' to Topic ID {selected_topic_from_list['id']} ...")
                    print(f"Categorization command '/{command_name}' mapped to '{selected_topic_from_list['title']}'.")
                else: print(f"Invalid topic number.")
            else: 
                active_command_to_topic_map[command_name] = None 
                logger.info(f"Mapped categorization command '/{command_name}' to Main Chat of group '{group_title}'.")
                print(f"Categorization command '/{command_name}' will send to main chat of '{group_title}'.")
        elif choice == 3 and is_forum_group: 
            command_name_manual = await _get_user_choice_async(prompt="Enter new categorization command name (no '/'): ", expect_int=False)
            if not command_name_manual or command_name_manual == "": print("Invalid command."); continue
            command_name_manual = command_name_manual.strip().lower().replace(" ", "_")
            if not command_name_manual: print("Command name empty."); continue
            manual_topic_id_str = await _get_user_choice_async(prompt=f"Numeric ID of topic for '/{command_name_manual}': ", expect_int=False)
            try: manual_topic_id = int(manual_topic_id_str)
            except ValueError: print("Invalid Topic ID (must be number)."); continue
            print(f"Verifying Topic ID {manual_topic_id} in '{group_title}'...")
            topic_info = await telegram_utils_module.get_topic_info_by_id(client, group_id, manual_topic_id)
            if topic_info:
                print(f"Verified Topic: Title='{topic_info['title']}', ID={topic_info['id']}")
                confirm_map_input = await _get_user_choice_async(prompt=f"Map '/{command_name_manual}'? (yes/no): ", expect_int=False)
                if confirm_map_input.lower() == 'yes':
                    active_command_to_topic_map[command_name_manual] = topic_info['id']
                    logger.info(f"Manually mapped categorization command '/{command_name_manual}' to Topic ID {topic_info['id']} ...")
                    print(f"Categorization command '/{command_name_manual}' mapped to '{topic_info['title']}'.")
                    if not any(t['id'] == topic_info['id'] for t in current_group_topics_cache):
                        current_group_topics_cache.append(topic_info)
                else: print("Mapping cancelled.")
            else: print(f"Could not verify Topic ID {manual_topic_id} in '{group_title}'.")
        elif choice == 3 and not is_forum_group:
             print("Option 3 (manual Topic ID) is not applicable for non-forum groups.")
        elif choice == 4: 
            if not active_command_to_topic_map: print("\nNo categorization mappings to remove."); continue
            _print_header("Current Categorization Mappings (for removal)")
            mappings_list = list(active_command_to_topic_map.items()) 
            cmd_width = 20; target_width = 45
            print(f"{'#':<4} {'Command':<{cmd_width}} {'Target':<{target_width}}")
            print(f"{'-'*4} {'-'*cmd_width} {'-'*target_width}")
            for index, (command, topic_id_map) in enumerate(mappings_list):
                target_description = ""
                if topic_id_map is None: target_description = "Main Group Chat"
                elif is_forum_group:
                    topic_title = next((t['title'] for t in current_group_topics_cache if t['id'] == topic_id_map), 
                                       f"Manually Added/Unknown Topic (ID: {topic_id_map})")
                    target_description = f"Topic: '{topic_title}' (ID: {topic_id_map})"
                else: target_description = f"Target ID: {topic_id_map} (Non-forum group with topic ID)"
                print(f"{index + 1:<{4}} /{command:<{cmd_width-1}} {target_description:<{target_width}}")
            _print_footer()
            map_number_to_remove = await _get_user_choice_async(prompt=f"Number of mapping to remove (1-{len(mappings_list)}), or 0 to cancel: ", expect_int=True)
            if map_number_to_remove == -1: continue 
            if map_number_to_remove == 0: print("Removal cancelled."); continue
            if 1 <= map_number_to_remove <= len(mappings_list):
                command_to_remove, _ = mappings_list[map_number_to_remove - 1]
                del active_command_to_topic_map[command_to_remove]
                logger.info(f"Removed categorization mapping for '/{command_to_remove}'.")
                print(f"Categorization mapping for '/{command_to_remove}' removed.")
            else: print("Invalid number for removal.")
        elif choice == 0: break
        else: print("Invalid choice for mapping.")

async def _handle_manage_authorized_pvs(client, cache_manager, telegram_utils_module):
    global directly_authorized_pvs
    _print_header("Manage Directly Authorized PVs")
    while True:
        print("\nAuthorized PVs Menu:")
        print("1. View authorized PVs")
        print("2. Authorize a new PV (List all)")
        print("3. Authorize a new PV (Search by ID, Username, or Name)") # New Search option
        print("4. De-authorize a PV")
        print("0. Back to main menu")

        choice = await _get_user_choice_async(prompt="Auth PV choice: ", expect_int=True)
        if choice == -1: continue

        if choice == 1: 
            if not directly_authorized_pvs:
                print("\nNo PVs are currently authorized for direct commands.")
            else:
                _display_entity_list(directly_authorized_pvs, "Directly Authorized PVs", entity_type="PV", show_numbers=False) 
        
        elif choice == 2 or choice == 3: # Authorize new PV (List or Search)
            print("\nSelect a PV to authorize for direct commands:")
            pvs_to_select_from = []
            if choice == 2: # List all
                 pvs_to_select_from = await _handle_list_all_pvs(client, cache_manager, telegram_utils_module, show_numbers=True)
            elif choice == 3: # Search
                 pvs_to_select_from = await _handle_search_pvs(client, cache_manager, telegram_utils_module, show_numbers=True)
            
            if not pvs_to_select_from:
                print("No PVs available to select from based on your previous action.")
                continue
            
            pv_number = await _get_user_choice_async(
                prompt=f"Enter number of PV to authorize (1-{len(pvs_to_select_from)}), or 0 to cancel: ",
                expect_int=True
            )
            if pv_number == -1: continue
            if pv_number == 0: print("Authorization cancelled."); continue

            if 1 <= pv_number <= len(pvs_to_select_from):
                pv_to_authorize = pvs_to_select_from[pv_number - 1]
                if not any(auth_pv['id'] == pv_to_authorize['id'] for auth_pv in directly_authorized_pvs):
                    auth_info = { 
                        'id': pv_to_authorize['id'],
                        'display_name': pv_to_authorize['display_name'],
                        'username': pv_to_authorize['username']
                    }
                    directly_authorized_pvs.append(auth_info)
                    logger.info(f"Authorized PV for direct commands: {auth_info['display_name']} (ID: {auth_info['id']})")
                    print(f"PV '{auth_info['display_name']}' is now authorized for direct commands.")
                else:
                    print(f"PV '{pv_to_authorize['display_name']}' is already authorized.")
            else:
                print("Invalid selection.")

        elif choice == 4: # De-authorize PV (was choice 3 before)
            if not directly_authorized_pvs:
                print("\nNo PVs are currently authorized to de-authorize.")
                continue
            
            print("\nSelect an authorized PV to de-authorize:")
            _display_entity_list(directly_authorized_pvs, "Currently Authorized PVs", entity_type="PV", show_numbers=True) 
            
            pv_number_to_deauth = await _get_user_choice_async(
                prompt=f"Enter number of PV to de-authorize (1-{len(directly_authorized_pvs)}), or 0 to cancel: ",
                expect_int=True
            )
            if pv_number_to_deauth == -1: continue
            if pv_number_to_deauth == 0: print("De-authorization cancelled."); continue

            if 1 <= pv_number_to_deauth <= len(directly_authorized_pvs):
                deauthorized_pv = directly_authorized_pvs.pop(pv_number_to_deauth - 1)
                logger.info(f"De-authorized PV: {deauthorized_pv['display_name']} (ID: {deauthorized_pv['id']})")
                print(f"PV '{deauthorized_pv['display_name']}' is no longer authorized for direct commands.")
            else:
                print("Invalid selection for de-authorization.")
        
        elif choice == 0: 
            break
        else:
            print("Invalid choice. Please try again.")


async def _toggle_monitoring(client, event_handlers_module):
    # ... (same as v22) ...
    global is_monitoring_active, registered_handler_info, \
           selected_pv_for_categorization, selected_target_group, active_command_to_topic_map, \
           OPENROUTER_API_KEY_CLI, OPENROUTER_MODEL_NAME_CLI, MAX_ANALYZE_MESSAGES_CLI, \
           directly_authorized_pvs

    if is_monitoring_active:
        if registered_handler_info:
            owner_handler_func, owner_event_filter, authorized_handler_func, authorized_event_filter_list = registered_handler_info
            try:
                if owner_handler_func and owner_event_filter:
                    client.remove_event_handler(owner_handler_func, owner_event_filter)
                    logger.info("SakaiBot CLI: Owner's event handler REMOVED.")
                if authorized_handler_func and authorized_event_filter_list:
                    for auth_filter in authorized_event_filter_list: 
                        client.remove_event_handler(authorized_handler_func, auth_filter)
                    logger.info("SakaiBot CLI: Authorized users' event handlers REMOVED.")
                print("GLOBAL Monitoring (for categorization & AI) stopped.")
                is_monitoring_active = False
                registered_handler_info = None
            except Exception as e:
                logger.error(f"Error removing event handlers: {e}", exc_info=True)
                print("Error stopping monitoring. Check logs.")
        else:
            logger.warning("Attempted to stop monitoring, but no handler info was stored.")
            is_monitoring_active = False 
    else:
        can_categorize = selected_target_group and active_command_to_topic_map
        can_ai = OPENROUTER_API_KEY_CLI and OPENROUTER_API_KEY_CLI != "YOUR_OPENROUTER_API_KEY_HERE"
        if not (can_categorize or can_ai): 
            print("Cannot start GLOBAL monitoring. Requirements not met:")
            if not selected_target_group or not active_command_to_topic_map : 
                 print("  - For categorization: Set target group (Opt 4) AND define command mappings (Opt 5).")
            if not can_ai: print("  - For AI features: Ensure OpenRouter API key is set in config.ini.")
            return
        current_default_context_pv_id = selected_pv_for_categorization['id'] if selected_pv_for_categorization else None
        owner_bound_handler = functools.partial(
            event_handlers_module.categorization_reply_handler_owner, 
            client=client, default_context_pv_id=current_default_context_pv_id, 
            categorization_group_id=selected_target_group['id'] if selected_target_group else None,
            command_topic_map=active_command_to_topic_map.copy() if active_command_to_topic_map else {},
            openrouter_api_key=OPENROUTER_API_KEY_CLI, openrouter_model_name=OPENROUTER_MODEL_NAME_CLI,
            max_analyze_messages_limit=MAX_ANALYZE_MESSAGES_CLI
        )
        owner_event_filter = events.NewMessage(outgoing=True) 
        authorized_user_bound_handler = functools.partial(
            event_handlers_module.authorized_user_command_handler, 
            client=client,
            categorization_group_id=selected_target_group['id'] if selected_target_group else None,
            command_topic_map=active_command_to_topic_map.copy() if active_command_to_topic_map else {},
            openrouter_api_key=OPENROUTER_API_KEY_CLI, openrouter_model_name=OPENROUTER_MODEL_NAME_CLI,
            max_analyze_messages_limit=MAX_ANALYZE_MESSAGES_CLI
        )
        authorized_pv_ids = [pv['id'] for pv in directly_authorized_pvs if pv and 'id' in pv]
        final_authorized_event_filters = [] 
        if authorized_pv_ids:
            auth_filter = events.NewMessage(incoming=True, chats=authorized_pv_ids)
            final_authorized_event_filters.append(auth_filter)
        try:
            client.add_event_handler(owner_bound_handler, owner_event_filter)
            logger.info(f"SakaiBot CLI: Owner's Event handler ADDED for NewMessage(outgoing=True).")
            if final_authorized_event_filters:
                for auth_filter in final_authorized_event_filters:
                    client.add_event_handler(authorized_user_bound_handler, auth_filter)
                    logger.info(f"SakaiBot CLI: Authorized User Event handler ADDED for NewMessage(incoming=True, chats={auth_filter.chats}).")
            registered_handler_info = (owner_bound_handler, owner_event_filter, authorized_user_bound_handler, final_authorized_event_filters) 
            is_monitoring_active = True
            logger.info(f"GLOBAL Monitoring started.")
            print(f"GLOBAL Monitoring started.")
            print("SakaiBot will now process your commands and commands from authorized PVs.")
        except Exception as e:
            logger.error(f"Error adding event handlers: {e}", exc_info=True)
            print("Error starting GLOBAL monitoring. Check logs.")


async def display_main_menu_loop(
    client, cache_manager, telegram_utils_module, 
    settings_manager_module, event_handlers_module,
    openrouter_api_key_main: str, openrouter_model_name_main: str,
    max_analyze_messages_main: int 
):
    # ... (same as v22) ...
    logger.info("CLI Handler started.")
    global selected_pv_for_categorization, selected_target_group, active_command_to_topic_map, \
           current_group_topics_cache, is_monitoring_active, registered_handler_info, \
           OPENROUTER_API_KEY_CLI, OPENROUTER_MODEL_NAME_CLI, MAX_ANALYZE_MESSAGES_CLI, \
           directly_authorized_pvs
    
    OPENROUTER_API_KEY_CLI = openrouter_api_key_main
    OPENROUTER_MODEL_NAME_CLI = openrouter_model_name_main
    MAX_ANALYZE_MESSAGES_CLI = max_analyze_messages_main 

    loaded_settings = settings_manager_module.load_user_settings()
    selected_pv_for_categorization = loaded_settings.get("selected_pv_for_categorization")
    selected_target_group = loaded_settings.get("selected_target_group") 
    active_command_to_topic_map = loaded_settings.get("active_command_to_topic_map", {})
    directly_authorized_pvs = loaded_settings.get("directly_authorized_pvs", []) 
    logger.info(f"CLI: Loaded directly_authorized_pvs: {[pv.get('id') for pv in directly_authorized_pvs]}") 

    if selected_target_group and selected_target_group.get('is_forum'): 
        logger.info(f"Loaded target forum group '{selected_target_group.get('title', 'N/A')}'. Fetching its topics for session cache...")
        try:
            topics, _ = await telegram_utils_module.get_group_topics(client, selected_target_group['id'])
            current_group_topics_cache = topics
            logger.info(f"Cached {len(current_group_topics_cache)} topics for group '{selected_target_group.get('title', 'N/A')}'.")
        except Exception as e:
            logger.error(f"Failed to pre-fetch topics for loaded group: {e}")
            current_group_topics_cache = []
    else:
        current_group_topics_cache = []

    logger.info("Displaying main menu.")
    running = True
    while running:
        _display_main_menu()
        
        choice = await _get_user_choice_async(prompt="Enter your choice: ", expect_int=True)
        
        if choice == -1: 
            await async_input("\nPress Enter to continue...")
            continue

        if choice == 1: await _handle_list_all_pvs(client, cache_manager, telegram_utils_module)
        elif choice == 2: await _handle_search_pvs(client, cache_manager, telegram_utils_module)
        elif choice == 3: await _handle_set_default_pv_context(client, cache_manager, telegram_utils_module) 
        elif choice == 4: await _handle_set_target_group(client, cache_manager, telegram_utils_module)
        elif choice == 5: await _handle_manage_command_topic_mappings(client, telegram_utils_module)
        elif choice == 7: await _handle_manage_authorized_pvs(client, cache_manager, telegram_utils_module) # Call the new handler
        elif choice == 6: await _toggle_monitoring(client, event_handlers_module) 
        elif choice == 0:
            logger.info("Exiting SakaiBot CLI. Saving settings...")
            settings_to_save = {
                "selected_pv_for_categorization": selected_pv_for_categorization, 
                "selected_target_group": selected_target_group, 
                "active_command_to_topic_map": active_command_to_topic_map,
                "directly_authorized_pvs": directly_authorized_pvs 
            }
            settings_manager_module.save_user_settings(settings_to_save)
            print("Settings saved. Exiting SakaiBot...")
            if is_monitoring_active and registered_handler_info:
                owner_handler_func, owner_event_filter, authorized_handler_func, authorized_event_filter_list = registered_handler_info
                try:
                    if owner_handler_func and owner_event_filter:
                        client.remove_event_handler(owner_handler_func, owner_event_filter) 
                    if authorized_handler_func and authorized_event_filter_list:
                        for auth_filter in authorized_event_filter_list:
                             client.remove_event_handler(authorized_handler_func, auth_filter)
                    logger.info("SakaiBot CLI: Monitoring stopped automatically on exit.")
                except Exception as e_stop:
                    logger.error(f"Could not stop monitoring on exit: {e_stop}")
            running = False
        else:
            logger.warning(f"Invalid menu choice: {choice}")
            print("Invalid choice. Please try again.")
        
        if choice != 0: 
            await async_input("\nPress Enter to continue...")
            
    logger.info("CLI Handler finished.")

