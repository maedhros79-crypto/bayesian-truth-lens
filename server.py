import os
import json
import anthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from database import init_db, get_license, decrement_queries, redeem_code
from prompts import SYSTEM_PROMPT
from followup import FOLLOWUP_SYSTEM, build_context_header

# ── Web search setup ──────────────────────────────────────────────────────────


def search_web(query: str, max_results: int = 5) -> str:
    """
    Search the web using Tavily and return formatted results.
    Returns empty string if Tavily key not configured.
    """
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    if not tavily_key:
        print("WARNING: TAVILY_API_KEY not set — skipping web search")
        return ""

    print(f"INFO: Running Tavily search for: {query[:80]}")
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results
        )
        results = response.get("results", [])
        if not results:
            return ""

        print(f"INFO: Tavily returned {len(results)} results")
        formatted = "CURRENT WEB SEARCH RESULTS (use these to supplement your assessment):\n\n"
        for i, r in enumerate(results, 1):
            formatted += f"Source {i}: {r.get('title', 'Unknown')}\n"
            formatted += f"URL: {r.get('url', '')}\n"
            formatted += f"Content: {r.get('content', '')[:500]}\n\n"
        return formatted

    except Exception as e:
        print(f"Tavily search failed: {e}")
        return ""


def is_temporally_sensitive(claim: str) -> bool:
    """
    Quick heuristic check for temporal sensitivity before sending to model.
    Catches obvious cases to trigger web search proactively.
    """
    temporal_keywords = [
        "2024", "2025", "2026", "current", "currently", "now", "today",
        "recent", "recently", "latest", "ongoing", "this year", "last year",
        "this month", "right now", "at the moment", "as of", "war", "conflict",
        "election", "president", "prime minister", "crisis", "invasion",
        "attack", "ceasefire", "treaty", "sanctions", "breaking"
    ]
    claim_lower = claim.lower()
    return any(keyword in claim_lower for keyword in temporal_keywords)

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

# ── Startup ───────────────────────────────────────────────────────────────────


@app.on_event("startup")
def startup():
    init_db()
    if not ANTHROPIC_API_KEY:
        print("WARNING: ANTHROPIC_API_KEY environment variable not set")

# ── Health check ──────────────────────────────────────────────────────────────


@app.get("/")
def health():
    return {
        "status": "ok",
        "service": "Bayesian Truth Lens API",
        "tavily_configured": bool(os.environ.get("TAVILY_API_KEY", "")),
        "resend_configured": bool(os.environ.get("RESEND_API_KEY", ""))
    }

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

    # ── Web search for temporally sensitive claims ───────────────────────────
    web_context = ""
    if is_temporally_sensitive(req.claim):
        print(
            f"INFO: Temporal sensitivity detected for claim: {req.claim[:80]}")
        web_context = search_web(req.claim)
        if web_context:
            print("INFO: Web context injected into assessment")
        else:
            print("WARNING: Temporal claim detected but web search returned empty")

    # Build system prompt — add plain language modifier if requested
    system = SYSTEM_PROMPT

    # Inject web search results if available
    if web_context:
        system += f"""

{web_context}

Use the above search results to supplement your assessment where relevant.
Cite specific sources when drawing on them. Note if search results are recent
enough to update your confidence tier or change your assessment meaningfully.
Always flag if the search results themselves appear biased or incomplete.
"""

    if req.plain_language:
        system += """

PLAIN LANGUAGE MODE — ACTIVE:
The user has requested simpler explanations. Apply these rules to your entire response:
- Replace all technical philosophical terms with everyday equivalents
  Examples: "ontological" → "about what exists", "empirically underdetermined" → 
  "we don't have enough evidence yet", "heuristic" → "mental shortcut"
- Use concrete real-world examples instead of abstract descriptions
- Keep sentences shorter — aim for one idea per sentence
- If you must use a technical term, define it immediately in plain language
- Write as if explaining to a curious and intelligent person who hasn't studied philosophy
- Same depth and nuance — just more accessible vocabulary
- Analogies and comparisons are encouraged
"""

    # Call Anthropic
    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2000,
            system=system,
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
        raise HTTPException(
            status_code=429, detail="Rate limit reached. Please try again shortly.")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Assessment failed: {str(e)}")

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

    # Flag whether web search was used
    parsed["web_search_used"] = bool(web_context)

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
        raise HTTPException(
            status_code=429, detail="Rate limit reached. Please try again shortly.")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Follow-up failed: {str(e)}")

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

# ── Email sending ─────────────────────────────────────────────────────────────


def send_license_email(email: str, license_key: str, queries: int):
    """Send license key email to new customer via Resend."""
    import resend

    resend.api_key = os.environ.get("RESEND_API_KEY", "")
    if not resend.api_key:
        print("WARNING: RESEND_API_KEY not set — skipping email")
        return False

    app_url = os.environ.get("APP_URL", "https://your-app.streamlit.app")

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


# ── Gumroad webhook ───────────────────────────────────────────────────────────

class GumroadWebhook(BaseModel):
    seller_id: str = ""
    product_id: str = ""
    product_name: str = ""
    email: str = ""
    price: int = 0
    sale_id: str = ""
    sale_timestamp: str = ""
    # Gumroad sends many fields — we only need a few


@app.post("/webhook/gumroad")
async def gumroad_webhook(request: Request):
    """
    Receives purchase notifications from Gumroad.
    Creates a license key and emails it to the buyer automatically.
    """
    from database import create_license

    # Gumroad sends form data not JSON
    form_data = await request.form()
    email = form_data.get("email", "")
    product_name = form_data.get("product_name", "")
    sale_id = form_data.get("sale_id", "")

    if not email:
        raise HTTPException(status_code=400, detail="No email in webhook")

    # Determine query allocation based on product
    # Adjust these based on your Gumroad product names
    if "credit" in product_name.lower() or "pack" in product_name.lower():
        queries = 300  # credit pack purchase
    else:
        queries = 300  # standard app purchase — adjust as needed

    # Create license key
    key = create_license(email=email, queries=queries)

    # Send email
    email_sent = send_license_email(email, key, queries)

    # Log the sale
    print(
        f"Sale processed: {sale_id} | {email} | {queries} queries | email_sent={email_sent}")

    return {
        "success": True,
        "license_key": key,
        "email": email,
        "queries": queries,
        "email_sent": email_sent
    }
