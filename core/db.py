"""
SQLite-backed persistence.
Everything that matters goes to
disk. SQLite is used synchronously but every call is routed through
asyncio.to_thread so it never blocks the bot's event loop; at this
application's message volume a single file-backed DB is more than enough,
and it avoids standing up a separate database server.
"""
import asyncio
import sqlite3
import time
from contextlib import contextmanager

from config import DB_PATH

_lock = asyncio.Lock()


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def _cursor():
    conn = _connect()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    finally:
        conn.close()


def _init_schema_sync():
    with _cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id, id)")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                step TEXT,
                service TEXT,
                date TEXT,
                time TEXT,
                status TEXT NOT NULL DEFAULT 'in_progress',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS appointment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                username TEXT,
                service TEXT,
                date TEXT,
                time TEXT,
                confirmed_at REAL NOT NULL
            )
        """)


async def init_schema():
    async with _lock:
        await asyncio.to_thread(_init_schema_sync)



# Conversations

def _get_conversation_sync(user_id, limit):
    with _cursor() as cur:
        cur.execute(
            "SELECT role, content FROM conversations WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (str(user_id), limit),
        )
        rows = cur.fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


async def get_conversation(user_id, limit):
    return await asyncio.to_thread(_get_conversation_sync, user_id, limit)


def _add_to_conversation_sync(user_id, role, content):
    with _cursor() as cur:
        cur.execute(
            "INSERT INTO conversations (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (str(user_id), role, content, time.time()),
        )


async def add_to_conversation(user_id, role, content):
    await asyncio.to_thread(_add_to_conversation_sync, user_id, role, content)


def _clear_conversation_sync(user_id):
    with _cursor() as cur:
        cur.execute("DELETE FROM conversations WHERE user_id=?", (str(user_id),))
        return cur.rowcount > 0


async def clear_conversation(user_id):
    return await asyncio.to_thread(_clear_conversation_sync, user_id)


def _prune_old_conversations_sync(max_age_seconds):
    cutoff = time.time() - max_age_seconds
    with _cursor() as cur:
        cur.execute("DELETE FROM conversations WHERE created_at < ?", (cutoff,))


async def prune_old_conversations(max_age_seconds):
    await asyncio.to_thread(_prune_old_conversations_sync, max_age_seconds)


def _count_active_conversations_sync(since_seconds):
    cutoff = time.time() - since_seconds
    with _cursor() as cur:
        cur.execute(
            "SELECT COUNT(DISTINCT user_id) AS n FROM conversations WHERE created_at >= ?",
            (cutoff,),
        )
        return cur.fetchone()["n"]


async def count_active_conversations(since_seconds=3600):
    return await asyncio.to_thread(_count_active_conversations_sync, since_seconds)



# Appointments (in-progress booking flow)

def _get_appointment_sync(user_id):
    with _cursor() as cur:
        cur.execute(
            "SELECT * FROM appointments WHERE user_id=? AND status='in_progress'",
            (str(user_id),),
        )
        row = cur.fetchone()
    return dict(row) if row else None


async def get_appointment(user_id):
    return await asyncio.to_thread(_get_appointment_sync, user_id)


def _set_appointment_sync(user_id, data, username=None):
    now = time.time()
    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO appointments (user_id, username, step, service, date, time, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'in_progress', ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=COALESCE(excluded.username, appointments.username),
                step=excluded.step,
                service=COALESCE(excluded.service, appointments.service),
                date=COALESCE(excluded.date, appointments.date),
                time=COALESCE(excluded.time, appointments.time),
                status='in_progress',
                updated_at=excluded.updated_at
            """,
            (
                str(user_id), username, data.get("step"), data.get("service"),
                data.get("date"), data.get("time"), now, now,
            ),
        )


async def set_appointment(user_id, data, username=None):
    await asyncio.to_thread(_set_appointment_sync, user_id, data, username)


def _clear_appointment_sync(user_id):
    with _cursor() as cur:
        cur.execute("DELETE FROM appointments WHERE user_id=?", (str(user_id),))
        return cur.rowcount > 0


async def clear_appointment(user_id):
    return await asyncio.to_thread(_clear_appointment_sync, user_id)


def _confirm_appointment_sync(user_id):
    with _cursor() as cur:
        cur.execute("SELECT * FROM appointments WHERE user_id=?", (str(user_id),))
        row = cur.fetchone()
        if not row:
            return None
        cur.execute(
            """
            INSERT INTO appointment_history (user_id, username, service, date, time, confirmed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (row["user_id"], row["username"], row["service"], row["date"], row["time"], time.time()),
        )
        cur.execute("DELETE FROM appointments WHERE user_id=?", (str(user_id),))
        return dict(row)


async def confirm_appointment(user_id):
    """Move an in-progress booking to permanent history and clear the
    working row. Returns the confirmed appointment dict, or None if there
    was nothing to confirm."""
    return await asyncio.to_thread(_confirm_appointment_sync, user_id)


def _prune_abandoned_appointments_sync(max_age_seconds):
    cutoff = time.time() - max_age_seconds
    with _cursor() as cur:
        cur.execute(
            "DELETE FROM appointments WHERE status='in_progress' AND updated_at < ?",
            (cutoff,),
        )
        return cur.rowcount


async def prune_abandoned_appointments(max_age_seconds=6 * 3600):
    """Clear stale in-progress booking flows (patient started but never
    finished). Confirmed appointments live in appointment_history and are
    never touched by this."""
    return await asyncio.to_thread(_prune_abandoned_appointments_sync, max_age_seconds)


def _get_appointments_count_sync():
    with _cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM appointments WHERE status='in_progress'")
        in_progress = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM appointment_history")
        confirmed = cur.fetchone()["n"]
    return {"in_progress": in_progress, "confirmed": confirmed}


async def get_appointments_count():
    return await asyncio.to_thread(_get_appointments_count_sync)
