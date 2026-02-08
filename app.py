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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            color: #ffffff;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #a8edea 0%, #fed6e3 100%);
        }
        
        [data-testid="stSidebar"] * {
            color: #2d3748 !important;
        }
        
        [data-testid="stSidebar"] h2 {
            color: #5a67d8 !important;
        }
        
        [data-testid="stSidebar"] .stTextArea textarea,
        [data-testid="stSidebar"] .stTextInput input {
            background: rgba(255, 255, 255, 0.7) !important;
            color: #2d3748 !important;
            border: 2px solid #cbd5e0 !important;
        }
        
        [data-testid="stSidebar"] .stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
        }
        
        /* Fix all input text colors - CRITICAL FIX */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stNumberInput > div > div > input {
            color: #ffffff !important;
            background: rgba(0, 0, 0, 0.3) !important;
            border: 2px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 12px !important;
            padding: 12px !important;
            font-weight: 500 !important;
        }
        
        .stTextInput > div > div > input::placeholder,
        .stTextArea > div > div > textarea::placeholder {
            color: rgba(255, 255, 255, 0.6) !important;
        }
        
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus,
        .stNumberInput > div > div > input:focus {
            border-color: #ffffff !important;
            background: rgba(0, 0, 0, 0.4) !important;
            box-shadow: 0 0 20px rgba(255, 255, 255, 0.4) !important;
            outline: none !important;
        }
        
        /* Extra specificity for chat input */
        input[type="text"],
        textarea {
            color: #ffffff !important;
            background: rgba(0, 0, 0, 0.3) !important;
        }
        
        /* Fix selectbox styling */
        .stSelectbox > div > div,
        .stSelectbox [data-baseweb="select"] {
            background: rgba(0, 0, 0, 0.3) !important;
            color: #ffffff !important;
            border: 2px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 12px !important;
        }
        
        .stSelectbox [data-baseweb="select"] > div {
            background: transparent !important;
            color: #ffffff !important;
        }
        
        .stSelectbox [data-baseweb="select"] svg {
            fill: #ffffff !important;
        }
        
        /* Dropdown menu styling */
        [data-baseweb="popover"] {
            background: rgba(102, 126, 234, 0.98) !important;
            backdrop-filter: blur(20px);
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 12px;
        }
        
        [data-baseweb="menu"] {
            background: transparent !important;
        }
        
        [role="option"] {
            color: #ffffff !important;
            background: transparent !important;
            padding: 12px 16px !important;
        }
        
        [role="option"]:hover {
            background: rgba(255, 255, 255, 0.25) !important;
        }
        
        .main-header {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(168, 237, 234, 0.95) 100%);
            backdrop-filter: blur(20px);
            border: 2px solid rgba(255, 255, 255, 0.5);
            border-radius: 24px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
        }
        
        .main-header h1 {
            color: #5a67d8 !important;
        }
        
        .main-header p {
            color: #4a5568 !important;
        }
        
        .glass-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(254, 214, 227, 0.9) 100%);
            backdrop-filter: blur(20px);
            border: 2px solid rgba(255, 255, 255, 0.5);
            border-radius: 20px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .glass-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
        }
        
        .glass-card * {
            color: #2d3748 !important;
        }
        
        .email-preview-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.85) 0%, rgba(168, 237, 234, 0.85) 100%);
            border: 2px solid rgba(102, 126, 234, 0.3);
            border-radius: 16px;
            padding: 16px;
            margin: 12px 0;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .email-preview-card:hover {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(168, 237, 234, 0.95) 100%);
            transform: translateX(5px);
            box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
        }
        
        .email-preview-card.selected {
            background: linear-gradient(135deg, rgba(168, 237, 234, 0.95) 0%, rgba(254, 214, 227, 0.95) 100%);
            border: 2px solid #667eea;
            box-shadow: 0 0 30px rgba(102, 126, 234, 0.5);
        }
        
        .email-preview-card * {
            color: #2d3748 !important;
        }
        
        .category-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            margin: 5px;
            font-size: 0.85em;
            font-weight: 600;
            border: 1px solid rgba(255, 255, 255, 0.3);
            box-shadow: 0 2px 10px rgba(240, 147, 251, 0.4);
        }
        
        .task-item {
            background: linear-gradient(135deg, rgba(168, 237, 234, 0.8) 0%, rgba(254, 214, 227, 0.8) 100%);
            border-left: 4px solid #48bb78;
            padding: 16px;
            margin: 12px 0;
            border-radius: 12px;
            color: #2d3748;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .chat-container {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.85) 0%, rgba(254, 214, 227, 0.85) 100%);
            border: 2px solid rgba(255, 255, 255, 0.5);
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
            border: 1px solid rgba(255, 255, 255, 0.3);
            font-size: 0.95em;
            box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
        }
        
        .chat-bubble-assistant {
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
            color: #2d3748;
            padding: 14px 18px;
            border-radius: 18px 18px 18px 4px;
            margin: 10px 0;
            max-width: 75%;
            margin-right: auto;
            border: 1px solid rgba(168, 237, 234, 0.5);
            font-size: 0.95em;
            box-shadow: 0 2px 10px rgba(168, 237, 234, 0.3);
        }
        
        .section-header {
            color: #ffffff;
            font-size: 1.6em;
            font-weight: 700;
            margin: 30px 0 20px 0;
            padding-bottom: 12px;
            border-bottom: 3px solid rgba(255, 255, 255, 0.6);
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        }
        
        .stButton>button {
            border-radius: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            border: 2px solid rgba(255, 255, 255, 0.3);
            padding: 12px 28px;
            font-weight: 600;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        
        .stButton>button:hover {
            background: linear-gradient(135deg, #764ba2 0%, #f093fb 100%);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
        }
        
        .metric-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(240, 147, 251, 0.8) 100%);
            padding: 25px;
            border-radius: 20px;
            text-align: center;
            border: 2px solid rgba(255, 255, 255, 0.5);
            box-shadow: 0 4px 20px rgba(102, 126, 234, 0.2);
        }
        
        .metric-value {
            font-size: 3em;
            font-weight: 700;
            color: #5a67d8;
            text-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
        }
        
        .metric-label {
            font-size: 1em;
            color: #4a5568;
            margin-top: 8px;
            font-weight: 500;
        }
        
        .success-badge {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            display: inline-block;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .warning-badge {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            display: inline-block;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: #ffffff !important;
        }
        
        .muted {
            color: rgba(255, 255, 255, 0.7);
            font-size: 0.9em;
        }
        
        p, span, div, label {
            color: #ffffff;
        }
        
        .stExpander {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 12px;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.4);
            border-radius: 5px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.6);
        }
        
        /* Email detail view */
        .email-detail-header {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(168, 237, 234, 0.9) 100%);
            padding: 25px;
            border-radius: 20px;
            margin-bottom: 20px;
            border: 2px solid rgba(102, 126, 234, 0.3);
            box-shadow: 0 4px 20px rgba(102, 126, 234, 0.2);
        }
        
        .email-detail-header * {
            color: #2d3748 !important;
        }
        
        .email-detail-header h2 {
            color: #5a67d8 !important;
        }
        
        .back-button {
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 12px;
            padding: 10px 20px;
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .back-button:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateX(-5px);
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

# Initialize session state
if 'selected_email' not in st.session_state:
    st.session_state['selected_email'] = None
if 'view_mode' not in st.session_state:
    st.session_state['view_mode'] = 'inbox'  # 'inbox' or 'detail'
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Sidebar Configuration
st.sidebar.markdown("<h2 style='text-align: center; color: #ffffff;'>⚙️ Configuration</h2>", unsafe_allow_html=True)

# LLM mode indicator
try:
    llm_key = getattr(llm, 'OPENAI_KEY', None)
    llm_model = getattr(llm, 'OPENAI_MODEL', 'unknown')
    try:
        secrets_key = st.secrets.get('OPENAI_API_KEY') if st.secrets else None
        if secrets_key and not llm_key:
            llm_key = secrets_key
    except Exception:
        pass
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
    <h1 style='text-align: center; color: #ffffff; font-size: 3.5em; margin: 0; text-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);'>
        📧 Email Productivity Agent
    </h1>
    <p style='text-align: center; color: rgba(255, 255, 255, 0.9); font-size: 1.3em; margin-top: 10px;'>
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
        st.success('✅ Demo loaded!')
        st.rerun()
    
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

# View Mode Logic
if st.session_state.view_mode == 'inbox':
    # INBOX VIEW
    col_top1, col_top2 = st.columns([2, 1])
    
    with col_top1:
        st.markdown("<div class='section-header'>📬 Email Inbox</div>", unsafe_allow_html=True)
    
    with col_top2:
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button('📥 Load Mock', use_container_width=True):
                load_mock_emails(str(MOCK_PATH))
                st.success('✅ Loaded!')
                st.rerun()
        
        with col_btn2:
            with st.expander("🌐 IMAP", expanded=False):
                st.markdown("### Connect Email")
                provider = st.selectbox('Provider', ['Gmail', 'Outlook', 'Yahoo', 'iCloud', 'Custom'])
                provider_hosts = {
                    'Gmail': 'imap.gmail.com',
                    'Outlook': 'outlook.office365.com',
                    'Yahoo': 'imap.mail.yahoo.com',
                    'iCloud': 'imap.mail.me.com'
                }
                try:
                    secrets = st.secrets if st.secrets else {}
                except Exception:
                    secrets = {}
                imap_server_default = os.getenv('IMAP_SERVER') or secrets.get('IMAP_SERVER', provider_hosts.get(provider, ''))
                imap_user_default = os.getenv('IMAP_USERNAME') or secrets.get('IMAP_USERNAME', '')
                imap_pass_default = os.getenv('IMAP_PASSWORD') or secrets.get('IMAP_PASSWORD', '')
                imap_limit_default = os.getenv('IMAP_LIMIT') or secrets.get('IMAP_LIMIT', 50)
                try:
                    imap_limit_default = int(imap_limit_default)
                except Exception:
                    imap_limit_default = 50
                imap_server = st.text_input('Server', value=imap_server_default)
                imap_user = st.text_input('Email', value=imap_user_default)
                imap_pass = st.text_input('Password', type='password', value=imap_pass_default)
                imap_limit = st.number_input('Max Messages', value=imap_limit_default, min_value=1, max_value=500)
                
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
                            st.rerun()
                        except Exception as e:
                            _friendly_imap_error(e)
                    else:
                        st.error('⚠️ Fill all fields')
    
    # Stats Dashboard
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
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Email List with better organization
    if emails:
        st.markdown(f"<p style='color: #ffffff; font-weight: 600; font-size: 1.1em;'>📨 {len(emails)} Messages</p>", unsafe_allow_html=True)
        
        # Show emails in a grid
        for idx, e in enumerate(emails):
            col_email, col_btn = st.columns([5, 1])
            
            with col_email:
                preview = e.get('subject', '(no subject)')[:60]
                sender = e.get('sender', 'Unknown')
                timestamp = e.get('timestamp', '')
                
                st.markdown(f"""
                <div class='email-preview-card'>
                    <div style='font-weight: 600; font-size: 1.1em; margin-bottom: 5px;'>📧 {preview}</div>
                    <div style='color: rgba(255, 255, 255, 0.7); font-size: 0.9em;'>From: {sender}</div>
                    <div style='color: rgba(255, 255, 255, 0.6); font-size: 0.85em;'>{timestamp}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_btn:
                if st.button('Open →', key=f"open-{e['id']}", use_container_width=True):
                    st.session_state['selected_email'] = e['id']
                    st.session_state['view_mode'] = 'detail'
                    st.session_state.chat_history = []
                    st.rerun()
    else:
        st.info("📭 No emails. Load mock data to start!")

else:
    # DETAIL VIEW
    selected = st.session_state.get('selected_email')
    
    if st.button('← Back to Inbox', key='back_to_inbox'):
        st.session_state['view_mode'] = 'inbox'
        st.session_state['selected_email'] = None
        st.rerun()
    
    if selected:
        email = get_email(selected)
        
        st.markdown("<div class='email-detail-header'>", unsafe_allow_html=True)
        
        # Email Header
        st.markdown(f"<h2 style='color: #ffffff; margin-bottom: 15px;'>📧 {email.get('subject','(no subject)')}</h2>", unsafe_allow_html=True)
        
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            st.markdown(f"<p><strong>👤 From:</strong> {email.get('sender')}</p>", unsafe_allow_html=True)
        with col_meta2:
            st.markdown(f"<p><strong>🕐 Date:</strong> {email.get('timestamp')}</p>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Email Content
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("**📄 Email Content:**")
        st.markdown(f"<pre style='white-space: pre-wrap; color: #ffffff; background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px;'>{email.get('body')}</pre>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Categories and Tasks
        proc = get_processed(selected)
        if proc:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            
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
                st.markdown("<br>**✅ Action Items:**", unsafe_allow_html=True)
                for t in tasks:
                    task_text = t.get('task') or t.get('raw', 'Task')
                    st.markdown(f"<div class='task-item'>📌 {task_text}</div>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # AI Processing Section
        st.markdown("<div class='section-header'>🤖 AI Actions</div>", unsafe_allow_html=True)
        
        col_act1, col_act2, col_act3 = st.columns(3)
        
        with col_act1:
            if st.button('🔍 Analyze Email', use_container_width=True):
                db_prompts = get_prompts()
                with st.spinner('🤖 Analyzing...'):
                    categories = llm.categorize(email.get('body',''), db_prompts.get('categorization_prompt', ''))
                    tasks = llm.extract_actions(email.get('body',''), db_prompts.get('action_item_prompt', ''))
                    save_processed(selected, categories, tasks)
                st.success('✅ Analysis complete!')
                st.rerun()
        
        with col_act2:
            tone = st.selectbox('Reply Tone', ['friendly','professional','concise','formal'], key='tone_select')
        
        with col_act3:
            if st.button('✍️ Generate Draft', use_container_width=True):
                db_prompts = get_prompts()
                with st.spinner('✍️ Drafting...'):
                    draft = llm.generate_draft(email.get('body',''), db_prompts.get('auto_reply_prompt', ''), tone)
                    subj = draft.get('subject') or f"Re: {email.get('subject','')}"
                    body = draft.get('body') or draft.get('text') or str(draft)
                    save_draft(selected, subj, body, {'generated_by': 'llm', 'tone': tone})
                st.success('✅ Draft saved!')
                st.rerun()
        
        # View Drafts Section
        st.markdown("<div class='section-header'>📝 Generated Drafts</div>", unsafe_allow_html=True)
        
        drafts = get_drafts(selected)
        if drafts:
            for d in drafts:
                with st.expander(f"📄 Draft #{d['id']} - {d['subject']}", expanded=False):
                    st.text_area(f"Draft Content {d['id']}", value=d['body'], height=200, key=f"draft_{d['id']}")
        else:
            st.info("No drafts yet. Click 'Generate Draft' to create one!")
        
        # Chat Assistant
        st.markdown("<div class='section-header'>💬 AI Chat Assistant</div>", unsafe_allow_html=True)
        
        # Chat History Display
        if st.session_state.chat_history:
            st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
            for m in st.session_state.chat_history:
                st.markdown(f"<div class='chat-bubble-user'><strong>You:</strong><br>{m['user']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='chat-bubble-assistant'><strong>AI:</strong><br>{m['assistant']}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("💡 Start chatting! Ask about summaries, tasks, or anything else about this email.")
        
        # Chat Input
        col_input, col_send = st.columns([5, 1])
        with col_input:
            user_q = st.text_input('Ask anything about this email...', placeholder='e.g., Summarize this email in 3 sentences', key='chat_input', label_visibility='collapsed')
        with col_send:
            send_clicked = st.button('Send 💬', use_container_width=True, key='send_chat')
        
        if send_clicked and user_q and user_q.strip():
            db_prompts = get_prompts()
            with st.spinner('🤖 Thinking...'):
                answer = llm.chat_with_email(email.get('body',''), db_prompts, user_q)
                st.session_state.chat_history.append({'user': user_q, 'assistant': answer})
            st.rerun()
        
        if st.session_state.chat_history:
            if st.button('🗑️ Clear Chat History'):
                st.session_state.chat_history = []
                st.rerun()
        
        # Prompt Tester
        with st.expander("🧪 Prompt Lab - Test AI Prompts", expanded=False):
            st.markdown("### Test and experiment with different AI prompts")
            
            col_p1, col_p2 = st.columns([2, 1])
            with col_p1:
                prompt_type = st.selectbox('Select Prompt Type', ['categorization_prompt','action_item_prompt','auto_reply_prompt','chat_system_instructions'])
            with col_p2:
                test_tone = st.selectbox('Test Tone', ['friendly','professional','concise','formal'], key='test_tone')
            
            tester_input = st.text_area('Test Input', value=email.get('body','')[:300], height=150)
            
            if st.button('🚀 Run Test', use_container_width=True, key='run_prompt_test'):
                with st.spinner('🧪 Testing prompt...'):
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
                            out = llm.chat_with_email(tester_input, get_prompts(), 'Summarize this content')
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
