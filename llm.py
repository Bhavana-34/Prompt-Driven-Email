import os
import json
import re
from typing import Any, Dict, List

OPENAI_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')

try:
    import openai
    if OPENAI_KEY:
        openai.api_key = OPENAI_KEY
except Exception:
    openai = None


def _mock_response(task: str):
    if task == 'categorize':
        return {'categories': ['Project Update'], 'confidence': 0.85, 'notes': 'Mentions deployment and schedule.'}
    if task == 'extract':
        return [{'task': 'Investigate payment errors', 'assignee': 'on-call', 'due': '', 'context': 'spike in 500s on payments.'}]
    if task == 'draft':
        return {'subject': 'Re: (auto) ', 'body': 'Thanks — I will take a look and follow up.', 'followups': []}
    return {'result': 'mock'}


def _extract_json_from_text(text: str):
    # Try to find the first JSON object/array in the text using regex
    json_match = re.search(r'({[\s\S]*}|\[[\s\S]*\])', text)
    if not json_match:
        return None
    jtext = json_match.group(1)
    try:
        return json.loads(jtext)
    except Exception:
        # try to fix common issues (replace single quotes)
        try:
            return json.loads(jtext.replace("'", '"'))
        except Exception:
            return None


def _call_openai(messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 400) -> str:
    if not openai or not OPENAI_KEY:
        return None
    try:
        resp = openai.ChatCompletion.create(model=OPENAI_MODEL, messages=messages, temperature=temperature, max_tokens=max_tokens)
        return resp['choices'][0]['message']['content']
    except Exception as e:
        # Return error message as string for higher-level handling
        return f"[OPENAI_ERROR] {e}"


def categorize(email_text: str, prompt: str) -> Dict[str, Any]:
    if not openai or not OPENAI_KEY:
        return _mock_response('categorize')
    system_prompt = prompt or 'Classify the email into categories.'
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": email_text}
    ]
    text = _call_openai(messages, temperature=0.0, max_tokens=300)
    if not text:
        return _mock_response('categorize')
    parsed = _extract_json_from_text(text)
    if parsed is not None:
        return parsed
    # fallback: try to parse whole text
    try:
        return json.loads(text)
    except Exception:
        return {"raw": text}


def extract_actions(email_text: str, prompt: str) -> List[Dict[str, Any]]:
    if not openai or not OPENAI_KEY:
        return _mock_response('extract')
    messages = [
        {"role": "system", "content": prompt or 'Extract action items.'},
        {"role": "user", "content": email_text}
    ]
    text = _call_openai(messages, temperature=0.0, max_tokens=500)
    if not text:
        return _mock_response('extract')
    parsed = _extract_json_from_text(text)
    if parsed is not None:
        return parsed
    try:
        return json.loads(text)
    except Exception:
        return [{"raw": text}]


def chat_with_email(email_text: str, prompts: Dict[str, Any], user_query: str) -> str:
    if not openai or not OPENAI_KEY:
        return f"[MOCK ANSWER] For query: {user_query}\n\n(Provide OPENAI_API_KEY to enable real LLM answers.)"
    system = prompts.get('chat_system_instructions') if prompts else 'You are the user\'s helpful email assistant.'
    # keep prompt context concise
    context_message = f"Email content:\n{email_text}\n\nUser query: {user_query}"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": context_message}
    ]
    text = _call_openai(messages, temperature=0.3, max_tokens=500)
    if not text:
        return '[OPENAI_ERROR] No response.'
    return text


def generate_draft(email_text: str, prompt: str, tone: str = 'friendly') -> Dict[str, Any]:
    if not openai or not OPENAI_KEY:
        return _mock_response('draft')
    # replace placeholder for tone when present
    try:
        prompt_text = prompt.replace('{{tone}}', tone)
    except Exception:
        prompt_text = prompt or ''
    messages = [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": email_text}
    ]
    text = _call_openai(messages, temperature=0.4, max_tokens=700)
    if not text:
        return _mock_response('draft')
    parsed = _extract_json_from_text(text)
    if parsed is not None:
        return parsed
    try:
        return json.loads(text)
    except Exception:
        return {"body": text}

