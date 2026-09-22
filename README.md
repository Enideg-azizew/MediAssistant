# MediAssistant — Clinic Telegram Bot

## Setup

1. `pip install -r requirements.txt`
2. `cp .env.example .env` and fill in real values:
   - `BOT_TOKEN` — from @BotFather
   - `GROQ_API_KEY` and/or `GEMINI_API_KEY` — at least one needed for AI replies
   - `DASHBOARD_TOKEN` — generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - `ADMIN_CHAT_ID` (optional) — a Telegram chat ID to notify when a patient confirms a booking
3. Fill in `clinic_profile.txt` with real clinic-specific facts (it's currently empty, so the AI has nothing clinic-specific to draw on beyond the hardcoded menu text).
4. `python main.py`

The dashboard is served at `http://<host>:8080/`. Open it in a browser and paste your `DASHBOARD_TOKEN` when prompted — every `/api/*` call requires that token in an `Authorization: Bearer <token>` header port.

## Main features.
- Answer to users based on clinic_profile.txt in natural language
- Register Appointments and provide pther informations
- Menu and button options for manual walkthrough
- Have dashboard with all customer detials for the bot owner.

## Issues
- Separation of concerns (logic and data) not implemented (yo be refactored)
- 
### Contact developer

```
+251936711812
indexazacc@gmail.com
```