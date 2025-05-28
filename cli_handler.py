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
selected_target_group = None  # Stores {'id': group_id, 'title': group_title, 'is_forum': bool}
active_command_to_topic_map = {} 
current_group_topics_cache = [] 

is_monitoring_active = False
registered_handler_info = None 


async def async_input(prompt: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, input, prompt)

async def _get_user_choice_async(prompt="Enter your choice: ", expect_int=True):
    while True:
        try:
            choice_str = await async_input(prompt)
            if expect_int:
                return int(choice_str)
            return choice_str 
        except ValueError:
            if expect_int:
                logger.warning("Invalid input. Please enter a number.")
                print("Invalid input. Please enter a number.")
            else: 
                logger.warning("Invalid input type.")
                print("Invalid input type.")
        except Exception as e:
            logger.error(f"Error getting user input: {e}")
            if expect_int: return -1 
            return "" 

def _display_main_menu():
    global selected_pv_for_categorization, selected_target_group, is_monitoring_active
    print("\nSakaiBot Menu:")
    print("1. List all my Private Chats (PVs)")
    print("2. Search PVs")
    
    pv_display_name = selected_pv_for_categorization['display_name'] if selected_pv_for_categorization and 'display_name' in selected_pv_for_categorization else "None"
    pv_status = f"(Selected PV: '{pv_display_name}')"
    
    group_status_text = "(No group selected)"
    if selected_target_group:
        # Use the 'is_forum' status stored in selected_target_group
        group_type = "Forum Group" if selected_target_group.get('is_forum') else "Regular Group"
        group_status_text = f"(Target: '{selected_target_group.get('title', 'N/A')}' - {group_type})"
        
    print(f"3. Select/Change PV for Categorization {pv_status}")
    print(f"4. Set/Change Categorization Target Group {group_status_text}")
    print("5. Manage Command Mappings (Requires Target Group)") 
    
    print("--- Categorization (Requires PV & Target Group & Mappings) ---")
    monitoring_status = "Stop Monitoring Selected PV" if is_monitoring_active else "Start Monitoring Selected PV"
    print(f"6. {monitoring_status}")
    print("0. Exit (Save Settings)")

def _display_entity_list(entity_list: list, title: str, entity_type: str = "PV"):
    if not entity_list:
        print(f"\nNo {entity_type}(s) to display.")
        return
    print(f"\n{title}")
    for index, item in enumerate(entity_list):
        item_id = item['id']
        if entity_type == "PV":
            display_name = item['display_name']
            username = item['username'] if item['username'] else "N/A"
            print(f"{index + 1}. Name: '{display_name}', Username: {username}, ID: {item_id}")
        elif entity_type == "Group":
            title_name = item['title']
            # Display 'is_forum' status if available from fetch_user_groups
            is_forum_str = ""
            if 'is_forum' in item: # Check if key exists
                is_forum_str = " (Forum)" if item.get('is_forum') else " (Regular/Unknown)"
            print(f"{index + 1}. Group Title: '{title_name}'{is_forum_str}, ID: {item_id}")
    print("---------------------------------")

async def _handle_list_all_pvs(client, cache_manager, telegram_utils_module, show_numbers=True):
    # ... (same as v18) ...
    print("\nFetching your PV list, please wait...")
    pvs = []
    try:
        pvs = await cache_manager.get_pvs(client, telegram_utils_module, force_refresh=False)
        _display_entity_list(pvs, "--- All Your Private Chats (PVs) ---", entity_type="PV")
    except Exception as e:
        logger.error(f"Error handling 'List all PVs': {e}", exc_info=True)
        print("An error occurred while fetching PVs. Check logs for details.")
    return pvs

async def _handle_search_pvs(client, cache_manager, telegram_utils_module, show_numbers=True):
    # ... (same as v18) ...
    search_query = await _get_user_choice_async(prompt="Enter search term for PVs (name or username): ", expect_int=False)
    search_results = []
    if not search_query : 
        print("Search cancelled or invalid input.")
        return search_results
    print(f"\nSearching PVs for '{search_query}', please wait...")
    try:
        all_pvs = await cache_manager.get_pvs(client, telegram_utils_module, force_refresh=False)
        if not all_pvs:
            print("Could not retrieve PV list to search.")
            return search_results
        search_results = _perform_pv_search(all_pvs, search_query)
        if search_results:
            _display_entity_list(search_results, f"--- PV Search Results for '{search_query}' ---", entity_type="PV")
        else:
            print(f"No PVs found matching '{search_query}'.")
    except Exception as e:
        logger.error(f"Error handling 'Search PVs': {e}", exc_info=True)
        print("An error occurred during PV search. Check logs for details.")
    return search_results

def _perform_pv_search(pvs_list: list, query: str) -> list:
    # ... (same as v18) ...
    if not query: return []
    query_lower = query.lower()
    results = []
    for pv in pvs_list:
        name_match = query_lower in pv['display_name'].lower()
        username_to_check = ""
        if pv['username']:
            username_to_check = pv['username'][1:].lower() if pv['username'].startswith('@') else pv['username'].lower()
        query_username_part = query_lower[1:] if query_lower.startswith('@') else query_lower
        username_match = False
        if pv['username'] and query_username_part:
             username_match = query_username_part in username_to_check
        if name_match or username_match:
            results.append(pv)
    return results

async def _handle_select_pv_for_categorization(client, cache_manager, telegram_utils_module):
    # ... (same as v18) ...
    global selected_pv_for_categorization
    print("\n--- Select PV for Categorization ---")
    print("1. List all PVs to select from")
    print("2. Search PVs to select from")
    print("0. Back to main menu")
    choice_input = await _get_user_choice_async(prompt="Choose an option: ", expect_int=True)
    if choice_input == -1: return
    pvs_to_select_from = []
    if choice_input == 1:
        pvs_to_select_from = await _handle_list_all_pvs(client, cache_manager, telegram_utils_module)
    elif choice_input == 2:
        pvs_to_select_from = await _handle_search_pvs(client, cache_manager, telegram_utils_module)
    elif choice_input == 0: return
    else:
        print("Invalid option. Returning to main menu.")
        return
    if not pvs_to_select_from:
        print("No PVs available to select from based on your previous action.")
        return
    while True:
        pv_number = await _get_user_choice_async(
            prompt=f"Enter the number of the PV to select (1-{len(pvs_to_select_from)}), or 0 to cancel: ",
            expect_int=True)
        if pv_number == -1: continue
        if pv_number == 0:
            print("Selection cancelled.")
            return
        if 1 <= pv_number <= len(pvs_to_select_from):
            selected_pv = pvs_to_select_from[pv_number - 1]
            selected_pv_for_categorization = selected_pv 
            logger.info(f"PV selected for categorization: ID={selected_pv['id']}, Name='{selected_pv['display_name']}'")
            print(f"\nSuccessfully selected PV: '{selected_pv['display_name']}' (ID: {selected_pv['id']}) for categorization.")
            return
        else:
            print(f"Invalid number. Please enter a number between 1 and {len(pvs_to_select_from)} or 0.")

def _display_topic_list(topics_list: list, group_title: str, show_numbers: bool = True):
    # ... (same as v18) ...
    if not topics_list:
        print(f"\nNo specific topics available/listed for group '{group_title}'.")
        return False
    print(f"\n--- Topics in '{group_title}' ---")
    for index, topic in enumerate(topics_list):
        if show_numbers:
            print(f"{index + 1}. Title: '{topic['title']}', ID: {topic['id']}")
        else:
            print(f"- Title: '{topic['title']}', ID: {topic['id']}")
    print("-----------------------------")
    return True

async def _handle_set_target_group(client, cache_manager, telegram_utils_module):
    global selected_target_group, active_command_to_topic_map, current_group_topics_cache
    print("\n--- Set/Change Categorization Target Group ---")
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

    _display_entity_list(user_groups, "--- Your Qualifying Supergroups ---", entity_type="Group")

    while True:
        group_number = await _get_user_choice_async(
            prompt=f"Enter the number of the group to select (1-{len(user_groups)}), or 0 to cancel: ",
            expect_int=True)
        if group_number == -1: continue
        if group_number == 0:
            print("Target group selection cancelled.")
            return
        if 1 <= group_number <= len(user_groups):
            # Get the initially fetched group info (which might have a preliminary 'is_forum' status)
            chosen_group_from_list = user_groups[group_number - 1]
            
            # Now, definitively check/fetch topics and the accurate 'is_forum' status
            print(f"\nVerifying group '{chosen_group_from_list['title']}' and fetching topics if it's a forum, please wait...")
            actual_topics, is_actually_forum = await telegram_utils_module.get_group_topics(client, chosen_group_from_list['id'])
            
            # Update the group info with the accurate 'is_forum' status
            updated_target_group_info = {
                'id': chosen_group_from_list['id'],
                'title': chosen_group_from_list['title'],
                'is_forum': is_actually_forum # Use the definitive status
            }

            if selected_target_group and selected_target_group['id'] != updated_target_group_info['id']:
                logger.info(f"Target group changed. Clearing command-topic map and topic cache.")
                active_command_to_topic_map = {} 
            
            selected_target_group = updated_target_group_info # Store the updated info
            current_group_topics_cache = actual_topics if is_actually_forum else [] # Cache topics only if it's a forum

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
    # ... (This function remains the same as v18, it will use the updated selected_target_group['is_forum']) ...
    global selected_target_group, active_command_to_topic_map, current_group_topics_cache
    if not selected_target_group:
        print("Please set a target group first (Main Menu - Option 4).")
        return
    group_id = selected_target_group['id']
    group_title = selected_target_group['title']
    is_forum_group = selected_target_group.get('is_forum', False) # Get the accurate is_forum status
    print(f"\n--- Manage Mappings for Group: '{group_title}' (ID: {group_id}) ---")
    
    # If it's a forum and topics aren't cached (e.g., first time after group selection or cache cleared)
    if is_forum_group and not current_group_topics_cache: 
        print(f"Re-fetching topics for forum '{group_title}', please wait...")
        try:
            topics, _ = await telegram_utils_module.get_group_topics(client, group_id)
            current_group_topics_cache = topics
        except Exception as e:
            logger.error(f"Could not fetch topics for group {group_id}: {e}", exc_info=True)
            print(f"Error: Could not fetch topics for group '{group_title}'.")
            current_group_topics_cache = [] # Ensure it's an empty list on error
    
    # Safeguard if current_group_topics_cache is None after attempting to fetch
    if current_group_topics_cache is None: current_group_topics_cache = []


    while True:
        print("\nCommand Mapping Menu:")
        print("1. View current mappings")
        if is_forum_group:
            print("2. Add new command (select topic from list)")
            print("3. Add new command (manual Topic ID entry)")
        else: 
            print("2. Add new command (will send to main group chat)")
        print("4. Remove a mapping (Not Implemented Yet)")
        print("0. Back to main menu")
        choice = await _get_user_choice_async(prompt="Mapping choice: ", expect_int=True)
        if choice == -1: continue
        if choice == 1: 
            if not active_command_to_topic_map:
                print("\nNo command mappings currently defined.")
            else:
                print("\n--- Current Command Mappings ---")
                for command, topic_id_map in active_command_to_topic_map.items():
                    target_description = ""
                    if topic_id_map is None: 
                        target_description = "Main Group Chat"
                    elif is_forum_group: # Only try to find title if it's a forum
                        topic_title = next((t['title'] for t in current_group_topics_cache if t['id'] == topic_id_map), 
                                           f"Manually Added/Unknown Topic (ID: {topic_id_map})")
                        target_description = f"Topic: '{topic_title}' (ID: {topic_id_map})"
                    else: # Should ideally not happen if topic_id_map is not None for non-forum
                        target_description = f"Target ID: {topic_id_map} (Group is not a forum)"
                    print(f"Command: /{command}  =>  {target_description}")
                print("------------------------------------")
        elif choice == 2: 
            command_name = await _get_user_choice_async(prompt="Enter new command name (e.g., 'funny', 'work', without '/'): ", expect_int=False)
            if not command_name or command_name == "": print("Invalid command."); continue
            command_name = command_name.strip().lower().replace(" ", "_")
            if not command_name: print("Command name empty."); continue
            if is_forum_group:
                if not current_group_topics_cache:
                    print(f"No topics automatically found for forum '{group_title}'. Try adding a topic manually by ID (Option 3).")
                    continue
                _display_topic_list(current_group_topics_cache, group_title, show_numbers=True)
                if not current_group_topics_cache: continue
                topic_number = await _get_user_choice_async(
                    prompt=f"Enter topic number for '/{command_name}' (1-{len(current_group_topics_cache)}), or 0 to cancel: ",
                    expect_int=True)
                if topic_number == -1: continue
                if topic_number == 0: print("Mapping cancelled."); continue
                if 1 <= topic_number <= len(current_group_topics_cache):
                    selected_topic_from_list = current_group_topics_cache[topic_number - 1]
                    active_command_to_topic_map[command_name] = selected_topic_from_list['id']
                    logger.info(f"Mapped command '/{command_name}' to Topic ID {selected_topic_from_list['id']} ...")
                    print(f"Command '/{command_name}' mapped to topic '{selected_topic_from_list['title']}'.")
                else: print(f"Invalid topic number.")
            else: 
                active_command_to_topic_map[command_name] = None 
                logger.info(f"Mapped command '/{command_name}' to Main Chat of group '{group_title}'.")
                print(f"Command '/{command_name}' will send to the main chat of group '{group_title}'.")
        elif choice == 3 and is_forum_group: 
            command_name_manual = await _get_user_choice_async(prompt="Enter command name (no '/'): ", expect_int=False)
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
                    logger.info(f"Manually mapped '/{command_name_manual}' to Topic ID {topic_info['id']} ...")
                    print(f"Command '/{command_name_manual}' mapped to topic '{topic_info['title']}'.")
                    if not any(t['id'] == topic_info['id'] for t in current_group_topics_cache):
                        current_group_topics_cache.append(topic_info)
                else: print("Mapping cancelled.")
            else: print(f"Could not verify Topic ID {manual_topic_id} in '{group_title}'.")
        elif choice == 3 and not is_forum_group:
             print("Option 3 (manual Topic ID) is not applicable for non-forum groups.")
        elif choice == 4: print("Remove a mapping - Not Implemented Yet.")
        elif choice == 0: break
        else: print("Invalid choice for mapping.")


async def _toggle_monitoring(client, event_handlers_module):
    # ... (same as v17) ...
    global is_monitoring_active, registered_handler_info, \
           selected_pv_for_categorization, selected_target_group, active_command_to_topic_map

    if is_monitoring_active:
        if registered_handler_info:
            handler_func, event_filter = registered_handler_info
            try:
                client.remove_event_handler(handler_func, event_filter)
                logger.info("SakaiBot CLI: Event handler REMOVED.")
                print("Categorization monitoring stopped.")
                is_monitoring_active = False
                registered_handler_info = None
            except Exception as e:
                logger.error(f"Error removing event handler: {e}", exc_info=True)
                print("Error stopping monitoring. Check logs.")
        else:
            logger.warning("Attempted to stop monitoring, but no handler info was stored.")
            is_monitoring_active = False 
    else:
        if not selected_pv_for_categorization:
            print("Please select a PV to monitor first (Option 3).")
            return
        if not selected_target_group:
            print("Please set a target group first (Option 4).")
            return
        if not active_command_to_topic_map:
            print(f"No command mappings defined. Please use Option 5.")
            return

        current_monitored_pv_id = selected_pv_for_categorization['id']
        current_target_group_id = selected_target_group['id']
        current_command_map = active_command_to_topic_map.copy()

        bound_handler = functools.partial(
            event_handlers_module.categorization_reply_handler, 
            client=client, 
            monitored_pv_id=current_monitored_pv_id,
            categorization_group_id=current_target_group_id,
            command_topic_map=current_command_map
        )
        
        event_filter = events.NewMessage(outgoing=True, chats=current_monitored_pv_id)
        
        try:
            client.add_event_handler(bound_handler, event_filter)
            registered_handler_info = (bound_handler, event_filter) 
            is_monitoring_active = True
            logger.info(f"SakaiBot CLI: Event handler ADDED for NewMessage(outgoing=True, chats={current_monitored_pv_id}).")
            logger.info(f"Categorization monitoring started for PV ID {current_monitored_pv_id}.")
            print(f"Monitoring started for PV: '{selected_pv_for_categorization['display_name']}'.")
            print("Reply to messages in that PV with your defined commands.")
            print("The CLI is still active. You can stop monitoring or perform other actions.")
        except Exception as e:
            logger.error(f"Error adding event handler: {e}", exc_info=True)
            print("Error starting monitoring. Check logs.")


async def display_main_menu_loop(client, cache_manager, telegram_utils_module, settings_manager_module, event_handlers_module):
    # ... (same as v18) ...
    logger.info("CLI Handler started.")
    global selected_pv_for_categorization, selected_target_group, active_command_to_topic_map, \
           current_group_topics_cache, is_monitoring_active, registered_handler_info
    
    loaded_settings = settings_manager_module.load_user_settings()
    selected_pv_for_categorization = loaded_settings.get("selected_pv_for_categorization")
    selected_target_group = loaded_settings.get("selected_target_group") 
    active_command_to_topic_map = loaded_settings.get("active_command_to_topic_map", {})
    
    # Re-fetch topics for the loaded group if it's a forum, to populate current_group_topics_cache
    if selected_target_group and selected_target_group.get('is_forum'): 
        logger.info(f"Loaded target forum group '{selected_target_group.get('title', 'N/A')}'. Fetching its topics for session cache...")
        try:
            # get_group_topics returns (topics, is_forum_flag)
            # We trust the is_forum flag already stored in selected_target_group from settings
            topics, _ = await telegram_utils_module.get_group_topics(client, selected_target_group['id'])
            current_group_topics_cache = topics
            logger.info(f"Cached {len(current_group_topics_cache)} topics for group '{selected_target_group.get('title', 'N/A')}'.")
        except Exception as e:
            logger.error(f"Failed to pre-fetch topics for loaded group: {e}")
            current_group_topics_cache = []
    else:
        current_group_topics_cache = [] # Ensure it's empty for non-forums or if no group selected

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
        elif choice == 3: await _handle_select_pv_for_categorization(client, cache_manager, telegram_utils_module)
        elif choice == 4: await _handle_set_target_group(client, cache_manager, telegram_utils_module)
        elif choice == 5: await _handle_manage_command_topic_mappings(client, telegram_utils_module)
        elif choice == 6: await _toggle_monitoring(client, event_handlers_module) 
        elif choice == 0:
            logger.info("Exiting SakaiBot CLI. Saving settings...")
            settings_to_save = {
                "selected_pv_for_categorization": selected_pv_for_categorization,
                "selected_target_group": selected_target_group, # This will save 'is_forum' too
                "active_command_to_topic_map": active_command_to_topic_map
            }
            settings_manager_module.save_user_settings(settings_to_save)
            print("Settings saved. Exiting SakaiBot...")
            if is_monitoring_active and registered_handler_info:
                handler_func, event_filter = registered_handler_info
                try:
                    client.remove_event_handler(handler_func, event_filter) 
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

