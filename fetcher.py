import re
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass
from typing import Optional


@dataclass
class FetchResult:
    text: str
    title: Optional[str]
    content_type: str  # "youtube" | "article"
    fetch_method: str  # "youtube_transcript" | "article_text" | "failed"
    error: Optional[str] = None


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    parsed = urlparse(url)
    if "youtube.com" in parsed.hostname or "www.youtube.com" in parsed.hostname:
        qs = parse_qs(parsed.query)
        return qs.get("v", [None])[0]
    if "youtu.be" in parsed.hostname:
        return parsed.path.lstrip("/")
    return None


def is_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        return "youtube.com" in host or "youtu.be" in host
    except Exception:
        return False


def fetch_youtube(url: str) -> FetchResult:
    """Fetch YouTube transcript and title."""
    video_id = extract_video_id(url)
    if not video_id:
        return FetchResult(
            text="", title=None, content_type="youtube",
            fetch_method="failed", error="Could not extract video ID from URL"
        )

    title = None
    # Try to get video title via youtube-transcript-api metadata
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # Get title from the transcript info if available
        for t in transcript_list:
            title = t.video_id  # fallback — just the ID
            break
    except Exception:
        pass

    # Try fetching title from page via httpx
    try:
        import httpx
        resp = httpx.get(
            f"https://www.youtube.com/watch?v={video_id}",
            follow_redirects=True,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        match = re.search(r"<title>(.*?)</title>", resp.text)
        if match:
            raw_title = match.group(1).replace(" - YouTube", "").strip()
            if raw_title:
                title = raw_title
    except Exception:
        pass

    # Fetch transcript
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_entries = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join(entry["text"] for entry in transcript_entries)

        # Truncate to ~6000 words
        words = full_text.split()
        if len(words) > 6000:
            full_text = " ".join(words[:6000])

        return FetchResult(
            text=full_text,
            title=title or f"YouTube video {video_id}",
            content_type="youtube",
            fetch_method="youtube_transcript"
        )
    except Exception as e:
        return FetchResult(
            text="", title=title, content_type="youtube",
            fetch_method="failed",
            error=f"Transcript unavailable: {str(e)}"
        )


def fetch_article(url: str) -> FetchResult:
    """Fetch article text using trafilatura, fallback to newspaper3k."""
    title = None
    text = None

    # Primary: trafilatura
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False)
            # Try to get title
            metadata = trafilatura.extract(
                downloaded, include_comments=False, output_format="json"
            )
            if metadata:
                import json
                try:
                    meta = json.loads(metadata)
                    title = meta.get("title")
                except Exception:
                    pass
    except Exception:
        pass

    # Fallback: newspaper3k
    if not text:
        try:
            from newspaper import Article
            article = Article(url)
            article.download()
            article.parse()
            text = article.text
            title = article.title or title
        except Exception:
            pass

    if not text:
        return FetchResult(
            text="", title=None, content_type="article",
            fetch_method="failed",
            error="Both trafilatura and newspaper3k failed to extract content"
        )

    # Truncate to ~4000 words
    words = text.split()
    if len(words) > 4000:
        text = " ".join(words[:4000])

    return FetchResult(
        text=text,
        title=title or "Untitled article",
        content_type="article",
        fetch_method="article_text"
    )


def fetch_content(url: str) -> FetchResult:
    """Route to YouTube or article fetcher based on URL."""
    if is_youtube_url(url):
        return fetch_youtube(url)
    return fetch_article(url)
