from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os

from db import (
    init_db,
    get_emails,
    get_email,
    save_processed,
    get_processed,
    get_prompts,
    save_draft,
    get_drafts,
    save_emails,
)
from imap_ingest import fetch_imap_emails
import llm

app = FastAPI(title="Email Productivity Agent API", version="1.0.0")


class ImapIngestRequest(BaseModel):
    server: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    mailbox: Optional[str] = "INBOX"
    limit: Optional[int] = Field(default=50, ge=1, le=500)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)


class DraftRequest(BaseModel):
    tone: str = Field(default="friendly")


@app.on_event("startup")
def _startup():
    init_db()


def _imap_config_from_env():
    server = os.getenv("IMAP_SERVER", "imap.gmail.com")
    username = os.getenv("IMAP_USERNAME")
    password = os.getenv("IMAP_PASSWORD")
    mailbox = os.getenv("IMAP_MAILBOX", "INBOX")
    try:
        limit = int(os.getenv("IMAP_LIMIT", "50"))
    except Exception:
        limit = 50
    return server, username, password, mailbox, limit


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest/gmail")
def ingest_gmail(payload: Optional[ImapIngestRequest] = None):
    server, username, password, mailbox, limit = _imap_config_from_env()
    if payload:
        server = payload.server or server
        username = payload.username or username
        password = payload.password or password
        mailbox = payload.mailbox or mailbox
        limit = payload.limit or limit

    if not username or not password:
        raise HTTPException(status_code=400, detail="IMAP_USERNAME and IMAP_PASSWORD must be set (Gmail app password recommended).")

    try:
        emails = fetch_imap_emails(server, username, password, mailbox=mailbox, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IMAP fetch failed: {e}")

    save_emails(emails)
    return {"ingested": len(emails), "mailbox": mailbox}


@app.get("/emails")
def list_emails():
    return get_emails()


@app.get("/emails/{email_id}")
def read_email(email_id: int):
    email_data = get_email(email_id)
    if not email_data:
        raise HTTPException(status_code=404, detail="Email not found")
    return email_data


@app.get("/emails/{email_id}/processed")
def read_processed(email_id: int):
    processed = get_processed(email_id)
    if not processed:
        return {"categories": None, "tasks": None}
    return processed


@app.post("/emails/{email_id}/process")
def process_email(email_id: int):
    email_data = get_email(email_id)
    if not email_data:
        raise HTTPException(status_code=404, detail="Email not found")
    prompts = get_prompts()
    categorization_prompt = prompts.get("categorization_prompt") or ""
    action_item_prompt = prompts.get("action_item_prompt") or ""
    categories = llm.categorize(email_data.get("body", ""), categorization_prompt)
    tasks = llm.extract_actions(email_data.get("body", ""), action_item_prompt)
    save_processed(email_id, categories, tasks)
    return {"categories": categories, "tasks": tasks}


@app.post("/emails/{email_id}/chat")
def chat_email(email_id: int, payload: ChatRequest):
    email_data = get_email(email_id)
    if not email_data:
        raise HTTPException(status_code=404, detail="Email not found")
    prompts = get_prompts()
    reply = llm.chat_with_email(email_data.get("body", ""), prompts, payload.query)
    return {"reply": reply}


@app.post("/emails/{email_id}/draft")
def draft_email(email_id: int, payload: DraftRequest):
    email_data = get_email(email_id)
    if not email_data:
        raise HTTPException(status_code=404, detail="Email not found")
    prompts = get_prompts()
    auto_reply_prompt = prompts.get("auto_reply_prompt") or ""
    draft = llm.generate_draft(email_data.get("body", ""), auto_reply_prompt, tone=payload.tone)
    subject = draft.get("subject", "") if isinstance(draft, dict) else ""
    body = draft.get("body", "") if isinstance(draft, dict) else str(draft)
    save_draft(email_id, subject, body, metadata={"tone": payload.tone})
    return {"draft": draft}


@app.get("/emails/{email_id}/drafts")
def list_drafts(email_id: int):
    return get_drafts(email_id)
