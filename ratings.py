from urllib.parse import urlparse
from datetime import datetime

from database import get_db
from models import CreatorReputation


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def save_rating(url: str, worth_time: bool | None, delivered_promise: bool | None, recommend_learning: bool | None) -> bool:
    """Save a content rating and update creator reputation."""
    domain = extract_domain(url)
    conn = get_db()
    try:
        # Insert rating
        conn.execute(
            """INSERT INTO content_ratings (url, domain, worth_time, delivered_promise, recommend_learning)
               VALUES (?, ?, ?, ?, ?)""",
            (url, domain,
             1 if worth_time is True else (0 if worth_time is False else None),
             1 if delivered_promise is True else (0 if delivered_promise is False else None),
             1 if recommend_learning is True else (0 if recommend_learning is False else None))
        )
        conn.commit()

        # Recalculate creator reputation
        _recalculate_reputation(conn, domain)
        return True
    finally:
        conn.close()


def _recalculate_reputation(conn, domain: str):
    """Recalculate creator reputation from all ratings for a domain."""
    rows = conn.execute(
        "SELECT worth_time, delivered_promise, recommend_learning FROM content_ratings WHERE domain = ?",
        (domain,)
    ).fetchall()

    total = len(rows)
    wt_pos = sum(1 for r in rows if r["worth_time"] == 1)
    dp_pos = sum(1 for r in rows if r["delivered_promise"] == 1)
    rl_pos = sum(1 for r in rows if r["recommend_learning"] == 1)

    conn.execute(
        """INSERT OR REPLACE INTO creator_reputation
           (domain, total_ratings, worth_time_positive, delivered_promise_positive,
            recommend_learning_positive, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (domain, total, wt_pos, dp_pos, rl_pos, datetime.now().isoformat())
    )
    conn.commit()


def get_creator_reputation_for_domain(domain: str) -> CreatorReputation | None:
    """Get creator reputation for a domain."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM creator_reputation WHERE domain = ?", (domain,)
        ).fetchone()
        if not row or row["total_ratings"] == 0:
            return None

        total = row["total_ratings"]
        wt_pct = row["worth_time_positive"] / total if total else 0
        dp_pct = row["delivered_promise_positive"] / total if total else 0
        rl_pct = row["recommend_learning_positive"] / total if total else 0

        avg_positive = (wt_pct + dp_pct + rl_pct) / 3
        if avg_positive > 0.75:
            tier = "High"
        elif avg_positive < 0.40:
            tier = "Low"
        else:
            tier = "Medium"

        return CreatorReputation(
            domain=domain,
            total_ratings=total,
            worth_time_pct=round(wt_pct, 2),
            delivered_promise_pct=round(dp_pct, 2),
            recommend_learning_pct=round(rl_pct, 2),
            human_trust_tier=tier,
        )
    finally:
        conn.close()
