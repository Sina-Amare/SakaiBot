# -*- coding: utf-8 -*-
# English comments as per our rules

import logging
from openai import AsyncOpenAI 
from datetime import datetime, timezone 
import pytz 

logger = logging.getLogger(__name__)

async def execute_custom_prompt(
    api_key: str, 
    model_name: str, 
    user_text_prompt: str,
    max_tokens: int = 1500, 
    temperature: float = 0.7,
    system_message: str or None = None 
) -> str:
    # ... (This function remains the same as sakaibot_ai_processor_py_v7_direct_prompt)
    if not api_key or "YOUR_OPENROUTER_API_KEY_HERE" in api_key or len(api_key) < 50:
        logger.error("AI Processor: OpenRouter API key is not configured or seems invalid.")
        return "AI Error: OpenRouter API key not configured or invalid. Please check your config.ini."
    if not model_name:
        logger.error("AI Processor: OpenRouter model name is not configured.")
        return "AI Error: OpenRouter model name not configured. Please check your config.ini."
    if not user_text_prompt:
        logger.warning("AI Processor: Received an empty prompt.")
        return "AI Error: Prompt cannot be empty."
    try:
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        messages_payload = []
        if system_message and system_message.strip():
            logger.debug(f"AI Processor: Using System Message: '{system_message}'")
            messages_payload.append({"role": "system", "content": system_message})
        else:
            logger.debug("AI Processor: No specific system message provided for this prompt call.")
        messages_payload.append({"role": "user", "content": user_text_prompt})
        logger.info(f"AI Processor: Sending prompt to AI model '{model_name}'. System message used: {'Yes' if system_message and system_message.strip() else 'No'}. Prompt starts with: '{user_text_prompt[:100]}...' (max_tokens: {max_tokens}, temp: {temperature})")
        completion = await client.chat.completions.create(
            model=model_name, 
            messages=messages_payload,
            max_tokens=max_tokens,
            temperature=temperature,
            extra_headers={ 
                "HTTP-Referer": "http://localhost/sakaibot", 
                "X-Title": "SakaiBot" 
            }
        )
        response_text = completion.choices[0].message.content.strip()
        logger.info(f"AI Processor: Model '{model_name}' responded successfully for custom prompt.")
        return response_text
    except Exception as e:
        logger.error(f"AI Processor: Error calling OpenRouter API for custom prompt with model '{model_name}': {e}", exc_info=True)
        return f"AI Error: Could not get response from model '{model_name}'. Details: {str(e)}"


async def translate_text_with_phonetics(
    api_key: str,
    model_name: str,
    text_to_translate: str,
    target_language: str,
    source_language: str = "auto" 
) -> str:
    # ... (This function remains the same as sakaibot_ai_processor_py_v5_analyze_format_fix)
    if not text_to_translate:
        return "AI Error: No text provided for translation."
    if not target_language:
        return "AI Error: Target language not specified."
    phonetic_instruction = (
        f"After providing the translation into {target_language}, "
        f"also provide a simple phonetic pronunciation of the translated text using Persian alphabet characters, "
        f"enclosed in parentheses. For example, if the source text is 'mother' and the target language is German, "
        f"the output should be similar to: Mutter (موتا). "
        f"If the source text is 'Wie geht es Ihnen?' and target language is English, "
        f"the output should be similar to: How are you? (هاو آر یو؟)."
    )
    if source_language.lower() == "auto":
        prompt = (
            f"Detect the language of the following text and then translate it to '{target_language}'.\n"
            f"{phonetic_instruction}\n\n"
            f"Text to translate:\n\"{text_to_translate}\"\n\n"
            f"Output:"
        )
    else:
        prompt = (
            f"Translate the following text from '{source_language}' to '{target_language}'.\n"
            f"{phonetic_instruction}\n\n"
            f"Text to translate:\n\"{text_to_translate}\"\n\n"
            f"Output:"
        )
    logger.info(f"AI Processor: Requesting translation for '{text_to_translate[:50]}...' to {target_language} with phonetics.")
    system_msg_for_translation = "You are a multilingual translator. Provide the translation and then its Persian phonetic pronunciation in parentheses."
    translation_response = await execute_custom_prompt(
        api_key=api_key, model_name=model_name, user_text_prompt=prompt,
        max_tokens=len(text_to_translate) * 4 + 150, temperature=0.2,
        system_message=system_msg_for_translation 
    )
    if "AI Error:" not in translation_response:
        logger.info(f"AI Processor: Translation with phonetics successful for '{text_to_translate[:50]}...'.")
    else:
        logger.error(f"AI Processor: Translation with phonetics failed for '{text_to_translate[:50]}...'. Response: {translation_response}")
    return translation_response


async def analyze_conversation_messages(
    api_key: str, 
    model_name: str, 
    messages_data: list 
) -> str:
    # ... (This function remains the same as sakaibot_ai_processor_py_v5_analyze_format_fix)
    if not api_key or "YOUR_OPENROUTER_API_KEY_HERE" in api_key or len(api_key) < 50:
        logger.error("AI Processor: OpenRouter API key not configured for analysis.")
        return "AI Error: OpenRouter API key not configured for analysis."
    if not model_name:
        logger.error("AI Processor: OpenRouter model name not configured for analysis.")
        return "AI Error: OpenRouter model name not configured for analysis."
    if not messages_data:
        return "No messages provided for analysis."
    formatted_messages_for_prompt = []
    senders = set()
    timestamps = []
    for msg_info in messages_data:
        sender = msg_info.get('sender', 'Unknown')
        text = msg_info.get('text')
        timestamp_obj = msg_info.get('timestamp') 
        if text: 
            ts_aware = timestamp_obj
            if isinstance(timestamp_obj, datetime):
                if timestamp_obj.tzinfo is None: ts_aware = pytz.utc.localize(timestamp_obj) 
                else: ts_aware = timestamp_obj.astimezone(pytz.utc) 
            elif isinstance(timestamp_obj, (int, float)): ts_aware = datetime.fromtimestamp(timestamp_obj, tz=pytz.utc)
            formatted_messages_for_prompt.append(f"{sender}: {text}")
            senders.add(sender)
            if ts_aware: timestamps.append(ts_aware)
    if not formatted_messages_for_prompt: return "No text messages found for analysis after formatting."
    combined_text_for_prompt_var = "\n".join(formatted_messages_for_prompt)
    num_messages = len(formatted_messages_for_prompt); num_senders = len(senders); duration_minutes = 0
    if len(timestamps) >= 2: 
        min_time = min(timestamps); max_time = max(timestamps)
        duration_minutes = int((max_time - min_time).total_seconds() / 60)
    elif len(timestamps) == 1: duration_minutes = 0
    prompt_template = (
        "شما یک دستیار هوشمند تحلیلگر مکالمات فارسی هستید. لطفاً متن گفتگوی زیر را به دقت بررسی کرده و یک گزارش تحلیلی جامع و ساختاریافته به زبان فارسی ارائه دهید. "
        "هنگام تحلیل، به زمینه فرهنگی، لحن محاوره‌ای، و روابط احتمالی بین گویندگان توجه ویژه داشته باشید. از تفسیر تحت‌اللفظی عباراتی که ممکن است در بستر دوستانه یا شوخی معنای متفاوتی داشته باشند، پرهیز کنید.\n\n"
        "گزارش شما باید شامل بخش‌های زیر با همین عناوین فارسی و به همین ترتیب باشد:\n\n"
        "1.  **خلاصه اجرایی مکالمه:**\n"
        "    یک پاراگراف کوتاه (حداکثر ۳-۴ جمله) که چکیده و هدف اصلی این بخش از گفتگو را بیان کند. از کلی‌گویی بپرهیزید و به مهم‌ترین نتیجه یا هدف گفتگو اشاره کنید.\n\n"
        "2.  **موضوعات اصلی و نکات کلیدی مطرح شده:**\n"
        "    موضوعات اصلی که در این گفتگو مورد بحث قرار گرفته‌اند را شناسایی و به صورت یک لیست شماره‌گذاری شده یا با عنوان‌های واضح بیان کنید. برای هر موضوع اصلی، نکات کلیدی، اطلاعات مهم، تصمیمات گرفته شده، یا سوالات اصلی مطرح شده را به طور خلاصه و دقیق (با جزئیات مرتبط از متن) ذکر نمایید. سعی کنید حداقل ۲ تا ۴ موضوع/نکته کلیدی را استخراج کنید، مگر اینکه گفتگو بسیار کوتاه باشد.\n\n"
        "3.  **تحلیل لحن و احساسات غالب:**\n"
        "    ابتدا در یک جمله، لحن کلی و احساسات غالب در طول این بخش از مکالمه را توصیف کنید (مثلاً: دوستانه و مشتاقانه، رسمی و جدی، طنزآمیز با چاشنی کنایه، پرتنش و چالشی، خنثی و اطلاع‌رسانی). از ایموجی‌های مناسب برای نمایش احساسات استفاده کنید (مثلاً: 😊, 😢, 😡, ❤️, 🤔, 😐).\n"
        "    سپس، به طور مختصر توضیح دهید که کدام بخش‌ها از گفتگو یا کدام عبارات شما را به این تشخیص رسانده‌اند. اگر تغییرات قابل توجهی در لحن یا احساسات در طول گفتگو وجود داشته، به آن اشاره کنید.\n\n"
        "4.  **اقدامات، تصمیمات، و قرارها (رویدادها):**\n"
        "    هرگونه اقدام انجام شده، تصمیم گرفته شده، قرار ملاقات تنظیم شده، یا وظیفه مشخص شده در این گفتگو را به صورت یک لیست موردی (bullet points) بیان کنید. اگر زمان، مکان، یا مسئول خاصی برای هر مورد ذکر شده، آن را نیز اضافه کنید. موارد را بر اساس قطعیت (ابتدا موارد قطعی، سپس پیشنهادات) مرتب کنید.\n\n"
        "آمار مکالمه: این گفتگو شامل {num_messages} پیام بین {num_senders} نفر در طی حدود {duration_minutes} دقیقه بوده است.\n\n"
        "پیام‌ها جهت تحلیل:\n"
        "```\n"
        "{actual_chat_messages}\n" 
        "```\n\n"
        "تحلیل فارسی:"
    )
    prompt = prompt_template.format(num_messages=num_messages, num_senders=num_senders, duration_minutes=duration_minutes, actual_chat_messages=combined_text_for_prompt_var)
    logger.info(f"AI Processor: Sending conversation ({num_messages} messages) for DETAILED analysis to model '{model_name}'.")
    system_msg_for_analysis = "You are a professional Persian chat analyst. Provide a comprehensive and structured report based on the user's detailed instructions, ensuring all requested sections are covered accurately and in Persian."
    analysis_response = await execute_custom_prompt(api_key=api_key, model_name=model_name, user_text_prompt=prompt, max_tokens=2000, temperature=0.4, system_message=system_msg_for_analysis)
    if "AI Error:" not in analysis_response: logger.info(f"AI Processor: Detailed analysis successful for {num_messages} messages.")
    else: logger.error(f"AI Processor: Detailed analysis failed. Response: {analysis_response}")
    return analysis_response

async def answer_question_from_chat_history(
    api_key: str,
    model_name: str,
    messages_data: list, # Expected: list of dicts {'sender': str, 'text': str, 'timestamp': datetime}
    user_question: str
) -> str:
    """
    Answers a specific user question based on the provided chat history.
    Uses a professional and colloquial tone.
    """
    if not api_key or "YOUR_OPENROUTER_API_KEY_HERE" in api_key or len(api_key) < 50:
        logger.error("AI Processor: OpenRouter API key not configured for question answering.")
        return "AI Error: OpenRouter API key not configured."
    if not model_name:
        logger.error("AI Processor: OpenRouter model name not configured for question answering.")
        return "AI Error: OpenRouter model name not configured."
    if not messages_data:
        return "No chat history provided to answer the question."
    if not user_question:
        return "No question provided to answer."

    formatted_messages_for_prompt = []
    for msg_info in messages_data:
        sender = msg_info.get('sender', 'Unknown')
        text = msg_info.get('text')
        if text:
            formatted_messages_for_prompt.append(f"{sender}: {text}")
    
    if not formatted_messages_for_prompt:
        return "No text messages found in the provided history."

    combined_history_text = "\n".join(formatted_messages_for_prompt)

    # Construct the prompt for the AI
    prompt = (
        "شما یک دستیار هوشمند هستید که به سوالات بر اساس تاریخچه یک گفتگو پاسخ می‌دهید.\n"
        "لطفاً با لحنی حرفه‌ای اما خودمونی و دوستانه، و فقط بر اساس اطلاعات موجود در تاریخچه گفتگوی زیر، به سوال کاربر پاسخ دهید.\n"
        "اگر پاسخ سوال در تاریخچه موجود نیست، به وضوح بیان کنید که اطلاعات کافی برای پاسخ در پیام‌های ارائه شده وجود ندارد.\n\n"
        "تاریخچه گفتگو (آخرین پیام‌ها اول آمده‌اند، به ترتیب معکوس زمانی):\n"
        "```\n"
        f"{combined_history_text}\n"
        "```\n\n"
        f"سوال کاربر: {user_question}\n\n"
        "پاسخ شما (به فارسی):"
    )

    logger.info(f"AI Processor: Answering question '{user_question[:50]}...' based on {len(formatted_messages_for_prompt)} messages using model '{model_name}'.")

    # System message to guide the AI's role and tone
    system_msg_for_qa = "You are an AI assistant specialized in answering questions based on provided chat history. Maintain a professional yet friendly and colloquial tone. If the answer isn't in the history, state that clearly. Respond in Persian unless the question implies another language."

    answer = await execute_custom_prompt(
        api_key=api_key,
        model_name=model_name,
        user_text_prompt=prompt,
        max_tokens=1000, # Adjust as needed, can be shorter for direct answers
        temperature=0.5, # A balance between factual and natural
        system_message=system_msg_for_qa
    )

    if "AI Error:" not in answer:
        logger.info(f"AI Processor: Successfully answered question '{user_question[:50]}...'.")
    else:
        logger.error(f"AI Processor: Failed to answer question '{user_question[:50]}...'. Response: {answer}")
        
    return answer


# Standalone Test Block
if __name__ == '__main__':
    # ... (Standalone test block can be updated to include answer_question_from_chat_history) ...
    import asyncio
    import pytz 
    from datetime import timedelta

    STANDALONE_TEST_API_KEY = "YOUR_OPENROUTER_API_KEY_FOR_STANDALONE_TESTING_ONLY" 
    STANDALONE_TEST_MODEL = "deepseek/deepseek-chat" 

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.getLogger("ai_processor").setLevel(logging.DEBUG)


    async def run_standalone_tests():
        if "YOUR_OPENROUTER_API_KEY_FOR_STANDALONE_TESTING_ONLY" in STANDALONE_TEST_API_KEY or \
           not STANDALONE_TEST_API_KEY or len(STANDALONE_TEST_API_KEY) < 50:
            print("Please set your actual OpenRouter API key in STANDALONE_TEST_API_KEY to run the test.")
            return

        print(f"\n--- Running Standalone AI Processor Tests (Model: {STANDALONE_TEST_MODEL}) ---")
        
        # Test /tellme
        print("\nTesting /tellme (answer_question_from_chat_history):")
        sample_history_for_tellme = [
            {'sender': "سینا", 'text': "یادته هفته پیش درباره اون رستوران ایتالیایی جدیده حرف می‌زدیم؟ اسمش چی بود؟", 'timestamp': datetime.now(pytz.utc) - timedelta(days=7, hours=1)},
            {'sender': "هومن", 'text': "آها، آره! فکر کنم 'لاپیتزا' بود. گفتیم آخر این هفته بریم امتحانش کنیم.", 'timestamp': datetime.now(pytz.utc) - timedelta(days=7)},
            {'sender': "غزل", 'text': "منم خیلی تعریفشو شنیدم! پاستاهاش میگن عالیه.", 'timestamp': datetime.now(pytz.utc) - timedelta(days=6)},
            {'sender': "سینا", 'text': "پس قرارمون شد جمعه شب، رستوران لاپیتزا. من رزرو می‌کنم.", 'timestamp': datetime.now(pytz.utc) - timedelta(days=5)},
            {'sender': "هومن", 'text': "عالیه، فقط من شاید یه کم دیرتر برسم، حدود ۹.", 'timestamp': datetime.now(pytz.utc) - timedelta(days=5, hours=-1)},
            {'sender': "غزل", 'text': "مشکلی نیست هومن جان. سینا، تو در مورد اون فیلم ترسناکه که گفتی چیزی پیدا کردی؟", 'timestamp': datetime.now(pytz.utc) - timedelta(days=4)},
            {'sender': "سینا", 'text': "آره، اسمش 'سکوت بره‌ها' بود، ولی خیلی قدیمیه. یه فیلم جدیدتر به اسم 'نجواگر' هم پیدا کردم که امتیازاش خوبه.", 'timestamp': datetime.now(pytz.utc) - timedelta(days=3)}
        ]
        
        question1 = "اسم رستورانی که قرار شد بریم چی بود و کی قرار گذاشتیم؟"
        print(f"\nQuestion 1: {question1}")
        response_tellme1 = await answer_question_from_chat_history(
            STANDALONE_TEST_API_KEY, 
            STANDALONE_TEST_MODEL, 
            sample_history_for_tellme,
            question1
        )
        print(f"AI Response for Question 1:\n{response_tellme1}")
        print("-" * 20)

        question2 = "در مورد چه فیلم‌هایی صحبت شد؟"
        print(f"\nQuestion 2: {question2}")
        response_tellme2 = await answer_question_from_chat_history(
            STANDALONE_TEST_API_KEY, 
            STANDALONE_TEST_MODEL, 
            sample_history_for_tellme,
            question2
        )
        print(f"AI Response for Question 2:\n{response_tellme2}")
        print("-" * 20)

        question3 = "غزل در مورد ماشینش چی گفت؟" # Question not in history
        print(f"\nQuestion 3: {question3}")
        response_tellme3 = await answer_question_from_chat_history(
            STANDALONE_TEST_API_KEY, 
            STANDALONE_TEST_MODEL, 
            sample_history_for_tellme,
            question3
        )
        print(f"AI Response for Question 3:\n{response_tellme3}")


    asyncio.run(run_standalone_tests())
