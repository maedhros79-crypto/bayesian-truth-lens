from pydantic import BaseModel
from typing import Optional


class ScoreRequest(BaseModel):
    url: str


class BatchScoreRequest(BaseModel):
    urls: list[str]


class SignalScore(BaseModel):
    tier: str  # "Low" | "Medium" | "High"
    reason: str


class CreatorReputation(BaseModel):
    domain: str
    total_ratings: int = 0
    worth_time_pct: float = 0.0
    delivered_promise_pct: float = 0.0
    recommend_learning_pct: float = 0.0
    human_trust_tier: str = "Medium"  # "High" | "Medium" | "Low"


class ScoreResult(BaseModel):
    url: str
    title: Optional[str] = None
    content_type: Optional[str] = None  # "youtube" | "article"
    verdict: Optional[str] = None  # "Pass" | "Watch" | "Skip"
    verdict_reason: Optional[str] = None
    scores: Optional[dict[str, SignalScore]] = None
    content_preview: Optional[str] = None
    fetch_method: Optional[str] = None  # "youtube_transcript" | "article_text" | "failed"
    error: Optional[str] = None
    creator_reputation: Optional[CreatorReputation] = None
    reputation_note: Optional[str] = None


# --- Feed Ingestion ---

class FeedRequest(BaseModel):
    feed_urls: list[str] = []
    filter_skip: bool = True
    limit_per_feed: int = 15
    total_limit: int = 50
    intent: str = "mix"          # mix | learning | creating | background | news
    use_saved_feeds: bool = True


# --- Ratings ---

class RateRequest(BaseModel):
    url: str
    worth_time: Optional[bool] = None
    delivered_promise: Optional[bool] = None
    recommend_learning: Optional[bool] = None


# --- Skills ---

class SkillTagRequest(BaseModel):
    url: str
    skill_name: str
    practice_notes: Optional[str] = None
    difficulty: Optional[str] = None  # "beginner" | "intermediate" | "advanced"


class SkillCompleteRequest(BaseModel):
    skill_id: int
    type: str  # "practice" | "rewatch"
    retained: Optional[bool] = None
    notes: Optional[str] = None


class SkillFindRelatedRequest(BaseModel):
    skill_name: str
    source_url: Optional[str] = None


# --- Trend Scorer ---

class TrendRequest(BaseModel):
    topic: str
    context: Optional[str] = None
