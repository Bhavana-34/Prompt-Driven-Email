import sqlite3
import json
import os
from typing import List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'email_agent.db')

def init_db():
    os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS emails (id INTEGER PRIMARY KEY, sender TEXT, subject TEXT, timestamp TEXT, body TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS processed (email_id INTEGER PRIMARY KEY, categories TEXT, tasks TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS prompts (name TEXT PRIMARY KEY, content TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS drafts (id INTEGER PRIMARY KEY AUTOINCREMENT, email_id INTEGER, subject TEXT, body TEXT, metadata TEXT)''')
    conn.commit()
    conn.close()

def load_mock_emails(json_path: str):
    init_db()
    with open(json_path, 'r', encoding='utf-8') as f:
        emails = json.load(f)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for e in emails:
        c.execute('SELECT 1 FROM emails WHERE id=?', (e['id'],))
        if c.fetchone():
            continue
        c.execute('INSERT INTO emails(id, sender, subject, timestamp, body) VALUES (?, ?, ?, ?, ?)',
                  (e['id'], e['sender'], e['subject'], e['timestamp'], e['body']))
    conn.commit()
    conn.close()

def get_emails() -> List[Dict[str, Any]]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute('SELECT id, sender, subject, timestamp FROM emails ORDER BY timestamp DESC').fetchall()
    conn.close()
    return [{'id': r[0], 'sender': r[1], 'subject': r[2], 'timestamp': r[3]} for r in rows]

def get_email(email_id: int) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    r = c.execute('SELECT id, sender, subject, timestamp, body FROM emails WHERE id=?', (email_id,)).fetchone()
    conn.close()
    if not r:
        return {}
    return {'id': r[0], 'sender': r[1], 'subject': r[2], 'timestamp': r[3], 'body': r[4]}

def save_processed(email_id: int, categories: Dict[str, Any], tasks: List[Dict[str, Any]]):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('REPLACE INTO processed(email_id, categories, tasks) VALUES (?, ?, ?)',
              (email_id, json.dumps(categories), json.dumps(tasks)))
    conn.commit()
    conn.close()

def get_processed(email_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    r = c.execute('SELECT categories, tasks FROM processed WHERE email_id=?', (email_id,)).fetchone()
    conn.close()
    if not r:
        return None
    return {'categories': json.loads(r[0]), 'tasks': json.loads(r[1])}

def get_prompts():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute('SELECT name, content FROM prompts').fetchall()
    conn.close()
    if not rows:
        # load defaults from prompts/default_prompts.json if present
        try:
            base = os.path.join(os.path.dirname(__file__), 'prompts', 'default_prompts.json')
            with open(base, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # seed DB with raw string content
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            for k, v in data.items():
                # ensure we store a string
                content = v if isinstance(v, str) else json.dumps(v)
                c.execute('INSERT OR REPLACE INTO prompts(name, content) VALUES (?, ?)', (k, content))
            conn.commit()
            conn.close()
            return {k: (v if isinstance(v, str) else json.dumps(v)) for k, v in data.items()}
        except Exception:
            return {}
    result = {}
    for r in rows:
        # return content as raw string
        result[r[0]] = r[1]
    return result

def save_prompt(name: str, content: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('REPLACE INTO prompts(name, content) VALUES (?, ?)', (name, content))
    conn.commit()
    conn.close()

def save_draft(email_id: int, subject: str, body: str, metadata: Dict[str, Any]=None):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO drafts(email_id, subject, body, metadata) VALUES (?, ?, ?, ?)',
              (email_id, subject, body, json.dumps(metadata or {})))
    conn.commit()
    conn.close()

def get_drafts(email_id: int):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute('SELECT id, subject, body, metadata FROM drafts WHERE email_id=? ORDER BY id DESC', (email_id,)).fetchall()
    conn.close()
    return [{'id': r[0], 'subject': r[1], 'body': r[2], 'metadata': json.loads(r[3])} for r in rows]
