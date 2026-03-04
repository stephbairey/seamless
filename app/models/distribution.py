"""Pydantic models for social copy distribution."""

from pydantic import BaseModel, ConfigDict


class SocialPost(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    platform: str  # facebook / instagram / linkedin / bluesky
    account: str  # e.g. "Maya Bairey, Author" / "linguainkbooks"
    voice_id: str  # maya-personal / lib / lim / job-search
    identity_name: str  # Maya Bairey / Steph Bairey
    body: str = ""  # Generated post text
    hashtags: list[str] = []  # Instagram only
    violations: list[dict] = []


class CopyRequest(BaseModel):
    content: str  # Pasted blog post or content
    brand: str  # maya-personal / lib / lim
    url: str = ""  # Optional link to include
    notes: str = ""  # Optional direction for generation


class CopyBatch(BaseModel):
    id: str
    created_at: str
    brand: str
    content_preview: str  # First 200 chars of input
    url: str = ""
    posts: list[SocialPost] = []
