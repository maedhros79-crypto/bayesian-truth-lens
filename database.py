import sqlite3
import secrets
import string
from datetime import datetime
from pathlib import Path

# Use /data for Railway persistent volume, fall back to local for development
import os
_data_dir = Path("/data") if Path("/data").exists() else Path(__file__).parent
DB_PATH = _data_dir / "licenses.db"


def get_connection():
    """Get a database connection with row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist. Safe to call on every startup."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                key         TEXT PRIMARY KEY,
                email       TEXT,
                queries     INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL,
                last_used   TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS redeem_codes (
                code        TEXT PRIMARY KEY,
                queries     INTEGER NOT NULL,
                used        INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL
            )
        """)
        conn.commit()


def generate_license_key() -> str:
    """Generate a unique license key in format BTL-XXXX-XXXX-XXXX."""
    chars = string.ascii_uppercase + string.digits
    segments = [''.join(secrets.choice(chars) for _ in range(4)) for _ in range(3)]
    return f"BTL-{'- '.join(segments)}".replace('- ', '-')


def generate_redeem_code() -> str:
    """Generate a unique redeem code for credit packs."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(16))


def create_license(email: str, queries: int = 300) -> str:
    """
    Create a new license key with initial query allocation.
    Returns the generated key.
    """
    key = generate_license_key()
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO licenses (key, email, queries, created_at) VALUES (?, ?, ?, ?)",
            (key, email, queries, now)
        )
        conn.commit()
    return key


def get_license(key: str) -> dict | None:
    """Look up a license key. Returns dict or None if not found."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM licenses WHERE key = ?", (key,)
        ).fetchone()
    return dict(row) if row else None


def decrement_queries(key: str) -> int:
    """
    Decrement query count by 1 for a valid key.
    Returns remaining query count, or -1 if key not found.
    Raises ValueError if no queries remaining.
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT queries FROM licenses WHERE key = ?", (key,)
        ).fetchone()

        if not row:
            return -1

        remaining = row["queries"]
        if remaining <= 0:
            raise ValueError("No queries remaining")

        now = datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE licenses SET queries = queries - 1, last_used = ? WHERE key = ?",
            (now, key)
        )
        conn.commit()
        return remaining - 1


def create_redeem_code(queries: int) -> str:
    """
    Create a redeem code worth a given number of queries.
    Returns the code string.
    """
    code = generate_redeem_code()
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO redeem_codes (code, queries, created_at) VALUES (?, ?, ?)",
            (code, queries, now)
        )
        conn.commit()
    return code


def redeem_code(license_key: str, code: str) -> int:
    """
    Apply a redeem code to a license key.
    Returns new query total.
    Raises ValueError if code invalid, already used, or license not found.
    """
    with get_connection() as conn:
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
        conn.execute(
            "UPDATE redeem_codes SET used = 1 WHERE code = ?", (code,)
        )
        conn.execute(
            "UPDATE licenses SET queries = queries + ? WHERE key = ?",
            (queries_to_add, license_key)
        )
        conn.commit()

        new_total = license_row["queries"] + queries_to_add
        return new_total
