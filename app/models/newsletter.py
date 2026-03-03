"""Pydantic models for PRG newsletter automation."""

from datetime import datetime

from pydantic import BaseModel


class NewsletterItem(BaseModel):
    id: str  # uuid4 hex
    source: str = "gmail"  # gmail, manual
    gmail_msg_id: str | None = None
    sender_name: str = ""
    sender_email: str = ""
    subject: str = ""
    body_text: str = ""
    body_html: str = ""
    is_multipart_related: bool = False
    category: str = "uncategorized"  # action_item, team_note, article, joana_rollup, uncategorized
    headline: str = ""
    display_order: int = 0
    event_date: str = ""  # ISO date (YYYY-MM-DD) of event in content, if any
    status: str = "collected"  # collected, included, excluded
    collected_at: datetime | None = None
    email_date: datetime | None = None


class NewsletterIssue(BaseModel):
    week_key: str  # e.g. "2026-W10"
    items: list[NewsletterItem] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None
    compiled_html: str = ""
    status: str = "draft"  # draft, review, exported


class NewsletterCompilation(BaseModel):
    issue: NewsletterIssue
    html: str = ""
    toc_headlines: list[str] = []
    item_count: int = 0
    violations: list[dict] = []
