# Persian (Farsi) Language Features 🇮🇷 - Enhanced Edition

SakaiBot includes comprehensive Persian language support with specialized prompts, analysis tools, and voice capabilities. Now enhanced with witty, sarcastic humor inspired by shows like The Office and adult comedies. All Persian functionality has been carefully preserved and refined with prompt engineering best practices.

## Table of Contents
- [Overview](#overview)
- [Persian Prompts](#persian-prompts)
- [Translation Features](#translation-features)
- [Conversation Analysis](#conversation-analysis)
- [Voice Support](#voice-support)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)

## Overview

SakaiBot's Persian features are designed to provide seamless support for Persian-speaking users with personality:

- **Full Persian translation** with phonetic pronunciation and subtle sarcasm
- **Persian conversation analysis** with The Office-style commentary
- **Persian voice support** (TTS and STT) with personality-matched voices
- **Persian-aware prompts** with wit, humor, and professional edge
- **Persian error and success messages** that actually make you smile
- **Special responses** for different chat scenarios (arguments, love, deadlines)
- **Multiple analysis personalities** (Monday blues, Friday vibes, sarcastic mode)

## Persian Prompts

All Persian prompts are centralized in `src/ai/persian_prompts.py` for easy maintenance and customization.

### Available Prompt Categories

1. **Translation Prompts**
   - Automatic language detection
   - Persian phonetic pronunciation using Persian alphabet
   - Bidirectional translation (Persian ↔ Other languages)

2. **Conversation Analysis**
   - Comprehensive Persian analysis template
   - Cultural context awareness
   - Emotion and sentiment analysis with Persian descriptions

3. **Question Answering**
   - Persian context-aware responses
   - Professional yet friendly Persian tone
   - Chat history analysis in Persian

4. **Voice Message Summarization**
   - Persian voice transcription summaries
   - Automatic language detection for summaries

## Translation Features

### Phonetic Support

When translating to/from Persian, the bot provides phonetic pronunciation:

```
Input: "Hello, how are you?"
Output:
Persian: سلام، حال شما چطور است؟
Phonetic: (سلام، هال شوما چِطور است؟)
```

### Usage via CLI

```bash
# Translate to Persian
sakaibot ai translate "Hello world" fa

# Translate from Persian with auto-detection
sakaibot ai translate "سلام دنیا" en
```

## Conversation Analysis

### Persian Analysis Template (The Office Style)

The bot uses a comprehensive Persian template with sarcastic wit:

1. **🎬 خلاصه اجرایی** ("What was today's episode about?")
   - Brief, honest summary like explaining to a friend who doesn't want to read the whole chat
   - If nothing important: "Nothing special, just repetitive talk"

2. **🎯 موضوعات اصلی** (What they actually said, not what they thought they were saying)
   - Main topics with enough detail to understand, but not so much you fall asleep
   - Side notes about weird things that came out of nowhere

3. **😂 تحلیل روانشناسی اجتماعی** ("What's wrong with these people?")
   - Honest description of conversation atmosphere
   - Character profiles ("the know-it-all", "the one who just says OK")
   - Golden moments worth recording

4. **📋 کارها و تصمیمات** (Things that will probably be forgotten)
   - Definite tasks (that might actually happen... maybe)
   - Semi-definite ("we'll talk about it later")
   - Wishes and dreams (things prefaced with "I wish" or "maybe")

5. **🔮 پیش‌بینی آینده** (Future Predictions)
   - Probability something actually gets done: X%
   - Probability this discussion repeats: X%
   - Probability everyone forgets: X%

6. **🎭 جمع‌بندی نهایی** (Final Wrap-up)
   - Like The Office endings: bitter truth but somehow comforting
   - Camera look and shoulder shrug included

### Usage Example

```bash
# Analyze last 100 messages in Persian
sakaibot pv analyze --type persian_detailed --count 100
```

## Voice Support

### Text-to-Speech (TTS)

SakaiBot supports Persian TTS with multiple voices:

- **fa-IR-DilaraNeural** (Female, default)
- **fa-IR-FaridNeural** (Male)

### Speech-to-Text (STT)

Persian voice messages are automatically transcribed using:
- Language code: `fa-IR`
- Google Speech Recognition for Persian

### Voice Commands

```bash
# Test Persian TTS
sakaibot ai tts "سلام، این یک آزمایش است" --voice fa-IR-DilaraNeural

# Transcribe Persian audio
sakaibot ai stt /path/to/persian_audio.wav
```

## Configuration

### Environment Variables

```env
# Set default language for analysis
DEFAULT_ANALYSIS_LANGUAGE=fa

# Persian TTS voice selection
DEFAULT_TTS_VOICE=fa-IR-DilaraNeural

# Enable Persian-first mode
PERSIAN_MODE=true
```

### Persian Commands Mapping

The bot recognizes both Persian and English commands:

```python
PERSIAN_COMMANDS = {
    "help": ["راهنما", "کمک"],
    "translate": ["ترجمه"],
    "analyze": ["تحلیل", "آنالیز"],
    "summarize": ["خلاصه", "چکیده"],
    "settings": ["تنظیمات"],
    "start": ["شروع"],
    "stop": ["توقف", "پایان"]
}
```

## Usage Examples

### 1. Persian Translation with Phonetics

```python
# In your code
from src.ai import get_ai_processor

ai = get_ai_processor()
result = await ai.translate_text(
    text="Machine learning is fascinating",
    target_language="fa"
)
# Output: 
# Persian: یادگیری ماشین جذاب است
# Phonetic: (یادگیری ماشین جَذّاب است)
```

### 2. Persian Conversation Analysis

```python
# Analyze chat messages in Persian
analysis = await ai.analyze_messages(
    messages=chat_history,
    analysis_type="persian_detailed"
)
# Returns comprehensive Persian analysis following the template
```

### 3. Persian Voice Message Processing

```python
# Process Persian voice message
transcription = await ai.transcribe_voice_to_text(audio_path)
summary = await ai.analyze_messages(
    messages=[{"text": transcription}],
    analysis_type="voice_summary"
)
# Returns Persian summary if original was Persian
```

### 4. CLI Commands

```bash
# Basic Persian operations
sakaibot ai translate "Good morning" fa
sakaibot ai prompt "به فارسی توضیح بده که هوش مصنوعی چیست"

# Persian conversation analysis
sakaibot pv analyze --lang fa --count 50

# Persian TTS generation
sakaibot ai tts "درود بر شما" --output greeting.mp3
```

## Error Messages (With Personality)

Error messages that actually make you smile:

- **کلید API نداریم. بدون کلید، من فقط یه برنامه بی‌فایده‌ام 🔑** - No API key (I'm useless without it)
- **مدل AI انتخاب نشده. انگار می‌خواید با هوای خالی کار کنم** - No AI model (working with thin air?)
- **پیامی نیست که پردازش کنم. یه چیزی بدید دیگه!** - No messages (give me something!)
- **اینترنت قطعه یا فیلتر شکن یادتون رفته روشن کنید؟** - Network error (VPN forgotten?)
- **آروم‌تر! API داره از دستمون فرار می‌کنه** - Rate limit (slow down!)

## Success Messages (Celebrating Small Wins)

Success messages with attitude:

- **API کانفیگ شد! حالا می‌تونیم کار کنیم 🚀** - API configured (now we can work!)
- **تحلیل تموم شد. نتیجه: همه دارن وقتشونو تلف می‌کنن 📊** - Analysis done (everyone's wasting time)
- **ترجمه انجام شد. Google Translate: 0 - ما: 1 ✅** - Translation done (we beat Google)
- **کش پاک شد. حافظه‌م مثل روز اول شد 🧹** - Cache cleared (memory like day one)
- **در حال مانیتور کردن... چشمام رو همه جا دارم 👀** - Monitoring (eyes everywhere)

## Preserving Custom Persian Prompts

If you have custom Persian prompts, add them to `src/ai/persian_prompts.py`:

```python
# Add your custom prompts
MY_CUSTOM_PROMPT = """
شما یک دستیار هوشمند هستید که...
[Your custom Persian prompt here]
"""

# Use in your code
from src.ai.persian_prompts import MY_CUSTOM_PROMPT
```

## Troubleshooting

### Persian Text Not Displaying Correctly

1. Ensure your terminal supports UTF-8 encoding
2. On Windows, use: `chcp 65001`
3. Check font support for Persian characters

### TTS Not Working

1. Verify edge-tts is installed: `pip install edge-tts`
2. Check internet connection (required for edge-tts)
3. Test with: `sakaibot ai test --persian`

### STT Recognition Issues

1. Ensure audio quality is good
2. Verify language is set to `fa-IR`
3. Check Google Speech API availability

## Contributing

To add or improve Persian features:

1. All Persian prompts go in `src/ai/persian_prompts.py`
2. Follow the existing naming convention
3. Test with Persian text including special characters
4. Ensure bidirectional text (RTL) support

## Support

For Persian-specific issues or feature requests:
- Open an issue with tag `persian-feature`
- Include sample Persian text for testing
- Specify expected behavior vs actual result