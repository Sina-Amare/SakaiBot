# -*- coding: utf-8 -*-
# English comments as per our rules

import asyncio
import logging
import functools 

import settings_manager
from telethon import events 
# event_handlers module will be passed as an argument

logger = logging.getLogger(__name__)

# Global variables (will be loaded from settings)
selected_pv_for_categorization = None
selected_target_group = None 
active_command_to_topic_map = {} 

# Session-specific caches/states
current_group_topics_cache = [] 
is_monitoring_active = False
registered_handler_info = None 

# AI Config (will be passed from main)
OPENROUTER_API_KEY = None
OPENROUTER_MODEL_NAME = "deepseek/chat" # Default


async def async_input(prompt: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, input, prompt)

async def _get_user_choice_async(prompt="Enter your choice: ", expect_int=True):
    # ... (same as v19/v18) ...
    while True:
        try:
            choice_str = await async_input(prompt)
            if not choice_str.strip() and expect_int:
                print("Input cannot be empty. Please enter a number.")
                continue
            if expect_int:
                return int(choice_str)
            return choice_str.strip() 
        except ValueError:
            if expect_int:
                logger.warning(f"Invalid input '{choice_str}'. Please enter a number.")
                print(f"Invalid input '{choice_str}'. Please enter a number.")
            else: 
                logger.warning(f"Invalid input type for '{choice_str}'.")
                print(f"Invalid input type for '{choice_str}'.")
        except Exception as e:
            logger.error(f"Error getting user input: {e}")
            if expect_int: return -1 
            return "" 

def _display_main_menu():
    # ... (same as v20 (your previous version)) ...
    global selected_pv_for_categorization, selected_target_group, is_monitoring_active
    print("\nSakaiBot Menu:")
    print("=" * 30)
    print("1. List all my Private Chats (PVs)")
    print("2. Search PVs")
    pv_display_name = selected_pv_for_categorization['display_name'] if selected_pv_for_categorization and 'display_name' in selected_pv_for_categorization else "None"
    pv_status = f"(Selected PV: '{pv_display_name}')"
    group_status_text = "(No group selected)"
    if selected_target_group:
        group_type = "Forum Group" if selected_target_group.get('is_forum') else "Regular Group"
        group_status_text = f"(Target: '{selected_target_group.get('title', 'N/A')}' - {group_type})"
    print(f"3. Select/Change PV for Categorization {pv_status}")
    print(f"4. Set/Change Categorization Target Group {group_status_text}")
    print("5. Manage Command Mappings") 
    print("-" * 30)
    print("--- Categorization & AI ---") # Menu section updated
    monitoring_status = "Stop Monitoring Selected PV" if is_monitoring_active else "Start Monitoring Selected PV"
    print(f"6. {monitoring_status} (for categorization & AI commands)") # Clarify monitoring scope
    # Add new AI command examples to menu description (optional)
    print("   (Active commands like /clown, /funny, /prompt=..., /analyze N, /translate=... will be processed)")
    print("=" * 30)
    print("0. Exit (Save Settings)")


def _print_header(title: str):
    print(f"\n{'=' * 5} {title} {'=' * (40 - len(title) if len(title) < 40 else 0)}")

def _print_footer():
    print(f"{'=' * 47}")

def _display_entity_list(entity_list: list, title: str, entity_type: str = "PV", show_numbers: bool = True):
    # ... (same as v20) ...
    if not entity_list:
        print(f"\nNo {entity_type}(s) to display.")
        return
    _print_header(title)
    idx_width = 4 if show_numbers else 0
    name_width = 30
    username_width = 25
    id_width = 15
    header_format = "{:<{idx}} {:<{name}} {:<{uname}} {:<{id}}"
    row_format = "{:<{idx}} {:<{name}} {:<{uname}} {:<{id}}"
    if entity_type == "PV":
        print(header_format.format("#" if show_numbers else "", "Display Name", "Username", "User ID",idx=idx_width, name=name_width, uname=username_width, id=id_width))
        print("-" * (idx_width + name_width + username_width + id_width + (3 if show_numbers else 1)))
        for index, item in enumerate(entity_list):
            prefix = f"{index + 1}." if show_numbers else "-"
            display_name = item['display_name']
            username = item['username'] if item['username'] else "N/A"
            print(row_format.format(prefix, display_name[:name_width-1], username[:username_width-1], str(item['id'])[:id_width-1], idx=idx_width, name=name_width, uname=username_width, id=id_width))
    elif entity_type == "Group":
        print(header_format.format("#" if show_numbers else "", "Group Title", "Type", "Group ID", idx=idx_width, name=name_width, uname=username_width, id=id_width))
        print("-" * (idx_width + name_width + username_width + id_width + (3 if show_numbers else 1)))
        for index, item in enumerate(entity_list):
            prefix = f"{index + 1}." if show_numbers else "-"
            title_name = item['title']
            is_forum_str = "Forum" if item.get('is_forum') else "Regular"
            print(row_format.format(prefix, title_name[:name_width-1], is_forum_str, str(item['id'])[:id_width-1], idx=idx_width, name=name_width, uname=username_width, id=id_width))
    _print_footer()

def _display_topic_list(topics_list: list, group_title: str, show_numbers: bool = True):
    # ... (same as v20) ...
    if not topics_list:
        print(f"\nNo specific topics available/listed for group '{group_title}'.")
        return False
    _print_header(f"Topics in '{group_title}'")
    idx_width = 4 if show_numbers else 0
    title_width = 35
    id_width = 15
    header_format = "{:<{idx}} {:<{title}} {:<{id}}"
    row_format = "{:<{idx}} {:<{title}} {:<{id}}"
    print(header_format.format("#" if show_numbers else "", "Topic Title", "Topic ID", idx=idx_width, title=title_width, id=id_width))
    print("-" * (idx_width + title_width + id_width + (2 if show_numbers else 0)))
    for index, topic in enumerate(topics_list):
        prefix = f"{index + 1}." if show_numbers else "-"
        print(row_format.format(prefix, topic['title'][:title_width-1], str(topic['id'])[:id_width-1], idx=idx_width, title=title_width, id=id_width))
    _print_footer()
    return True

async def _handle_list_all_pvs(client, cache_manager, telegram_utils_module): # Removed show_numbers, default is True
    # ... (same as v20, but pass show_numbers=True to _display_entity_list) ...
    print("\nFetching your PV list, please wait...")
    pvs = []
    try:
        pvs = await cache_manager.get_pvs(client, telegram_utils_module, force_refresh=False)
        _display_entity_list(pvs, "All Your Private Chats (PVs)", entity_type="PV", show_numbers=True)
    except Exception as e:
        logger.error(f"Error handling 'List all PVs': {e}", exc_info=True)
        print("An error occurred while fetching PVs. Check logs for details.")
    return pvs


async def _handle_search_pvs(client, cache_manager, telegram_utils_module): # Removed show_numbers
    # ... (same as v20, but pass show_numbers=True to _display_entity_list) ...
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
            _display_entity_list(search_results, f"PV Search Results for '{search_query}'", entity_type="PV", show_numbers=True)
        else:
            print(f"No PVs found matching '{search_query}'.")
    except Exception as e:
        logger.error(f"Error handling 'Search PVs': {e}", exc_info=True)
        print("An error occurred during PV search. Check logs for details.")
    return search_results

async def _handle_select_pv_for_categorization(client, cache_manager, telegram_utils_module):
    # ... (same as v20) ...
    global selected_pv_for_categorization
    _print_header("Select PV for Categorization")
    print("1. List all PVs to select from")
    print("2. Search PVs to select from")
    print("0. Back to main menu")
    choice_input = await _get_user_choice_async(prompt="Choose an option: ", expect_int=True)
    if choice_input == -1: return
    pvs_to_select_from = []
    if choice_input == 1:
        pvs_to_select_from = await _handle_list_all_pvs(client, cache_manager, telegram_utils_module) # show_numbers defaults to True
    elif choice_input == 2:
        pvs_to_select_from = await _handle_search_pvs(client, cache_manager, telegram_utils_module) # show_numbers defaults to True
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

async def _handle_set_target_group(client, cache_manager, telegram_utils_module):
    # ... (same as v20) ...
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
    # ... (same as v20, including remove mapping logic) ...
    global selected_target_group, active_command_to_topic_map, current_group_topics_cache
    if not selected_target_group:
        print("Please set a target group first (Main Menu - Option 4).")
        return

    group_id = selected_target_group['id']
    group_title = selected_target_group['title']
    is_forum_group = selected_target_group.get('is_forum', False)
    
    _print_header(f"Manage Mappings for Group: '{group_title}'")
    
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
        print("\nCommand Mapping Menu:")
        print("1. View current mappings")
        if is_forum_group:
            print("2. Add new command (select topic from list)")
            print("3. Add new command (manual Topic ID entry)")
        else: 
            print("2. Add new command (will send to main group chat)")
        print("4. Remove a mapping")
        print("0. Back to main menu")

        choice = await _get_user_choice_async(prompt="Mapping choice: ", expect_int=True)
        if choice == -1: continue

        if choice == 1: 
            if not active_command_to_topic_map:
                print("\nNo command mappings currently defined.")
            else:
                _print_header("Current Command-Topic Mappings")
                cmd_width = 20
                target_width = 45
                print(f"{'Command':<{cmd_width}} {'Target':<{target_width}}")
                print(f"{'-'*cmd_width} {'-'*target_width}")
                for command, topic_id_map in active_command_to_topic_map.items():
                    target_description = ""
                    if topic_id_map is None: 
                        target_description = "Main Group Chat"
                    elif is_forum_group:
                        topic_title = next((t['title'] for t in current_group_topics_cache if t['id'] == topic_id_map), 
                                           f"Manually Added/Unknown Topic (ID: {topic_id_map})")
                        target_description = f"Topic: '{topic_title}' (ID: {topic_id_map})"
                    else: 
                        target_description = f"Target ID: {topic_id_map} (Group is not a forum)"
                    print(f"/{command:<{cmd_width-1}} {target_description:<{target_width}}")
                _print_footer()
        
        elif choice == 2: 
            command_name = await _get_user_choice_async(prompt="Enter new command name (e.g., 'funny', 'work', without '/'): ", expect_int=False)
            if not command_name or command_name == "": print("Invalid command."); continue
            command_name = command_name.strip().lower().replace(" ", "_")
            if not command_name: print("Command name cannot be empty after sanitization."); continue

            if is_forum_group:
                if not current_group_topics_cache:
                    print(f"No topics automatically found for forum '{group_title}'. Try adding a topic manually by ID (Option 3 in this menu).")
                    continue
                
                displayed_any_topic = _display_topic_list(current_group_topics_cache, group_title, show_numbers=True)
                if not displayed_any_topic: 
                    print(f"Still no topics to select from in '{group_title}'. Add manually or ensure topics exist.")
                    continue

                topic_number = await _get_user_choice_async(
                    prompt=f"Enter topic number for '/{command_name}' (1-{len(current_group_topics_cache)}), or 0 to cancel: ",
                    expect_int=True)
                if topic_number == -1: continue
                if topic_number == 0: print("Mapping cancelled."); continue
                
                if 1 <= topic_number <= len(current_group_topics_cache):
                    selected_topic_from_list = current_group_topics_cache[topic_number - 1]
                    active_command_to_topic_map[command_name] = selected_topic_from_list['id']
                    logger.info(f"Mapped command '/{command_name}' to Topic ID {selected_topic_from_list['id']} ('{selected_topic_from_list['title']}')")
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
            if not command_name_manual: print("Command name cannot be empty after sanitization."); continue

            manual_topic_id_str = await _get_user_choice_async(prompt=f"Numeric ID of topic for '/{command_name_manual}': ", expect_int=False)
            try: manual_topic_id = int(manual_topic_id_str)
            except ValueError: print("Invalid Topic ID (must be number)."); continue
            
            print(f"Verifying Topic ID {manual_topic_id} in '{group_title}'...")
            topic_info = await telegram_utils_module.get_topic_info_by_id(client, group_id, manual_topic_id)
            if topic_info:
                print(f"Verified Topic: Title='{topic_info['title']}', ID={topic_info['id']}")
                confirm_map_input = await _get_user_choice_async(prompt=f"Map '/{command_name_manual}' to this topic? (yes/no): ", expect_int=False)
                if confirm_map_input.lower() == 'yes':
                    active_command_to_topic_map[command_name_manual] = topic_info['id']
                    logger.info(f"Manually mapped '/{command_name_manual}' to Topic ID {topic_info['id']} ('{topic_info['title']}')")
                    print(f"Command '/{command_name_manual}' mapped to topic '{topic_info['title']}'.")
                    if not any(t['id'] == topic_info['id'] for t in current_group_topics_cache):
                        current_group_topics_cache.append(topic_info)
                else: print("Mapping cancelled.")
            else: print(f"Could not verify Topic ID {manual_topic_id} in '{group_title}'.")
        
        elif choice == 3 and not is_forum_group:
             print("Option 3 (manual Topic ID) is not applicable for non-forum groups.")

        elif choice == 4: # Remove a mapping
            if not active_command_to_topic_map:
                print("\nNo command mappings currently defined to remove.")
                continue

            _print_header("Current Mappings (for removal)")
            mappings_list = list(active_command_to_topic_map.items()) 
            cmd_width = 20
            target_width = 45
            print(f"{'#':<4} {'Command':<{cmd_width}} {'Target':<{target_width}}")
            print(f"{'-'*4} {'-'*cmd_width} {'-'*target_width}")

            for index, (command, topic_id_map) in enumerate(mappings_list):
                target_description = ""
                if topic_id_map is None: 
                    target_description = "Main Group Chat"
                elif is_forum_group:
                    topic_title = next((t['title'] for t in current_group_topics_cache if t['id'] == topic_id_map), 
                                       f"Manually Added/Unknown Topic (ID: {topic_id_map})")
                    target_description = f"Topic: '{topic_title}' (ID: {topic_id_map})"
                else: 
                    target_description = f"Target ID: {topic_id_map} (Group is not a forum)"
                print(f"{index + 1:<{4}} /{command:<{cmd_width-1}} {target_description:<{target_width}}")
            _print_footer()

            map_number_to_remove = await _get_user_choice_async(
                prompt=f"Enter number of mapping to remove (1-{len(mappings_list)}), or 0 to cancel: ", 
                expect_int=True
            )
            if map_number_to_remove == -1: continue 
            if map_number_to_remove == 0: print("Removal cancelled."); continue

            if 1 <= map_number_to_remove <= len(mappings_list):
                command_to_remove, _ = mappings_list[map_number_to_remove - 1]
                del active_command_to_topic_map[command_to_remove]
                logger.info(f"Removed mapping for command '/{command_to_remove}'.")
                print(f"Mapping for command '/{command_to_remove}' has been removed.")
            else:
                print("Invalid number for removal.")

        elif choice == 0: 
            break
        else:
            print("Invalid choice for mapping. Please try again.")


async def _toggle_monitoring(client, event_handlers_module):
    global is_monitoring_active, registered_handler_info, \
           selected_pv_for_categorization, selected_target_group, active_command_to_topic_map, \
           OPENROUTER_API_KEY, OPENROUTER_MODEL_NAME # Make AI config accessible

    if is_monitoring_active:
        if registered_handler_info:
            handler_func, event_filter = registered_handler_info
            try:
                client.remove_event_handler(handler_func, event_filter)
                logger.info("SakaiBot CLI: Event handler REMOVED.")
                print("Categorization and AI monitoring stopped.")
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
        # For categorization, target group and map are needed.
        # For AI commands like /prompt, they might not be.
        # We can make the checks more granular if needed.
        if not selected_target_group and any(cmd not in ["prompt", "analyze", "translate"] for cmd in active_command_to_topic_map.keys()):
             print("Please set a target group (Option 4) if using categorization commands.")
             # Allow proceeding if only AI commands are implicitly active or if map is empty
        if not active_command_to_topic_map and not (OPENROUTER_API_KEY and OPENROUTER_API_KEY != "YOUR_OPENROUTER_API_KEY_HERE"):
            print(f"No command mappings defined (Option 5) and/or OpenRouter API key not set for AI commands.")
            # If only AI commands are desired and API key is set, this check can be relaxed.
            # For now, let's assume some mapping or AI key is needed.
            # return # Let's allow starting if API key is there for AI features

        if not (OPENROUTER_API_KEY and OPENROUTER_API_KEY != "YOUR_OPENROUTER_API_KEY_HERE"):
            logger.warning("OpenRouter API key not configured. AI features like /prompt, /analyze, /translate will fail.")
            print("Warning: OpenRouter API key not configured. AI features will fail.")


        current_monitored_pv_id = selected_pv_for_categorization['id']
        
        # Pass all necessary current configurations to the handler
        bound_handler = functools.partial(
            event_handlers_module.categorization_reply_handler, # This handler will now also route AI commands
            client=client, 
            monitored_pv_id=current_monitored_pv_id,
            categorization_group_id=selected_target_group['id'] if selected_target_group else None,
            command_topic_map=active_command_to_topic_map.copy() if active_command_to_topic_map else {},
            openrouter_api_key=OPENROUTER_API_KEY, # Pass AI key
            openrouter_model_name=OPENROUTER_MODEL_NAME # Pass model name
        )
        
        event_filter = events.NewMessage(outgoing=True, chats=current_monitored_pv_id)
        
        try:
            client.add_event_handler(bound_handler, event_filter)
            registered_handler_info = (bound_handler, event_filter) 
            is_monitoring_active = True
            logger.info(f"SakaiBot CLI: Event handler ADDED for NewMessage(outgoing=True, chats={current_monitored_pv_id}).")
            logger.info(f"Monitoring started for PV ID {current_monitored_pv_id} for categorization and AI commands.")
            print(f"Monitoring started for PV: '{selected_pv_for_categorization['display_name']}'.")
            print("Reply to messages in that PV with your defined commands (e.g., /funny, /prompt=..., etc.).")
            print("The CLI is still active. You can stop monitoring or perform other actions.")
        except Exception as e:
            logger.error(f"Error adding event handler: {e}", exc_info=True)
            print("Error starting monitoring. Check logs.")


async def display_main_menu_loop(
    client, cache_manager, telegram_utils_module, 
    settings_manager_module, event_handlers_module,
    openrouter_api_key_main: str, openrouter_model_name_main: str # Receive AI config from main
):
    logger.info("CLI Handler started.")
    global selected_pv_for_categorization, selected_target_group, active_command_to_topic_map, \
           current_group_topics_cache, is_monitoring_active, registered_handler_info, \
           OPENROUTER_API_KEY, OPENROUTER_MODEL_NAME
    
    # Store AI config globally within this module for _toggle_monitoring
    OPENROUTER_API_KEY = openrouter_api_key_main
    OPENROUTER_MODEL_NAME = openrouter_model_name_main

    loaded_settings = settings_manager_module.load_user_settings()
    selected_pv_for_categorization = loaded_settings.get("selected_pv_for_categorization")
    selected_target_group = loaded_settings.get("selected_target_group") 
    active_command_to_topic_map = loaded_settings.get("active_command_to_topic_map", {})
    
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
        elif choice == 3: await _handle_select_pv_for_categorization(client, cache_manager, telegram_utils_module)
        elif choice == 4: await _handle_set_target_group(client, cache_manager, telegram_utils_module)
        elif choice == 5: await _handle_manage_command_topic_mappings(client, telegram_utils_module)
        elif choice == 6: await _toggle_monitoring(client, event_handlers_module) 
        elif choice == 0:
            logger.info("Exiting SakaiBot CLI. Saving settings...")
            settings_to_save = {
                "selected_pv_for_categorization": selected_pv_for_categorization,
                "selected_target_group": selected_target_group, 
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

