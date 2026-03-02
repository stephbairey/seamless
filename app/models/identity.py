"""Pydantic models for identity routing."""

from pydantic import BaseModel


class IdentityContext(BaseModel):
    context_id: str
    label: str
    tags: list[str]
    name: str | None = None
    title: str | None = None
    email: str | None = None
    voice_id: str | None = None
    notes: str | None = None


class IdentityResult(BaseModel):
    context: IdentityContext
    match_score: float
    matched_tags: list[str]


class ClientOverride(BaseModel):
    client: str
    known_as: str | None = None
    reason: str | None = None


class Violation(BaseModel):
    rule_id: str
    label: str
    severity: str  # high, medium, low
    description: str
    matched_text: str | None = None
    position: int | None = None  # character offset
    line: int | None = None
    suggestion: str | None = None
    confidence: str = "high"  # high, medium, low
