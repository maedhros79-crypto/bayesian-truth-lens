from datetime import datetime, date, timedelta

from database import get_db

# Ebbinghaus-based intervals in days
INTERVALS = [1, 7, 16, 35, 62, 90]


def create_skill(
    skill_name: str,
    source_url: str,
    practice_notes: str | None,
    difficulty: str | None,
    practice_prompt: str | None = None,
) -> dict:
    """Create a skill and generate its spaced repetition schedule."""
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO skills (skill_name, source_url, practice_notes, difficulty, practice_prompt)
               VALUES (?, ?, ?, ?, ?)""",
            (skill_name, source_url, practice_notes, difficulty, practice_prompt)
        )
        skill_id = cursor.lastrowid

        today = date.today()
        rewatch_schedule = []
        practice_schedule = []

        for i, interval in enumerate(INTERVALS):
            due = today + timedelta(days=interval)
            due_str = due.isoformat()

            # Rewatch schedule
            conn.execute(
                """INSERT INTO skill_schedule (skill_id, type, due_date, interval_number)
                   VALUES (?, ?, ?, ?)""",
                (skill_id, "rewatch", due_str, i + 1)
            )
            rewatch_schedule.append(due_str)

            # Practice schedule
            conn.execute(
                """INSERT INTO skill_schedule (skill_id, type, due_date, interval_number)
                   VALUES (?, ?, ?, ?)""",
                (skill_id, "practice", due_str, i + 1)
            )
            practice_schedule.append(due_str)

        conn.commit()

        return {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "source_url": source_url,
            "rewatch_schedule": rewatch_schedule,
            "practice_schedule": practice_schedule,
            "next_due": rewatch_schedule[0] if rewatch_schedule else None,
        }
    finally:
        conn.close()


def get_due_skills() -> dict:
    """Get all skills with items due today or overdue."""
    conn = get_db()
    try:
        today = date.today().isoformat()
        rows = conn.execute(
            """SELECT ss.id as schedule_id, ss.skill_id, ss.type, ss.due_date,
                      ss.interval_number, s.skill_name, s.source_url, s.practice_notes,
                      s.practice_prompt, s.difficulty
               FROM skill_schedule ss
               JOIN skills s ON ss.skill_id = s.id
               WHERE ss.due_date <= ? AND ss.completed_at IS NULL AND s.active = 1
               ORDER BY ss.due_date ASC""",
            (today,)
        ).fetchall()

        due_items = []
        for row in rows:
            due_date = date.fromisoformat(row["due_date"])
            days_overdue = (date.today() - due_date).days
            due_items.append({
                "skill_id": row["skill_id"],
                "skill_name": row["skill_name"],
                "due_date": row["due_date"],
                "type": row["type"],
                "source_url": row["source_url"],
                "practice_notes": row["practice_notes"],
                "practice_prompt": row["practice_prompt"],
                "difficulty": row["difficulty"],
                "interval_number": row["interval_number"],
                "days_overdue": days_overdue,
            })

        return {"due_today": due_items}
    finally:
        conn.close()


def complete_skill_item(skill_id: int, item_type: str, retained: bool | None, notes: str | None) -> dict:
    """Mark a skill schedule item as complete and adjust future intervals."""
    conn = get_db()
    try:
        today = date.today().isoformat()
        now = datetime.now().isoformat()

        # Find the next uncompleted item of this type for this skill
        row = conn.execute(
            """SELECT id, interval_number, due_date FROM skill_schedule
               WHERE skill_id = ? AND type = ? AND completed_at IS NULL
               ORDER BY due_date ASC LIMIT 1""",
            (skill_id, item_type)
        ).fetchone()

        if not row:
            return {"error": "No pending schedule item found"}

        # Mark as complete
        conn.execute(
            """UPDATE skill_schedule SET completed_at = ?, retained = ?, notes = ?
               WHERE id = ?""",
            (now, 1 if retained else 0 if retained is False else None, notes, row["id"])
        )

        interval_adjusted = False

        # Adjust future intervals based on retention
        if retained is not None:
            next_item = conn.execute(
                """SELECT id, due_date, interval_number FROM skill_schedule
                   WHERE skill_id = ? AND type = ? AND completed_at IS NULL
                   ORDER BY due_date ASC LIMIT 1""",
                (skill_id, item_type)
            ).fetchone()

            if next_item:
                current_due = date.fromisoformat(next_item["due_date"])
                days_until = (current_due - date.today()).days

                if not retained:
                    # Shorten next interval by 50%
                    new_days = max(1, days_until // 2)
                    new_due = date.today() + timedelta(days=new_days)
                    conn.execute(
                        "UPDATE skill_schedule SET due_date = ? WHERE id = ?",
                        (new_due.isoformat(), next_item["id"])
                    )
                    interval_adjusted = True
                else:
                    # Check for 3 consecutive retained=true
                    recent = conn.execute(
                        """SELECT retained FROM skill_schedule
                           WHERE skill_id = ? AND type = ? AND completed_at IS NOT NULL
                           ORDER BY completed_at DESC LIMIT 3""",
                        (skill_id, item_type)
                    ).fetchall()
                    if len(recent) >= 3 and all(r["retained"] == 1 for r in recent):
                        new_days = min(180, int(days_until * 1.25))
                        new_days = max(1, new_days)
                        new_due = date.today() + timedelta(days=new_days)
                        conn.execute(
                            "UPDATE skill_schedule SET due_date = ? WHERE id = ?",
                            (new_due.isoformat(), next_item["id"])
                        )
                        interval_adjusted = True

        conn.commit()

        # Get next due date
        next_row = conn.execute(
            """SELECT due_date FROM skill_schedule
               WHERE skill_id = ? AND type = ? AND completed_at IS NULL
               ORDER BY due_date ASC LIMIT 1""",
            (skill_id, item_type)
        ).fetchone()

        return {
            "next_due": next_row["due_date"] if next_row else None,
            "interval_adjusted": interval_adjusted,
        }
    finally:
        conn.close()


def get_all_skills() -> list[dict]:
    """Get all skills with their schedules and completion history."""
    conn = get_db()
    try:
        skills = conn.execute(
            "SELECT * FROM skills WHERE active = 1 ORDER BY created_at DESC"
        ).fetchall()

        result = []
        for skill in skills:
            schedule = conn.execute(
                """SELECT type, due_date, interval_number, completed_at, retained, notes
                   FROM skill_schedule WHERE skill_id = ? ORDER BY due_date ASC""",
                (skill["id"],)
            ).fetchall()

            result.append({
                "skill_id": skill["id"],
                "skill_name": skill["skill_name"],
                "source_url": skill["source_url"],
                "practice_notes": skill["practice_notes"],
                "difficulty": skill["difficulty"],
                "created_at": skill["created_at"],
                "schedule": [
                    {
                        "type": s["type"],
                        "due_date": s["due_date"],
                        "interval_number": s["interval_number"],
                        "completed_at": s["completed_at"],
                        "retained": s["retained"],
                        "notes": s["notes"],
                    }
                    for s in schedule
                ],
            })

        return result
    finally:
        conn.close()


def find_related(skill_name: str, source_url: str | None) -> dict:
    """Generate an optimized search query for finding related content."""
    query = f"{skill_name} tutorial"
    return {
        "query_used": query,
        "note": (
            "Related content discovery requires web search integration — "
            "this endpoint returns a search query optimized for finding "
            "quality content on this skill. Use with the RSS feed endpoint "
            "or manual search."
        ),
    }
