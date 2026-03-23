import os
import json
import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from database import init_db, get_license, decrement_queries, redeem_code
from prompts import SYSTEM_PROMPT
from followup import FOLLOWUP_SYSTEM, build_context_header

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="Bayesian Truth Lens API")

# Allow requests from any frontend origin during development
# Lock this down to your actual domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# Anthropic client — API key loaded from environment variable
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

CLAIM_TYPE_LABELS = {
    "POLITICAL_BEHAVIORAL":        "Political / Behavioral",
    "EMPIRICALLY_SETTLED":         "Empirically Settled",
    "EMPIRICALLY_CONTESTED":       "Empirically Contested",
    "EMPIRICALLY_UNDERDETERMINED": "Empirically Underdetermined",
    "CURRENTLY_UNFALSIFIABLE":     "Currently Unfalsifiable",
    "STRUCTURALLY_METAPHYSICAL":   "Structurally Metaphysical",
    "CONSPIRACY_PATTERN":          "Conspiracy / Pattern Claim",
    "MORAL_COMPLEXITY":            "Moral Complexity",
    "CONTESTED_SOCIAL":            "Contested Social Claim",
}

CONFIDENCE_DESCRIPTIONS = {
    "HIGH":   "Strong convergent evidence. Key assumptions are widely shared and stable.",
    "MEDIUM": "Mixed or partial evidence. Reasonable people disagree, or claim is underdetermined but plausible.",
    "LOW":    "Weak, absent, or contradictory evidence. LOW does not mean false — it means we cannot get there from here with current evidence and reasonable assumptions.",
}

# ── Request / Response models ─────────────────────────────────────────────────

class AssessRequest(BaseModel):
    license_key: str
    claim: str

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

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
    if not ANTHROPIC_API_KEY:
        print("WARNING: ANTHROPIC_API_KEY environment variable not set")

# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok", "service": "Bayesian Truth Lens API"}

# ── License status ────────────────────────────────────────────────────────────

@app.get("/status/{license_key}")
def license_status(license_key: str):
    """Check how many queries remain on a license key."""
    license = get_license(license_key)
    if not license:
        raise HTTPException(status_code=404, detail="License key not found")
    return {
        "valid": True,
        "queries_remaining": license["queries"],
        "email": license["email"]
    }

# ── Assess endpoint ───────────────────────────────────────────────────────────

@app.post("/assess")
def assess(req: AssessRequest):
    """
    Assess a claim using the Examined Uncertainty framework.
    Requires a valid license key with queries remaining.
    """
    # Validate license
    license = get_license(req.license_key)
    if not license:
        raise HTTPException(status_code=401, detail="Invalid license key")
    if license["queries"] <= 0:
        raise HTTPException(
            status_code=402,
            detail="No queries remaining. Purchase more at bayesiantruth.lens/credits"
        )

    # Call Anthropic
    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Assess this claim:\n\n{req.claim}"
                }
            ]
        )
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=500, detail="API configuration error")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit reached. Please try again shortly.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")

    # Parse response
    raw_text = response.content[0].text.strip()

    if "```" in raw_text:
        parts = raw_text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                parsed = json.loads(part)
                raw_text = part
                break
            except json.JSONDecodeError:
                continue

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not parse model response: {str(e)}"
        )

    # Add labels
    parsed["claim_type_label"] = CLAIM_TYPE_LABELS.get(
        parsed.get("claim_type", ""), parsed.get("claim_type", "Unknown")
    )
    parsed["confidence_description"] = CONFIDENCE_DESCRIPTIONS.get(
        parsed.get("confidence_tier", ""), ""
    )

    # Decrement query count AFTER successful assessment
    try:
        queries_remaining = decrement_queries(req.license_key)
        parsed["queries_remaining"] = queries_remaining
    except ValueError:
        raise HTTPException(status_code=402, detail="No queries remaining")

    return parsed

# ── Follow-up endpoint ────────────────────────────────────────────────────────

@app.post("/followup")
def followup(req: FollowupRequest):
    """
    Handle a follow-up conversation message scoped to the original assessment.
    Requires a valid license key with queries remaining.
    """
    license = get_license(req.license_key)
    if not license:
        raise HTTPException(status_code=401, detail="Invalid license key")
    if license["queries"] <= 0:
        raise HTTPException(status_code=402, detail="No queries remaining")

    context_header = build_context_header(req.claim, req.assessment)

    messages = [
        {"role": "user", "content": context_header},
        {"role": "assistant", "content": "Understood. I have the assessment context. What would you like to explore further?"}
    ]

    for msg in req.history:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": req.message})

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1500,
            system=FOLLOWUP_SYSTEM,
            messages=messages
        )
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Rate limit reached. Please try again shortly.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Follow-up failed: {str(e)}")

    try:
        queries_remaining = decrement_queries(req.license_key)
    except ValueError:
        raise HTTPException(status_code=402, detail="No queries remaining")

    return {
        "response": response.content[0].text,
        "queries_remaining": queries_remaining
    }

# ── Redeem endpoint ───────────────────────────────────────────────────────────

@app.post("/redeem")
def redeem(req: RedeemRequest):
    """
    Apply a credit pack redeem code to a license key.
    Adds queries to the license.
    """
    try:
        new_total = redeem_code(req.license_key, req.redeem_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "queries_remaining": new_total,
        "message": f"Credits added. You now have {new_total} queries remaining."
    }

# ── Admin: create license ─────────────────────────────────────────────────────

@app.post("/admin/create-license")
def create_license_endpoint(req: CreateLicenseRequest):
    """
    Admin endpoint to create a new license key.
    Protected by admin secret set in environment variable.
    """
    admin_secret = os.environ.get("ADMIN_SECRET", "")
    if not admin_secret or req.admin_secret != admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    from database import create_license
    key = create_license(email=req.email, queries=req.queries)
    return {
        "license_key": key,
        "email": req.email,
        "queries": req.queries
    }
