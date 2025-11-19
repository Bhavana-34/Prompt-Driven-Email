"""
Small test harness to run LLM functions against the mock inbox.
Run: `python run_llm_tests.py`
Requires OPENAI_API_KEY env var to test with real model; otherwise uses mock responses.
"""
import os
import json
from llm import categorize, extract_actions, generate_draft

BASE = os.path.dirname(__file__)
MOCK = os.path.join(BASE, 'data', 'mock_emails.json')

def load_mock():
    with open(MOCK, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    emails = load_mock()
    sample = emails[0]
    print('=== Sample Email ===')
    print(sample['subject'])
    print(sample['body'])
    print('\n=== Categorize ===')
    cat = categorize(sample['body'], open(os.path.join(BASE, 'prompts', 'default_prompts.json')).read())
    print(json.dumps(cat, indent=2))
    print('\n=== Extract Actions ===')
    prompts = json.load(open(os.path.join(BASE, 'prompts', 'default_prompts.json')))
    actions = extract_actions(sample['body'], prompts.get('action_item_prompt',''))
    print(json.dumps(actions, indent=2))
    print('\n=== Generate Draft ===')
    draft = generate_draft(sample['body'], prompts.get('auto_reply_prompt',''), tone='professional')
    print(json.dumps(draft, indent=2))

if __name__ == '__main__':
    main()
