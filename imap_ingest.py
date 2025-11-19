"""
Read-only IMAP ingestion helper. Use with caution — store credentials securely and prefer app passwords or OAuth.

Functions:
- fetch_imap_emails(server, username, password, mailbox='INBOX', limit=50)

This module uses Python's built-in imaplib and email packages.
"""
import imaplib
import email
from email.header import decode_header
from typing import List, Dict
import datetime


def _decode_header(hdr):
    if hdr is None:
        return ''
    parts = decode_header(hdr)
    out = ''
    for s, enc in parts:
        if isinstance(s, bytes):
            try:
                out += s.decode(enc or 'utf-8')
            except Exception:
                out += s.decode('utf-8', errors='ignore')
        else:
            out += s
    return out


def fetch_imap_emails(server: str, username: str, password: str, mailbox: str = 'INBOX', limit: int = 50) -> List[Dict]:
    """Connect to IMAP server and fetch the most recent `limit` messages from `mailbox`.
    Returns a list of dicts: {id, sender, subject, timestamp, body}
    """
    M = imaplib.IMAP4_SSL(server)
    M.login(username, password)
    M.select(mailbox)
    typ, data = M.search(None, 'ALL')
    ids = data[0].split()
    ids = ids[-limit:]
    results = []
    for num in reversed(ids):
        typ, msg_data = M.fetch(num, '(RFC822)')
        if typ != 'OK':
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        sender = _decode_header(msg.get('From'))
        subject = _decode_header(msg.get('Subject'))
        date_raw = msg.get('Date')
        try:
            parsed_date = email.utils.parsedate_to_datetime(date_raw)
            timestamp = parsed_date.isoformat()
        except Exception:
            timestamp = date_raw or ''
        # extract body (prefer text/plain)
        body = ''
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = str(part.get('Content-Disposition'))
                if ctype == 'text/plain' and 'attachment' not in disp:
                    try:
                        body = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                    except Exception:
                        body = str(part.get_payload())
                    break
        else:
            try:
                body = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
            except Exception:
                body = str(msg.get_payload())
        results.append({'id': int(num), 'sender': sender, 'subject': subject, 'timestamp': timestamp, 'body': body})
    M.logout()
    return results
