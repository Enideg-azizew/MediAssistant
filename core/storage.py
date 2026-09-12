"""
Public storage API used by the rest of the app.

Everything here is now backed by SQLite (see core/db.py) instead of plain
in-memory dicts, so conversation history and appointments survive a
restart and are never silently wiped. All functions are async - callers
must await them.
"""
from config import CONTEXT
import core.db as db

init_schema = db.init_schema


async def get_conversation(user_id):
    """Return the last CONTEXT turns of a user's conversation."""
    return await db.get_conversation(user_id, CONTEXT * 2)


async def add_to_conversation(user_id, role, content):
    await db.add_to_conversation(user_id, role, content)


async def clear_conversation(user_id):
    return await db.clear_conversation(user_id)


async def get_appointment(user_id):
    return await db.get_appointment(user_id)


async def set_appointment(user_id, data, username=None):
    await db.set_appointment(user_id, data, username=username)


async def clear_appointment(user_id):
    return await db.clear_appointment(user_id)


async def confirm_appointment(user_id):
    """Finalize a booking: moves it to permanent history and clears the
    working row. Returns the confirmed appointment dict or None."""
    return await db.confirm_appointment(user_id)


async def get_active_chats_count():
    return await db.count_active_conversations(since_seconds=3600)


async def get_appointments_count():
    """Returns {'in_progress': n, 'confirmed': n}."""
    return await db.get_appointments_count()


async def housekeeping():
    """Periodic cleanup: prune old conversation rows and abandoned
    (never-finished) booking flows. Confirmed appointments are never
    touched by this."""
    await db.prune_old_conversations(max_age_seconds=30 * 24 * 3600)
    return await db.prune_abandoned_appointments(max_age_seconds=6 * 3600)
