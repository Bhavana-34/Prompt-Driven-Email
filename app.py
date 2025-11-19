import streamlit as st
from pathlib import Path
import os
import json
from db import init_db, load_mock_emails, get_emails, get_email, save_processed, get_processed, get_prompts, save_prompt, save_draft, get_drafts
import llm
from imap_ingest import fetch_imap_emails
import streamlit.components.v1 as components

BASE = Path(__file__).parent
DATA_DIR = BASE / 'data'
MOCK_PATH = DATA_DIR / 'mock_emails.json'

st.set_page_config(page_title='Email Productivity Agent', layout='wide', initial_sidebar_state='expanded')

def local_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        * {
            font-family: 'Inter', sans-serif;
        }
        
        .stApp { 
            background: linear-gradient(to bottom right, #0f0c29, #302b63, #24243e);
            color: #e0e0e0;
        }
        
        .main-header {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .glass-card {
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 16px;
            padding: 20px;
            margin: 15px 0;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .glass-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
            border-color: rgba(138, 180, 248, 0.5);
        }
        
        .email-card {
            background: linear-gradient(135deg, rgba(138, 180, 248, 0.1) 0%, rgba(83, 122, 255, 0.05) 100%);
            border-left: 4px solid #8ab4f8;
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            transition: all 0.3s ease;
        }
        
        .email-card:hover {
            border-left-width: 6px;
            box-shadow: 0 8px 30px rgba(138, 180, 248, 0.3);
        }
        
        .email-list-item {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 15px;
            margin: 10px 0;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .email-list-item:hover {
            background: rgba(138, 180, 248, 0.15);
            border-color: #8ab4f8;
            transform: translateX(5px);
        }
        
        .email-list-item.selected {
            background: linear-gradient(135deg, rgba(138, 180, 248, 0.25) 0%, rgba(83, 122, 255, 0.15) 100%);
            border: 2px solid #8ab4f8;
            box-shadow: 0 0 20px rgba(138, 180, 248, 0.4);
        }
        
        .category-badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: 5px;
            font-size: 0.85em;
            font-weight: 500;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .task-item {
            background: rgba(255, 255, 255, 0.08);
            border-left: 3px solid #4ade80;
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            backdrop-filter: blur(10px);
            box-shadow: 0 2px 10px rgba(74, 222, 128, 0.2);
        }
        
        .chat-container {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 16px;
            padding: 20px;
            max-height: 400px;
            overflow-y: auto;
            margin: 15px 0;
        }
        
        .chat-bubble-user {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 14px 18px;
            border-radius: 18px 18px 4px 18px;
            margin: 10px 0;
            max-width: 75%;
            margin-left: auto;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.2);
            font-size: 0.95em;
        }
        
        .chat-bubble-assistant {
            background: rgba(255, 255, 255, 0.1);
            color: #e0e0e0;
            padding: 14px 18px;
            border-radius: 18px 18px 18px 4px;
            margin: 10px 0;
            max-width: 75%;
            margin-right: auto;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.15);
            font-size: 0.95em;
        }
        
        .section-header {
            color: #8ab4f8;
            font-size: 1.4em;
            font-weight: 600;
            margin: 25px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(138, 180, 248, 0.5);
            text-shadow: 0 0 10px rgba(138, 180, 248, 0.5);
        }
        
        .stButton>button {
            border-radius: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 10px 24px;
            font-weight: 500;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
            border-color: rgba(255, 255, 255, 0.4);
        }
        
        .metric-card {
            background: linear-gradient(135deg, rgba(138, 180, 248, 0.15) 0%, rgba(83, 122, 255, 0.1) 100%);
            padding: 20px;
            border-radius: 16px;
            text-align: center;
            border: 1px solid rgba(138, 180, 248, 0.3);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        }
        
        .metric-value {
            font-size: 2.5em;
            font-weight: 700;
            color: #8ab4f8;
            text-shadow: 0 0 20px rgba(138, 180, 248, 0.6);
        }
        
        .metric-label {
            font-size: 0.9em;
            color: #b8b8b8;
            margin-top: 5px;
        }
        
        .stTextInput>div>div>input {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            color: #e0e0e0;
            padding: 12px;
        }
        
        .stTextInput>div>div>input:focus {
            border-color: #8ab4f8;
            box-shadow: 0 0 15px rgba(138, 180, 248, 0.3);
        }
        
        .stTextArea>div>div>textarea {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            color: #e0e0e0;
        }
        
        .stSelectbox>div>div {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            color: #e0e0e0;
        }
        
        .success-badge {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
            font-weight: 500;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
        }
        
        .warning-badge {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            display: inline-block;
            font-weight: 500;
            box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
        }
        
        h1, h2, h3 {
            color: #e0e0e0;
        }
        
        .muted {
            color: #9ca3af;
            font-size: 0.9em;
        }
        
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(138, 180, 248, 0.5);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(138, 180, 248, 0.8);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

local_css()

def _show_reload_script(delay_ms: int = 800):
    components.html(f"<script>setTimeout(function(){{location.reload();}}, {delay_ms});</script>", height=0)

def _friendly_imap_error(exc: Exception):
    msg = str(exc)
    if 'Application-specific password required' in msg or 'APP-PASSWORD' in msg or 'application-specific password' in msg.lower():
        st.error("🔒 Your provider requires an app-specific password. For Gmail: https://support.google.com/accounts/answer/185833")
    elif 'AUTHENTICATIONFAILED' in msg.upper():
        st.error('🔒 Authentication failed — verify credentials and enable IMAP')
    else:
        st.error(f'⚠️ IMAP Error: {msg}')

init_db()

# Sidebar Configuration
st.sidebar.markdown("<h2 style='text-align: center; color: #8ab4f8;'>⚙️ Configuration</h2>", unsafe_allow_html=True)

# LLM mode indicator
try:
    llm_key = getattr(llm, 'OPENAI_KEY', None)
    llm_model = getattr(llm, 'OPENAI_MODEL', 'unknown')
except Exception:
    llm_key = None
    llm_model = 'unknown'

if llm_key:
    st.sidebar.markdown(f"<div class='success-badge'>🤖 AI Active: {llm_model}</div>", unsafe_allow_html=True)
else:
    st.sidebar.markdown("<div class='warning-badge'>🤖 Mock Mode (No API Key)</div>", unsafe_allow_html=True)

st.sidebar.markdown('---')

prompts = get_prompts() or {}

with st.sidebar.expander('📝 Customize AI Prompts', expanded=False):
    st.markdown("*Fine-tune the AI behavior*")
    cat = st.text_area('Categorization', value=prompts.get('categorization_prompt', ''), height=100)
    act = st.text_area('Action Extraction', value=prompts.get('action_item_prompt', ''), height=100)
    auto = st.text_area('Auto-Reply', value=prompts.get('auto_reply_prompt', ''), height=100)
    chat_sys = st.text_area('Chat Instructions', value=prompts.get('chat_system_instructions', ''), height=80)
    if st.button('💾 Save Prompts'):
        try:
            save_prompt('categorization_prompt', cat)
            save_prompt('action_item_prompt', act)
            save_prompt('auto_reply_prompt', auto)
            save_prompt('chat_system_instructions', chat_sys)
            st.success('✅ Prompts saved!')
            prompts = get_prompts() or {}
        except Exception as e:
            st.error(f'❌ Error: {e}')

# Main Header
st.markdown("""
<div class='main-header'>
    <h1 style='text-align: center; color: #8ab4f8; font-size: 3em; margin: 0; text-shadow: 0 0 20px rgba(138, 180, 248, 0.5);'>
        📧 Email Productivity Agent
    </h1>
    <p style='text-align: center; color: #b8b8b8; font-size: 1.2em; margin-top: 10px;'>
        AI-Powered Email Intelligence Platform
    </p>
</div>
""", unsafe_allow_html=True)

# Quick Start Guide
with st.expander('👋 Quick Start Guide', expanded=False):
    col_guide1, col_guide2 = st.columns([1, 3])
    with col_guide1:
        st.markdown("### 🚀")
    with col_guide2:
        st.markdown("""
        **Get Started in 3 Steps:**
        
        1. **Load Data** → Click 'Load Mock Data' or connect via IMAP
        2. **Select Email** → Click any email from the inbox
        3. **Analyze** → Use AI to categorize, extract tasks, or chat
        """)
    
    col_a, col_b, col_c = st.columns(3)
    if col_a.button('📥 Load Demo', use_container_width=True):
        load_mock_emails(str(MOCK_PATH))
        try:
            st.experimental_rerun()
        except Exception:
            st.success('✅ Demo loaded!')
    
    if col_b.button('🧪 Test AI', use_container_width=True):
        try:
            emails_list = get_emails()
            if not emails_list:
                st.info('💡 Load demo first!')
            else:
                sample = emails_list[0]
                e = get_email(sample['id'])
                prompts = get_prompts()
                
                with st.spinner('🤖 AI Processing...'):
                    cat_out = llm.categorize(e.get('body',''), prompts.get('categorization_prompt',''))
                    act_out = llm.extract_actions(e.get('body',''), prompts.get('action_item_prompt',''))
                
                st.markdown(f"**📧 Test Email:** {e.get('subject')}")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown('**🏷️ Categories**')
                    st.json(cat_out)
                with col2:
                    st.markdown('**✅ Actions**')
                    st.json(act_out)
        except Exception as exc:
            st.error(f'⚠️ {exc}')
    
    if col_c.button('📚 Help', use_container_width=True):
        st.info('💡 Edit prompts in sidebar to customize AI. Use chat to interact naturally with emails!')

st.markdown("---")

# Main Layout
col1, col2 = st.columns([1, 2.5])

with col1:
    st.markdown("<div class='section-header'>📬 Inbox</div>", unsafe_allow_html=True)
    
    # Quick Actions
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button('📥 Load Mock', use_container_width=True):
            load_mock_emails(str(MOCK_PATH))
            try:
                st.experimental_rerun()
            except Exception:
                st.success('✅ Loaded!')
    
    with col_btn2:
        with st.popover("🌐 IMAP"):
            st.markdown("### Connect Email")
            provider = st.selectbox('Provider', ['Gmail', 'Outlook', 'Yahoo', 'iCloud', 'Custom'])
            provider_hosts = {
                'Gmail': 'imap.gmail.com',
                'Outlook': 'outlook.office365.com',
                'Yahoo': 'imap.mail.yahoo.com',
                'iCloud': 'imap.mail.me.com'
            }
            imap_server = st.text_input('Server', value=provider_hosts.get(provider, ''))
            imap_user = st.text_input('Email')
            imap_pass = st.text_input('Password', type='password')
            imap_limit = st.number_input('Max Messages', value=50, min_value=1, max_value=500)
            
            if provider == 'Gmail':
                st.info('💡 Use App Password with 2FA')
            
            col_t1, col_t2 = st.columns(2)
            if col_t1.button('🔍 Test'):
                import imaplib
                if imap_server and imap_user and imap_pass:
                    try:
                        with st.spinner('Testing...'):
                            M = imaplib.IMAP4_SSL(imap_server)
                            M.login(imap_user, imap_pass)
                            M.logout()
                        st.success('✅ Success!')
                    except Exception as e:
                        _friendly_imap_error(e)
                else:
                    st.error('⚠️ Fill all fields')
            
            if col_t2.button('📥 Fetch'):
                if imap_server and imap_user and imap_pass:
                    try:
                        with st.spinner('Fetching...'):
                            msgs = fetch_imap_emails(imap_server, imap_user, imap_pass, limit=imap_limit)
                            import sqlite3
                            init_db()
                            conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), 'data', 'email_agent.db'))
                            c = conn.cursor()
                            for m in msgs:
                                c.execute('SELECT 1 FROM emails WHERE id=?', (m['id'],))
                                if c.fetchone():
                                    continue
                                c.execute('INSERT INTO emails(id, sender, subject, timestamp, body) VALUES (?, ?, ?, ?, ?)',
                                          (m['id'], m['sender'], m['subject'], m['timestamp'], m['body']))
                            conn.commit()
                            conn.close()
                        st.success(f'✅ {len(msgs)} fetched!')
                        try:
                            st.experimental_rerun()
                        except:
                            _show_reload_script(800)
                    except Exception as e:
                        _friendly_imap_error(e)
                else:
                    st.error('⚠️ Fill all fields')
    
    # Email List
    emails = get_emails()
    st.markdown(f"<p style='color: #8ab4f8; font-weight: 600;'>📨 {len(emails)} Messages</p>", unsafe_allow_html=True)
    
    if 'selected_email' not in st.session_state:
        st.session_state['selected_email'] = None
    
    if emails:
        for e in emails:
            is_selected = st.session_state.get('selected_email') == e['id']
            preview = e.get('subject', '(no subject)')[:45]
            sender = e.get('sender', 'Unknown')[:25]
            
            if st.button(f"{'✉️' if is_selected else '📧'} {preview}", 
                        key=f"select-{e['id']}", 
                        use_container_width=True,
                        type='primary' if is_selected else 'secondary'):
                st.session_state['selected_email'] = e['id']
                try:
                    st.experimental_rerun()
                except:
                    st.rerun()
            
            st.markdown(f"<p class='muted'>From: {sender}</p>", unsafe_allow_html=True)
            if is_selected:
                st.markdown("<hr style='border: 2px solid #8ab4f8; margin: 8px 0;'>", unsafe_allow_html=True)
            else:
                st.markdown("---")
    else:
        st.info("📭 No emails. Load mock data to start!")
    
    selected = st.session_state.get('selected_email')

with col2:
    if selected:
        email = get_email(selected)
        
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        
        # Email Header
        st.markdown(f"<h2 style='color: #8ab4f8; margin-bottom: 15px;'>📧 {email.get('subject','(no subject)')}</h2>", unsafe_allow_html=True)
        
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            st.markdown(f"<p><strong>👤 From:</strong> {email.get('sender')}</p>", unsafe_allow_html=True)
        with col_meta2:
            st.markdown(f"<p><strong>🕐 Date:</strong> {email.get('timestamp')}</p>", unsafe_allow_html=True)
        
        # Categories and Tasks
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
                st.markdown("**🏷️ Categories:**")
                for c in cats_list:
                    st.markdown(f"<span class='category-badge'>{c}</span>", unsafe_allow_html=True)
            
            if tasks:
                st.markdown("**✅ Action Items:**", unsafe_allow_html=True)
                for t in tasks:
                    task_text = t.get('task') or t.get('raw', 'Task')
                    st.markdown(f"<div class='task-item'>📌 {task_text}</div>", unsafe_allow_html=True)
        
        # Email Body
        st.markdown("**📄 Content:**")
        st.markdown(f"<div class='email-card'><pre style='white-space: pre-wrap; color: #e0e0e0;'>{email.get('body')}</pre></div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # AI Processing Section
        st.markdown("<div class='section-header'>🤖 AI Actions</div>", unsafe_allow_html=True)
        
        col_act1, col_act2, col_act3 = st.columns(3)
        
        with col_act1:
            if st.button('🔍 Analyze', use_container_width=True):
                db_prompts = get_prompts()
                with st.spinner('🤖 Analyzing...'):
                    categories = llm.categorize(email.get('body',''), db_prompts.get('categorization_prompt', ''))
                    tasks = llm.extract_actions(email.get('body',''), db_prompts.get('action_item_prompt', ''))
                    save_processed(selected, categories, tasks)
                st.success('✅ Done!')
                try:
                    st.experimental_rerun()
                except:
                    st.rerun()
        
        with col_act2:
            tone = st.selectbox('Tone', ['friendly','professional','concise','formal'], key='tone_select')
        
        with col_act3:
            if st.button('✍️ Draft', use_container_width=True):
                db_prompts = get_prompts()
                with st.spinner('✍️ Drafting...'):
                    draft = llm.generate_draft(email.get('body',''), db_prompts.get('auto_reply_prompt', ''), tone)
                    subj = draft.get('subject') or f"Re: {email.get('subject','')}"
                    body = draft.get('body') or draft.get('text') or str(draft)
                    save_draft(selected, subj, body, {'generated_by': 'llm', 'tone': tone})
                st.success('✅ Draft saved!')
                try:
                    st.experimental_rerun()
                except:
                    st.rerun()
        
        # View Drafts
        if st.button('📝 View Drafts', use_container_width=True):
            drafts = get_drafts(selected)
            if drafts:
                for d in drafts:
                    st.markdown(f"<div class='glass-card'><strong>Draft #{d['id']}</strong> — {d['subject']}</div>", unsafe_allow_html=True)
                    st.text_area(f"Draft {d['id']}", value=d['body'], height=120, key=f"draft_{d['id']}")
            else:
                st.info("No drafts yet!")
        
        # Chat Assistant
        st.markdown("<div class='section-header'>💬 AI Chat</div>", unsafe_allow_html=True)
        
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        col_input, col_send = st.columns([5, 1])
        with col_input:
            user_q = st.text_input('Ask anything...', placeholder='e.g., Summarize this email', key='chat_input', label_visibility='collapsed')
        with col_send:
            send_clicked = st.button('💬', use_container_width=True, key='send_chat')
        
        if send_clicked and user_q and user_q.strip():
            db_prompts = get_prompts()
            with st.spinner('🤖 Thinking...'):
                answer = llm.chat_with_email(email.get('body',''), db_prompts, user_q)
                st.session_state.chat_history.append({'user': user_q, 'assistant': answer})
            try:
                st.experimental_rerun()
            except:
                st.rerun()
        
        # Chat History
        if st.session_state.chat_history:
            st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
            for m in st.session_state.chat_history:
                st.markdown(f"<div class='chat-bubble-user'>{m['user']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='chat-bubble-assistant'>{m['assistant']}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            if st.button('🗑️ Clear Chat'):
                st.session_state.chat_history = []
                try:
                    st.experimental_rerun()
                except:
                    st.rerun()
        else:
            st.info("💡 Start chatting! Ask about tasks, summaries, or anything else.")
        
        # Prompt Tester
        st.markdown("<div class='section-header'>🧪 Prompt Lab</div>", unsafe_allow_html=True)
        
        col_p1, col_p2 = st.columns([2, 1])
        with col_p1:
            prompt_type = st.selectbox('Test Prompt', ['categorization_prompt','action_item_prompt','auto_reply_prompt','chat_system_instructions'])
        with col_p2:
            test_tone = st.selectbox('Tone', ['friendly','professional','concise','formal'], key='test_tone')
        
        tester_input = st.text_area('Input', value=email.get('body','')[:300], height=100)
        
        if st.button('🚀 Run Test', use_container_width=True):
            with st.spinner('🧪 Testing...'):
                try:
                    tester_prompt = get_prompts().get(prompt_type, '')
                    
                    if prompt_type == 'categorization_prompt':
                        out = llm.categorize(tester_input, tester_prompt)
                        st.markdown("**📊 Categorization Results:**")
                    elif prompt_type == 'action_item_prompt':
                        out = llm.extract_actions(tester_input, tester_prompt)
                        st.markdown("**✅ Extracted Actions:**")
                    elif prompt_type == 'auto_reply_prompt':
                        out = llm.generate_draft(tester_input, tester_prompt, test_tone)
                        st.markdown("**✍️ Generated Draft:**")
                    else:
                        out = llm.chat_with_email(tester_input, get_prompts(), 'Summarize')
                        st.markdown("**💬 Chat Response:**")
                    
                    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                    try:
                        st.json(out)
                    except:
                        st.code(str(out), language='text')
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.success('✅ Test complete!')
                except Exception as e:
                    st.error(f'❌ Test failed: {str(e)}')
    
    else:
        # No email selected
        st.markdown("<div class='glass-card' style='padding: 40px;'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #8ab4f8;'>📬 Select an Email</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #9ca3af;'>Choose an email from the inbox to view details and use AI features</p>", unsafe_allow_html=True)
        
        # Stats Dashboard
        st.markdown("<div style='margin-top: 30px;'>", unsafe_allow_html=True)
        emails = get_emails()
        col_s1, col_s2, col_s3 = st.columns(3)
        
        with col_s1:
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value'>{len(emails)}</div>
                <div class='metric-label'>Total Emails</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_s2:
            processed_count = sum(1 for e in emails if get_processed(e['id']))
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value'>{processed_count}</div>
                <div class='metric-label'>Processed</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_s3:
            draft_count = sum(len(get_drafts(e['id']) or []) for e in emails)
            st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-value'>{draft_count}</div>
                <div class='metric-label'>Drafts Generated</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #9ca3af; padding: 20px;'>
    <p>🤖 Powered by AI • Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)
