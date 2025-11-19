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
        .stApp { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .main-container {
            background: white;
            border-radius: 16px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .email-card { 
            padding: 16px; 
            border-radius: 12px; 
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            margin: 10px 0;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .email-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 24px rgba(0,0,0,0.12);
        }
        .muted { 
            color: #6b7280; 
            font-size: 0.9em;
        }
        .category-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: 4px;
            font-size: 0.85em;
            font-weight: 500;
            box-shadow: 0 2px 8px rgba(102,126,234,0.3);
        }
        .task-item {
            background: #fff;
            border-left: 4px solid #667eea;
            padding: 12px;
            margin: 8px 0;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .chat-bubble-user {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 16px;
            border-radius: 18px;
            margin: 8px 0;
            max-width: 80%;
            float: right;
            clear: both;
        }
        .chat-bubble-assistant {
            background: #f3f4f6;
            color: #1f2937;
            padding: 12px 16px;
            border-radius: 18px;
            margin: 8px 0;
            max-width: 80%;
            float: left;
            clear: both;
        }
        .section-header {
            color: #667eea;
            font-size: 1.3em;
            font-weight: 600;
            margin: 20px 0 10px 0;
            padding-bottom: 8px;
            border-bottom: 2px solid #667eea;
        }
        .stButton>button {
            border-radius: 8px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 8px 20px;
            font-weight: 500;
            transition: all 0.3s;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102,126,234,0.4);
        }
        .metric-card {
            background: white;
            padding: 16px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            text-align: center;
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
        st.error("🔒 IMAP error: Your provider requires an application-specific (app) password. For Gmail, create an App Password: https://support.google.com/accounts/answer/185833")
    elif 'AUTHENTICATIONFAILED' in msg.upper():
        st.error('🔒 IMAP error: Authentication failed — check username and password, and ensure IMAP is enabled for the account.')
    else:
        st.error(f'⚠️ IMAP error: {msg}')

init_db()

# Sidebar Configuration
st.sidebar.image("https://img.icons8.com/fluency/96/000000/email.png", width=80)
st.sidebar.title('⚙️ Configuration')

# LLM mode indicator
try:
    llm_key = getattr(llm, 'OPENAI_KEY', None)
    llm_model = getattr(llm, 'OPENAI_MODEL', 'unknown')
except Exception:
    llm_key = None
    llm_model = 'unknown'

if llm_key:
    st.sidebar.success(f'🤖 LLM Mode: Real\n\nModel: {llm_model}')
else:
    st.sidebar.warning('🤖 LLM Mode: Mock\n\nNo OpenAI key detected')

st.sidebar.markdown('---')

prompts = get_prompts() or {}

with st.sidebar.expander('📝 Edit AI Prompts', expanded=False):
    st.markdown("*Customize how the AI processes emails*")
    cat = st.text_area('Categorization Prompt', value=prompts.get('categorization_prompt', ''), height=120)
    act = st.text_area('Action Extraction Prompt', value=prompts.get('action_item_prompt', ''), height=120)
    auto = st.text_area('Auto-reply Prompt', value=prompts.get('auto_reply_prompt', ''), height=120)
    chat_sys = st.text_area('Chat System Instructions', value=prompts.get('chat_system_instructions', ''), height=100)
    if st.button('💾 Save All Prompts'):
        try:
            save_prompt('categorization_prompt', cat)
            save_prompt('action_item_prompt', act)
            save_prompt('auto_reply_prompt', auto)
            save_prompt('chat_system_instructions', chat_sys)
            st.success('✅ Prompts saved successfully!')
            prompts = get_prompts() or {}
        except Exception as e:
            st.error(f'❌ Error saving prompts: {e}')

# Main Title
st.markdown("<h1 style='text-align: center; color: white; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>📧 Email Productivity Agent</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: white; font-size: 1.1em;'>AI-Powered Email Management & Automation</p>", unsafe_allow_html=True)

# Welcome Section
with st.expander('👋 Welcome — Quick Start Guide', expanded=False):
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.image("https://img.icons8.com/fluency/96/000000/artificial-intelligence.png", width=80)
    with col_b:
        st.markdown(
            """
            **Email Productivity Agent** supercharges your inbox with AI:
            
            ✅ **Smart Categorization** - Automatically classify emails  
            ✅ **Action Extraction** - Find tasks, deadlines, and assignees  
            ✅ **Draft Generation** - Create replies in seconds  
            ✅ **Email Chat** - Ask questions about any email  
            """
        )
    
    st.markdown("### 🚀 Quick Actions")
    c1, c2, c3 = st.columns(3)
    if c1.button('📥 Load Demo Inbox', use_container_width=True):
        load_mock_emails(str(MOCK_PATH))
        try:
            st.experimental_rerun()
        except Exception:
            st.success('✅ Mock inbox loaded! Refresh to see messages.')
    
    if c2.button('🧪 Test AI on Sample Email', use_container_width=True):
        try:
            emails_list = get_emails()
            if not emails_list:
                st.info('💡 Load the demo inbox first!')
            else:
                sample = emails_list[0]
                e = get_email(sample['id'])
                prompts = get_prompts()
                cat_prompt = prompts.get('categorization_prompt','')
                act_prompt = prompts.get('action_item_prompt','')
                auto_prompt = prompts.get('auto_reply_prompt','')
                
                with st.spinner('🤖 AI is analyzing...'):
                    cat_out = llm.categorize(e.get('body',''), cat_prompt)
                    act_out = llm.extract_actions(e.get('body',''), act_prompt)
                    draft_out = llm.generate_draft(e.get('body',''), auto_prompt, tone='friendly')
                
                st.markdown(f"**📧 Sample Email:** {e.get('subject')}")
                cols = st.columns(3)
                with cols[0]:
                    st.markdown('**🏷️ Categories**')
                    try:
                        st.json(cat_out)
                    except Exception:
                        st.write(cat_out)
                with cols[1]:
                    st.markdown('**✅ Action Items**')
                    try:
                        st.json(act_out)
                    except Exception:
                        st.write(act_out)
                with cols[2]:
                    st.markdown('**✍️ Draft Reply**')
                    try:
                        st.json(draft_out)
                    except Exception:
                        st.write(draft_out)
        except Exception as exc:
            st.error(f'⚠️ Error: {exc}')
    
    if c3.button('📚 View Documentation', use_container_width=True):
        st.info('💡 Edit prompts in the sidebar to customize AI behavior. Use the chat feature to interact with emails naturally!')

st.markdown("---")

# Main Layout
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("<div class='section-header'>📬 Inbox</div>", unsafe_allow_html=True)
    
    # Quick Actions
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button('📥 Load Mock Data', use_container_width=True):
            load_mock_emails(str(MOCK_PATH))
            try:
                st.experimental_rerun()
            except Exception:
                st.success('✅ Mock inbox loaded!')
    
    with col_btn2:
        with st.popover("🌐 IMAP Sync"):
            st.markdown("### Connect Your Email")
            provider = st.selectbox('Provider', ['Custom', 'Gmail', 'Outlook/Office365', 'Yahoo', 'iCloud', 'AOL', 'Fastmail', 'Zoho', 'ProtonMail'])
            provider_hosts = {
                'Gmail': 'imap.gmail.com',
                'Outlook/Office365': 'outlook.office365.com',
                'Yahoo': 'imap.mail.yahoo.com',
                'iCloud': 'imap.mail.me.com',
                'AOL': 'imap.aol.com',
                'Fastmail': 'imap.fastmail.com',
                'Zoho': 'imap.zoho.com',
                'ProtonMail': '127.0.0.1'
            }
            default_server = provider_hosts.get(provider, '') if provider != 'Custom' else ''
            imap_server = st.text_input('IMAP Server', value=default_server)
            imap_user = st.text_input('Email Address')
            imap_pass = st.text_input('Password', type='password')
            imap_limit = st.number_input('Max Messages', value=50, min_value=1, max_value=500)
            
            notes = {
                'Gmail': '💡 Enable IMAP in Settings and use an App Password',
                'Yahoo': '💡 Generate an app password if 2FA is enabled',
                'iCloud': '💡 Generate an app-specific password',
            }
            if provider in notes:
                st.info(notes[provider])
            
            col_test, col_fetch = st.columns(2)
            if col_test.button('🔍 Test Login'):
                import imaplib
                if not (imap_server and imap_user and imap_pass):
                    st.error('⚠️ Fill all fields')
                else:
                    try:
                        with st.spinner('Testing...'):
                            M = imaplib.IMAP4_SSL(imap_server)
                            M.login(imap_user, imap_pass)
                            M.logout()
                        st.success('✅ Login successful!')
                    except Exception as e:
                        _friendly_imap_error(e)
            
            if col_fetch.button('📥 Fetch Emails'):
                if not (imap_server and imap_user and imap_pass):
                    st.error('⚠️ Fill all fields')
                else:
                    try:
                        with st.spinner('Fetching...'):
                            msgs = fetch_imap_emails(imap_server, imap_user, imap_pass, limit=imap_limit)
                            from db import init_db
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
                        st.success(f'✅ Fetched {len(msgs)} messages!')
                        try:
                            st.experimental_rerun()
                        except Exception:
                            _show_reload_script(800)
                    except Exception as e:
                        _friendly_imap_error(e)
    
    # Email List
    emails = get_emails()
    st.markdown(f"**📨 {len(emails)} Messages**")
    
    if emails:
        for e in emails:
            with st.container():
                preview = e.get('subject', '(no subject)')[:50]
                sender = e.get('sender', 'Unknown')[:30]
                if st.button(f"📧 {preview}", key=f"select-{e['id']}", use_container_width=True):
                    st.session_state['selected_email'] = e['id']
                st.markdown(f"<p class='muted'>From: {sender}</p>", unsafe_allow_html=True)
                st.markdown("---")
    else:
        st.info("📭 No emails loaded. Click 'Load Mock Data' to get started!")
    
    selected = st.session_state.get('selected_email')

with col2:
    if selected:
        email = get_email(selected)
        
        # Email Header
        st.markdown(f"<div class='main-container'>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='color: #667eea;'>📧 {email.get('subject','(no subject)')}</h2>", unsafe_allow_html=True)
        
        col_sender, col_time = st.columns(2)
        with col_sender:
            st.markdown(f"**👤 From:** {email.get('sender')}")
        with col_time:
            st.markdown(f"**🕐 Date:** {email.get('timestamp')}")
        
        # Categories and Tasks Display
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
                st.markdown("**✅ Action Items:**")
                for t in tasks:
                    task_text = t.get('task') or t.get('raw', 'Unknown task')
                    st.markdown(f"<div class='task-item'>📌 {task_text}</div>", unsafe_allow_html=True)
        
        # Email Body
        st.markdown("**📄 Email Content:**")
        st.markdown(f"<div class='email-card'><pre style='white-space: pre-wrap; font-family: system-ui;'>{email.get('body')}</pre></div>", unsafe_allow_html=True)
        
        # Processing Actions
        st.markdown("<div class='section-header'>🤖 AI Processing</div>", unsafe_allow_html=True)
        
        col_process1, col_process2, col_process3 = st.columns(3)
        
        if col_process1.button('🔍 Analyze Email', use_container_width=True):
            db_prompts = get_prompts()
            cat_prompt = db_prompts.get('categorization_prompt') or ''
            act_prompt = db_prompts.get('action_item_prompt') or ''
            
            with st.spinner('🤖 AI is analyzing...'):
                categories = llm.categorize(email.get('body',''), cat_prompt)
                tasks = llm.extract_actions(email.get('body',''), act_prompt)
                save_processed(selected, categories, tasks)
            st.success('✅ Analysis complete!')
            try:
                st.experimental_rerun()
            except Exception:
                st.info('Please refresh to see results.')
        
        # Tone selector always visible
        tone = st.selectbox('Reply Tone', ['friendly','professional','concise','formal'], key='main_tone')
        
        if col_process2.button('✍️ Generate Draft', use_container_width=True):
            db_prompts = get_prompts()
            auto_prompt = db_prompts.get('auto_reply_prompt') or ''
            
            with st.spinner('✍️ Generating draft...'):
                draft = llm.generate_draft(email.get('body',''), auto_prompt, tone)
                subj = draft.get('subject') or f"Re: {email.get('subject','')}"
                body = draft.get('body') or draft.get('text') or str(draft)
                save_draft(selected, subj, body, {'generated_by': 'llm', 'tone': tone})
            st.success('✅ Draft saved!')
            try:
                st.experimental_rerun()
            except Exception:
                st.info('Draft saved. Refresh to view.')
        
        if col_process3.button('📝 View Drafts', use_container_width=True):
            drafts = get_drafts(selected)
            if drafts:
                for d in drafts:
                    st.markdown(f"**Draft #{d['id']}** - {d['subject']}")
                    st.text_area(f"Draft {d['id']}", value=d['body'], height=150, key=f"draft_{d['id']}")
            else:
                st.info("No drafts available. Generate one first!")
        
        # Chat Assistant
        st.markdown("<div class='section-header'>💬 Chat Assistant</div>", unsafe_allow_html=True)
        
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Chat input and send button
        col_input, col_send = st.columns([4, 1])
        with col_input:
            user_q = st.text_input('💭 Ask about this email...', placeholder='e.g., "Summarize this", "What are the action items?"', key='chat_input', label_visibility='collapsed')
        with col_send:
            send_clicked = st.button('💬 Send', use_container_width=True, key='send_chat')
        
        if send_clicked and user_q and user_q.strip():
            db_prompts = get_prompts()
            with st.spinner('🤖 Thinking...'):
                answer = llm.chat_with_email(email.get('body',''), db_prompts, user_q)
                st.session_state.chat_history.append({'user': user_q, 'assistant': answer})
            try:
                st.experimental_rerun()
            except:
                st.rerun()
        
        # Display chat history
        if st.session_state.chat_history:
            st.markdown("**💬 Conversation:**")
            chat_container = st.container()
            with chat_container:
                for idx, m in enumerate(st.session_state.chat_history):
                    st.markdown(f"<div class='chat-bubble-user'>👤 You: {m['user']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='chat-bubble-assistant'>🤖 Assistant: {m['assistant']}</div>", unsafe_allow_html=True)
                    st.markdown("<div style='clear: both; margin-bottom: 10px;'></div>", unsafe_allow_html=True)
            
            if st.button('🗑️ Clear Chat History', key='clear_chat'):
                st.session_state.chat_history = []
                try:
                    st.experimental_rerun()
                except:
                    st.rerun()
        else:
            st.info("💡 Ask me anything about this email! Try 'Summarize this' or 'What tasks are mentioned?'")
        
        # Prompt Tester
        st.markdown("<div class='section-header'>🧪 Prompt Testing Lab</div>", unsafe_allow_html=True)
        
        col_test1, col_test2 = st.columns([2, 1])
        with col_test1:
            prompt_type = st.selectbox('Select Prompt to Test', ['categorization_prompt','action_item_prompt','auto_reply_prompt','chat_system_instructions'], key='prompt_type_select')
        with col_test2:
            test_tone = st.selectbox('Tone (for drafts)', ['friendly','professional','concise','formal'], key='test_tone_select')
        
        tester_prompt = get_prompts().get(prompt_type, '')
        st.text_area('Current Prompt (read-only)', value=str(tester_prompt)[:500] + '...' if len(str(tester_prompt)) > 500 else str(tester_prompt), height=80, disabled=True, key='prompt_display')
        
        tester_input = st.text_area('Test Input (email body)', value=email.get('body','')[:500], height=120, key='test_input_area')
        
        if st.button('🚀 Run Prompt Test', use_container_width=True, key='run_test_btn'):
            with st.spinner('🧪 Testing prompt...'):
                try:
                    if prompt_type == 'categorization_prompt':
                        out = llm.categorize(tester_input, tester_prompt)
                        st.markdown("**📊 Categorization Results:**")
                    elif prompt_type == 'action_item_prompt':
                        out = llm.extract_actions(tester_input, tester_prompt)
                        st.markdown("**✅ Extracted Action Items:**")
                    elif prompt_type == 'auto_reply_prompt':
                        out = llm.generate_draft(tester_input, tester_prompt, test_tone)
                        st.markdown("**✍️ Generated Draft:**")
                    else:
                        out = llm.chat_with_email(tester_input, get_prompts(), 'Summarize this email')
                        st.markdown("**💬 Chat Response:**")
                    
                    try:
                        st.json(out)
                    except Exception:
                        st.code(str(out), language='text')
                    st.success('✅ Test completed!')
                except Exception as e:
                    st.error(f'❌ Test failed: {str(e)}')
        
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        # No email selected state
        st.markdown("<div class='main-container'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; color: #667eea;'>📬 Select an email to get started</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6b7280;'>Choose an email from the inbox on the left to view details and interact with AI features</p>", unsafe_allow_html=True)
        
        # Show some stats
        emails = get_emails()
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.markdown(f"<div class='metric-card'><h3 style='color: #667eea;'>{len(emails)}</h3><p>Total Emails</p></div>", unsafe_allow_html=True)
        with col_stat2:
            processed_count = sum(1 for e in emails if get_processed(e['id']))
            st.markdown(f"<div class='metric-card'><h3 style='color: #667eea;'>{processed_count}</h3><p>Processed</p></div>", unsafe_allow_html=True)
        with col_stat3:
            draft_count = sum(len(get_drafts(e['id']) or []) for e in emails)
            st.markdown(f"<div class='metric-card'><h3 style='color: #667eea;'>{draft_count}</h3><p>Drafts</p></div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
