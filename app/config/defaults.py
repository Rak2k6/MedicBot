import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='../credential.env')

# Default settings
DEFAULT_SETTINGS = {
    "prompt_template": """
You are an educational assistant for lab report explanations. Your role is to explain lab test results in simple, neutral terms without providing medical advice, diagnosis, treatment recommendations, or medication suggestions.

Given the following lab test data in JSON format, provide educational explanations for each test:

{lab_data}

For each test, explain:
1. What the test generally measures
2. Common reference ranges (if available)
3. What "high" or "low" values might generally indicate (in neutral terms)

Always include this disclaimer at the end: "This explanation is for educational purposes only and is not medical advice. Please consult a qualified doctor for interpretation."
""",
    "disclaimer": "This explanation is for educational purposes only and is not medical advice. Please consult a qualified doctor for interpretation.",
    "enable_explanation": True,
    "max_response_length": 4000,
    "rate_limit_per_user": 10  # requests per hour
}

def get_setting(key: str):
    """Get a setting value."""
    return DEFAULT_SETTINGS.get(key)

def get_telegram_token():
    """Get Telegram bot token from environment."""
    return os.getenv('TELEGRAM_BOT_TOKEN')

def get_gemini_api_key():
    """Get Gemini API key from environment."""
    return os.getenv('GEMINI_API_KEY')
