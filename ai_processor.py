# -*- coding: utf-8 -*-
# English comments as per our rules

import logging
from openai import AsyncOpenAI # Using the async version of the OpenAI client

logger = logging.getLogger(__name__)

async def execute_custom_prompt(
    api_key: str, 
    model_name: str, 
    user_text_prompt: str,
    max_tokens: int = 1000, 
    temperature: float = 0.7 
) -> str:
    """
    Sends a custom text prompt from the user to the specified AI model via OpenRouter API
    and returns the AI's response. The AI should attempt to respond in the same language
    as the user's prompt.

    Args:
        api_key (str): The OpenRouter API key (read from config.ini).
        model_name (str): The model identifier (e.g., "deepseek/chat", read from config.ini).
        user_text_prompt (str): The text prompt provided by the user via the /prompt= command.
        max_tokens (int): Maximum tokens for the AI's response.
        temperature (float): Temperature for AI generation (creativity).

    Returns:
        str: The AI's response, or an error message if something goes wrong.
    """
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

        # The system message can be minimal or removed if we want the AI to purely follow the user's language.
        # Or, we can instruct it to respond in the language of the prompt.
        # For now, we'll keep it simple and let the model infer from the user's prompt.
        messages_payload = [
            # Optional system message:
            # {"role": "system", "content": "You are a helpful assistant. Respond in the language of the user's prompt."},
            {"role": "user", "content": user_text_prompt}
        ]

        logger.info(f"AI Processor: Sending prompt to AI model '{model_name}': '{user_text_prompt[:100]}...'")
        
        completion = await client.chat.completions.create(
            model=model_name, 
            messages=messages_payload,
            max_tokens=max_tokens,
            temperature=temperature,
            extra_headers={ 
                "HTTP-Referer": "http://localhost/sakaibot", # Replace with your actual site or a placeholder
                "X-Title": "SakaiBot" 
            }
        )

        response_text = completion.choices[0].message.content.strip()
        logger.info(f"AI Processor: Model '{model_name}' responded successfully.")
        return response_text

    except Exception as e:
        logger.error(f"AI Processor: Error calling OpenRouter API with model '{model_name}': {e}", exc_info=True)
        return f"AI Error: Could not get response from model '{model_name}'. Details: {str(e)}"

# This block is for standalone testing of this module.
# It will NOT run when this module is imported by main.py.
if __name__ == '__main__':
    import asyncio
    # IMPORTANT: For standalone testing, replace the placeholder with your actual API key
    # and desired model. The main SakaiBot application will use these from your config.ini file.
    STANDALONE_TEST_API_KEY = "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" # YOUR KEY
    STANDALONE_TEST_MODEL = "deepseek/deepseek-chat-v3-0324:free" # YOUR MODEL

    # Configure a simple logger for standalone testing
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Also configure the module's own logger if you want to see its logs during standalone test
    logging.getLogger("ai_processor").setLevel(logging.INFO)


    async def run_standalone_tests():
        if "YOUR_OPENROUTER_API_KEY_HERE" in STANDALONE_TEST_API_KEY or not STANDALONE_TEST_API_KEY or len(STANDALONE_TEST_API_KEY) < 50:
            print("*************************************************************************************")
            print("WARNING: STANDALONE_TEST_API_KEY is not set or is invalid in ai_processor.py.")
            print("Please edit ai_processor.py and set STANDALONE_TEST_API_KEY to your OpenRouter key")
            print("if you wish to run standalone tests for this module.")
            print("This will NOT affect the main SakaiBot application, which uses config.ini.")
            print("*************************************************************************************")
            return

        print(f"\n--- Running Standalone AI Processor Test (Model: {STANDALONE_TEST_MODEL}) ---")
        
        prompts_to_test = [
            "Hello, who are you?",
            "یک ایده برای نوشتن در مورد تکنولوژی پیشنهاد بده.",
            "Quel temps fait-il à Paris ?"
        ]

        for i, user_prompt in enumerate(prompts_to_test):
            print(f"\nTesting Prompt {i+1}: {user_prompt}")
            response = await execute_custom_prompt(STANDALONE_TEST_API_KEY, STANDALONE_TEST_MODEL, user_prompt)
            print(f"AI Response for Prompt {i+1}:\n{response}")
            print("-" * 20)

    asyncio.run(run_standalone_tests())
