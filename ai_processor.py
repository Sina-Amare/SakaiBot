# -*- coding: utf-8 -*-
# English comments as per our rules

import logging
from openai import AsyncOpenAI
from datetime import datetime, timezone
import pytz
import os # Added for STT related file operations if any, though primarily in event_handlers

# For Speech-to-Text (STT)
import speech_recognition as sr
# from pydub import AudioSegment # Conversion will be handled in event_handlers

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
    if not api_key or "YOUR_OPENROUTER_API_KEY_HERE" in api_key or len(api_key) < 10: # Basic check
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
                "HTTP-Referer": "http://localhost/sakaibot", # Replace with your actual site URL if deployed
                "X-Title": "SakaiBot" # Replace with your actual app name
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
        max_tokens=len(text_to_translate) * 4 + 150, temperature=0.2, # Adjusted max_tokens
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
    messages_data: list # Expected: list of dicts {'sender': str, 'text': str, 'timestamp': datetime}
) -> str:
    # ... (This function remains the same as sakaibot_ai_processor_py_v5_analyze_format_fix)
    if not api_key or "YOUR_OPENROUTER_API_KEY_HERE" in api_key or len(api_key) < 10:
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
        timestamp_obj = msg_info.get('timestamp') # datetime object expected

        if text: # Ensure there is text content
            # Ensure timestamp is timezone-aware (UTC)
            ts_aware = timestamp_obj
            if isinstance(timestamp_obj, datetime):
                if timestamp_obj.tzinfo is None:
                    ts_aware = pytz.utc.localize(timestamp_obj) # Assume UTC if naive
                else:
                    ts_aware = timestamp_obj.astimezone(pytz.utc) # Convert to UTC
            elif isinstance(timestamp_obj, (int, float)): # If timestamp is a Unix timestamp
                ts_aware = datetime.fromtimestamp(timestamp_obj, tz=pytz.utc)
            # else: ts_aware might remain None or original if not datetime/int/float

            formatted_messages_for_prompt.append(f"{sender}: {text}")
            senders.add(sender)
            if ts_aware: # Only append if we have a valid timestamp
                timestamps.append(ts_aware)

    if not formatted_messages_for_prompt:
        return "No text messages found for analysis after formatting."

    combined_text_for_prompt_var = "\n".join(formatted_messages_for_prompt)
    num_messages = len(formatted_messages_for_prompt)
    num_senders = len(senders)
    duration_minutes = 0
    if len(timestamps) >= 2: # Calculate duration only if we have at least two timestamps
        min_time = min(timestamps)
        max_time = max(timestamps)
        duration_minutes = int((max_time - min_time).total_seconds() / 60)
    elif len(timestamps) == 1: # If only one message, duration is 0
        duration_minutes = 0

    # Persian prompt template for conversation analysis
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
    analysis_response = await execute_custom_prompt(api_key=api_key, model_name=model_name, user_text_prompt=prompt, max_tokens=2000, temperature=0.4, system_message=system_msg_for_analysis) # Increased max_tokens for detailed analysis
    if "AI Error:" not in analysis_response:
        logger.info(f"AI Processor: Detailed analysis successful for {num_messages} messages.")
    else:
        logger.error(f"AI Processor: Detailed analysis failed. Response: {analysis_response}")
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
    if not api_key or "YOUR_OPENROUTER_API_KEY_HERE" in api_key or len(api_key) < 10:
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
        if text: # Ensure there is text content
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

async def transcribe_voice_to_text(audio_wav_path: str) -> str:
    """
    Transcribes voice from a .wav audio file to text using SpeechRecognition library (Google Web Speech API).
    This is a free method suitable for testing, but has limitations.
    Requires ffmpeg to be installed for pydub (used in event_handler) to convert original audio to WAV.
    """
    if not os.path.exists(audio_wav_path):
        logger.error(f"STT Error: Audio file not found at {audio_wav_path}")
        return "STT Error: Processed audio file not found."

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_wav_path) as source:
            audio_data = recognizer.record(source) # read the entire audio file
        logger.info(f"STT: Audio file '{audio_wav_path}' loaded successfully. Attempting transcription...")
        # Recognize speech using Google Web Speech API (free, no key needed, but has limitations)
        # For Persian, use language="fa-IR"
        text = recognizer.recognize_google(audio_data, language="fa-IR")
        logger.info(f"STT: Transcription successful: '{text[:100]}...'")
        return text
    except sr.WaitTimeoutError:
        logger.error("STT Error: No speech detected (WaitTimeoutError).")
        return "STT Error: No speech detected or timeout."
    except sr.UnknownValueError:
        logger.info("STT: Google Web Speech API could not understand audio.")
        return "STT Error: Speech was unintelligible."
    except sr.RequestError as e:
        logger.error(f"STT Error: Could not request results from Google Web Speech API; {e}")
        return f"STT Error: API request failed ({e}). Check internet connection."
    except Exception as e:
        logger.error(f"STT Error: An unexpected error occurred during transcription: {e}", exc_info=True)
        return f"STT Error: Transcription failed ({e})."


# Standalone Test Block
if __name__ == '__main__':
    # ... (Standalone test block can be updated to include answer_question_from_chat_history and transcribe_voice_to_text) ...
    import asyncio
    # import pytz # Already imported
    from datetime import timedelta # Already imported

    STANDALONE_TEST_API_KEY = "YOUR_OPENROUTER_API_KEY_FOR_STANDALONE_TESTING_ONLY" # Replace if testing AI features
    STANDALONE_TEST_MODEL = "deepseek/deepseek-chat" # Replace if testing AI features

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logging.getLogger("ai_processor").setLevel(logging.DEBUG)
    logging.getLogger("speech_recognition").setLevel(logging.DEBUG)


    async def run_standalone_tests():
        if "YOUR_OPENROUTER_API_KEY_FOR_STANDALONE_TESTING_ONLY" in STANDALONE_TEST_API_KEY or \
           not STANDALONE_TEST_API_KEY or len(STANDALONE_TEST_API_KEY) < 10: # Basic check
            print("WARNING: OpenRouter API key not set in STANDALONE_TEST_API_KEY. AI features (/tellme, /analyze etc.) will fail if called.")
            # For STT, API key is not needed for recognize_google

        print(f"\n--- Running Standalone AI Processor Tests (Model for AI: {STANDALONE_TEST_MODEL}) ---")

        # Test /tellme (Example - will fail if API key is placeholder)
        print("\nTesting /tellme (answer_question_from_chat_history):")
        # ... (rest of the /tellme test code from previous version)

        # Test STT (transcribe_voice_to_text)
        # This requires a sample .wav file. Create a dummy one for the test structure.
        print("\nTesting STT (transcribe_voice_to_text):")
        dummy_wav_path = "test_audio.wav"
        try:
            # Create a simple dummy WAV file if pydub is available for testing structure
            # In a real scenario, you'd use an actual voice recording.
            from pydub import AudioSegment
            from pydub.generators import Sine
            # Generate a 1-second sine wave at 440 Hz (A4 note)
            # This is just to have a file, it won't transcribe to meaningful Persian.
            sine_wave = Sine(440).to_audio_segment(duration=1000).set_channels(1)
            sine_wave.export(dummy_wav_path, format="wav")
            print(f"Created dummy '{dummy_wav_path}' for STT test structure.")

            stt_response = await transcribe_voice_to_text(dummy_wav_path)
            print(f"STT Response for dummy WAV:\n{stt_response}")
            print("Note: The dummy WAV contains a sine wave, so 'Speech unintelligible' or similar is expected.")

        except ImportError:
            print("pydub not installed, skipping dummy WAV creation for STT test.")
            print("To test STT, manually create a 'test_audio.wav' file with some Persian speech.")
            if os.path.exists(dummy_wav_path): # If manually created
                 stt_response = await transcribe_voice_to_text(dummy_wav_path)
                 print(f"STT Response for manually provided '{dummy_wav_path}':\n{stt_response}")
            else:
                print(f"'{dummy_wav_path}' not found.")
        except Exception as e_stt_test:
            print(f"Error during STT standalone test: {e_stt_test}")
        finally:
            if os.path.exists(dummy_wav_path):
                os.remove(dummy_wav_path)
                print(f"Removed dummy '{dummy_wav_path}'.")


    asyncio.run(run_standalone_tests())
