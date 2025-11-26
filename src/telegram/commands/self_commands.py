"""Self-command handlers for userbot commands."""

from typing import Optional
from telethon import events
from telethon.tl.types import Message

from ..core.settings import SettingsManager
from ..telegram.user_verifier import TelegramUserVerifier
from ..utils.logging import get_logger

logger = get_logger(__name__)


async def handle_auth_command(event: events.NewMessage.Event, args: str):
    """Handle /auth command.
    
    Usage:
        /auth list - List all authorized users
        /auth add @username - Add user by username
        /auth add 123456789 - Add user by ID
        /auth remove @username - Remove user
    """
    try:
        parts = args.split(maxsplit=1) if args else []
        subcommand = parts[0] if parts else 'list'
        
        settings_manager = SettingsManager()
        settings = settings_manager.load_user_settings()
        auth_pvs = settings.get('directly_authorized_pvs', [])
        
        if subcommand == 'list':
            # Format and display authorized users
            if not auth_pvs:
                await event.edit("🔐 <b>Authorized Users</b>\n\nNo authorized users.", parse_mode='html')
                return
            
            msg = "🔐 <b>Authorized Users</b>\n\n"
            
            # Get user details for each ID
            for i, user_id in enumerate(auth_pvs, 1):
                try:
                    user = await event.client.get_entity(user_id)
                    display_name = user.first_name
                    if user.last_name:
                        display_name += f" {user.last_name}"
                    username = f"@{user.username}" if user.username else "N/A"
                    msg += f"{i}. {display_name} ({username})\n"
                    msg += f"   <code>{user_id}</code>\n\n"
                except Exception as e:
                    msg += f"{i}. <code>{user_id}</code>\n   (Details unavailable)\n\n"
            
            msg += f"<i>Total: {len(auth_pvs)} users</i>"
            await event.edit(msg, parse_mode='html')
        
        elif subcommand == 'add':
            identifier = parts[1] if len(parts) > 1 else None
            if not identifier:
                await event.edit("❌ Usage: <code>/auth add @username</code> or <code>/auth add 123456789</code>", parse_mode='html')
                return
            
            # Verify user
            verifier = TelegramUserVerifier(event.client)
            user_info = await verifier.verify_user_by_identifier(identifier)
            
            if not user_info:
                await event.edit(f"❌ User not found: {identifier}", parse_mode='html')
                return
            
            if user_info['id'] in auth_pvs:
                await event.edit(f"⚠️ {user_info['display_name']} is already authorized", parse_mode='html')
                return
            
            # Add to authorized list
            auth_pvs.append(user_info['id'])
            settings['directly_authorized_pvs'] = auth_pvs
            settings_manager.save_user_settings(settings)
            
            username_str = f"@{user_info.get('username', 'N/A')}"
            await event.edit(
                f"✅ <b>Authorized</b>\n\n"
                f"👤 {user_info['display_name']}\n"
                f"🔗 {username_str}\n"
                f"🆔 <code>{user_info['id']}</code>\n\n"
                f"<i>Total authorized: {len(auth_pvs)}</i>",
                parse_mode='html'
            )
        
        elif subcommand == 'remove':
            identifier = parts[1] if len(parts) > 1 else None
            if not identifier:
                await event.edit("❌ Usage: <code>/auth remove @username</code> or <code>/auth remove 123456789</code>", parse_mode='html')
                return
            
            # Verify user
            verifier = TelegramUserVerifier(event.client)
            user_info = await verifier.verify_user_by_identifier(identifier)
            
            if not user_info:
                await event.edit(f"❌ User not found: {identifier}", parse_mode='html')
                return
            
            if user_info['id'] not in auth_pvs:
                await event.edit(f"⚠️ {user_info['display_name']} is not authorized", parse_mode='html')
                return
            
            # Remove from authorized list
            auth_pvs.remove(user_info['id'])
            settings['directly_authorized_pvs'] = auth_pvs
            settings_manager.save_user_settings(settings)
            
            username_str = f"@{user_info.get('username', 'N/A')}"
            await event.edit(
                f"🗑️ <b>Removed Authorization</b>\n\n"
                f"👤 {user_info['display_name']}\n"
                f"🔗 {username_str}\n"
                f"🆔 <code>{user_info['id']}</code>\n\n"
                f"<i>Total authorized: {len(auth_pvs)}</i>",
                parse_mode='html'
            )
        
        else:
            await event.edit(
                "❌ Unknown subcommand\n\n"
                "<b>Usage:</b>\n"
                "<code>/auth list</code>\n"
                "<code>/auth add @username</code>\n"
                "<code>/auth remove @username</code>",
                parse_mode='html'
            )
    
    except Exception as e:
        logger.error(f"Error in /auth command: {e}", exc_info=True)
        await event.edit(f"❌ Error: {str(e)}", parse_mode='html')


async def handle_help_command(event: events.NewMessage.Event, args: str):
    """Handle /help command."""
    try:
        if not args:
            # Show all commands
            msg = """
🤖 <b>SakaiBot Self-Commands</b>

<b>📋 AUTHORIZATION</b>
<code>/auth list</code> - View authorized users
<code>/auth add @user</code> - Add authorized user  
<code>/auth remove @user</code> - Remove user

<b>⚙️ STATUS</b>
<code>/status</code> - Bot statistics

<b>❓ HELP</b>
<code>/help</code> - This message
<code>/help auth</code> - Help for auth commands

<i>💡 All existing commands (/tts, /translate, /prompt, etc.) still work!</i>
"""
            await event.edit(msg, parse_mode='html')
        elif args == 'auth':
            msg = """
<b>Authorization Commands</b>

<code>/auth list</code>
View all authorized users with details

<code>/auth add @username</code>
<code>/auth add 123456789</code>
Add a user to authorized list
Supports username or user ID

<code>/auth remove @username</code>
<code>/auth remove 123456789</code>
Remove a user from authorized list

<i>Authorized users can interact with the bot</i>
"""
            await event.edit(msg, parse_mode='html')
        else:
            await event.edit(f"❌ No help available for: {args}", parse_mode='html')
    
    except Exception as e:
        logger.error(f"Error in /help command: {e}", exc_info=True)
        await event.edit(f"❌ Error: {str(e)}", parse_mode='html')


async def handle_status_command(event: events.NewMessage.Event):
    """Handle /status command."""
    try:
        import platform
        import psutil
        from datetime import datetime
        
        settings_manager = SettingsManager()
        settings = settings_manager.load_user_settings()
        
        # Get bot info
        me = await event.client.get_me()
        bot_name = me.first_name
        
        # Get system info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Get authorized users count
        auth_count = len(settings.get('directly_authorized_pvs', []))
        
        # Get monitoring status
        monitoring = settings.get('is_monitoring_active', False)
        monitoring_status = "🟢 Active" if monitoring else "🔴 Inactive"
        
        # Get target group
        target_group = settings.get('selected_target_group')
        group_info = target_group.get('title', 'None') if target_group else 'None'
        
        msg = f"""
🤖 <b>SakaiBot Status</b>

<b>👤 Bot Account</b>
{bot_name}

<b>📊 Statistics</b>
Authorized Users: {auth_count}
Monitoring: {monitoring_status}
Target Group: {group_info}

<b>💻 System</b>
CPU: {cpu_percent}%
Memory: {memory.percent}%
Platform: {platform.system()} {platform.release()}

<i>Updated: {datetime.now().strftime('%H:%M:%S')}</i>
"""
        await event.edit(msg, parse_mode='html')
    
    except Exception as e:
        logger.error(f"Error in /status command: {e}", exc_info=True)
        await event.edit(f"❌ Error: {str(e)}", parse_mode='html')
