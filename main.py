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
import cli_handler 
import event_handlers 
import settings_manager 

_client_instance_for_signal = None
_app_is_exiting_cleanly = False 

# --- Custom File Handler with Auto-Flush (Moved to the top of Logger Setup) ---
class AutoFlushFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()
# --- End of Custom File Handler ---

# --- Logger Setup ---
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 1. Console Handler (shared by most loggers, except event_handlers)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
if sys.platform == "win32" and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 2. General Application Log File Handler (sakaibot.log)
app_log_file_handler = AutoFlushFileHandler("sakaibot.log", encoding='utf-8', mode='a') 
app_log_file_handler.setFormatter(log_formatter)

# 3. Dedicated Monitor Activity Log File Handler (monitor_activity.log)
monitor_log_file_handler = AutoFlushFileHandler("monitor_activity.log", encoding='utf-8', mode='a') 
monitor_log_file_handler.setFormatter(log_formatter)

# --- Configure Loggers ---
main_logger = logging.getLogger(__name__)
main_logger.setLevel(logging.INFO) 
main_logger.addHandler(app_log_file_handler) 
main_logger.addHandler(console_handler)    
main_logger.propagate = False

# Logger for event_handlers (monitoring activities)
monitor_event_logger = logging.getLogger("event_handlers") 
monitor_event_logger.setLevel(logging.DEBUG) 
monitor_event_logger.addHandler(monitor_log_file_handler) 
# To see event_handler logs in console as well during debugging, uncomment the next line:
# monitor_event_logger.addHandler(console_handler) 
monitor_event_logger.propagate = False 

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

# logging.getLogger('telethon').setLevel(logging.INFO) 

# --- Configuration Loading & Signal Handling (Same as before) ---
CONFIG_FILE_NAME = "config.ini"
def load_config():
    # ... (load_config function from sakaibot_main_py_v_isolated_monitor_log)
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE_NAME):
        main_logger.error(f"Configuration file '{CONFIG_FILE_NAME}' not found.")
        main_logger.error("Please copy 'config.ini.example' to 'config.ini' and fill in your details.")
        sys.exit(1)
    try:
        with open(CONFIG_FILE_NAME, 'r', encoding='utf-8') as f:
            config.read_file(f)
    except Exception as e:
        main_logger.error(f"Could not read configuration file '{CONFIG_FILE_NAME}' with UTF-8: {e}")
        try:
            config.read(CONFIG_FILE_NAME) 
        except Exception as e_fallback:
            main_logger.error(f"Could not read configuration file '{CONFIG_FILE_NAME}' with default encoding: {e_fallback}")
            sys.exit(1)
    required_sections_keys = {
        "Telegram": ["api_id", "api_hash", "phone_number"],
        "UserBot": ["session_name"],
    }
    for section, keys in required_sections_keys.items():
        if section not in config:
            main_logger.error(f"Missing section '{section}' in '{CONFIG_FILE_NAME}'.")
            sys.exit(1)
        for key in keys:
            if key not in config[section] or not config[section][key]:
                main_logger.error(f"Missing or empty key '{key}' in section '{section}' in '{CONFIG_FILE_NAME}'.")
                sys.exit(1)
    main_logger.info("Configuration loaded successfully.") 
    return config

def save_current_settings_on_exit(source="unknown"):
    # ... (save_current_settings_on_exit function from sakaibot_main_py_v_isolated_monitor_log)
    global _app_is_exiting_cleanly
    if _app_is_exiting_cleanly: 
        main_logger.info(f"Save on exit ({source}): Skipped, app is already exiting cleanly.")
        return
    main_logger.info(f"Attempting to save settings on exit (source: {source})...")
    if hasattr(cli_handler, 'selected_pv_for_categorization') and \
       hasattr(cli_handler, 'selected_target_group') and \
       hasattr(cli_handler, 'active_command_to_topic_map'):
        if cli_handler.selected_pv_for_categorization is not None or \
           cli_handler.selected_target_group is not None or \
           cli_handler.active_command_to_topic_map:
            settings_to_save = {
                "selected_pv_for_categorization": cli_handler.selected_pv_for_categorization,
                "selected_target_group": cli_handler.selected_target_group,
                "active_command_to_topic_map": cli_handler.active_command_to_topic_map
            }
            settings_manager.save_user_settings(settings_to_save)
        else:
            main_logger.info(f"Save on exit ({source}): No specific settings were configured to save.")
    else:
        main_logger.warning(f"Save on exit ({source}): cli_handler settings variables not found.")

def sigint_handler(sig, frame):
    # ... (sigint_handler function from sakaibot_main_py_v_isolated_monitor_log)
    main_logger.warning(f"SIGINT (Ctrl+C) received. SakaiBot is stopping.")
    save_current_settings_on_exit(source="SIGINT")
    global _client_instance_for_signal
    if _client_instance_for_signal and \
       hasattr(cli_handler, 'is_monitoring_active') and cli_handler.is_monitoring_active and \
       hasattr(cli_handler, 'registered_handler_info') and cli_handler.registered_handler_info:
        main_logger.info("SIGINT: Attempting to stop monitoring...")
        cli_handler.is_monitoring_active = False 
        main_logger.info("SIGINT: Monitoring flag set to False.")
    main_logger.info("Raising SystemExit to allow finally blocks to run.")
    sys.exit(0) 

async def main(config_values):
    # ... (main async function from sakaibot_main_py_v_isolated_monitor_log, ensure async_input is used for auth)
    global _client_instance_for_signal, _app_is_exiting_cleanly
    api_id = config_values.getint('Telegram', 'api_id')
    api_hash = config_values.get('Telegram', 'api_hash')
    phone_number = config_values.get('Telegram', 'phone_number')
    session_name = config_values.get('UserBot', 'session_name')
    client = TelegramClient(session_name, api_id, api_hash, system_version="4.16.30-vxCUSTOM")
    _client_instance_for_signal = client 
    main_logger.info(f"Initializing Telegram client with session: '{session_name}.session'")
    try:
        main_logger.info("Attempting to connect to Telegram...")
        await client.connect()
        if not await client.is_user_authorized():
            main_logger.info(f"User is not authorized. Sending code request to {phone_number}...")
            try:
                await client.send_code_request(phone_number)
                code_ok = False
                while not code_ok:
                    code = await cli_handler.async_input('Please enter the code you received: ') 
                    try:
                        await client.sign_in(phone_number, code)
                        code_ok = True
                    except SessionPasswordNeededError:
                        main_logger.info("Two-factor authentication (2FA) is enabled.")
                        password_ok = False
                        while not password_ok:
                            password = await cli_handler.async_input('Please enter your 2FA password: ') 
                            try:
                                await client.sign_in(password=password)
                                password_ok = True
                                code_ok = True
                            except Exception as e_pass:
                                main_logger.error(f"2FA login failed: {e_pass}. Please try again.")
                    except Exception as e_code:
                        main_logger.error(f"Code verification failed: {e_code}. Please try again.")
            except Exception as e_send_code:
                main_logger.error(f"Failed to send code request: {e_send_code}")
                return
        me = await client.get_me()
        if me:
            username_str = f"@{me.username}" if me.username else "N/A"
            main_logger.info(f"Successfully signed in as: {me.first_name} (Username: {username_str})")
            main_logger.info("Handing control to CLI Handler...")
            await cli_handler.display_main_menu_loop(
                client, cache_manager, telegram_utils, settings_manager, event_handlers 
            )
            _app_is_exiting_cleanly = True 
        else:
            main_logger.error("Could not get user information after sign-in.")
    except ConnectionError:
        main_logger.error("Connection to Telegram failed. Please check your internet connection.")
    except SystemExit: 
        main_logger.info("SakaiBot is exiting via SystemExit (likely from signal handler).")
    except KeyboardInterrupt: 
        main_logger.warning("KeyboardInterrupt directly caught in main loop (should have been SIGINT).")
    except Exception as e:
        main_logger.error(f"An unexpected error occurred in main: {e}", exc_info=True)
    finally:
        main_logger.info("Main 'finally' block reached.")
        if not _app_is_exiting_cleanly: 
            save_current_settings_on_exit(source="main_finally")
        if hasattr(cli_handler, 'is_monitoring_active') and cli_handler.is_monitoring_active and \
           hasattr(cli_handler, 'registered_handler_info') and cli_handler.registered_handler_info:
            if client.is_connected(): 
                main_logger.info("Main finally: Ensuring monitoring is stopped.")
                handler_func, event_filter = cli_handler.registered_handler_info
                try:
                    client.remove_event_handler(handler_func, event_filter) 
                    cli_handler.is_monitoring_active = False 
                    main_logger.info("Main finally: Monitoring handler removed.")
                except Exception as e_final_stop:
                    main_logger.error(f"Main finally: Error stopping monitoring: {e_final_stop}")
        if client.is_connected():
            main_logger.info("Disconnecting client...")
            await client.disconnect() 
        main_logger.info("SakaiBot has been stopped.")

if __name__ == '__main__':
    signal.signal(signal.SIGINT, sigint_handler)
    loaded_config = load_config()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main(loaded_config))
    except SystemExit: 
        main_logger.info("SakaiBot exited cleanly via SystemExit after asyncio.run.")
    except KeyboardInterrupt: 
        main_logger.info("SakaiBot stopped by user (Ctrl+C at asyncio.run level).")
    finally:
        main_logger.info("Main __main__ finally: Ensuring event loop is closed.")
        if not loop.is_closed():
             loop.close()
