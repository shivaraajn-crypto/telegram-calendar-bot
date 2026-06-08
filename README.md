# Telegram Calendar Bot

A Telegram bot for scheduling team/unit events, deployed as a webhook worker on Railway.

## Features
- `/addevent <title> <YYYY-MM-DD> <HH:MM>` — add an event
- `/updateevent <old_title> <new_title> <YYYY-MM-DD> <HH:MM>` — update
- `/deleteevent <title>` — delete
- `/week` — events in the next 7 days
- `/find <keyword>` — search by title
- `/hello` or `/help` — interactive menu with inline buttons (Quick Add flow)

## Local development (polling)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # leave WEBHOOK_URL empty to use polling
# edit .env and put your bot token in TELEGRAM_BOT_TOKEN
python bot.py
```

## Production (webhook on Railway)

1. **Revoke the old token** (it was leaked in the original notebook):
   - Open @BotFather on Telegram → `/revoke` → copy the new token.
2. Push this repo to GitHub (the `shivaraajn-crypto/telegram-calendar-bot` remote).
3. On [railway.app](https://railway.app) → New Project → Deploy from GitHub → pick this repo.
4. In the service **Settings**, switch the service type to **Worker** (not Web).
5. Add these **Variables**:
   - `TELEGRAM_BOT_TOKEN` = (the new token from step 1)
   - `WEBHOOK_URL` = your Railway public URL, e.g. `https://telegram-calendar-bot.up.railway.app` (no trailing slash). Find it under Settings → Networking → Generate Domain.
6. Deploy. When the worker logs show `Webhook set: ...`, message your bot with `/hello` to test.

> The `PORT` variable is set by Railway automatically.

## Files
- `bot.py` — bot source
- `Procfile` — `worker: python bot.py`
- `requirements.txt` — `python-telegram-bot==13.7`, `apscheduler==3.10.4`
- `runtime.txt` — Python 3.11.9
- `.env.example` — template for local dev
- `.gitignore` — excludes `.env`, `*.db`, `__pycache__/`
