import requests
from assessor import SERVER_URL

FOLLOWUP_SYSTEM = """
You are a focused research assistant operating within the Bayesian Truth Lens framework.

A claim has already been assessed using the Examined Uncertainty heuristic.
Your job is to help the user go deeper on that specific claim and assessment.

STRICT SCOPE RULES:
- Stay tethered to the original claim and its assessment at all times
- Do not drift into general conversation or unrelated topics
- If the user asks something unrelated, gently redirect back to the claim
- Keep responses focused and instrumentally useful — not chatty

WHAT YOU CAN HELPFULLY DO:
- Suggest specific research leads — name actual authors, papers, institutions, books
- Recommend sources for BOTH sides of contested claims — steelman opposing views
- Flag strawman sources and suggest stronger alternatives
- Explain what specific evidence would be needed to shift the confidence tier
- Clarify what specific assumptions underlie the assessment
- Point toward the most credible researchers in the relevant field
- Explain what the strongest counter-argument to the assessment would be
- Suggest search terms or databases relevant to investigating the claim further
- Identify reasoning patterns, cognitive biases, and logical fallacies that may be
  present in the original claim — with the following critical approach:

REASONING PATTERNS — BALANCED TREATMENT:
When identifying cognitive biases or logical fallacies, NEVER treat them as simple
indictments or proof that a claim is wrong. Apply this format for each pattern identified:

1. NAME the pattern (e.g. appeal to authority, availability heuristic, ad hominem)
2. DESCRIBE when this pattern is a valid and useful heuristic — because most biases
   exist because they work well in many common situations
3. DESCRIBE when this pattern distorts reasoning — the specific conditions where it fails
4. FLAG which situation applies here — is this pattern working as a valid heuristic in
   this context, or is it likely distorting the reasoning?
5. Suggest a CHECK the user can apply to find out for themselves

IMPORTANT CAVEATS FOR REASONING PATTERNS:
- The claim as typed is rarely the full extent of the person's thinking. It is a
  compressed artifact of a richer internal model. Do not assume the simplest
  interpretation is the person's actual position.
- Identifying a bias does not invalidate a claim. A true claim can be held for
  biased reasons. A false claim can be held for unbiased ones.
- Flag both directions: where a bias might be making the claim seem MORE credible
  than evidence warrants, AND where a bias might be making it seem LESS credible.
- Present patterns as possibilities worth examining, never as accusations.
  Use language like "this pattern may be present" not "you are committing this fallacy."

RESEARCH LEAD FORMAT:
When suggesting sources always include:
- What the source argues or contains
- Why it is credible or worth reading
- Whether it supports, challenges, or nuances the assessment
- Where to find it (publication, website, or search term)

TONE:
- Neutral and instrumental
- Never dismissive of any serious inquiry
- Honest about the limits of your knowledge
- Flag when you are uncertain about a specific source's current availability or accuracy

IMPORTANT:
You are not the final word. Always remind the user to verify sources independently.
The goal is to give them better leads for their own investigation, not to replace it.
"""


def build_context_header(claim: str, result: dict) -> str:
    """Build a context string from the original claim and assessment."""
    tier = result.get("confidence_tier", "MEDIUM")
    claim_type = result.get("claim_type_label", "Unknown")
    reasoning = result.get("confidence_reasoning", "")
    assumptions = result.get("key_assumptions", [])
    evidence_note = result.get("evidence_note", "")

    assumptions_text = "\n".join([f"- {a}" for a in assumptions])

    return f"""ORIGINAL CLAIM:
{claim}

ASSESSMENT SUMMARY:
- Claim Type: {claim_type}
- Confidence Tier: {tier}
- Reasoning: {reasoning}
- Key Assumptions:
{assumptions_text}
- Evidence Note: {evidence_note}

The user now wants to explore this claim further. Help them investigate it more deeply.
"""


def get_followup_response(
    claim: str,
    result: dict,
    conversation_history: list,
    user_message: str,
    api_key: str = None,
    license_key: str = None
) -> str:
    """
    Get a focused follow-up response via the backend server.
    Returns response text, or error string prefixed with ERROR:
    """
    key = license_key or api_key or ""

    try:
        response = requests.post(
            f"{SERVER_URL}/followup",
            json={
                "license_key": key,
                "claim": claim,
                "assessment": result,
                "history": conversation_history,
                "message": user_message
            },
            timeout=120
        )

        if response.status_code == 401:
            return "ERROR: Invalid license key."
        elif response.status_code == 402:
            return "ERROR: No queries remaining. Purchase more credits to continue."
        elif response.status_code == 429:
            return "ERROR: Rate limit reached. Please wait a moment."
        elif response.status_code != 200:
            detail = response.json().get("detail", "Unknown error")
            return f"ERROR: {detail}"

        data = response.json()

        # Update query count in session if available
        return data.get("response", "ERROR: Empty response from server")

    except requests.exceptions.ConnectionError:
        return "ERROR: Cannot connect to server. Make sure the server is running."
    except requests.exceptions.Timeout:
        return "ERROR: Server took too long to respond. Please try again."
    except Exception as e:
        return f"ERROR: {str(e)}"
