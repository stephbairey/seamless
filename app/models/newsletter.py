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
    # Rewrite fields
    rewrite_type: str = ""  # action_item, meeting_notes_inline, meeting_notes_attachment, article_share, personal_share, joana_rollup
    rewritten_body: str = ""  # LLM output (HTML fragment: text + <br/> + <strong> + <a>, no <p> tags)
    rewrite_status: str = "pending"  # pending, done, skipped, edited
    source_url: str = ""  # URL for external content (article link, hosted PDF, event page)
    extra_context: str = ""  # free text Maya can paste (flyer text, PDF content, details)
    is_stale: bool = False  # event_date before newsletter send date
    stale_reason: str = ""  # human-readable explanation


class NewsletterIssue(BaseModel):
    week_key: str  # e.g. "2026-W10"
    items: list[NewsletterItem] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None
    compiled_html: str = ""
    status: str = "draft"  # draft, review, exported
    newsletter_date: str = ""  # display string for header, e.g. "MARCH 5, 2026"
    next_meeting_day: str = ""  # e.g. "Saturday, March 8, 2026, 10:00 AM"
    next_meeting_location: str = ""  # e.g. "First Unitarian Church, 1011 SW 12th Ave"


class NewsletterCompilation(BaseModel):
    issue: NewsletterIssue
    html: str = ""
    toc_headlines: list[str] = []
    item_count: int = 0
    violations: list[dict] = []
