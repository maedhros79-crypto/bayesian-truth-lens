"""
RCP Unified Service — Reality Calibration Platform
Combines Bayesian Truth Lens (Module 1) and RSS Content Quality Feed (Module 2)
in a single FastAPI application.

Port: 8000 (single service, single port)
"""

import os
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

from models import (
    ScoreRequest, BatchScoreRequest, ScoreResult,
    FeedRequest, RateRequest,
    SkillTagRequest, SkillCompleteRequest, SkillFindRelatedRequest,
    TrendRequest,
)
from fetcher import fetch_content
from scorer import score_content
from database import (
    init_db, get_db,
    get_license, decrement_queries,
    create_license, create_redeem_code, redeem_code as db_redeem_code,
)
from feed_manager import score_feed_items
from ratings import save_rating, get_creator_reputation_for_domain
from skills import create_skill, get_due_skills, complete_skill_item, get_all_skills, find_related
from trend_scorer import assess_trend
from channel_resolver import resolve_channel
from btl_assessor import assess_claim, get_followup
import anthropic

load_dotenv()

app = FastAPI(title="Reality Calibration Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


@app.on_event("startup")
def startup():
    init_db()
    if not ANTHROPIC_API_KEY:
        print("WARNING: ANTHROPIC_API_KEY not set")


def get_api_key() -> str:
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not set")
    return ANTHROPIC_API_KEY


# ─── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "Reality Calibration Platform",
        "modules": ["btl", "rss"],
        "tavily_configured": bool(os.getenv("TAVILY_API_KEY")),
        "resend_configured": bool(os.getenv("RESEND_API_KEY")),
    }


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 1 — Bayesian Truth Lens
# ══════════════════════════════════════════════════════════════════════════════

class AssessRequest(BaseModel):
    license_key: str
    claim: str
    plain_language: bool = False


class FollowupMessage(BaseModel):
    role: str
    content: str


class FollowupRequest(BaseModel):
    license_key: str
    claim: str
    assessment: dict
    history: list[FollowupMessage]
    message: str


class RedeemRequest(BaseModel):
    license_key: str
    redeem_code: str


class CreateLicenseRequest(BaseModel):
    admin_secret: str
    email: str
    queries: int = 300


@app.post("/assess")
async def assess(req: AssessRequest):
    """Assess a claim using the Examined Uncertainty framework."""
    license = get_license(req.license_key)
    if not license:
        raise HTTPException(status_code=401, detail="Invalid license key")
    if license["queries"] <= 0:
        raise HTTPException(status_code=402, detail="No queries remaining")

    try:
        result = await assess_claim(
            claim=req.claim,
            api_key=get_api_key(),
            plain_language=req.plain_language,
        )
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=500, detail="API configuration error")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit reached. Please try again shortly.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")

    try:
        queries_remaining = decrement_queries(req.license_key)
        result["queries_remaining"] = queries_remaining
    except ValueError:
        raise HTTPException(status_code=402, detail="No queries remaining")

    return result


@app.post("/followup")
async def followup(req: FollowupRequest):
    """Follow-up conversation scoped to original BTL assessment."""
    license = get_license(req.license_key)
    if not license:
        raise HTTPException(status_code=401, detail="Invalid license key")
    if license["queries"] <= 0:
        raise HTTPException(status_code=402, detail="No queries remaining")

    try:
        response_text = await get_followup(
            claim=req.claim,
            assessment=req.assessment,
            history=[{"role": m.role, "content": m.content} for m in req.history],
            message=req.message,
            api_key=get_api_key(),
        )
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit reached. Please try again shortly.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Follow-up failed: {str(e)}")

    try:
        queries_remaining = decrement_queries(req.license_key)
    except ValueError:
        raise HTTPException(status_code=402, detail="No queries remaining")

    return {"response": response_text, "queries_remaining": queries_remaining}


@app.get("/status/{license_key}")
def license_status(license_key: str):
    license = get_license(license_key)
    if not license:
        raise HTTPException(status_code=404, detail="License key not found")
    return {
        "valid": True,
        "queries_remaining": license["queries"],
        "email": license["email"],
    }


@app.post("/redeem")
def redeem(req: RedeemRequest):
    try:
        new_total = db_redeem_code(req.license_key, req.redeem_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "success": True,
        "queries_remaining": new_total,
        "message": f"Credits added. You now have {new_total} queries remaining.",
    }


@app.post("/admin/create-license")
def create_license_endpoint(req: CreateLicenseRequest):
    admin_secret = os.getenv("ADMIN_SECRET", "")
    if not admin_secret or req.admin_secret != admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    key = create_license(email=req.email, queries=req.queries)
    return {"license_key": key, "email": req.email, "queries": req.queries}


# ─── Gumroad webhook ────────────────────────────────────────────────────────

@app.post("/webhook/gumroad")
async def gumroad_webhook(request: Request):
    form_data = await request.form()
    email = form_data.get("email", "")
    product_name = form_data.get("product_name", "")
    sale_id = form_data.get("sale_id", "")

    if not email:
        raise HTTPException(status_code=400, detail="No email in webhook")

    queries = 300  # default; adjust per product name if needed
    if "credit" in product_name.lower() or "pack" in product_name.lower():
        queries = 300

    key = create_license(email=email, queries=queries)
    email_sent = _send_license_email(email, key, queries)

    print(f"Sale processed: {sale_id} | {email} | {queries} queries | email_sent={email_sent}")
    return {"success": True, "license_key": key, "email": email, "queries": queries, "email_sent": email_sent}


def _send_license_email(email: str, license_key: str, queries: int) -> bool:
    import resend
    resend.api_key = os.getenv("RESEND_API_KEY", "")
    if not resend.api_key:
        print("WARNING: RESEND_API_KEY not set — skipping email")
        return False
    app_url = os.getenv("APP_URL", "https://your-app.streamlit.app")
    try:
        resend.Emails.send({
            "from": "Bayesian Truth Lens <onboarding@resend.dev>",
            "to": email,
            "subject": "Your Bayesian Truth Lens License Key",
            "html": f"""
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    <h2 style="color: #333;">Your Bayesian Truth Lens License Key</h2>
    <p>Thank you for your purchase. Here is your license key:</p>
    <div style="background: #f5f5f5; border: 1px solid #ddd; border-radius: 6px;
                padding: 16px; font-family: monospace; font-size: 1.2em;
                text-align: center; letter-spacing: 2px; margin: 24px 0;">
        {license_key}
    </div>
    <p>This key includes <strong>{queries} queries</strong>.</p>
    <p>To get started:</p>
    <ol>
        <li>Go to <a href="{app_url}">{app_url}</a></li>
        <li>Enter your license key in the License Key field</li>
        <li>Type any claim and hit Assess</li>
    </ol>
    <p style="margin-top: 32px; color: #666; font-size: 0.9em;">
        This tool is a thinking aid, not an oracle.
        The judgment is always yours.<br><br>
        Keep this email — your license key is not stored anywhere else.
    </p>
</div>
            """
        })
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# MODULE 2 — RSS Content Quality Feed
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/score", response_model=ScoreResult)
async def score_url(req: ScoreRequest):
    api_key = get_api_key()
    fetch_result = fetch_content(req.url)
    return await score_content(req.url, fetch_result, api_key)


@app.post("/score-batch", response_model=list[ScoreResult])
async def score_batch(req: BatchScoreRequest):
    api_key = get_api_key()

    async def score_one(url: str) -> ScoreResult:
        fetch_result = fetch_content(url)
        return await score_content(url, fetch_result, api_key)

    results = list(await asyncio.gather(*[score_one(url) for url in req.urls]))
    verdict_order = {"Pass": 0, "Watch": 1, "Skip": 2}
    return sorted(results, key=lambda r: verdict_order.get(r.verdict, 3))


@app.post("/feed", response_model=list[ScoreResult])
async def load_feed(req: FeedRequest):
    api_key = get_api_key()
    return await score_feed_items(
        feed_urls=req.feed_urls,
        api_key=api_key,
        filter_skip=req.filter_skip,
        limit_per_feed=req.limit_per_feed,
        total_limit=req.total_limit,
        intent=req.intent,
        use_saved_feeds=req.use_saved_feeds,
    )


# ─── Ratings ────────────────────────────────────────────────────────────────

@app.post("/rate")
async def rate_content(req: RateRequest):
    save_rating(req.url, req.worth_time, req.delivered_promise, req.recommend_learning)
    return {"saved": True}


@app.get("/creator-reputation/{domain}")
async def creator_reputation(domain: str):
    rep = get_creator_reputation_for_domain(domain)
    if not rep:
        return {
            "domain": domain,
            "total_ratings": 0,
            "worth_time_pct": 0,
            "delivered_promise_pct": 0,
            "recommend_learning_pct": 0,
            "human_trust_tier": "No data",
        }
    return rep


# ─── Skills ──────────────────────────────────────────────────────────────────

@app.post("/skills/tag")
async def tag_skill(req: SkillTagRequest):
    api_key = get_api_key()
    practice_prompt = None
    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        prompt_text = (
            f"Generate a single concrete practice exercise for someone learning {req.skill_name}."
            + (f" Their notes: {req.practice_notes}." if req.practice_notes else "")
            + " 2-3 sentences maximum. Specific and actionable."
        )
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt_text}]
        )
        practice_prompt = message.content[0].text.strip()
    except Exception:
        pass
    return create_skill(req.skill_name, req.url, req.practice_notes, req.difficulty, practice_prompt)


@app.get("/skills/due")
async def skills_due():
    return get_due_skills()


@app.post("/skills/complete")
async def skill_complete(req: SkillCompleteRequest):
    return complete_skill_item(req.skill_id, req.type, req.retained, req.notes)


@app.get("/skills/all")
async def all_skills():
    return get_all_skills()


@app.post("/skills/find-related")
async def skill_find_related(req: SkillFindRelatedRequest):
    return find_related(req.skill_name, req.source_url)


@app.post("/skills/skip-today")
async def skill_skip_today(req: dict):
    from datetime import date, timedelta
    skill_id = req.get("skill_id")
    item_type = req.get("type", "practice")
    if not skill_id:
        raise HTTPException(status_code=400, detail="skill_id required")
    conn = get_db()
    try:
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        row = conn.execute(
            """SELECT id FROM skill_schedule
               WHERE skill_id = ? AND type = ? AND completed_at IS NULL
               ORDER BY due_date ASC LIMIT 1""",
            (skill_id, item_type)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE skill_schedule SET due_date = ? WHERE id = ?",
                (tomorrow, row["id"])
            )
            conn.commit()
        return {"skipped": True, "new_due": tomorrow}
    finally:
        conn.close()


# ─── Trend Scorer ─────────────────────────────────────────────────────────────

@app.post("/assess-trend")
async def assess_trend_endpoint(req: TrendRequest):
    api_key = get_api_key()
    return await assess_trend(req.topic, req.context, api_key)


# ─── Feed Persistence ──────────────────────────────────────────────────────────

@app.get("/feeds/saved")
async def get_saved_feeds():
    conn = get_db()
    feeds = conn.execute(
        "SELECT id, url, label, category FROM saved_feeds WHERE active=1 ORDER BY category, label"
    ).fetchall()
    conn.close()
    return [dict(f) for f in feeds]


@app.post("/feeds/save")
async def save_feed(req: dict):
    url = req.get("url", "").strip()
    label = req.get("label", url).strip()
    category = req.get("category", "General").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url required")
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO saved_feeds (url, label, category) VALUES (?, ?, ?)",
        (url, label, category)
    )
    conn.commit()
    conn.close()
    return {"saved": True}


@app.delete("/feeds/saved/{feed_id}")
async def delete_saved_feed(feed_id: int):
    conn = get_db()
    conn.execute("UPDATE saved_feeds SET active=0 WHERE id=?", (feed_id,))
    conn.commit()
    conn.close()
    return {"deleted": True}


# ─── Watch Queue ──────────────────────────────────────────────────────────────

@app.post("/queue/add")
async def queue_add(req: dict):
    url = req.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url required")
    conn = get_db()
    try:
        max_pos = conn.execute("SELECT MAX(position) FROM watch_queue").fetchone()[0] or 0
        conn.execute(
            """INSERT INTO watch_queue (url, title, source_feed, category, verdict, position)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (url, req.get("title"), req.get("source_feed"), req.get("category"),
             req.get("verdict"), max_pos + 1)
        )
        conn.commit()
        return {"queued": True}
    finally:
        conn.close()


@app.get("/queue")
async def queue_list():
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM watch_queue ORDER BY position ASC, added_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.delete("/queue/{item_id}")
async def queue_remove(item_id: int):
    conn = get_db()
    try:
        conn.execute("DELETE FROM watch_queue WHERE id=?", (item_id,))
        conn.commit()
        return {"deleted": True}
    finally:
        conn.close()


@app.post("/queue/clear")
async def queue_clear():
    conn = get_db()
    try:
        conn.execute("DELETE FROM watch_queue")
        conn.commit()
        return {"cleared": True}
    finally:
        conn.close()


# ─── Channel Resolver ─────────────────────────────────────────────────────────

@app.post("/resolve-channel")
async def resolve_youtube_channel(req: dict):
    query = req.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    return await resolve_channel(query)


# ─── Frontend ─────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")
