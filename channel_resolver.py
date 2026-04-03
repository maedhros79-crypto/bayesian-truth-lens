import re
import httpx
from urllib.parse import urlparse


async def resolve_channel(query: str) -> dict:
    query = query.strip()

    # Method 1: direct channel URL with UC channel ID
    if "youtube.com/channel/UC" in query:
        match = re.search(r"channel/(UC[a-zA-Z0-9_-]+)", query)
        if match:
            channel_id = match.group(1)
            return {
                "channel_name": channel_id,
                "channel_id": channel_id,
                "rss_url": f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
                "found": True
            }

    # Method 2: @handle in query or URL
    handle_match = re.search(r"@([a-zA-Z0-9_.-]+)", query)
    if handle_match:
        result = await resolve_via_handle(handle_match.group(1))
        if result:
            return result

    # Method 3: search by name
    result = await resolve_via_scrape(query)
    if result:
        return result

    return {"found": False, "error": f"Could not find channel for '{query}'"}


async def resolve_via_handle(handle: str) -> dict | None:
    url = f"https://www.youtube.com/@{handle}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
                follow_redirects=True
            )
        match = re.search(r'"channelId":"(UC[a-zA-Z0-9_-]+)"', resp.text)
        if match:
            channel_id = match.group(1)
            return {
                "channel_name": handle,
                "channel_id": channel_id,
                "rss_url": f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
                "found": True
            }
    except Exception:
        pass
    return None


async def resolve_via_scrape(query: str) -> dict | None:
    search_url = f"https://www.youtube.com/results?search_query={query}&sp=EgIQAg%3D%3D"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                search_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept-Language": "en-US,en;q=0.9"
                },
                timeout=10,
                follow_redirects=True
            )
        matches = re.findall(r'"channelId":"(UC[a-zA-Z0-9_-]+)"', resp.text)
        names = re.findall(r'"text":"([^"]{3,50})"', resp.text)
        if matches:
            return {
                "channel_name": names[0] if names else query,
                "channel_id": matches[0],
                "rss_url": f"https://www.youtube.com/feeds/videos.xml?channel_id={matches[0]}",
                "found": True
            }
    except Exception:
        pass
    return None
