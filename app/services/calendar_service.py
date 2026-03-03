"""Calendar service — unified views, conflict detection, cadence tracking, meeting prep."""

import logging
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.calendar import (
    CadenceItem,
    CalendarEvent,
    ConflictInfo,
    DayBriefing,
    MeetingPrep,
)
from app.services.gcal_client import gcal_client
from app.services.yaml_store import yaml_store

logger = logging.getLogger(__name__)

TZ = ZoneInfo("America/Los_Angeles")

# Prefixes/patterns to skip
SKIP_PREFIXES = ("✅",)
SKIP_PATTERNS = (re.compile(r"^Delivery:", re.IGNORECASE),)

# Writing Cohort canonical calendar
WRITING_COHORT_CANONICAL = "mjbairey@gmail.com"
WRITING_COHORT_PATTERN = re.compile(
    r"^(Writing Cohort|Entrepreneur Cohort)", re.IGNORECASE
)

# Event name parsing patterns
CLIENT_FORMAL_RE = re.compile(
    r"^(.+?)\s+and\s+Steph\s*@\s*Lingua\s*Ink", re.IGNORECASE
)
CLIENT_COLON_RE = re.compile(r"^([^:]+):(Maya|Steph)$", re.IGNORECASE)
MULTI_PERSON_RE = re.compile(r"^[^:]+:[^:]+:[^:]+")
HOD_RE = re.compile(r"^HoD\b", re.IGNORECASE)


class CalendarService:

    def _load_clients(self) -> list[dict]:
        data = yaml_store.read("client-registry.yaml")
        clients = data.get("clients", [])
        # Also include organizations and business lines for matching
        clients.extend(data.get("organizations", []))
        clients.extend(data.get("business_lines", []))
        clients.extend(data.get("personal", []))
        return clients

    def _load_calendar_map(self) -> dict:
        return yaml_store.read("calendar-map.yaml")

    def _load_identity_routing(self) -> dict:
        return yaml_store.read("identity-routing.yaml")

    # --- Event filtering ---

    def should_skip(self, event: CalendarEvent) -> bool:
        summary = event.summary.strip()
        if not summary:
            return False

        for prefix in SKIP_PREFIXES:
            if summary.startswith(prefix):
                return True

        for pattern in SKIP_PATTERNS:
            if pattern.match(summary):
                # Only skip Delivery: events on stephbairey (legacy)
                if "Delivery" in summary.lower() and event.calendar_id == "stephbairey@gmail.com":
                    return True

        return False

    def is_writing_cohort_duplicate(self, event: CalendarEvent) -> bool:
        if WRITING_COHORT_PATTERN.match(event.summary.strip()):
            return event.calendar_id != WRITING_COHORT_CANONICAL
        return False

    def filter_events(self, events: list[CalendarEvent]) -> list[CalendarEvent]:
        filtered = []
        for event in events:
            if self.should_skip(event):
                continue
            if self.is_writing_cohort_duplicate(event):
                continue
            filtered.append(event)
        return filtered

    # --- Event name parsing ---

    def parse_event_client(self, event: CalendarEvent) -> dict:
        """Extract client/context info from an event summary.

        Returns dict with keys: client_name, identity_hint, match_type
        """
        summary = event.summary.strip()
        if not summary:
            return {}

        # "ClientName and Steph @ Lingua Ink"
        m = CLIENT_FORMAL_RE.match(summary)
        if m:
            return {
                "client_name": m.group(1).strip(),
                "identity_hint": "Steph",
                "match_type": "formal_calendly",
            }

        # "Client:Maya" or "Client:Steph"
        m = CLIENT_COLON_RE.match(summary)
        if m:
            return {
                "client_name": m.group(1).strip(),
                "identity_hint": m.group(2).strip(),
                "match_type": "colon_format",
            }

        # Multi-person "Name:Name:Name"
        if MULTI_PERSON_RE.match(summary):
            return {
                "client_name": "",
                "identity_hint": "",
                "match_type": "multi_person",
            }

        # HoD = Lynn Haller
        if HOD_RE.match(summary):
            return {
                "client_name": "Lynn Haller",
                "identity_hint": "Maya",
                "match_type": "hod_project",
            }

        # Writing Cohort
        if WRITING_COHORT_PATTERN.match(summary):
            return {
                "client_name": "Free Cohort",
                "identity_hint": "Maya",
                "match_type": "writing_cohort",
            }

        # Try fuzzy match against client names
        clients = self._load_clients()
        summary_lower = summary.lower()
        for client in clients:
            name = client.get("name", "")
            if not name:
                continue
            name_lower = name.lower()
            first_name = name_lower.split()[0] if name_lower else ""

            if name_lower in summary_lower or (first_name and first_name in summary_lower):
                return {
                    "client_name": name,
                    "identity_hint": client.get("identity", ""),
                    "match_type": "name_match",
                }

        return {}

    def resolve_client_profile(self, client_name: str) -> dict:
        if not client_name:
            return {}
        clients = self._load_clients()
        name_lower = client_name.lower()
        for client in clients:
            if client.get("name", "").lower() == name_lower:
                return client
        # Partial match
        for client in clients:
            if name_lower in client.get("name", "").lower():
                return client
        return {}

    def resolve_identity_for_client(self, client_name: str) -> dict:
        routing = self._load_identity_routing()
        overrides = routing.get("client_overrides", [])
        for override in overrides:
            if override.get("client", "").lower() == client_name.lower():
                known_as = override.get("known_as", "")
                # Find the matching identity context
                for ctx in routing.get("contexts", []):
                    ctx_name = ctx.get("name", "")
                    if known_as and ctx_name and known_as in ctx_name:
                        return {
                            "name": ctx.get("name", ""),
                            "title": ctx.get("title", ""),
                            "email": ctx.get("email", ""),
                            "voice_id": ctx.get("voice_id", ""),
                            "known_as": known_as,
                        }
        return {}

    # --- Conflict detection ---

    def detect_conflicts(self, events: list[CalendarEvent]) -> list[ConflictInfo]:
        conflicts = []
        timed = [e for e in events if not e.all_day and e.start and e.end]

        for i in range(len(timed)):
            for j in range(i + 1, len(timed)):
                a, b = timed[i], timed[j]
                overlap = self._overlap_minutes(a, b)
                if overlap > 0:
                    conflicts.append(ConflictInfo(
                        event_a=a, event_b=b, overlap_minutes=overlap,
                    ))
        return conflicts

    def _overlap_minutes(self, a: CalendarEvent, b: CalendarEvent) -> int:
        if not (a.start and a.end and b.start and b.end):
            return 0
        overlap_start = max(a.start, b.start)
        overlap_end = min(a.end, b.end)
        if overlap_start < overlap_end:
            return int((overlap_end - overlap_start).total_seconds() / 60)
        return 0

    # --- Cadence tracking ---

    def get_cadences(self, target_date: date, events: list[CalendarEvent]) -> list[CadenceItem]:
        """Check recurring cadences against actual events in the window."""
        cadences = []
        today = target_date

        # Hard-coded cadence definitions from calendar-map.yaml
        cadence_defs = [
            {
                "label": "Sulima call",
                "weekday": 3,  # Thursday
                "pattern": re.compile(r"Sulima", re.IGNORECASE),
                "source": "Thu 9am, linguainkmedia",
            },
            {
                "label": "Devon meeting",
                "weekday": 3,  # Thursday
                "pattern": re.compile(r"Devon", re.IGNORECASE),
                "source": "Thu 10am, linguainkmedia",
            },
            {
                "label": "Writing Cohort",
                "weekday": [3, 6],  # Thu + Sun
                "pattern": re.compile(r"Writing Cohort", re.IGNORECASE),
                "source": "Thu+Sun noon, mjbairey",
            },
            {
                "label": "HoD meeting",
                "weekday": 1,  # Tuesday
                "pattern": re.compile(r"HoD", re.IGNORECASE),
                "source": "Tue 1pm, linguainkmedia",
            },
            {
                "label": "Story Lounge",
                "weekday": 4,  # Friday
                "pattern": re.compile(r"Story Lounge", re.IGNORECASE),
                "source": "Fri 9am, linguainkmedia",
            },
        ]

        event_summaries = [e.summary for e in events]

        for cdef in cadence_defs:
            weekdays = cdef["weekday"] if isinstance(cdef["weekday"], list) else [cdef["weekday"]]

            for wd in weekdays:
                # Find the next occurrence of this weekday from target_date
                days_ahead = wd - today.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                next_date = today + timedelta(days=days_ahead)

                # Check if there's a matching event
                has_match = any(cdef["pattern"].search(s) for s in event_summaries)

                if next_date == today:
                    status = "today"
                elif next_date < today:
                    status = "overdue" if not has_match else "upcoming"
                else:
                    status = "upcoming"

                cadences.append(CadenceItem(
                    label=cdef["label"],
                    next_due=next_date.strftime("%a %b %d"),
                    status=status,
                    source=cdef["source"],
                ))

        # Monthly/quarterly cadences
        cadences.extend(self._check_monthly_cadences(today))

        return cadences

    def _check_monthly_cadences(self, today: date) -> list[CadenceItem]:
        items = []

        # ARC board report — last week of month
        last_day = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        last_week_start = last_day - timedelta(days=6)
        if last_week_start <= today <= last_day:
            items.append(CadenceItem(
                label="ARC board report",
                next_due=f"Due by {last_day.strftime('%b %d')}",
                status="today" if today == last_day else "upcoming",
                source="Last week of month, stephbairey",
            ))
        elif today > last_day:
            # Already past, compute next month
            next_month = (last_day + timedelta(days=1))
            next_last = (next_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            items.append(CadenceItem(
                label="ARC board report",
                next_due=f"Due by {next_last.strftime('%b %d')}",
                status="upcoming",
                source="Last week of month, stephbairey",
            ))

        # Royalty reports — 1st of quarter
        quarter_months = [1, 4, 7, 10]
        for qm in quarter_months:
            qdate = date(today.year if qm >= today.month else today.year + 1, qm, 1)
            if qdate >= today:
                days_until = (qdate - today).days
                if days_until == 0:
                    status = "today"
                elif days_until <= 7:
                    status = "upcoming"
                else:
                    status = "upcoming"

                items.append(CadenceItem(
                    label="Royalty reports",
                    next_due=qdate.strftime("%b %d"),
                    status=status,
                    source="1st of quarter, linguainkmedia",
                ))
                break

        return items

    # --- Meeting prep ---

    def build_meeting_prep(self, event: CalendarEvent) -> MeetingPrep | None:
        parsed = self.parse_event_client(event)
        if not parsed or not parsed.get("client_name"):
            return None

        client_name = parsed["client_name"]
        profile = self.resolve_client_profile(client_name)
        identity = self.resolve_identity_for_client(client_name)

        context = ""
        if client_name.lower() == "sulima malzin" or "sulima" in client_name.lower():
            context = (
                "Most important client. Weekly Thursday 9am call. "
                "Author + mentor, 86 years old. "
                "4 books: Arms Filled with Bittersweet, All in the Soup Together, "
                "Words That Dance, Tributaries."
            )
        elif "free cohort" in client_name.lower() or "writing cohort" in client_name.lower():
            context = (
                "Free writing cohort since Sept 2024. "
                "Critique rotation (alphabetical): Deb, Iris, Julie, Kay, Maura, Maya."
            )
        elif client_name.lower() == "lynn haller" or "hod" in event.summary.lower():
            context = (
                "The Hallway of Doorknobs. Children's picture book (IFS therapy). "
                "Target launch: May 12, 2026. Lynn left writing cohort."
            )
        elif "devon" in client_name.lower():
            context = (
                "Life coach. Web dev client. $195/hr, $1,950 project ceiling. "
                "WordPress/Enfold/Avia, no staging."
            )

        return MeetingPrep(
            event=event,
            client_name=client_name,
            client_profile=profile,
            identity_info=identity,
            recent_context=context,
        )

    # --- Peterday check ---

    def check_peterday(self, events: list[CalendarEvent]) -> list[CalendarEvent]:
        """Return events on Saturday (Peterday) that look like work events."""
        warnings = []
        # Personal/household events on Saturday are fine; work events are not
        work_keywords = re.compile(
            r"(meeting|call|cohort|client|steph.*@.*lingua|devon|sulima|hod|prg|arc|tda)",
            re.IGNORECASE,
        )
        for event in events:
            if event.start and event.start.weekday() == 5:  # Saturday
                if work_keywords.search(event.summary):
                    warnings.append(event)
        return warnings

    # --- Day briefing ---

    async def get_day_briefing(self, target_date: date) -> DayBriefing:
        start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=TZ)
        end = start + timedelta(days=1)

        all_events = await gcal_client.list_all_events(start, end)
        filtered = self.filter_events(all_events)

        conflicts = self.detect_conflicts(filtered)

        # Look at a wider window for cadence context (this week)
        week_start = start - timedelta(days=start.weekday())
        week_end = week_start + timedelta(days=7)
        week_events = await gcal_client.list_all_events(week_start, week_end)
        week_filtered = self.filter_events(week_events)

        cadences = self.get_cadences(target_date, week_filtered)

        prep_items = []
        for event in filtered:
            prep = self.build_meeting_prep(event)
            if prep:
                prep_items.append(prep)

        peterday_warnings = self.check_peterday(filtered)

        return DayBriefing(
            date=target_date,
            events=filtered,
            conflicts=conflicts,
            cadence_items=cadences,
            meeting_prep_items=prep_items,
            peterday_warnings=peterday_warnings,
        )

    async def get_week_events(self, week_start: date) -> dict:
        """Get events for a full week, organized by day."""
        start = datetime(week_start.year, week_start.month, week_start.day, tzinfo=TZ)
        end = start + timedelta(days=7)

        all_events = await gcal_client.list_all_events(start, end)
        filtered = self.filter_events(all_events)

        by_day: dict[str, list[CalendarEvent]] = {}
        for i in range(7):
            day = week_start + timedelta(days=i)
            by_day[day.isoformat()] = []

        for event in filtered:
            if event.start:
                day_key = event.start.date().isoformat() if hasattr(event.start, 'date') else str(event.start)[:10]
                if day_key in by_day:
                    by_day[day_key].append(event)

        conflicts = self.detect_conflicts(filtered)
        cadences = self.get_cadences(week_start, filtered)
        peterday_warnings = self.check_peterday(filtered)

        return {
            "week_start": week_start,
            "by_day": by_day,
            "all_events": filtered,
            "conflicts": conflicts,
            "cadences": cadences,
            "peterday_warnings": peterday_warnings,
        }


# Shared instance
calendar_service = CalendarService()
