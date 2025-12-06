"""Self-command handlers for userbot commands."""

from typing import Optional
from telethon import events
from telethon.tl.types import Message

from ...core.settings import SettingsManager
from ..user_verifier import TelegramUserVerifier
from ...utils.logging import get_logger

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
    """Handle /help command - comprehensive bot usage guide."""
    try:
        if not args:
            # Main help message
            msg = """🤖 <b>SakaiBot Help</b>
<i>Your AI-powered userbot assistant</i>

━━━━━━━━━━━━━━━━━━━━━━

⚡ <b>QUICK START</b>
<code>/prompt=Hello!</code> → Chat with AI
<code>/image=flux/sunset</code> → Generate image
<code>/analyze=100</code> → Analyze chat
<code>/help fa</code> → راهنمای فارسی

━━━━━━━━━━━━━━━━━━━━━━

🎨 <b>IMAGE GENERATION</b>

<code>/image=flux/your prompt</code>
Fast, high-quality artistic images

<code>/image=sdxl/your prompt</code>
Stable, photorealistic images

<i>💡 Prompts auto-enhanced by AI</i>

━━━━━━━━━━━━━━━━━━━━━━

🤖 <b>AI COMMANDS</b>

<code>/prompt=question</code>
Ask anything, get AI response
  ├ <code>=think</code> → Deep reasoning
  └ <code>=web</code> → Web search

<code>/translate=en=متن</code>
Translate to any language

<code>/analyze=100</code> → Persian (default)
<code>/analyze=100 en</code> → English output
  ├ <code>=general</code> → Formal analysis
  ├ <code>=fun</code> → Comedy roast
  ├ <code>=romance</code> → Relationship
  └ <code>=think</code> → Deep analysis

<code>/tellme=50=question</code>
Ask about chat history
  ├ <code>=think</code> → Deep reasoning
  └ <code>=web</code> → Web search


━━━━━━━━━━━━━━━━━━━━━━

🎧 <b>VOICE & AUDIO</b>

<code>/tts=text here</code>
Text to speech

<code>/stt</code> <i>(reply to voice)</i>
Transcribe + AI summary

━━━━━━━━━━━━━━━━━━━━━━

🔐 <b>MANAGEMENT</b>

<code>/auth list</code> → View users
<code>/auth add @user</code> → Authorize
<code>/auth remove @user</code> → Revoke
<code>/group</code> → Manage categorization
<code>/status</code> → Bot stats

━━━━━━━━━━━━━━━━━━━━━━

📚 <b>DETAILED GUIDES</b>
<code>/help images</code> • <code>/help ai</code>
<code>/help voice</code> • <code>/help auth</code>
<code>/help group</code> • <code>/help fa</code>

━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>LIMITS</b>
• 10 requests per 60 seconds
• Max 10,000 messages for analyze

<i>🔗 SakaiBot v2.0 • OpenRouter + Gemini</i>"""
            await event.edit(msg, parse_mode='html')
        
        elif args == 'fa' or args == 'persian' or args == 'فارسی':
            # Persian version of help
            msg = """🤖 <b>راهنمای ساکای‌بات</b>
<i>دستیار هوشمند تلگرام شما</i>

━━━━━━━━━━━━━━━━━━━━━━

⚡ <b>شروع سریع</b>
<code>/prompt=سلام!</code> ← گفتگو با هوش مصنوعی
<code>/image=flux=غروب</code> ← ساخت تصویر
<code>/help</code> ← English Guide

━━━━━━━━━━━━━━━━━━━━━━

🎨 <b>تولید تصویر</b>

<code>/image=flux=توضیحات</code>
تصاویر هنری سریع و باکیفیت

<code>/image=sdxl=توضیحات</code>
تصاویر واقع‌گرایانه و دقیق

<i>💡 توضیحات خودکار بهبود می‌یابند</i>

━━━━━━━━━━━━━━━━━━━━━━

🤖 <b>دستورات هوش مصنوعی</b>

<code>/prompt=سوال</code>
پاسخ هوش مصنوعی
  ├ <code>=think</code> ← تفکر عمیق
  └ <code>=web</code> ← جستجوی وب

<code>/translate=fa=text</code>
ترجمه به هر زبانی

<code>/analyze=100</code>
تحلیل پیام‌های چت
  ├ <code>=general</code> ← تحلیل جامع
  ├ <code>=fun</code> ← سبک طنز
  └ <code>=romance</code> ← تحلیل رابطه

<code>/tellme=50=سوال</code>
سوال درباره تاریخچه چت
  ├ <code>=think</code> ← تفکر عمیق
  └ <code>=web</code> ← جستجوی وب

━━━━━━━━━━━━━━━━━━━━━━

🎧 <b>صدا و گفتار</b>

<code>/tts=متن</code>
تبدیل متن به گفتار

<code>/stt</code> <i>(ریپلای روی ویس)</i>
رونویسی + خلاصه‌سازی

━━━━━━━━━━━━━━━━━━━━━━

🔐 <b>مدیریت</b>

<code>/auth list</code> ← لیست کاربران
<code>/auth add @user</code> ← افزودن
<code>/auth remove @user</code> ← حذف
<code>/status</code> ← آمار ربات

━━━━━━━━━━━━━━━━━━━━━━

📚 <b>راهنماهای تفصیلی</b>
<code>/help images</code> • <code>/help ai</code>
<code>/help voice</code> • <code>/help auth</code>

━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>محدودیت‌ها</b>
• ۱۰ درخواست در هر ۶۰ ثانیه
• حداکثر ۱۰٬۰۰۰ پیام برای تحلیل

<i>🔗 ساکای‌بات v2.0 • OpenRouter + Gemini</i>"""
            await event.edit(msg, parse_mode='html')
        
        elif args == 'images' or args == 'image':
            msg = """🎨 <b>Image Generation Guide</b>

━━━━━━━━━━━━━━━━━━━━━━

📝 <b>BASIC USAGE</b>

<code>/image=flux=a sunset over mountains</code>
<code>/image=sdxl=cyberpunk city, neon lights</code>

━━━━━━━━━━━━━━━━━━━━━━

🔥 <b>FLUX MODEL</b>
<i>Fast • Artistic • Creative</i>

• Speed: ~15-30 seconds
• Best for: Art, creative concepts
• Style: Vibrant, modern, detailed

⚡ <b>SDXL MODEL</b>
<i>Stable • Realistic • Detailed</i>

• Speed: ~20-40 seconds
• Best for: Photos, portraits
• Style: Photorealistic, natural

━━━━━━━━━━━━━━━━━━━━━━

💡 <b>PROMPT TIPS</b>

✅ <b>Do:</b>
• Be specific: <code>golden retriever puppy in grass</code>
• Add style: <code>..., photorealistic, 4k</code>
• Describe: colors, lighting, mood

❌ <b>Don't:</b>
• Too vague: <code>dog</code>
• Too long: 500+ words

━━━━━━━━━━━━━━━━━━━━━━

⚙️ <b>FEATURES</b>

• 🪄 AI prompt enhancement
• 📊 Queue system
• 🔄 Real-time updates
• 🗑️ Auto-cleanup

━━━━━━━━━━━━━━━━━━━━━━

🔧 <b>TROUBLESHOOTING</b>

<code>Rate limit</code> → Wait 60 seconds
<code>Content filtered</code> → Change prompt
<code>Timeout</code> → Try again later
<code>Invalid model</code> → Use flux or sdxl

━━━━━━━━━━━━━━━━━━━━━━

<i>📊 Limit: 10 requests per 60 seconds</i>"""
            await event.edit(msg, parse_mode='html')
        
        elif args == 'ai':
            msg = """🤖 <b>AI Commands Guide</b>

━━━━━━━━━━━━━━━━━━━━━━

💬 <b>1. PROMPT</b>
<i>Ask AI anything</i>

<code>/prompt=what is quantum computing?</code>
<code>/prompt=write a poem about stars</code>
<code>/prompt=explain this code: [paste]</code>

<b>Flags:</b>
<code>=think</code> → Deep reasoning mode
<code>=web</code> → Web search enabled

━━━━━━━━━━━━━━━━━━━━━━

🌐 <b>2. TRANSLATE</b>
<i>Translate to any language</i>

<code>/translate=en=سلام دنیا</code>
<code>/translate=fa=Hello world</code>

<i>💡 Reply to any message with /translate=lang</i>

<b>Languages:</b> en, fa, es, ar, fr, de, zh, ja, ru...

━━━━━━━━━━━━━━━━━━━━━━

📊 <b>3. ANALYZE</b>
<i>Chat analysis & insights</i>

<b>Basic (Persian output):</b>
<code>/analyze=100</code> → Last 100 messages
<code>/analyze=fun=500</code> → Fun/comedy style
<code>/analyze=romance=200</code> → Relationship

<b>English output:</b>
<code>/analyze=100 en</code>
<code>/analyze=fun=500 en</code>
<code>/analyze=romance=200 en</code>

<b>With thinking mode:</b>
<code>/analyze=fun=3000=think</code>
<code>/analyze=500=think en</code>

<b>Modes:</b>
• <code>general</code> → Professional analysis
• <code>fun</code> → Comedy roast
• <code>romance</code> → Relationship signals

━━━━━━━━━━━━━━━━━━━━━━

❓ <b>4. TELLME</b>
<i>Ask about chat history</i>

<code>/tellme=50=what topics discussed?</code>
<code>/tellme=100=who talked most?</code>
<code>/tellme=200=summarize</code>

<b>Flags:</b> <code>=think</code> or <code>=web</code>

━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>LIMITS</b>
• 10 requests per 60 seconds
• Max 10,000 messages for analyze

<i>🔗 OpenRouter + Google Gemini</i>"""
            await event.edit(msg, parse_mode='html')
        
        elif args == 'voice':
            msg = """🎧 <b>Voice & Audio Guide</b>

━━━━━━━━━━━━━━━━━━━━━━

🔊 <b>TEXT-TO-SPEECH (TTS)</b>
<i>Convert text to voice</i>

<code>/tts=Hello world!</code>
<code>/tts=سلام دنیا!</code>

<i>💡 Or reply to any message with /tts</i>

<b>Voice Options:</b>
Alloy • Echo • Fable • Onyx • Nova • Shimmer

━━━━━━━━━━━━━━━━━━━━━━

🎤 <b>SPEECH-TO-TEXT (STT)</b>
<i>Transcribe voice messages</i>

Reply to any voice with:
<code>/stt</code>

<b>You Get:</b>
📝 Accurate transcription
🔍 AI summary & insights

━━━━━━━━━━━━━━━━━━━━━━

📁 <b>SUPPORTED FORMATS</b>

• Voice: .ogg, .opus
• Audio: .mp3, .wav, .m4a
• Video: .mp4, .mkv

━━━━━━━━━━━━━━━━━━━━━━

💡 <b>TIPS</b>

• Clear audio = better results
• Monitoring → auto-transcribe
• Long files take more time

━━━━━━━━━━━━━━━━━━━━━━

<i>🔗 Powered by AI speech models</i>"""
            await event.edit(msg, parse_mode='html')
        
        elif args == 'auth':
            msg = """🔐 <b>Authorization Guide</b>

━━━━━━━━━━━━━━━━━━━━━━

📋 <b>VIEW USERS</b>

<code>/auth list</code>

Shows:
• Name & username
• User ID
• Total count

━━━━━━━━━━━━━━━━━━━━━━

➕ <b>ADD USER</b>

<code>/auth add @username</code>
<code>/auth add 123456789</code>

━━━━━━━━━━━━━━━━━━━━━━

➖ <b>REMOVE USER</b>

<code>/auth remove @username</code>
<code>/auth remove 123456789</code>

━━━━━━━━━━━━━━━━━━━━━━

⚙️ <b>HOW IT WORKS</b>

✅ Authorized → Can use all commands
❌ Unauthorized → Ignored
👑 You → Always full access
💾 Changes → Save instantly

━━━━━━━━━━━━━━━━━━━━━━

<i>⚠️ Only add users you trust!</i>"""
            await event.edit(msg, parse_mode='html')
        
        elif args == 'group':
            msg = """📂 <b>Group Categorization Guide</b>

━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>WHAT IS CATEGORIZATION?</b>

Forward messages to specific topics in a group
based on categories you define.

━━━━━━━━━━━━━━━━━━━━━━

📋 <b>COMMANDS</b>

<code>/group list</code>
View all configured groups

<code>/group select</code>
Select target group for forwarding

<code>/group topics</code>
List topics in selected group

<code>/group map</code>
Configure category → topic mapping

<code>/group clear</code>
Clear all mappings

━━━━━━━━━━━━━━━━━━━━━━

🔧 <b>SETUP WORKFLOW</b>

1. <code>/group list</code> - See your groups
2. <code>/group select</code> - Pick target group
3. <code>/group topics</code> - View available topics
4. <code>/group map</code> - Create category mappings
5. Done! Reply to messages with category name

━━━━━━━━━━━━━━━━━━━━━━

💡 <b>USAGE EXAMPLE</b>

1. Set up mapping: "meme" → "Memes" topic
2. Reply to a message: <code>meme</code>
3. Bot forwards to Memes topic

━━━━━━━━━━━━━━━━━━━━━━

<i>📡 Requires a group with forum topics enabled</i>"""
            await event.edit(msg, parse_mode='html')
        
        else:
            # Unknown help topic
            msg = f"""
❌ <b>Unknown help topic:</b> <code>{args}</code>

<b>Available help topics:</b>
<code>/help</code> - Main guide (all features)
<code>/help images</code> - Image generation
<code>/help ai</code> - AI commands
<code>/help voice</code> - Voice features
<code>/help auth</code> - Authorization
<code>/help group</code> - Categorization

<i>Type /help to see the complete guide</i>
"""
            await event.edit(msg, parse_mode='html')
    
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
        
        msg = f"""🤖 <b>SakaiBot Status</b>

━━━━━━━━━━━━━━━━━━━━━━

👤 <b>ACCOUNT</b>
{bot_name}

━━━━━━━━━━━━━━━━━━━━━━

📊 <b>STATISTICS</b>

🔐 Authorized Users: <code>{auth_count}</code>
📡 Monitoring: {monitoring_status}
💬 Target: <code>{group_info}</code>

━━━━━━━━━━━━━━━━━━━━━━

💻 <b>SYSTEM</b>

🖥️ CPU: <code>{cpu_percent}%</code>
🧠 RAM: <code>{memory.percent}%</code>
📟 OS: <code>{platform.system()}</code>

━━━━━━━━━━━━━━━━━━━━━━

<i>⏱️ {datetime.now().strftime('%H:%M:%S')}</i>"""
        await event.edit(msg, parse_mode='html')
    
    except Exception as e:
        logger.error(f"Error in /status command: {e}", exc_info=True)
        await event.edit(f"❌ Error: {str(e)}", parse_mode='html')
