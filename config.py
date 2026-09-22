import os
import json
import sys
import logging

logger = logging.getLogger("mediassistant.config")

# ---------------------------------------------------------------------------
# Secrets: environment variables ONLY. Never hardcode keys in this file.
# Copy .env.example to .env (or set these in your host's secret manager) and
# fill in real values. The process will refuse to start if any required
# secret is missing, rather than silently running half-broken.
# ---------------------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Token required to use the /api/* dashboard endpoints and the dashboard
# login screen. Generate one with e.g. `python -c "import secrets;
# print(secrets.token_urlsafe(32))"` and set it as an env var 
# a real value.
DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "")

# Optional: a Telegram chat ID (usually the clinic staff's own chat with the
# bot, or a private group) that gets pinged whenever a patient confirms an
# appointment. Leave unset to disable staff notifications.
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

WEB_PORT = int(os.getenv("PORT", 8080))
DB_PATH = os.getenv("DB_PATH", "mediassistant.db")

_REQUIRED = {
    "BOT_TOKEN": BOT_TOKEN,
    "DASHBOARD_TOKEN": DASHBOARD_TOKEN,
}
_missing = [name for name, val in _REQUIRED.items() if not val]
if _missing:
    sys.exit(
        "Missing required environment variable(s): " + ", ".join(_missing) +
        "\nSee .env.example for the full list of settings, then set them as "
        "real environment variables (do not hardcode secrets in config.py)."
    )
if not GROQ_API_KEY and not GEMINI_API_KEY:
    logger.warning(
        "Neither GROQ_API_KEY nor GEMINI_API_KEY is set — the bot will have "
        "no working AI model and will always fall back to the maintenance "
        "message."
    )

# File paths
PROFILE_FILE = os.getenv("PROFILE_FILE", "clinic_profile.txt")
CONFIG_FILE = os.getenv("CONFIG_FILE", "config.json")

# Load clinic profile
try:
    with open(PROFILE_FILE, "r", encoding="utf-8") as f:
        PROFILE = f.read().strip()
except FileNotFoundError:
    PROFILE = ""
if not PROFILE:
    logger.warning(
        "%s is empty — the AI assistant has no clinic-specific facts to "
        "draw on beyond the static menu text. Fill it in with services, "
        "policies, doctors, hours, etc.", PROFILE_FILE
    )

# Load bot behavior config (non-secret, safe to keep in git)
with open(CONFIG_FILE, "r") as f:
    cfg = json.load(f)

# System prompt
SYSTEM_PROMPT = f"""You are the AI assistant for MediLab Specialty Clinic in Addis Abeba.

CLINIC PROFILE:
{PROFILE}

CRITICAL RULES:
- RESPOND IN EXACTLY 2-3 SENTENCES MAXIMUM
- Keep responses under 50 words total

1. Respond using "we" and "our" - never "I"
2. For medical queries: give general info ONLY, always recommend an in-person visit. Never diagnose.
3. For urgent symptoms: say "Visit now or call emergency" first.
4. For costs: give ranges only, mention insurance and Telebirr.
5. Be warm, professional, clear.
6. Be culturally respectful (Ethiopian context).
7. Never mention being AI, bot, or language model.
8. For lab queries: include test name, price, turnaround time, preparation (if any).

RESPONSE LENGTH: Maximum 50 words, 3 sentences maximum.
"""

# AI settings
MAX_TOKENS = 600

# Model fallback chains. NOTE: 
# availability change over time, and a stale ID here just wastes a retry.
GROQ_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-pro",
]

ALL_MODELS = GEMINI_MODELS + GROQ_MODELS


MIN_LENGTH = cfg["message_filters"]["min_length"]
SKIP_COMMANDS = cfg["message_filters"]["ignore_commands"]
SKIP_BOTS = cfg["message_filters"]["ignore_bots"]
CONTEXT = cfg["context_window"]
TEMP = cfg["temperature"]


class _RuntimeConfig:
    """Settings the dashboard can change while the bot is running.

    Wrapping them in one shared, mutable object means
    every reader sees the current value.
    """

    def __init__(self, cfg):
        self.enabled = cfg["enabled"]
        self.blacklist = set(cfg["blacklist_users"])
        self.whitelist = set(cfg["whitelist_users"])
        self.reply_dms = cfg["reply_to_dms"]
        self.reply_groups = cfg["reply_to_groups"]
        self.delay = cfg["delay_seconds"]
        self.rate_limit = cfg["max_messages_per_hour"]

    def apply(self, data: dict):
        """Apply a partial update (e.g. from the dashboard API)."""
        if "enabled" in data:
            self.enabled = bool(data["enabled"])
        if "blacklist_users" in data:
            self.blacklist = set(data["blacklist_users"])
        if "whitelist_users" in data:
            self.whitelist = set(data["whitelist_users"])
        if "reply_to_dms" in data:
            self.reply_dms = bool(data["reply_to_dms"])
        if "reply_to_groups" in data:
            self.reply_groups = bool(data["reply_to_groups"])
        if "delay_seconds" in data:
            self.delay = int(data["delay_seconds"])
        if "max_messages_per_hour" in data:
            self.rate_limit = int(data["max_messages_per_hour"])

    def to_cfg_dict(self, base_cfg: dict) -> dict:
        """Merge current runtime values back into a full config.json shape."""
        merged = dict(base_cfg)
        merged["enabled"] = self.enabled
        merged["blacklist_users"] = sorted(self.blacklist)
        merged["whitelist_users"] = sorted(self.whitelist)
        merged["reply_to_dms"] = self.reply_dms
        merged["reply_to_groups"] = self.reply_groups
        merged["delay_seconds"] = self.delay
        merged["max_messages_per_hour"] = self.rate_limit
        return merged


runtime = _RuntimeConfig(cfg)
