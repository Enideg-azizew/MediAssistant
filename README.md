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

The dashboard is served at `http://<host>:8080/`. Open it in a browser and paste your `DASHBOARD_TOKEN` when prompted — every `/api/*` call requires that token in an `Authorization: Bearer <token>` header, so the dashboard is no longer wide open to anyone who can reach the port.

## What changed from the original version

**Fixed a crash that broke every message.** `can_send()` was called with no arguments but required one — every incoming message raised `TypeError` and the bot silently never replied. It now has a working default.

**Nothing gets silently lost anymore.** Conversations and appointments used to live only in in-memory dicts that were wiped every hour, and confirmed bookings were dropped with no notification and no record. Everything now persists to a SQLite database (`core/db.py`): confirmed appointments move into a permanent `appointment_history` table, and only abandoned (never-finished) booking flows and old chat logs get pruned periodically. A restart no longer loses anything.

**Staff now hear about bookings.** When a patient confirms an appointment, the bot (optionally) pings a configured admin chat with the details, on top of the permanent database record.

**Dashboard is authenticated.** All `/api/*` endpoints require a bearer token (`DASHBOARD_TOKEN`); previously anyone who could reach port 8080 could toggle the bot or change its config.

**Secrets are no longer in source.** The original `config.py` had a real Groq API key hardcoded (commented out, but still present in the file). All secrets now come from environment variables via `.env`, and the app refuses to start if required ones are missing. **If you're reusing this codebase, rotate any key that was ever committed to it.**

**Dashboard toggle/config changes actually take effect.** Settings like "enabled", rate limit, and reply behavior used to be plain module-level constants — other modules imported them by value at startup, so changes made from the dashboard were invisible to the message handler. They're now held in one shared `runtime` object everyone reads live.

**Config API validates input.** Unknown fields, out-of-range temperature, and non-numeric rate/delay values are now rejected with a 400 instead of silently corrupting `config.json` or crashing.

**Minor content fix.** The FAQ told patients to call "911" for emergencies — a US number, not valid in Ethiopia. Replaced with a placeholder (907) that **you should verify** with the clinic before deploying.

**Logging instead of print().** Structured, leveled logs instead of scattered `print()` calls.

## Still worth doing before a real production launch

- Verify the hardcoded AI model IDs in `config.py` (`GROQ_MODELS`, `GEMINI_MODELS`) are still valid with each provider — model availability changes.
- Confirm the correct local emergency number for the FAQ text in `core/services.py`.
- Consider moving to a hosted Postgres/MySQL instance instead of a local SQLite file if you'll run multiple instances or need remote backups.
- Add automated tests (there currently are none).
- Put the dashboard behind HTTPS (e.g. a reverse proxy) — the bearer token is sent in plaintext over plain HTTP otherwise.
