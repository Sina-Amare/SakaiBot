"""Sample test data and fixtures."""

# Sample translation commands
SAMPLE_TRANSLATION_COMMANDS = [
    {
        "command": "en Hello world",
        "target": "en",
        "source": "auto",
        "text": "Hello world",
        "description": "Basic translation command"
    },
    {
        "command": "en,fa Hello world",
        "target": "en",
        "source": "fa",
        "text": "Hello world",
        "description": "Translation with source language"
    },
    {
        "command": "en=Hello world",
        "target": "en",
        "source": "auto",
        "text": "Hello world",
        "description": "Translation with equals format"
    },
    {
        "command": "en,fa=Hello world",
        "target": "en",
        "source": "fa",
        "text": "Hello world",
        "description": "Translation with source language and equals format"
    },
    {
        "command": "fa سلام دنیا",
        "target": "fa",
        "source": "auto",
        "text": "سلام دنیا",
        "description": "Persian translation command"
    }
]

# Sample AI responses
SAMPLE_AI_RESPONSES = [
    {
        "response": "Hello world (هلو ورلد)",
        "translation": "Hello world",
        "pronunciation": "هلو ورلد",
        "description": "Simple translation with pronunciation"
    },
    {
        "response": """Translation: Hello world
Phonetic: (هلو ورلد)""",
        "translation": "Hello world",
        "pronunciation": "هلو ورلد",
        "description": "Structured AI response"
    },
    {
        "response": """Detected Language: English
Translation: Hello world
Phonetic: (هلو ورلد)""",
        "translation": "Hello world",
        "pronunciation": "هلو ورلد",
        "description": "AI response with language detection"
    }
]

# Sample STT text formats
SAMPLE_STT_TEXTS = [
    {
        "input": "[NOTES] **متن پیاده‌سازی شده:**\nسلام دنیا\n[SEARCH] **جمع‌بندی و تحلیل هوش مصنوعی:**\nاین یک پیام ساده است",
        "output": "سلام دنیا",
        "description": "Standard STT format"
    },
    {
        "input": "[NOTES] **متن پیاده‌سازی شده:**\nچطور هستی؟ خوبم، ممنون.\nممنون که پرسیدی.\n\n[SEARCH] **جمع‌بندی و تحلیل هوش مصنوعی:**\nمکالمه دوستانه",
        "output": "چطور هستی؟ خوبم، ممنون.\nمنون که پرسیدی.",
        "description": "Multi-line STT format"
    }
]

# Valid language codes
VALID_LANGUAGE_CODES = [
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("fa", "Persian"),
    ("ar", "Arabic"),
    ("zh", "Chinese"),
    ("ja", "Japanese"),
    ("ko", "Korean")
]

# Valid language names
VALID_LANGUAGE_NAMES = [
    ("english", "en"),
    ("spanish", "es"),
    ("farsi", "fa"),
    ("persian", "fa"),
    ("français", "fr"),
    ("deutsch", "de")
]

# Invalid language codes
INVALID_LANGUAGE_CODES = [
    "",
    "invalid",
    "xyz",
    "123",
    "engli"  # Partial match test case
]
