import json
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from urllib.parse import urlparse

import feedparser

from database import get_db
from fetcher import fetch_content, FetchResult
from scorer import score_content
from models import ScoreResult, CreatorReputation
from ratings import get_creator_reputation_for_domain


# Categories associated with each intent mode
INTENT_PRIORITY_CATEGORIES = {
    "learning":    {"Science", "Philosophy", "Technology"},
    "creating":    {"Art & Design", "Music", "Craft"},
    "background":  {"Entertainment", "General"},
}


def get_saved_feed_categories() -> dict[str, str]:
    """Return {feed_url: category} for all active saved feeds."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT url, category FROM saved_feeds WHERE active=1"
        ).fetchall()
        return {row["url"]: (row["category"] or "General") for row in rows}
    finally:
        conn.close()


def get_saved_feed_urls() -> list[str]:
    """Return URLs of all active saved feeds."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT url FROM saved_feeds WHERE active=1"
        ).fetchall()
        return [row["url"] for row in rows]
    finally:
        conn.close()


async def parse_feeds(feed_urls: list[str], limit_per_feed: int = 15) -> list[dict]:
    """Parse RSS/Atom feeds — up to limit_per_feed items per feed."""
    all_items: list[dict] = []

    async def parse_one(feed_url: str) -> list[dict]:
        try:
            feed = await asyncio.to_thread(feedparser.parse, feed_url)
            items: list[dict] = []
            for entry in feed.entries:
                if len(items) >= limit_per_feed:
                    break
                url = entry.get("link", "")
                if not url:
                    continue
                items.append({
                    "url": url,
                    "title": entry.get("title", ""),
                    "summary": (entry.get("summary", "") or entry.get("description", "")),
                    "source_feed": feed_url,
                    "published": entry.get("published", ""),
                    "published_parsed": entry.get("published_parsed"),
                })
            return items
        except Exception:
            return []

    results = await asyncio.gather(*[parse_one(u) for u in feed_urls])
    for chunk in results:
        all_items.extend(chunk)
    return all_items


def interleave_by_source(items: list[dict]) -> list[dict]:
    """Round-robin interleave items so every source feed gets equal representation."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        buckets[item.get("source_feed", "")].append(item)

    interleaved: list[dict] = []
    keys = list(buckets.keys())
    while any(buckets[k] for k in keys):
        for k in keys:
            if buckets[k]:
                interleaved.append(buckets[k].pop(0))
    return interleaved


def apply_intent_filter(
    items: list[dict],
    intent: str,
    feed_categories: dict[str, str],
) -> list[dict]:
    """Reorder or filter items based on session intent."""
    if not intent or intent == "mix":
        return items

    if intent == "news":
        cutoff = datetime.now() - timedelta(days=7)
        filtered = []
        for item in items:
            pp = item.get("published_parsed")
            if pp:
                try:
                    pub_dt = datetime(*pp[:6])
                    if pub_dt >= cutoff:
                        filtered.append(item)
                except Exception:
                    filtered.append(item)
            else:
                filtered.append(item)
        return filtered

    priority_cats = INTENT_PRIORITY_CATEGORIES.get(intent, set())
    if not priority_cats:
        return items

    priority, other = [], []
    for item in items:
        cat = feed_categories.get(item.get("source_feed", ""), "General")
        (priority if cat in priority_cats else other).append(item)
    return priority + other


def get_cached_score(url: str) -> ScoreResult | None:
    """Return cached score if it exists and is less than 6 hours old."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM score_cache WHERE url = ?", (url,)
        ).fetchone()
        if not row:
            return None

        scored_at = datetime.fromisoformat(row["scored_at"])
        if datetime.now() - scored_at > timedelta(hours=6):
            conn.execute("DELETE FROM score_cache WHERE url = ?", (url,))
            conn.commit()
            return None

        scores = json.loads(row["scores_json"]) if row["scores_json"] else None
        from models import SignalScore
        parsed_scores = None
        if scores:
            parsed_scores = {k: SignalScore(**v) for k, v in scores.items()}

        return ScoreResult(
            url=row["url"],
            title=row["title"],
            content_type=row["content_type"],
            verdict=row["verdict"],
            verdict_reason=row["verdict_reason"],
            scores=parsed_scores,
            fetch_method=row["fetch_method"],
        )
    finally:
        conn.close()


def cache_score(result: ScoreResult):
    """Persist a score result to the cache."""
    conn = get_db()
    try:
        scores_json = None
        if result.scores:
            scores_json = json.dumps({
                k: {"tier": v.tier, "reason": v.reason}
                for k, v in result.scores.items()
            })
        conn.execute(
            """INSERT OR REPLACE INTO score_cache
               (url, title, content_type, verdict, verdict_reason, scores_json, fetch_method, scored_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (result.url, result.title, result.content_type,
             result.verdict, result.verdict_reason, scores_json,
             result.fetch_method, datetime.now().isoformat())
        )
        conn.commit()
    finally:
        conn.close()


def attach_reputation(result: ScoreResult) -> ScoreResult:
    """Attach creator reputation data to a score result."""
    try:
        domain = urlparse(result.url).hostname or ""
        rep = get_creator_reputation_for_domain(domain)
        if rep and rep.total_ratings >= 3:
            result.creator_reputation = rep
            if result.verdict and rep.total_ratings >= 5:
                ai_positive = result.verdict in ("Pass", "Watch")
                human_positive = rep.worth_time_pct > 0.6
                if ai_positive and not human_positive:
                    result.reputation_note = "Human raters score this creator lower than AI assessment"
                elif not ai_positive and human_positive:
                    result.reputation_note = "Human raters score this creator higher than AI assessment"
    except Exception:
        pass
    return result


async def score_feed_items(
    feed_urls: list[str],
    api_key: str,
    filter_skip: bool = True,
    limit_per_feed: int = 15,
    total_limit: int = 50,
    intent: str = "mix",
    use_saved_feeds: bool = True,
) -> list[ScoreResult]:
    """Parse feeds, score items, return ranked results."""

    # Merge in saved feeds if requested
    all_urls = list(feed_urls)
    if use_saved_feeds:
        saved = get_saved_feed_urls()
        for u in saved:
            if u not in all_urls:
                all_urls.append(u)

    if not all_urls:
        return []

    # Load URL→category map for intent filtering
    feed_categories = get_saved_feed_categories()

    # Parse: N items per feed, then interleave by source
    items = await parse_feeds(all_urls, limit_per_feed)
    items = interleave_by_source(items)

    # Apply intent filtering / prioritisation
    items = apply_intent_filter(items, intent, feed_categories)

    # Hard cap at total_limit
    items = items[:total_limit]

    async def score_one(item: dict) -> ScoreResult:
        url = item["url"]
        cached = get_cached_score(url)
        if cached:
            return attach_reputation(cached)

        summary = item.get("summary", "")
        if summary and len(summary) > 100:
            fetch_result = FetchResult(
                text=summary,
                title=item.get("title", ""),
                content_type="article",
                fetch_method="feed_summary",
            )
        else:
            fetch_result = fetch_content(url)

        result = await score_content(url, fetch_result, api_key)
        if result.verdict:
            cache_score(result)
        return attach_reputation(result)

    results = list(await asyncio.gather(*[score_one(item) for item in items]))

    # Sort: Pass first, Watch second, Skip last
    verdict_order = {"Pass": 0, "Watch": 1, "Skip": 2}
    results.sort(key=lambda r: verdict_order.get(r.verdict, 3))

    if filter_skip:
        results = [r for r in results if r.verdict != "Skip"]

    return results
