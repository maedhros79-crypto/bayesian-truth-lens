import json
import requests

# ── Server configuration ──────────────────────────────────────────────────────
# Change this to your Railway URL when deployed
# e.g. "https://bayesian-truth-lens.up.railway.app"
SERVER_URL = "http://localhost:8000"

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


def assess_claim(claim_text: str, api_key: str = None, license_key: str = None) -> dict:
    """
    Send a claim to the backend server for assessment.
    api_key parameter kept for interface compatibility but not used.
    license_key is used for server authentication.
    """
    key = license_key or api_key or ""

    try:
        response = requests.post(
            f"{SERVER_URL}/assess",
            json={
                "license_key": key,
                "claim": claim_text
            },
            timeout=120
        )

        if response.status_code == 401:
            return {"error": "Invalid license key. Please check your key and try again."}
        elif response.status_code == 402:
            return {"error": "No queries remaining. Purchase more credits to continue."}
        elif response.status_code == 429:
            return {"error": "Rate limit reached. Please wait a moment and try again."}
        elif response.status_code != 200:
            detail = response.json().get("detail", "Unknown error")
            return {"error": f"Server error: {detail}"}

        result = response.json()

        # Add labels if not already present from server
        if "claim_type_label" not in result:
            result["claim_type_label"] = CLAIM_TYPE_LABELS.get(
                result.get("claim_type", ""), result.get("claim_type", "Unknown")
            )
        if "confidence_description" not in result:
            result["confidence_description"] = CONFIDENCE_DESCRIPTIONS.get(
                result.get("confidence_tier", ""), ""
            )

        return result

    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to server. Make sure the server is running."}
    except requests.exceptions.Timeout:
        return {"error": "Server took too long to respond. Please try again."}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
