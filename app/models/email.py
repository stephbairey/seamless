"""Pydantic models for email triage."""

from datetime import datetime

from pydantic import BaseModel


class EmailMessage(BaseModel):
    id: str
    thread_id: str
    subject: str = ""
    sender: str = ""
    sender_email: str = ""
    to: str = ""
    delivered_to: str = ""
    date: datetime | None = None
    snippet: str = ""
    body_text: str = ""
    body_html: str = ""
    labels: list[str] = []
    label_ids: list[str] = []
    is_unread: bool = False
    is_multipart_related: bool = False
    in_reply_to: str = ""
    message_id: str = ""


class EmailClassification(BaseModel):
    message_id: str
    suggested_label: str | None = None
    suggested_label_id: str | None = None
    matched_client: str | None = None
    match_method: str | None = None  # exact_email, domain, name_fragment, prg_member
    priority: str = "normal"  # normal, high, urgent
    priority_reason: str | None = None
    is_prg_newsletter: bool = False
    needs_manual_review: bool = False
    review_reason: str | None = None
    confidence: str = "high"  # high, medium, low


class ReplyDraft(BaseModel):
    message_id: str
    thread_id: str
    send_as: str  # email address to send from
    send_as_name: str  # display name
    voice_id: str
    to: str
    subject: str
    in_reply_to: str = ""
    body: str = ""
    violations: list[dict] = []


class DigestGroup(BaseModel):
    label: str
    messages: list[EmailMessage] = []
    count: int = 0


class DailyDigest(BaseModel):
    generated_at: datetime
    total_messages: int = 0
    priority_items: list[EmailClassification] = []
    newsletter_candidates: list[EmailMessage] = []
    needs_review: list[EmailMessage] = []
    by_label: list[DigestGroup] = []
