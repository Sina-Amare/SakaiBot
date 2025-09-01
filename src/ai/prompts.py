"""Prompt templates and prompt management for AI interactions.

This module centralizes all prompt templates used in the application,
providing a clean interface for prompt generation and customization.
"""

from typing import Dict, Any, Optional
from string import Template

from src.core.constants import LANGUAGES


class PromptTemplate:
    """Base class for prompt templates with safe substitution."""
    
    def __init__(self, template: str):
        """Initialize prompt template.
        
        Args:
            template: Template string with $variable placeholders
        """
        self.template = Template(template)
    
    def render(self, **kwargs: Any) -> str:
        """Render template with provided variables.
        
        Args:
            **kwargs: Variables to substitute in template
            
        Returns:
            str: Rendered template
            
        Raises:
            KeyError: If required variables are missing
        """
        return self.template.substitute(**kwargs)
    
    def safe_render(self, **kwargs: Any) -> str:
        """Safely render template, leaving missing variables as-is.
        
        Args:
            **kwargs: Variables to substitute in template
            
        Returns:
            str: Rendered template with unmatched variables left as placeholders
        """
        return self.template.safe_substitute(**kwargs)


class TranslationPrompts:
    """Prompt templates for translation functionality."""
    
    AUTO_DETECT_TEMPLATE = PromptTemplate(
        "Detect the language of the following text and then translate it to '$target_language'.\n"
        "$phonetic_instruction\n\n"
        "Text to translate:\n\"$text_to_translate\"\n\n"
        "Output:"
    )
    
    SPECIFIC_LANGUAGE_TEMPLATE = PromptTemplate(
        "Translate the following text from '$source_language' to '$target_language'.\n"
        "$phonetic_instruction\n\n"
        "Text to translate:\n\"$text_to_translate\"\n\n"
        "Output:"
    )
    
    PHONETIC_INSTRUCTION = (
        "After providing the translation into {target_language}, "
        "also provide a simple phonetic pronunciation of the translated text using Persian alphabet characters, "
        "enclosed in parentheses. For example, if the source text is 'mother' and the target language is German, "
        "the output should be similar to: Mutter (موتا). "
        "If the source text is 'Wie geht es Ihnen?' and target language is English, "
        "the output should be similar to: How are you? (هاو آر یو؟)."
    )
    
    SYSTEM_MESSAGE = (
        "You are a multilingual translator. Provide the translation and then its "
        "Persian phonetic pronunciation in parentheses."
    )
    
    @classmethod
    def get_translation_prompt(
        cls,
        text_to_translate: str,
        target_language: str,
        source_language: str = "auto",
        include_phonetics: bool = True
    ) -> str:
        """Generate translation prompt.
        
        Args:
            text_to_translate: Text to translate
            target_language: Target language
            source_language: Source language ("auto" for detection)
            include_phonetics: Whether to include phonetic pronunciation
            
        Returns:
            str: Generated prompt
        """
        phonetic_instruction = (
            cls.PHONETIC_INSTRUCTION.format(target_language=target_language)
            if include_phonetics else ""
        )
        
        if source_language.lower() == "auto":
            return cls.AUTO_DETECT_TEMPLATE.render(
                target_language=target_language,
                phonetic_instruction=phonetic_instruction,
                text_to_translate=text_to_translate
            )
        else:
            return cls.SPECIFIC_LANGUAGE_TEMPLATE.render(
                source_language=source_language,
                target_language=target_language,
                phonetic_instruction=phonetic_instruction,
                text_to_translate=text_to_translate
            )


class AnalysisPrompts:
    """Prompt templates for conversation analysis."""
    
    PERSIAN_ANALYSIS_TEMPLATE = PromptTemplate(
        "شما یک دستیار هوشمند تحلیلگر مکالمات فارسی هستید. لطفاً متن گفتگوی زیر را به دقت بررسی کرده "
        "و یک گزارش تحلیلی جامع و ساختاریافته به زبان فارسی ارائه دهید. "
        "هنگام تحلیل، به زمینه فرهنگی، لحن محاوره‌ای، و روابط احتمالی بین گویندگان توجه ویژه داشته باشید. "
        "از تفسیر تحت‌اللفظی عباراتی که ممکن است در بستر دوستانه یا شوخی معنای متفاوتی داشته باشند، پرهیز کنید.\n\n"
        
        "گزارش شما باید شامل بخش‌های زیر با همین عناوین فارسی و به همین ترتیب باشد:\n\n"
        
        "1.  **خلاصه اجرایی مکالمه:**\n"
        "    یک پاراگراف کوتاه (حداکثر ۳-۴ جمله) که چکیده و هدف اصلی این بخش از گفتگو را بیان کند. "
        "از کلی‌گویی بپرهیزید و به مهم‌ترین نتیجه یا هدف گفتگو اشاره کنید.\n\n"
        
        "2.  **موضوعات اصلی و نکات کلیدی مطرح شده:**\n"
        "    موضوعات اصلی که در این گفتگو مورد بحث قرار گرفته‌اند را شناسایی و به صورت یک لیست "
        "شماره‌گذاری شده یا با عنوان‌های واضح بیان کنید. برای هر موضوع اصلی، نکات کلیدی، اطلاعات مهم، "
        "تصمیمات گرفته شده، یا سوالات اصلی مطرح شده را به طور خلاصه و دقیق (با جزئیات مرتبط از متن) "
        "ذکر نمایید. سعی کنید حداقل ۲ تا ۴ موضوع/نکته کلیدی را استخراج کنید، مگر اینکه گفتگو بسیار کوتاه باشد.\n\n"
        
        "3.  **تحلیل لحن و احساسات غالب:**\n"
        "    ابتدا در یک جمله، لحن کلی و احساسات غالب در طول این بخش از مکالمه را توصیف کنید "
        "(مثلاً: دوستانه و مشتاقانه، رسمی و جدی، طنزآمیز با چاشنی کنایه، پرتنش و چالشی، خنثی و اطلاع‌رسانی). "
        "از ایموجی‌های مناسب برای نمایش احساسات استفاده کنید (مثلاً: 😊, 😢, 😡, ❤️, 🤔, 😐).\n"
        "    سپس، به طور مختصر توضیح دهید که کدام بخش‌ها از گفتگو یا کدام عبارات شما را به این تشخیص رسانده‌اند. "
        "اگر تغییرات قابل توجهی در لحن یا احساسات در طول گفتگو وجود داشته، به آن اشاره کنید.\n\n"
        
        "4.  **اقدامات، تصمیمات، و قرارها (رویدادها):**\n"
        "    هرگونه اقدام انجام شده، تصمیم گرفته شده، قرار ملاقات تنظیم شده، یا وظیفه مشخص شده در این گفتگو "
        "را به صورت یک لیست موردی (bullet points) بیان کنید. اگر زمان، مکان، یا مسئول خاصی برای هر مورد ذکر شده، "
        "آن را نیز اضافه کنید. موارد را بر اساس قطعیت (ابتدا موارد قطعی، سپس پیشنهادات) مرتب کنید.\n\n"
        
        "آمار مکالمه: این گفتگو شامل $num_messages پیام بین $num_senders نفر در طی حدود $duration_minutes دقیقه بوده است.\n\n"
        
        "پیام‌ها جهت تحلیل:\n"
        "```\n"
        "$actual_chat_messages\n"
        "```\n\n"
        
        "تحلیل فارسی:"
    )
    
    SYSTEM_MESSAGE = (
        "You are a professional Persian chat analyst. Provide a comprehensive and structured "
        "report based on the user's detailed instructions, ensuring all requested sections are "
        "covered accurately and in Persian."
    )
    
    @classmethod
    def get_analysis_prompt(
        cls,
        messages_text: str,
        num_messages: int,
        num_senders: int,
        duration_minutes: int
    ) -> str:
        """Generate analysis prompt.
        
        Args:
            messages_text: Formatted messages text
            num_messages: Number of messages
            num_senders: Number of unique senders
            duration_minutes: Conversation duration in minutes
            
        Returns:
            str: Generated analysis prompt
        """
        return cls.PERSIAN_ANALYSIS_TEMPLATE.render(
            num_messages=num_messages,
            num_senders=num_senders,
            duration_minutes=duration_minutes,
            actual_chat_messages=messages_text
        )


class QuestionAnswerPrompts:
    """Prompt templates for question answering from chat history."""
    
    QA_TEMPLATE = PromptTemplate(
        "شما یک دستیار هوشمند هستید که به سوالات بر اساس تاریخچه یک گفتگو پاسخ می‌دهید.\n"
        "لطفاً با لحنی حرفه‌ای اما خودمونی و دوستانه، و فقط بر اساس اطلاعات موجود در تاریخچه گفتگوی زیر، "
        "به سوال کاربر پاسخ دهید.\n"
        "اگر پاسخ سوال در تاریخچه موجود نیست، به وضوح بیان کنید که اطلاعات کافی برای پاسخ در پیام‌های "
        "ارائه شده وجود ندارد.\n\n"
        
        "تاریخچه گفتگو (آخرین پیام‌ها اول آمده‌اند، به ترتیب معکوس زمانی):\n"
        "```\n"
        "$chat_history\n"
        "```\n\n"
        
        "سوال کاربر: $user_question\n\n"
        "پاسخ شما (به فارسی):"
    )
    
    SYSTEM_MESSAGE = (
        "You are an AI assistant specialized in answering questions based on provided chat history. "
        "Maintain a professional yet friendly and colloquial tone. If the answer isn't in the history, "
        "state that clearly. Respond in Persian unless the question implies another language."
    )
    
    @classmethod
    def get_qa_prompt(cls, chat_history: str, user_question: str) -> str:
        """Generate question answering prompt.
        
        Args:
            chat_history: Formatted chat history
            user_question: User's question
            
        Returns:
            str: Generated prompt
        """
        return cls.QA_TEMPLATE.render(
            chat_history=chat_history,
            user_question=user_question
        )


class CommonPrompts:
    """Common prompt templates used across the application."""
    
    SUMMARIZATION_TEMPLATE = PromptTemplate(
        "Please provide a concise summary of the following text in $language. "
        "Focus on the main points and key information.\n\n"
        "Text to summarize:\n$text\n\n"
        "Summary:"
    )
    
    ERROR_ANALYSIS_TEMPLATE = PromptTemplate(
        "Analyze the following error and provide a helpful explanation and potential solutions:\n\n"
        "Error: $error_message\n"
        "Context: $context\n\n"
        "Analysis:"
    )
    
    CONTENT_MODERATION_TEMPLATE = PromptTemplate(
        "Analyze the following message for inappropriate content. "
        "Consider context, intent, and cultural nuances. "
        "Rate the content as: SAFE, MILD_CONCERN, MODERATE_CONCERN, or HIGH_CONCERN.\n\n"
        "Message: $message\n"
        "Language: $language\n\n"
        "Analysis:"
    )
    
    @classmethod
    def get_summarization_prompt(cls, text: str, language: str = "Persian") -> str:
        """Generate summarization prompt.
        
        Args:
            text: Text to summarize
            language: Output language
            
        Returns:
            str: Generated prompt
        """
        return cls.SUMMARIZATION_TEMPLATE.render(text=text, language=language)
    
    @classmethod
    def get_error_analysis_prompt(cls, error_message: str, context: str = "") -> str:
        """Generate error analysis prompt.
        
        Args:
            error_message: Error message to analyze
            context: Additional context
            
        Returns:
            str: Generated prompt
        """
        return cls.ERROR_ANALYSIS_TEMPLATE.render(
            error_message=error_message,
            context=context or "No additional context provided"
        )
    
    @classmethod
    def get_moderation_prompt(cls, message: str, language: str = "fa") -> str:
        """Generate content moderation prompt.
        
        Args:
            message: Message to moderate
            language: Message language
            
        Returns:
            str: Generated prompt
        """
        return cls.CONTENT_MODERATION_TEMPLATE.render(
            message=message,
            language=LANGUAGES.get(language, language)
        )


class SystemMessages:
    """System message templates for different AI tasks."""
    
    GENERAL_ASSISTANT = (
        "You are a helpful AI assistant. Provide accurate, helpful, and contextually "
        "appropriate responses. Be concise but comprehensive."
    )
    
    TRANSLATOR = (
        "You are a professional translator with expertise in multiple languages. "
        "Provide accurate translations while maintaining the original meaning, tone, and context."
    )
    
    ANALYZER = (
        "You are a conversation analyst with expertise in communication patterns, "
        "sentiment analysis, and social dynamics. Provide insightful and objective analysis."
    )
    
    MODERATOR = (
        "You are a content moderator focused on identifying potentially harmful, "
        "inappropriate, or policy-violating content while being mindful of context and cultural nuances."
    )
    
    SUMMARIZER = (
        "You are a text summarization specialist. Create concise, accurate summaries "
        "that capture the essential information and key points."
    )
    
    PERSIAN_SPECIALIST = (
        "شما یک متخصص زبان فارسی هستید که در زمینه فرهنگ، ادبیات، و ارتباطات فارسی تخصص دارید. "
        "پاسخ‌های شما باید دقیق، مناسب فرهنگی، و به زبان فارسی باشد."
    )


def get_system_message(task_type: str, language: str = "en") -> str:
    """Get appropriate system message for task type.
    
    Args:
        task_type: Type of task (translate, analyze, moderate, etc.)
        language: Target language
        
    Returns:
        str: Appropriate system message
    """
    if language == "fa" or language == "persian":
        return SystemMessages.PERSIAN_SPECIALIST
    
    task_mapping = {
        "translate": SystemMessages.TRANSLATOR,
        "analyze": SystemMessages.ANALYZER,
        "moderate": SystemMessages.MODERATOR,
        "summarize": SystemMessages.SUMMARIZER,
        "general": SystemMessages.GENERAL_ASSISTANT,
    }
    
    return task_mapping.get(task_type.lower(), SystemMessages.GENERAL_ASSISTANT)


def calculate_max_tokens(input_text: str, base_tokens: int = 150) -> int:
    """Calculate appropriate max_tokens based on input length.
    
    Args:
        input_text: Input text to estimate tokens for
        base_tokens: Base tokens for response overhead
        
    Returns:
        int: Estimated max_tokens needed
    """
    # Rough estimate: 4 characters per token for most languages
    estimated_input_tokens = len(input_text) // 4
    # Add base tokens for response and some buffer
    return min(8192, estimated_input_tokens + base_tokens + 200)
