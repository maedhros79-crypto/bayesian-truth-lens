"""
Unified RCP database — RSS scorer schema + BTL license management.
Single SQLite file. Safe to call init_db() on every startup.
"""

import sqlite3
import os
import secrets
import string
from datetime import datetime
from pathlib import Path

# Railway persistent volume or local fallback
_data_dir = Path("/data") if Path("/data").exists() else Path(__file__).parent
DB_PATH = os.getenv("DB_PATH", str(_data_dir / "rcp.db"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        -- ── RSS / Content scoring ──────────────────────────────────────────

        CREATE TABLE IF NOT EXISTS score_cache (
            url TEXT PRIMARY KEY,
            title TEXT,
            content_type TEXT,
            verdict TEXT,
            verdict_reason TEXT,
            scores_json TEXT,
            fetch_method TEXT,
            scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS content_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            domain TEXT,
            worth_time INTEGER,
            delivered_promise INTEGER,
            recommend_learning INTEGER,
            rated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS creator_reputation (
            domain TEXT PRIMARY KEY,
            total_ratings INTEGER DEFAULT 0,
            worth_time_positive INTEGER DEFAULT 0,
            delivered_promise_positive INTEGER DEFAULT 0,
            recommend_learning_positive INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT NOT NULL,
            source_url TEXT,
            practice_notes TEXT,
            difficulty TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS skill_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id INTEGER REFERENCES skills(id),
            type TEXT NOT NULL,
            due_date DATE NOT NULL,
            interval_number INTEGER,
            completed_at TIMESTAMP,
            retained INTEGER,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS saved_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            label TEXT,
            category TEXT DEFAULT 'General',
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS watch_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT,
            source_feed TEXT,
            category TEXT,
            verdict TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            position INTEGER
        );

        -- ── BTL license management ─────────────────────────────────────────

        CREATE TABLE IF NOT EXISTS licenses (
            key         TEXT PRIMARY KEY,
            email       TEXT,
            queries     INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL,
            last_used   TEXT
        );

        CREATE TABLE IF NOT EXISTS redeem_codes (
            code        TEXT PRIMARY KEY,
            queries     INTEGER NOT NULL,
            used        INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL
        );
    """)

    conn.commit()

    # Non-breaking column migrations
    for migration in [
        "ALTER TABLE skills ADD COLUMN practice_prompt TEXT",
    ]:
        try:
            cursor.execute(migration)
            conn.commit()
        except Exception:
            pass  # column already exists

    conn.close()


# ── License helpers ────────────────────────────────────────────────────────────

def _generate_license_key() -> str:
    chars = string.ascii_uppercase + string.digits
    segments = [''.join(secrets.choice(chars) for _ in range(4)) for _ in range(3)]
    return f"BTL-{'-'.join(segments)}"


def _generate_redeem_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(16))


def create_license(email: str, queries: int = 300) -> str:
    key = _generate_license_key()
    now = datetime.utcnow().isoformat()
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO licenses (key, email, queries, created_at) VALUES (?, ?, ?, ?)",
            (key, email, queries, now)
        )
        conn.commit()
        return key
    finally:
        conn.close()


def get_license(key: str) -> dict | None:
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM licenses WHERE key = ?", (key,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def decrement_queries(key: str) -> int:
    """Returns remaining count. Raises ValueError if none left or key not found."""
    conn = get_db()
    try:
        row = conn.execute("SELECT queries FROM licenses WHERE key = ?", (key,)).fetchone()
        if not row:
            return -1
        if row["queries"] <= 0:
            raise ValueError("No queries remaining")
        now = datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE licenses SET queries = queries - 1, last_used = ? WHERE key = ?",
            (now, key)
        )
        conn.commit()
        return row["queries"] - 1
    finally:
        conn.close()


def create_redeem_code(queries: int) -> str:
    code = _generate_redeem_code()
    now = datetime.utcnow().isoformat()
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO redeem_codes (code, queries, created_at) VALUES (?, ?, ?)",
            (code, queries, now)
        )
        conn.commit()
        return code
    finally:
        conn.close()


def redeem_code(license_key: str, code: str) -> int:
    """Apply a redeem code. Returns new query total. Raises ValueError on failure."""
    conn = get_db()
    try:
        redeem_row = conn.execute(
            "SELECT * FROM redeem_codes WHERE code = ?", (code,)
        ).fetchone()
        if not redeem_row:
            raise ValueError("Invalid redeem code")
        if redeem_row["used"]:
            raise ValueError("Redeem code already used")

        license_row = conn.execute(
            "SELECT queries FROM licenses WHERE key = ?", (license_key,)
        ).fetchone()
        if not license_row:
            raise ValueError("Invalid license key")

        queries_to_add = redeem_row["queries"]
        conn.execute("UPDATE redeem_codes SET used = 1 WHERE code = ?", (code,))
        conn.execute(
            "UPDATE licenses SET queries = queries + ? WHERE key = ?",
            (queries_to_add, license_key)
        )
        conn.commit()
        return license_row["queries"] + queries_to_add
    finally:
        conn.close()
