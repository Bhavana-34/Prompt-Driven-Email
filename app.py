import streamlit as st
from pathlib import Path
import os
import json
from db import init_db, load_mock_emails, get_emails, get_email, save_processed, get_processed, get_prompts, save_prompt, save_draft, get_drafts
import llm
from imap_ingest import fetch_imap_emails

BASE = Path(__file__).parent
DATA_DIR = BASE / 'data'
MOCK_PATH = DATA_DIR / 'mock_emails.json'

st.set_page_config(page_title='Email Productivity Agent', layout='wide')

def local_css():
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(135deg,#f7f8fc,#e6f2ff); }
        .email-card { padding: 10px; border-radius:8px; background: white; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
        .muted { color: #6b7280; }
        </style>
        """,
        unsafe_allow_html=True,
    )

local_css()

init_db()

st.sidebar.title('Prompts')
prompts = get_prompts() or {}

with st.sidebar.expander('Edit Prompts'):
    # prompts are stored as raw strings
    cat = st.text_area('Categorization Prompt', value=prompts.get('categorization_prompt', ''), height=140)
    act = st.text_area('Action Extraction Prompt', value=prompts.get('action_item_prompt', ''), height=140)
    auto = st.text_area('Auto-reply Prompt', value=prompts.get('auto_reply_prompt', ''), height=140)
    chat_sys = st.text_area('Chat System Instructions', value=prompts.get('chat_system_instructions', ''), height=100)
    if st.button('Save Prompts'):
        try:
            save_prompt('categorization_prompt', cat)
            save_prompt('action_item_prompt', act)
            save_prompt('auto_reply_prompt', auto)
            save_prompt('chat_system_instructions', chat_sys)
            st.success('Prompts saved.')
            # refresh local copy
            prompts = get_prompts() or {}
        except Exception as e:
            st.error(f'Error saving prompts: {e}')

st.title('Email Productivity Agent')

col1, col2 = st.columns([2,6])

with col1:
    st.header('Inbox')
    if st.button('Load mock inbox'):
        load_mock_emails(str(MOCK_PATH))
        st.experimental_rerun()
    st.markdown('**Inbox controls**')
    with st.expander('IMAP Ingest (read-only)'):
        st.write('Fetch emails from an IMAP server into the local DB (read-only). Credentials are not stored by the app. Use app passwords or OAuth when possible.')
        imap_server = st.text_input('IMAP server (e.g., imap.gmail.com)')
        imap_user = st.text_input('Username (email)')
        imap_pass = st.text_input('Password / App password', type='password')
        imap_limit = st.number_input('Max messages to fetch', value=50, min_value=1, max_value=500)
        if st.button('Fetch from IMAP'):
            if not (imap_server and imap_user and imap_pass):
                st.error('Please provide IMAP server, username, and password.')
            else:
                st.info('Connecting to IMAP (read-only)...')
                try:
                    msgs = fetch_imap_emails(imap_server, imap_user, imap_pass, limit=imap_limit)
                    # write into local DB
                    from db import init_db, get_email as db_get_email, save_processed
                    import sqlite3, os
                    init_db()
                    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'data', 'email_agent.db'))
                    c = conn.cursor()
                    for m in msgs:
                        c.execute('SELECT 1 FROM emails WHERE id=?', (m['id'],))
                        if c.fetchone():
                            continue
                        c.execute('INSERT INTO emails(id, sender, subject, timestamp, body) VALUES (?, ?, ?, ?, ?)',
                                  (m['id'], m['sender'], m['subject'], m['timestamp'], m['body']))
                    conn.commit(); conn.close()
                    st.success(f'Fetched {len(msgs)} messages.')
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f'IMAP error: {e}')
    emails = get_emails()
    # show a nicer list with previews and small badges
    st.markdown('**Messages**')
    for e in emails:
        preview = e.get('subject')
        st.button(f"{e['id']}: {preview}", key=f"select-{e['id']}")
    selected_ids = [k for k in st.session_state.keys() if k.startswith('select-') and st.session_state[k]]
    selected = None
    if selected_ids:
        # pick last clicked
        last = selected_ids[-1]
        selected = int(last.split('-')[1])
    st.markdown('---')
    st.write('Filter by category suggestion: (use chat query to get all urgent)')

with col2:
    if selected:
        email = get_email(selected)
        st.subheader(email.get('subject','(no subject)'))
        st.write(f"**From:** {email.get('sender')}    **At:** {email.get('timestamp')}")
        # show stored categories and tasks if available
        proc = get_processed(selected)
        if proc:
            cats = proc.get('categories')
            tasks = proc.get('tasks')
            if isinstance(cats, dict) and 'categories' in cats:
                cats_list = cats.get('categories', [])
            elif isinstance(cats, list):
                cats_list = cats
            else:
                cats_list = []
            if cats_list:
                for c in cats_list:
                    st.markdown(f"<span style='display:inline-block;padding:4px 8px;border-radius:8px;background:#eef2ff;color:#3730a3;margin-right:6px'>{c}</span>", unsafe_allow_html=True)
            if tasks:
                st.markdown('**Extracted tasks**')
                for t in tasks:
                    st.write(f"- {t.get('task') or t.get('raw')}")
        st.markdown(f"<div class='email-card'><pre>{email.get('body')}</pre></div>", unsafe_allow_html=True)


        st.markdown('**Processing**')
        proc = get_processed(selected)
        if proc:
            st.info('This email was processed previously.')
            st.json(proc)
        if st.button('Run Categorize & Extract'):
            # read prompts from DB
            db_prompts = get_prompts()
            cat_prompt = db_prompts.get('categorization_prompt') or ''
            act_prompt = db_prompts.get('action_item_prompt') or ''
            # if stored as JSON string, try to parse
            if isinstance(cat_prompt, (dict, list)):
                cat_prompt = json.dumps(cat_prompt)
            if isinstance(act_prompt, (dict, list)):
                act_prompt = json.dumps(act_prompt)
            st.info('Calling LLM to categorize...')
            categories = llm.categorize(email.get('body',''), cat_prompt)
            st.info('Calling LLM to extract action items...')
            tasks = llm.extract_actions(email.get('body',''), act_prompt)
            save_processed(selected, categories, tasks)
            st.success('Processed and saved.')
            st.experimental_rerun()

        st.markdown('---')
        st.subheader('Chat Assistant')
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        user_q = st.text_input('Ask about this email (e.g., "Summarize", "What tasks?")')
        tone = st.selectbox('Reply tone (for drafts)', ['friendly','professional','concise','formal'])
        cols = st.columns([1,1,1])
        if cols[0].button('Ask') and user_q.strip():
            db_prompts = get_prompts()
            # if stored as strings
            for k,v in db_prompts.items():
                if isinstance(v, str):
                    try:
                        db_prompts[k] = json.loads(v)
                    except Exception:
                        db_prompts[k] = v
            st.info('Calling LLM for chat response...')
            answer = llm.chat_with_email(email.get('body',''), db_prompts, user_q)
            st.session_state.chat_history.append({'user': user_q, 'assistant': answer})
        if cols[1].button('Generate Draft'):
            db_prompts = get_prompts()
            auto_prompt = db_prompts.get('auto_reply_prompt') or ''
            if isinstance(auto_prompt, (dict, list)):
                auto_prompt = json.dumps(auto_prompt)
            st.info('Generating draft...')
            draft = llm.generate_draft(email.get('body',''), auto_prompt, tone)
            subj = draft.get('subject') or f"Re: {email.get('subject','') }"
            body = draft.get('body') or draft.get('text') or str(draft)
            save_draft(selected, subj, body, {'generated_by': 'llm', 'tone': tone})
            st.success('Draft generated and saved.')
            st.experimental_rerun()

        if cols[2].button('Show drafts'):
            drafts = get_drafts(selected)
            for d in drafts:
                st.markdown('---')
                st.markdown(f"**Draft {d['id']}** — Subject: {d['subject']}")
                st.text_area(f"Draft body {d['id']}", value=d['body'], height=150)

        # Prompt testing panel
        st.markdown('---')
        st.subheader('Prompt tester')
        prompt_type = st.selectbox('Prompt to test', ['categorization_prompt','action_item_prompt','auto_reply_prompt','chat_system_instructions'])
        tester_prompt = get_prompts().get(prompt_type, '')
        tester_input = st.text_area('Input to run (email body)', value=email.get('body',''), height=140)
        if st.button('Run prompt test'):
            st.info('Running prompt test...')
            if prompt_type == 'categorization_prompt':
                out = llm.categorize(tester_input, tester_prompt)
                st.json(out)
            elif prompt_type == 'action_item_prompt':
                out = llm.extract_actions(tester_input, tester_prompt)
                st.json(out)
            elif prompt_type == 'auto_reply_prompt':
                out = llm.generate_draft(tester_input, tester_prompt, tone)
                st.json(out)
            else:
                out = llm.chat_with_email(tester_input, get_prompts(), 'Summarize this email')
                st.write(out)

        st.markdown('**Chat history**')
        for m in st.session_state.chat_history:
            st.markdown(f"**You:** {m['user']}")
            st.markdown(f"**Assistant:** {m['assistant']}")
