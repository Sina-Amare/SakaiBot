# -*- coding: utf-8 -*-
# English comments as per our rules

import asyncio
import configparser
import logging
import os
import sys
import signal

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Import our modules
import telegram_utils
import cache_manager
import cli_handler # Will manage its own state via cli_handler.cli_state
import event_handlers
import settings_manager
import ai_processor

# Module-level globals for signal handling and shutdown
_client_instance_for_signal = None
_cli_handler_module_for_signal = None # Will store the cli_handler module reference
_main_is_shutting_down_flag = False # To prevent re-entrant shutdown calls

# --- Custom File Handler with Auto-Flush ---
class AutoFlushFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()
# --- End of Custom File Handler ---

# --- Logger Setup ---
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
app_log_file_handler = AutoFlushFileHandler("sakaibot.log", encoding='utf-8', mode='a')
app_log_file_handler.setFormatter(log_formatter)
monitor_log_file_handler = AutoFlushFileHandler("monitor_activity.log", encoding='utf-8', mode='a')
monitor_log_file_handler.setFormatter(log_formatter)

main_logger = logging.getLogger(__name__)
main_logger.setLevel(logging.INFO)
main_logger.addHandler(app_log_file_handler)
main_logger.addHandler(console_handler)
main_logger.propagate = False

monitor_event_logger = logging.getLogger("event_handlers")
monitor_event_logger.setLevel(logging.DEBUG) # Keep DEBUG for event_handlers
monitor_event_logger.addHandler(monitor_log_file_handler)
monitor_event_logger.propagate = False

ai_logger = logging.getLogger("ai_processor")
ai_logger.setLevel(logging.INFO)
ai_logger.addHandler(app_log_file_handler) # Also log AI to main app log
ai_logger.addHandler(console_handler) # And console
ai_logger.propagate = False

def setup_other_module_logger(module_name, level=logging.INFO):
    logger = logging.getLogger(module_name)
    if not logger.handlers:
        logger.setLevel(level)
        logger.addHandler(app_log_file_handler)
        logger.addHandler(console_handler)
        logger.propagate = False
setup_other_module_logger("telegram_utils")
setup_other_module_logger("cache_manager")
setup_other_module_logger("cli_handler")
setup_other_module_logger("settings_manager")

CONFIG_FILE_NAME = "config.ini"
DEFAULT_MAX_ANALYZE_MESSAGES = 5000

def load_config():
    config = configparser.ConfigParser(defaults={'max_analyze_messages': str(DEFAULT_MAX_ANALYZE_MESSAGES)})
    if not os.path.exists(CONFIG_FILE_NAME):
        main_logger.error(f"Configuration file '{CONFIG_FILE_NAME}' not found.")
        main_logger.error(f"Please ensure '{CONFIG_FILE_NAME}' exists and is correctly filled.")
        sys.exit(1)
    try:
        with open(CONFIG_FILE_NAME, 'r', encoding='utf-8') as f: config.read_file(f)
    except Exception as e:
        main_logger.error(f"Could not read '{CONFIG_FILE_NAME}': {e}"); sys.exit(1)

    required_sections_keys = {
        "Telegram": ["api_id", "api_hash", "phone_number"],
        "UserBot": ["session_name"],
        "OpenRouter": ["api_key", "model_name"]
        # "Paths" section is optional for now, will check for ffmpeg_executable later
    }
    for section, keys in required_sections_keys.items():
        if section not in config:
            main_logger.error(f"Missing section '{section}' in '{CONFIG_FILE_NAME}'.")
            sys.exit(1)
        for key in keys:
            if key not in config[section] or not config[section][key]:
                if section == "OpenRouter" and key == "api_key" and \
                   (not config[section][key] or "YOUR_OPENROUTER_API_KEY_HERE" in config[section][key]):
                    main_logger.warning(f"OpenRouter API key is placeholder in '{CONFIG_FILE_NAME}'. AI features might fail.")
                elif section == "OpenRouter" and key == "model_name" and not config[section][key]:
                    main_logger.warning(f"OpenRouter model_name is missing. Using default.")
                elif not (section == "UserBot" and key == "max_analyze_messages"): # max_analyze_messages has a default
                    main_logger.error(f"Missing or empty key '{key}' in section '{section}'.")
                    sys.exit(1)

    if not config.has_option('UserBot', 'max_analyze_messages'):
        main_logger.info(f"'max_analyze_messages' not found. Using default {DEFAULT_MAX_ANALYZE_MESSAGES}.")
        if not config.has_section('UserBot'): config.add_section('UserBot')
        config.set('UserBot', 'max_analyze_messages', str(DEFAULT_MAX_ANALYZE_MESSAGES))
    else:
        try:
            val = config.getint('UserBot', 'max_analyze_messages')
            if val <=0:
                main_logger.warning(f"Invalid 'max_analyze_messages' ({val}). Using default {DEFAULT_MAX_ANALYZE_MESSAGES}.")
                config.set('UserBot', 'max_analyze_messages', str(DEFAULT_MAX_ANALYZE_MESSAGES))
        except ValueError:
            main_logger.warning(f"Invalid 'max_analyze_messages' format. Using default {DEFAULT_MAX_ANALYZE_MESSAGES}.")
            config.set('UserBot', 'max_analyze_messages', str(DEFAULT_MAX_ANALYZE_MESSAGES))

    loaded_api_key = config.get('OpenRouter', 'api_key', fallback="NOT_FOUND")
    if loaded_api_key != "NOT_FOUND" and len(loaded_api_key) > 10 and "YOUR_OPENROUTER_API_KEY_HERE" not in loaded_api_key :
        main_logger.info(f"Loaded OpenRouter API Key: {loaded_api_key[:10]}...{loaded_api_key[-4:]}")

    # Load ffmpeg path if specified
    ffmpeg_path = None
    if config.has_section("Paths") and config.has_option("Paths", "ffmpeg_executable"):
        ffmpeg_path = config.get("Paths", "ffmpeg_executable")
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            main_logger.info(f"Found ffmpeg_executable path in config: {ffmpeg_path}")
        elif ffmpeg_path:
            main_logger.warning(f"ffmpeg_executable path in config ('{ffmpeg_path}') does not exist. STT might fail.")
            ffmpeg_path = None # Reset if path is invalid
        else:
            main_logger.info("ffmpeg_executable not specified or empty in config. pydub will try to find ffmpeg in PATH.")
    else:
        main_logger.info("No [Paths] section or ffmpeg_executable option in config. pydub will try to find ffmpeg in PATH.")
    
    config.ffmpeg_path_resolved = ffmpeg_path # Store it on the config object for easy passing

    main_logger.info("Configuration loaded successfully.")
    return config

def perform_graceful_shutdown_tasks(client_instance, cli_handler_module_ref, source="unknown"):
    """Consolidates tasks for graceful shutdown. Uses cli_handler_module_ref.cli_state."""
    global _main_is_shutting_down_flag

    main_logger.info(f"Performing graceful shutdown tasks (source: {source})...")
    current_cli_state = cli_handler_module_ref.cli_state if cli_handler_module_ref else None

    if not current_cli_state:
        main_logger.error(f"Graceful shutdown ({source}): cli_state not available. Cannot save settings or stop monitoring.")
        return

    if not current_cli_state.get('settings_saved_on_cli_exit', False):
        main_logger.info(f"Graceful shutdown ({source}): Attempting to save settings...")
        settings_to_save = {
            "selected_pv_for_categorization": current_cli_state.get("selected_pv_for_categorization"),
            "selected_target_group": current_cli_state.get("selected_target_group"),
            "active_command_to_topic_map": current_cli_state.get("active_command_to_topic_map", {}),
            "directly_authorized_pvs": current_cli_state.get("directly_authorized_pvs", [])
        }
        settings_manager.save_user_settings(settings_to_save)
        main_logger.info(f"Graceful shutdown ({source}): Settings saved.")
    else:
        main_logger.info(f"Graceful shutdown ({source}): Settings were already saved by CLI exit.")

    if client_instance and client_instance.is_connected() and current_cli_state.get('is_monitoring_active', False):
        main_logger.info(f"Graceful shutdown ({source}): Attempting to stop event monitoring...")
        registered_info = current_cli_state.get('registered_handler_info')
        if registered_info:
            owner_handler_func, owner_event_filter, authorized_handler_func, authorized_event_filter_list = registered_info
            try:
                if owner_handler_func and owner_event_filter:
                    client_instance.remove_event_handler(owner_handler_func, owner_event_filter)
                if authorized_handler_func and authorized_event_filter_list:
                    for auth_filter in authorized_event_filter_list:
                        client_instance.remove_event_handler(authorized_handler_func, auth_filter)
                current_cli_state['is_monitoring_active'] = False
                current_cli_state['registered_handler_info'] = None
                main_logger.info(f"Graceful shutdown ({source}): Monitoring handlers removed.")
            except Exception as e_stop:
                main_logger.error(f"Graceful shutdown ({source}): Error stopping monitoring: {e_stop}")
        else:
            main_logger.warning(f"Graceful shutdown ({source}): Monitoring was active but no handler info found in cli_state.")
            current_cli_state['is_monitoring_active'] = False
    elif current_cli_state.get('is_monitoring_active', False):
         main_logger.info(f"Graceful shutdown ({source}): Monitoring active but client not connected or available.")


def sigint_handler_main(sig, frame):
    global _main_is_shutting_down_flag, _client_instance_for_signal, _cli_handler_module_for_signal

    if _main_is_shutting_down_flag:
        main_logger.info("SIGINT: Shutdown already in progress. Ignoring.")
        return

    _main_is_shutting_down_flag = True
    main_logger.warning(f"SIGINT (Ctrl+C) received by main process. Initiating graceful shutdown.")

    if _client_instance_for_signal and _cli_handler_module_for_signal:
        perform_graceful_shutdown_tasks(
            _client_instance_for_signal,
            _cli_handler_module_for_signal,
            source="SIGINT"
        )
    else:
        main_logger.error("SIGINT: Client instance or CLI handler module not available for graceful shutdown.")
    main_logger.info("SIGINT: Exiting application now.")
    sys.exit(0)

async def main(config_values):
    global _client_instance_for_signal, _cli_handler_module_for_signal, _main_is_shutting_down_flag
    _main_is_shutting_down_flag = False

    api_id = config_values.getint('Telegram', 'api_id')
    api_hash = config_values.get('Telegram', 'api_hash')
    phone_number = config_values.get('Telegram', 'phone_number')
    session_name = config_values.get('UserBot', 'session_name')

    openrouter_api_key = config_values.get('OpenRouter', 'api_key', fallback="YOUR_OPENROUTER_API_KEY_HERE")
    openrouter_model_name = config_values.get('OpenRouter', 'model_name', fallback="deepseek/chat")
    max_analyze_messages_conf = config_values.getint('UserBot', 'max_analyze_messages', fallback=DEFAULT_MAX_ANALYZE_MESSAGES)
    
    # Get the resolved ffmpeg path from the config object
    ffmpeg_executable_path = getattr(config_values, 'ffmpeg_path_resolved', None)


    if max_analyze_messages_conf <= 0:
        main_logger.warning(f"Configured max_analyze_messages ({max_analyze_messages_conf}) is not positive. Using default {DEFAULT_MAX_ANALYZE_MESSAGES}.")
        max_analyze_messages_conf = DEFAULT_MAX_ANALYZE_MESSAGES
    main_logger.info(f"Using max_analyze_messages: {max_analyze_messages_conf}")

    if not openrouter_api_key or "YOUR_OPENROUTER_API_KEY_HERE" in openrouter_api_key or len(openrouter_api_key) < 10:
        main_logger.warning("OpenRouter API key not properly configured. AI features will be disabled or may fail.")
        openrouter_api_key = None

    client = TelegramClient(session_name, api_id, api_hash, system_version="4.16.30-vxCUSTOM")
    _client_instance_for_signal = client
    _cli_handler_module_for_signal = cli_handler

    main_logger.info(f"Initializing Telegram client with session: '{session_name}.session'")
    try:
        await client.connect()
        if not await client.is_user_authorized():
            main_logger.info(f"User not authorized. Sending code to {phone_number}...")
            try:
                await client.send_code_request(phone_number)
                code_ok = False
                while not code_ok:
                    code = await cli_handler.async_input('Enter code: ')
                    try:
                        await client.sign_in(phone_number, code)
                        code_ok = True
                    except SessionPasswordNeededError:
                        main_logger.info("2FA enabled.")
                        password_ok = False
                        while not password_ok:
                            password = await cli_handler.async_input('Enter 2FA password: ')
                            try:
                                await client.sign_in(password=password)
                                password_ok = True; code_ok = True
                            except Exception as e_pass: main_logger.error(f"2FA login failed: {e_pass}.")
                    except Exception as e_code: main_logger.error(f"Code verification failed: {e_code}.")
            except Exception as e_send_code: main_logger.error(f"Failed to send code: {e_send_code}"); return

        me = await client.get_me()
        if me:
            main_logger.info(f"Signed in as: {me.first_name} (@{me.username or 'N/A'})")
            main_logger.info("Handing control to CLI Handler...")

            await cli_handler.display_main_menu_loop(
                client, cache_manager, telegram_utils, settings_manager, event_handlers,
                openrouter_api_key, openrouter_model_name,
                max_analyze_messages_conf,
                ffmpeg_path=ffmpeg_executable_path # Pass the ffmpeg path
            )
            _main_is_shutting_down_flag = True
            main_logger.info("Returned from CLI handler (Option 0 exit). Main will now proceed to finally block.")

        else: main_logger.error("Could not get user info.")
    except ConnectionError: main_logger.error("Connection to Telegram failed.")
    except SystemExit:
        main_logger.info("SakaiBot is exiting via SystemExit.")
        _main_is_shutting_down_flag = True
    except KeyboardInterrupt:
        main_logger.warning("KeyboardInterrupt directly caught in main loop (should be SIGINT).")
        if not _main_is_shutting_down_flag:
            _main_is_shutting_down_flag = True
            perform_graceful_shutdown_tasks(client, cli_handler, source="KeyboardInterrupt_main")
    except Exception as e:
        main_logger.error(f"An unexpected error occurred in main: {e}", exc_info=True)
        if not _main_is_shutting_down_flag:
            _main_is_shutting_down_flag = True
            perform_graceful_shutdown_tasks(client, cli_handler, source="main_exception")
    finally:
        main_logger.info("Main 'finally' block reached.")
        if not _main_is_shutting_down_flag:
            _main_is_shutting_down_flag = True
            main_logger.info("Main 'finally': Shutdown not initiated by SIGINT or clean CLI exit. Performing tasks.")
            perform_graceful_shutdown_tasks(client, cli_handler, source="main_finally_unexpected_exit")
        else:
            main_logger.info("Main 'finally': Shutdown was already initiated. Skipping redundant tasks if covered.")

        if client and client.is_connected():
            main_logger.info("Disconnecting client...")
            await client.disconnect()
        main_logger.info("SakaiBot has been stopped.")

if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigint_handler_main)
    loaded_config = load_config()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main(loaded_config))
    except SystemExit:
        main_logger.info("SakaiBot exited via SystemExit from asyncio.run (likely from SIGINT).")
    except KeyboardInterrupt:
        main_logger.info("SakaiBot stopped by user (Ctrl+C at asyncio.run level).")
        if not _main_is_shutting_down_flag and _client_instance_for_signal and _cli_handler_module_for_signal:
            _main_is_shutting_down_flag = True
            main_logger.warning("Ctrl+C at asyncio.run: Manually triggering shutdown tasks.")
    finally:
        main_logger.info("Main __main__ finally: Ensuring event loop is closed.")
        if loop and not loop.is_closed():
            for task in asyncio.all_tasks(loop):
                task.cancel()
            try:
                loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop), return_exceptions=True))
            except Exception as e:
                main_logger.error(f"Error during task cleanup in __main__ finally: {e}")
            loop.close()
        main_logger.info("Event loop closed. SakaiBot finished.")

