import json
import anthropic


TREND_SYSTEM_PROMPT = """You are a calibrated trend assessor for a reality calibration platform
built on the Examined Uncertainty principle. Your job is to assess whether a concern
people are worried about is well-founded, mixed, overblown, or primarily algorithmically
amplified noise.

CRITICAL REQUIREMENT — GENUINE BALANCE:
Before rendering any assessment, you must explicitly steelman BOTH directions:
1. The strongest case that this concern is serious and urgent
2. The strongest case that this concern is overblown, manageable, or even beneficial

These steelmans must be genuine — not token acknowledgments. A real steelman means
presenting the opposing case as its most intelligent defenders would present it.

PRINCIPLES:
- Separate genuine signal from media and algorithmic amplification
- Acknowledge genuine concerns without catastrophizing
- Acknowledge manageable or beneficial aspects without dismissing real risks
- Some trends are real but there is nothing useful to do about them — say so honestly
- Some trends are algorithmic artifacts — say so honestly
- Confidence tiers: Low / Medium / High — never false precision
- Political and social topics require extra care — explicitly name when reasonable
  people hold fundamentally different values-based positions, not just factual ones
- Smaller population may reduce environmental pressure AND may reduce civilizational
  resilience — both are true and neither cancels the other
- Consciousness and complex civilization have genuine value — this perspective
  deserves representation alongside environmental sustainability perspectives
- You are not the last word — show reasoning so the user can disagree
- Never drift toward the framing that feels safest — commit to your best assessment
  then surface the strongest counterargument to your own conclusion

Return ONLY valid JSON. No preamble. No markdown fences."""


async def assess_trend(topic: str, context: str | None, api_key: str) -> dict:
    """Assess a trend/concern using Claude."""
    client = anthropic.AsyncAnthropic(api_key=api_key)

    user_prompt = f"""Assess the following trend or concern:

Topic: {topic}
{f"Additional context: {context}" if context else ""}

Return JSON with this exact structure:
{{
  "topic": "{topic}",
  "concern_tier": "Well-founded | Mixed evidence | Overblown | Algorithmically amplified",
  "confidence": "Low | Medium | High",
  "summary": "2-3 sentence plain English assessment",
  "what_evidence_supports": "What evidence supports this concern",
  "what_evidence_doesnt_support": "What evidence doesn't support or contradicts this concern",
  "genuine_vs_amplified": "What part of this is real signal vs media/algorithm distortion",
  "useful_action": "What, if anything, a reasonable person should actually do about this",
  "socratic_question": "One question worth sitting with"
}}"""

    try:
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=TREND_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )

        raw_text = message.content[0].text.strip()
        return json.loads(raw_text)

    except json.JSONDecodeError:
        return {
            "topic": topic,
            "error": "Failed to parse trend assessment as JSON",
        }
    except Exception as e:
        return {
            "topic": topic,
            "error": f"Trend assessment failed: {str(e)}",
        }
