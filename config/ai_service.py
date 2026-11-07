import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Models supported by Groq, ordered by preference for this environment
GROQ_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
]

def get_groq_client(timeout=30.0):
    """Initializes and returns Groq client if API key exists."""
    api_key = getattr(settings, 'GROQ_API_KEY', None)
    if not api_key:
        return None
    try:
        from groq import Groq
        return Groq(api_key=api_key, timeout=timeout)
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
        return None

def call_groq_chat(messages, temperature=0.3, max_tokens=600, response_format=None, preferred_model=None):
    """
    Executes a chat completion across prioritized Groq models with robust fallback.
    Returns the raw string output or None.
    """
    client = get_groq_client()
    if not client:
        return None

    model_queue = []
    if preferred_model:
        model_queue.append(preferred_model)
    for m in GROQ_MODELS:
        if m not in model_queue:
            model_queue.append(m)

    kwargs = {
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    if response_format:
        kwargs["response_format"] = response_format

    for model_name in model_queue:
        try:
            completion = client.chat.completions.create(model=model_name, **kwargs)
            if completion and completion.choices:
                content = completion.choices[0].message.content
                if content and content.strip():
                    return content.strip()
        except Exception as e:
            logger.warning(f"Groq completion with model {model_name} failed: {e}")
            continue

    logger.error("All Groq models failed to return a valid response.")
    return None

def call_groq_json(messages, temperature=0.2, max_tokens=800, preferred_model=None):
    """
    Executes a chat completion and safely extracts and parses the JSON payload.
    """
    raw = call_groq_chat(messages, temperature=temperature, max_tokens=max_tokens, preferred_model=preferred_model)
    if not raw:
        return None

    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except Exception as e:
        start_obj = cleaned.find('{')
        end_obj = cleaned.rfind('}')
        if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
            try:
                return json.loads(cleaned[start_obj:end_obj + 1])
            except Exception:
                pass
        start_arr = cleaned.find('[')
        end_arr = cleaned.rfind(']')
        if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
            try:
                return json.loads(cleaned[start_arr:end_arr + 1])
            except Exception:
                pass
        logger.error(f"Failed to parse Groq response as JSON: {cleaned[:200]}... Error: {e}")
        return None
