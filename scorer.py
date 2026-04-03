import json
import anthropic
from models import ScoreResult, SignalScore
from fetcher import FetchResult


SYSTEM_PROMPT = """You are a content quality scorer for a reality calibration platform. Your job is to assess whether a piece of content is worth a person's time and attention.

You score against four signals:
1. Signal-to-Noise Ratio — genuine substance vs emotional hook with thin content
2. Evergreen Value — durable ideas vs recency-bait
3. Respect for Audience Intelligence — handles complexity vs pre-chews everything
4. Padding vs Craft — cynical time-wasting vs intentional pacing

For each signal, return: Low / Medium / High and 2-3 sentences of plain reasoning.

Then produce an overall verdict: Pass / Watch / Skip, and one sentence explaining why.

IMPORTANT PRINCIPLES:
- You are not a taste-maker. You are scoring epistemic quality and respect for the viewer's time.
- Recency is neutral. Old content that holds up scores the same as new content that holds up.
- Do not penalize creators for thumbnail choices or algorithmic packaging they may have been forced to adopt.
- AI-generated slop has a specific texture: high production confidence, no genuine uncertainty, optimized for completion not understanding. Flag it when you see it.
- A video that is slow but intentional is better than one that is fast but hollow.
- You are not the last word. Always show your reasoning so the user can disagree with you.

ADDITIONAL QUALITY SIGNALS:
- Genuine craft, beauty, and emotional resonance are legitimate quality signals. A video that inspires someone to create, think, or engage more deeply with life scores well on Audience Respect even if it is not purely informational.
- Content that leaves the viewer more curious, more capable, or more inspired is genuinely high quality regardless of genre.
- Distinguish manufactured positivity (hollow inspiration content, motivational filler) from genuine uplift arising from craft, honesty, or beauty. The first is slop. The second is signal.
- Thoughtful entertainment that respects viewer intelligence scores the same as serious educational content with equivalent craft and substance.

Return ONLY valid JSON matching the specified structure. No preamble. No markdown fences."""


def build_user_prompt(fetch_result: FetchResult) -> str:
    content_label = "YouTube transcript" if fetch_result.content_type == "youtube" else "Article text"
    return f"""Score the following {content_label}.

Title: {fetch_result.title or "Unknown"}

Content:
{fetch_result.text}

Return JSON with this exact structure:
{{
  "verdict": "Pass | Watch | Skip",
  "verdict_reason": "One sentence plain English.",
  "scores": {{
    "signal_to_noise": {{
      "tier": "Low | Medium | High",
      "reason": "2-3 sentences explaining why."
    }},
    "evergreen_value": {{
      "tier": "Low | Medium | High",
      "reason": "2-3 sentences explaining why."
    }},
    "audience_respect": {{
      "tier": "Low | Medium | High",
      "reason": "2-3 sentences explaining why."
    }},
    "padding_vs_craft": {{
      "tier": "Low | Medium | High",
      "reason": "2-3 sentences explaining why."
    }}
  }}
}}"""


async def score_content(url: str, fetch_result: FetchResult, api_key: str) -> ScoreResult:
    """Score fetched content using Claude API."""

    # If fetch failed, return early
    if fetch_result.fetch_method == "failed":
        return ScoreResult(
            url=url,
            title=fetch_result.title,
            content_type=fetch_result.content_type,
            fetch_method="failed",
            error=fetch_result.error or "Content fetch failed",
            content_preview=None
        )

    client = anthropic.AsyncAnthropic(api_key=api_key)

    user_prompt = build_user_prompt(fetch_result)

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        raw_text = message.content[0].text.strip()

        # Parse JSON response
        parsed = json.loads(raw_text)

        scores = {}
        for key in ["signal_to_noise", "evergreen_value", "audience_respect", "padding_vs_craft"]:
            s = parsed.get("scores", {}).get(key, {})
            scores[key] = SignalScore(
                tier=s.get("tier", "Medium"),
                reason=s.get("reason", "No reasoning provided.")
            )

        return ScoreResult(
            url=url,
            title=fetch_result.title,
            content_type=fetch_result.content_type,
            verdict=parsed.get("verdict", "Watch"),
            verdict_reason=parsed.get("verdict_reason", "No reason provided."),
            scores=scores,
            content_preview=fetch_result.text[:300] if fetch_result.text else None,
            fetch_method=fetch_result.fetch_method
        )

    except json.JSONDecodeError as e:
        return ScoreResult(
            url=url,
            title=fetch_result.title,
            content_type=fetch_result.content_type,
            fetch_method=fetch_result.fetch_method,
            error=f"Failed to parse Claude response as JSON: {str(e)}",
            content_preview=fetch_result.text[:300] if fetch_result.text else None
        )
    except Exception as e:
        return ScoreResult(
            url=url,
            title=fetch_result.title,
            content_type=fetch_result.content_type,
            fetch_method=fetch_result.fetch_method,
            error=f"Scoring failed: {str(e)}",
            content_preview=fetch_result.text[:300] if fetch_result.text else None
        )
