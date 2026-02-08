You can run this app here
https://prompt-driven-email-du8juwtcvuja9pqp4a93rr.streamlit.app/
# Email Productivity Agent

An interactive, prompt-driven Email Productivity Agent built with Streamlit and OpenAI. It processes a mock inbox (or your own), categorizes emails, extracts action items, drafts replies, and offers a chat-style assistant for each email. Prompts are editable so you control the agent "brain". A FastAPI service is also included for API-based deployments.

## Features
- Load a mock inbox of sample emails
- Edit prompt templates for categorization, action extraction, and auto-replies
- Process emails using the configured prompts (categorize & extract tasks)
- Per-email chat assistant for summaries, task queries, and drafting
- Generate and store editable drafts (never sent automatically)

## Requirements
- Python 3.10+
- An OpenAI API key set in `OPENAI_API_KEY` (optional; app can run in offline/mock mode but LLM features will be limited)

## Quick Start

1. Create a venv and install dependencies:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

2. (Optional) Set your OpenAI API key in environment:

```powershell
$env:OPENAI_API_KEY = 'sk-...'
$env:OPENAI_MODEL = 'gpt-4'  # optional, defaults to 'gpt-4' if not set
```

3. Run the Streamlit app:

```powershell
streamlit run app.py
```

4. The app will create a local SQLite DB at `data/email_agent.db` and load the mock inbox.

## FastAPI API (recommended for deployment)

Run the API locally:

```powershell
uvicorn fastapi_app:app --host 0.0.0.0 --port 8000
```

Key endpoints:
- GET /health
- POST /ingest/gmail (ingest Gmail via IMAP)
- GET /emails
- GET /emails/{email_id}
- POST /emails/{email_id}/process
- POST /emails/{email_id}/chat
- POST /emails/{email_id}/draft
- GET /emails/{email_id}/drafts

### Gmail IMAP setup
1. Enable 2-Step Verification on your Gmail account.
2. Create an App Password in your Google Account (recommended).
3. Set environment variables:

```text
IMAP_SERVER=imap.gmail.com
IMAP_USERNAME=you@gmail.com
IMAP_PASSWORD=your_app_password
IMAP_MAILBOX=INBOX
IMAP_LIMIT=50
```

Then call POST /ingest/gmail to pull messages into the local database.

## Files of Interest
- `app.py` — Streamlit frontend + orchestration
- `fastapi_app.py` — FastAPI service for API deployment
- `llm.py` — Minimal LLM wrapper using OpenAI (configurable via env)
- `db.py` — SQLite helpers for emails, prompts, processed results, and drafts
- `data/mock_emails.json` — sample inbox (15 emails)
- `prompts/default_prompts.json` — default prompt templates to get started

## Editing Prompts
Open the sidebar "Prompts" section. Edit or replace any prompt and click "Save Prompts". Prompts drive categorization, extraction, and draft generation.

## Demo Video Guidance
Record a 5–10 minute screen capture demonstrating:
- Launching the app and loading the mock inbox
- Opening the prompt editor and modifying a prompt
- Running the pipeline for several emails (categorize + extract)
- Selecting an email and using the chat assistant to summarize, ask for tasks, and generate a reply draft
- Editing and saving a draft

Tips for recording: narrate the prompt changes, explain why the agent behavior changed, and highlight a saved draft.

## Notes
- Drafts are stored locally and not sent. Use this system as a productivity assistant and not an automated mailer.
- If you don't provide `OPENAI_API_KEY`, the app will respond with helpful mock output so you can still explore flows.

## Deployment Options

1) Streamlit Community Cloud (recommended for quick demos)

- Push this repo to GitHub. On Streamlit Cloud, create a new app, connect your repo, and set the start command to:

```text
streamlit run app.py
```

- In the Streamlit app settings, add environment variables: `OPENAI_API_KEY` and optionally `OPENAI_MODEL`.

2) Docker (recommended for controlled deployments)

- Build and run locally:

```powershell
docker build -t email-agent .
docker run -p 8000:8000 -e OPENAI_API_KEY=%OPENAI_API_KEY% -e IMAP_USERNAME=%IMAP_USERNAME% -e IMAP_PASSWORD=%IMAP_PASSWORD% email-agent
```

3) Container hosts / Cloud providers

- Use the included `Dockerfile` or deploy to Azure App Service / AWS ECS / Google Cloud Run. Ensure you add `OPENAI_API_KEY` as a secret.

### Deploy to Google Cloud Run (quick)

- Build and push image (requires `gcloud` configured and Docker):

```powershell
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/email-agent
gcloud run deploy email-agent --image gcr.io/YOUR_PROJECT_ID/email-agent --platform managed --region YOUR_REGION --allow-unauthenticated --set-env-vars OPENAI_API_KEY=$env:OPENAI_API_KEY
```

### Deploy to Azure App Service (quick)

- Build a Docker image and push to Azure Container Registry, then create a Web App for Containers and set `OPENAI_API_KEY` in App Settings.

### Streamlit Community Cloud

If you prefer a managed Streamlit hosting:

- Push the repo to GitHub. Create a new app on https://streamlit.io/cloud, connect the repo, set the branch and the main file to `app.py`, and add `OPENAI_API_KEY` in the Secrets section.


4) Heroku (legacy / not recommended for new projects)

- The included `Procfile` can be used for Heroku-like platforms. Add `OPENAI_API_KEY`, `IMAP_USERNAME`, and `IMAP_PASSWORD` as config vars.

## Demo Recording Checklist
- Open the app and load the mock inbox
- Edit one prompt in the sidebar and save
- Process an email (Categorize & Extract) and show the stored results
- Use the Chat Assistant to ask "What tasks?" and show the LLM response
- Generate a draft, open the drafts panel, and edit the draft


If you'd like, I can also:
- Add user authentication or connect to a real IMAP inbox
- Add export/backup for drafts and processed results

Enjoy — and tell me if you want additional features or a production deployment setup!
