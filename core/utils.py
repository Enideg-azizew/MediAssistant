import time
import logging
from collections import deque
from config import SKIP_COMMANDS, SKIP_BOTS, MIN_LENGTH, runtime

logger = logging.getLogger("mediassistant")

###LANGUAGE aint 2ork
# Amharic detection
AMHARIC_RANGE = range(0x1200, 0x137F)  # Unicode Ethiopic block

def detect_language(text):
    """Detect if text contains Amharic characters"""
    for char in text:
        if ord(char) in AMHARIC_RANGE:
            return "am"
    return "en"

def get_greeting(lang):
    if lang == "am":
        return "ሰላም, ወደ MediLab ክሊኒክ እንኳን ደህና መጡ።"
    return "👋 Welcome to MediLab Clinic! How can I help you today?"


##RATE_LIMITERS
# Global rate limit queue
msg_times = deque(maxlen=1000)

def can_send(rate_limit=None):
    """Check if we're under the rate limit.

    It now defaults to the live (dashboard-adjustable) rate limit .
    """
    if rate_limit is None:
        rate_limit = runtime.rate_limit
    now = time.time()
    while msg_times and msg_times[0] < now - 3600:
        msg_times.popleft()
    return len(msg_times) < rate_limit

def record_message():
    """Record that a message was sent"""
    msg_times.append(time.time())

##HELPERS
def should_reply(update):
    """Check if we should reply to this message"""
    if not runtime.enabled:
        return False

    user_id = update.effective_user.id
    if user_id in runtime.blacklist:
        return False
    if user_id in runtime.whitelist:
        return True

    chat_type = update.effective_chat.type
    if chat_type in ['private']:
        return runtime.reply_dms
    if chat_type in ['group', 'supergroup']:
        return runtime.reply_groups

    return False

def check_message(update):
    """Validate if message should be processed"""
    if not update.message or not update.message.text:
        return False
    text = update.message.text
    if len(text) < MIN_LENGTH:
        return False
    if SKIP_COMMANDS and text.startswith('/'):
        return False
    if SKIP_BOTS and update.message.from_user and update.message.from_user.is_bot:
        return False
    return True
