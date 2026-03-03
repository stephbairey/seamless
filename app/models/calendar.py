"""Pydantic models for calendar sync."""

from datetime import date, datetime

from pydantic import BaseModel


class CalendarEvent(BaseModel):
    id: str
    calendar_id: str
    calendar_label: str = ""
    summary: str = ""
    description: str = ""
    location: str = ""
    start: datetime | None = None
    end: datetime | None = None
    all_day: bool = False
    recurring: bool = False
    attendees: list[str] = []
    creator: str = ""
    identity: str = ""
    color_id: str = ""
    html_link: str = ""


class ConflictInfo(BaseModel):
    event_a: CalendarEvent
    event_b: CalendarEvent
    overlap_minutes: int = 0


class MeetingPrep(BaseModel):
    event: CalendarEvent
    client_name: str = ""
    client_profile: dict = {}
    identity_info: dict = {}
    recent_context: str = ""


class CadenceItem(BaseModel):
    label: str
    next_due: str = ""
    status: str = "upcoming"  # upcoming, today, overdue
    source: str = ""


class DayBriefing(BaseModel):
    date: date
    events: list[CalendarEvent] = []
    conflicts: list[ConflictInfo] = []
    cadence_items: list[CadenceItem] = []
    meeting_prep_items: list[MeetingPrep] = []
    peterday_warnings: list[CalendarEvent] = []
