"""
BTL claim assessment module — Bayesian Truth Lens logic.
Extracted from BTL server.py into a clean module that fits the unified RCP service.
"""

import os
import json
import anthropic

from prompts import SYSTEM_PROMPT
from btl_followup import FOLLOWUP_SYSTEM, build_context_header


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
    "EVALUATIVE_VAGUE":            "Evaluative / Open Question",
}

CONFIDENCE_DESCRIPTIONS = {
    "HIGH":   "Strong convergent evidence. Key assumptions are widely shared and stable.",
    "MEDIUM": "Mixed or partial evidence. Reasonable people disagree, or claim is underdetermined but plausible.",
    "LOW":    "Weak, absent, or contradictory evidence. LOW does not mean false — it means we cannot get there from here with current evidence and reasonable assumptions.",
}

TEMPORAL_KEYWORDS = [
    "2024", "2025", "2026", "current", "currently", "now", "today",
    "recent", "recently", "latest", "ongoing", "this year", "last year",
    "this month", "right now", "at the moment", "as of", "war", "conflict",
    "election", "president", "prime minister", "crisis", "invasion",
    "attack", "ceasefire", "treaty", "sanctions", "breaking",
]


def is_temporally_sensitive(claim: str) -> bool:
    claim_lower = claim.lower()
    return any(kw in claim_lower for kw in TEMPORAL_KEYWORDS)


def search_web(query: str, max_results: int = 5) -> str:
    """Search via Tavily. Returns formatted results string or empty string."""
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    if not tavily_key:
        return ""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
        response = client.search(query=query, search_depth="basic", max_results=max_results)
        results = response.get("results", [])
        if not results:
            return ""
        formatted = "CURRENT WEB SEARCH RESULTS (use these to supplement your assessment):\n\n"
        for i, r in enumerate(results, 1):
            formatted += f"Source {i}: {r.get('title', 'Unknown')}\n"
            formatted += f"URL: {r.get('url', '')}\n"
            formatted += f"Content: {r.get('content', '')[:500]}\n\n"
        return formatted
    except Exception as e:
        print(f"Tavily search failed: {e}")
        return ""


async def assess_claim(
    claim: str,
    api_key: str,
    plain_language: bool = False,
) -> dict:
    """
    Run full BTL claim assessment. Returns parsed result dict.
    Raises exceptions on API failure — caller handles HTTP status codes.
    """
    client = anthropic.AsyncAnthropic(api_key=api_key)

    # Web search for temporally sensitive claims
    web_context = ""
    if is_temporally_sensitive(claim):
        web_context = search_web(claim)

    # Build system prompt
    system = SYSTEM_PROMPT

    if web_context:
        system += f"""

{web_context}

Use the above search results to supplement your assessment where relevant.
Cite specific sources when drawing on them. Note if search results are recent
enough to update your confidence tier or change your assessment meaningfully.
Always flag if the search results themselves appear biased or incomplete.
"""

    if plain_language:
        system += """

PLAIN LANGUAGE MODE — ACTIVE:
Replace all technical philosophical terms with everyday equivalents.
Use concrete real-world examples instead of abstract descriptions.
Keep sentences shorter — one idea per sentence.
If you must use a technical term, define it immediately in plain language.
Write as if explaining to a curious and intelligent person who hasn't studied philosophy.
Same depth and nuance — just more accessible vocabulary.
Analogies and comparisons are encouraged.
"""

    message = await client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": f"Assess this claim:\n\n{claim}"}]
    )

    raw_text = message.content[0].text.strip()

    # Strip markdown fences if present
    if "```" in raw_text:
        for part in raw_text.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                parsed = json.loads(part)
                break
            except json.JSONDecodeError:
                continue
        else:
            parsed = json.loads(raw_text)
    else:
        parsed = json.loads(raw_text)

    # Add labels
    parsed["claim_type_label"] = CLAIM_TYPE_LABELS.get(
        parsed.get("claim_type", ""), parsed.get("claim_type", "Unknown")
    )
    parsed["confidence_description"] = CONFIDENCE_DESCRIPTIONS.get(
        parsed.get("confidence_tier", ""), ""
    )
    parsed["web_search_used"] = bool(web_context)

    return parsed


async def get_followup(
    claim: str,
    assessment: dict,
    history: list[dict],
    message: str,
    api_key: str,
) -> str:
    """Run BTL follow-up conversation. Returns response text."""
    client = anthropic.AsyncAnthropic(api_key=api_key)

    context_header = build_context_header(claim, assessment)

    messages = [
        {"role": "user", "content": context_header},
        {"role": "assistant", "content": "Understood. I have the assessment context. What would you like to explore further?"},
    ]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    response = await client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        system=FOLLOWUP_SYSTEM,
        messages=messages,
    )

    return response.content[0].text
