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
            msg = """
🤖 <b>SakaiBot - Complete Guide</b>

<i>Smart userbot with AI, image generation, voice, and monitoring</i>

<b>🎨 IMAGE GENERATION</b>
<code>/image=flux=your prompt here</code>
Generate images with FLUX model (fast, high quality)

<code>/image=sdxl=your prompt here</code>
Generate images with SDXL model (stable, detailed)

<i>• Prompts auto-enhanced by OpenRouter AI
• Max 1000 characters per prompt
• Rate limit: 10 requests per 60 seconds</i>

<b>🤖 AI COMMANDS</b>
<code>/prompt=your question</code>
Ask AI any question or give instructions

<code>/translate=en=text here</code>
Translate text to any language (en, fa, es, etc.)
<i>Can also reply to a message with /translate=lang</i>

<code>/analyze=100</code>
AI analyzes last 100 messages in chat
<i>Modes: /analyze=fun=50, /analyze=romance=200</i>

<code>/tellme=50=your question</code>
Ask AI about last 50 messages in chat

<b>🎧 VOICE & AUDIO</b>
<code>/tts=text to speak</code>
Convert text to speech (reply to message also works)
<i>Supports multiple voices and languages</i>

<code>/stt</code> (reply to voice message)
Transcribe voice to text + AI summary

<b>📋 USERBOT COMMANDS</b>
<code>/auth list</code> - View authorized users
<code>/auth add @user</code> - Authorize a user
<code>/auth remove @user</code> - Remove authorization

<code>/status</code> - Bot statistics & system info

<code>/help</code> - This comprehensive guide
<code>/help fa</code> - Persian version (نسخه فارسی)
<code>/help images</code> - Image generation details
<code>/help ai</code> - AI commands details
<code>/help voice</code> - Voice features details

<b>⚠️ LIMITATIONS & NOTES</b>
• Rate limit: 10 AI/image requests per 60 seconds
• Monitoring must be started from CLI (not Telegram)
• Only authorized users can use bot features
• Image generation requires configured worker URLs
• Max message history for analyze: 10,000 messages

<b>💡 TIPS</b>
• Use specific, detailed prompts for better images
• AI prompt enhancement works automatically
• Voice messages auto-transcribed if monitoring active
• Check /status for current bot configuration

<i>🔗 SakaiBot v2.0.0 | Powered by OpenRouter & Gemini</i>
"""
            await event.edit(msg, parse_mode='html')
        
        elif args == 'fa' or args == 'persian' or args == 'فارسی':
            # Persian version of help
            msg = """
🤖 <b>ساکای‌بات - راهنمای کامل</b>

<i>ربات هوشمند با قابلیت هوش مصنوعی، تولید تصویر و پردازش صوتی</i>

<b>🎨 تولید تصویر</b>
<code>/image=flux=توضیحات تصویر به فارسی یا انگلیسی</code>
تولید تصویر با مدل FLUX (سریع و با کیفیت بالا)

<code>/image=sdxl=توضیحات تصویر به فارسی یا انگلیسی</code>
تولید تصویر با مدل SDXL (پایدار و دقیق)

<i>• توضیحات به صورت خودکار با هوش مصنوعی بهبود می‌یابند
• حداکثر ۱۰۰۰ کاراکتر برای هر درخواست
• محدودیت: ۱۰ درخواست در هر ۶۰ ثانیه</i>

<b>🤖 دستورات هوش مصنوعی</b>
<code>/prompt=سوال یا دستور شما</code>
از هوش مصنوعی هر سوالی بپرسید یا دستوری بدهید

<code>/translate=fa=text here</code>
ترجمه متن به هر زبانی (فارسی، انگلیسی، اسپانیایی و...)
<i>می‌توانید روی یک پیام ریپلای کنید و /translate=fa بزنید</i>

<code>/analyze=100</code>
هوش مصنوعی آخرین ۱۰۰ پیام چت را تحلیل می‌کند
<i>حالت‌ها: /analyze=fun=50، /analyze=romance=200</i>

<code>/tellme=50=سوال شما</code>
از هوش مصنوعی درباره آخرین ۵۰ پیام چت سوال بپرسید

<b>🎧 صدا و گفتار</b>
<code>/tts=متن برای تبدیل به گفتار</code>
تبدیل متن به گفتار (روی پیام ریپلای هم کار می‌کند)
<i>از صداها و زبان‌های مختلف پشتیبانی می‌کند</i>

<code>/stt</code> (روی ویس پیام ریپلای کنید)
تبدیل گفتار به متن + خلاصه‌سازی با هوش مصنوعی

<b>📋 دستورات یوزربات</b>
<code>/auth list</code> - مشاهده کاربران مجاز
<code>/auth add @user</code> - اضافه کردن کاربر مجاز
<code>/auth remove @user</code> - حذف مجوز کاربر

<code>/status</code> - آمار ربات و اطلاعات سیستم

<code>/help</code> - این راهنمای کامل
<code>/help fa</code> - نسخه فارسی راهنما
<code>/help images</code> - جزئیات تولید تصویر
<code>/help ai</code> - جزئیات دستورات هوش مصنوعی
<code>/help voice</code> - جزئیات امکانات صوتی

<b>⚠️ محدودیت‌ها و نکات</b>
• محدودیت: ۱۰ درخواست هوش مصنوعی/تصویر در هر ۶۰ ثانیه
• مانیتورینگ باید از CLI راه‌اندازی شود (نه از تلگرام)
• فقط کاربران مجاز می‌توانند از امکانات استفاده کنند
• تولید تصویر نیاز به تنظیم worker URLs دارد
• حداکثر تاریخچه پیام برای تحلیل: ۱۰٬۰۰۰ پیام

<b>💡 نکات کاربردی</b>
• از توضیحات دقیق و مفصل برای تصاویر بهتر استفاده کنید
• بهبود خودکار توضیحات با هوش مصنوعی فعال است
• پیام‌های صوتی به صورت خودکار رونویسی می‌شوند (اگر مانیتورینگ فعال باشد)
• برای مشاهده تنظیمات فعلی /status را بزنید

<i>🔗 ساکای‌بات نسخه ۲.۰.۰ | قدرت گرفته از OpenRouter و Gemini</i>
"""
            await event.edit(msg, parse_mode='html')
        
        elif args == 'images' or args == 'image':
            msg = """
<b>🎨 Image Generation Guide</b>

<b>Basic Usage:</b>
<code>/image=flux=a beautiful sunset over mountains</code>
<code>/image=sdxl=cyberpunk city at night, neon lights</code>

<b>Models Available:</b>

<b>FLUX</b> - Fast, modern, high quality
• Best for: Creative, artistic images
• Speed: ~15-30 seconds
• Style: Modern, vibrant, detailed

<b>SDXL</b> - Stable, detailed, realistic
• Best for: Realistic photos, portraits
• Speed: ~20-40 seconds
• Style: Photorealistic, stable output

<b>Prompt Tips:</b>
✅ Be specific: "golden retriever puppy playing in grass"
✅ Add style: "..., photorealistic, 4k, detailed"
✅ Describe details: colors, lighting, composition
❌ Too vague: "dog"
❌ Too complex: 500+ words

<b>Features:</b>
• Automatic AI prompt enhancement (OpenRouter → Gemini fallback)
• Queue system handles multiple requests
• Real-time status updates
• Auto-cleanup of temporary files

<b>Rate Limits:</b>
• 10 requests per 60 seconds per user
• If limit exceeded, wait 60 seconds

<b>Troubleshooting:</b>
• "Rate limit exceeded" → Wait 60 seconds
• "Content filtered" → Try different prompt
• "Timeout" → Worker overloaded, try again
• "Invalid model" → Use 'flux' or 'sdxl' only

<i>Images are auto-deleted after sending to save space</i>
"""
            await event.edit(msg, parse_mode='html')
        
        elif args == 'ai':
            msg = """
<b>🤖 AI Commands Guide</b>

<b>1. PROMPT - General AI Queries</b>
<code>/prompt=what is quantum computing?</code>
<code>/prompt=write a poem about stars</code>
<code>/prompt=explain this code: [paste code]</code>

<i>Use for: Questions, explanations, creative writing</i>

<b>2. TRANSLATE - Language Translation</b>
<code>/translate=en=سلام دنیا</code>
<code>/translate=fa=Hello world</code>
<code>/translate=es,en=Hola amigo</code> (Spanish to English)

<i>Reply to any message with /translate=lang</i>

Supported languages:
• en (English), fa (Persian), es (Spanish)
• ar (Arabic), fr (French), de (German)
• zh (Chinese), ja (Japanese), ru (Russian)
• And many more...

<b>3. ANALYZE - Chat Analysis</b>
<code>/analyze=100</code> - Analyze last 100 messages
<code>/analyze=fun=50</code> - Fun analysis mode
<code>/analyze=romance=200</code> - Romance analysis
<code>/analyze=general=500</code> - General insights

<i>AI provides summary, themes, and insights</i>

<b>4. TELLME - Chat Q&A</b>
<code>/tellme=50=what topics were discussed?</code>
<code>/tellme=100=who talked the most?</code>
<code>/tellme=200=summarize the conversation</code>

<i>Ask questions about recent chat history</i>

<b>Rate Limits:</b>
All AI commands share: 10 requests per 60 seconds

<b>Max History:</b>
• Analyze: Up to 10,000 messages
• Tellme: Up to 10,000 messages

<i>Powered by OpenRouter & Google Gemini</i>
"""
            await event.edit(msg, parse_mode='html')
        
        elif args == 'voice':
            msg = """
<b>🎧 Voice & Audio Guide</b>

<b>TEXT-TO-SPEECH (TTS)</b>
<code>/tts=Hello, this is a test message</code>
<code>/tts=سلام، این یک پیام تست است</code>

<i>Or reply to any text message with:</i>
<code>/tts</code>

<b>Features:</b>
• Multiple voice options (Alloy, Echo, Fable, etc.)
• Supports multiple languages
• Queue system for multiple requests
• Real-time status updates

<b>SPEECH-TO-TEXT (STT)</b>
Reply to any voice message with:
<code>/stt</code>

<b>What you get:</b>
1. 📝 Transcribed text (accurate transcription)
2. 🔍 AI Summary & Analysis (key points, insights)

<i>Works with voice notes, audio files, and videos</i>

<b>Auto-Transcription:</b>
When monitoring is active, voice messages are automatically transcribed without needing /stt command.

<b>Supported Formats:</b>
• Voice notes (.ogg, .opus)
• Audio files (.mp3, .wav, .m4a)
• Video audio tracks (.mp4, .mkv)

<b>Rate Limits:</b>
• TTS: Shared 10 req/60s limit
• STT: No specific limit (uses AI quota)

<b>Quality Notes:</b>
• Clear audio = better transcription
• Background noise may affect accuracy
• Long files may take time to process

<i>Powered by advanced AI speech models</i>
"""
            await event.edit(msg, parse_mode='html')
        
        elif args == 'auth':
            msg = """
<b>🔐 Authorization Commands</b>

<b>📋 LIST USERS</b>
<code>/auth list</code>
View all authorized users with:
• Full name and username
• User ID (for reference)
• Total count

<b>➕ ADD USER</b>
<code>/auth add @username</code>
<code>/auth add 123456789</code>

Supports both:
• Username format: @username
• Direct user ID: 123456789

<b>➖ REMOVE USER</b>
<code>/auth remove @username</code>
<code>/auth remove 123456789</code>

Remove authorization from user

<b>How Authorization Works:</b>
• Only authorized users can use bot commands
• Unauthorized users are ignored
• Admin (you) has full access always
• Changes save immediately

<b>Use Cases:</b>
• Allow trusted friends to use bot
• Revoke access when needed
• Control who can generate images
• Manage AI command access

<i>⚠️ Only add users you trust</i>
"""
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
