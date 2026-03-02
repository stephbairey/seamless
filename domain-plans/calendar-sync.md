# Domain Plan: Calendar Sync

## Purpose
Provide unified calendar awareness across Maya's 3 Google Calendars and integrate calendar data with other systems (ClickUp task due dates, local dashboard display, meeting prep). Replace the abandoned ClickUp-Calendar native sync with something that actually works.

## Inputs
- knowledge/conventions.md — Calendar naming rules, identity routing for invites, HoD abbreviation
- knowledge/tools.md — Calendar architecture, Granola transcription, dashboard display
- knowledge/rhythms.md — Weekly/monthly cadences, recurring event schedule
- data/calendar-map.yaml — 3 calendars with identity/purpose mapping, recurring events, integration status

## System Overview
**Three calendars, unified view:**
- **linguainkmedia@gmail.com** — Business and operations. Client meetings, organizational commitments. Invites sent when contact knows Steph/Lingua Ink.
- **mjbairey@gmail.com** — Creative and writing. Writing Cohort (Sundays noon-2pm, canonical home), critique groups, publishing tasks. Invites sent when contact knows Maya.
- **stephbairey@gmail.com** — Home and personal. Household events, Pete's Alexa entries. Feeds the local dashboard. History back to 2000.

All viewed in a unified view from linguainkmedia@gmail.com. All in America/Los_Angeles timezone.

**Naming conventions:** Client meetings use `ClientName and Steph @ Lingua Ink` (formal) or `Client:Maya` (informal). Multi-person meetings use `Name:Name:Name` format.

**Current integrations:**
- ClickUp-Calendar native sync: **abandoned** (didn't work well). ✅-prefixed events on linguainkmedia calendar are legacy artifacts.
- stephbairey calendar → local dashboard: **active**. Python fetcher pulls calendar data for the household display.
- Pete adds events via Alexa → stephbairey calendar.

**Known issues:**
- Writing Cohort appears on all 3 calendars (should only be on mjbairey). Duplication is accidental, caused by email confusion over time.
- Legacy "Delivery:" events on stephbairey calendar are no longer active — Maya uses a different delivery tracking method now.

**Identity routing for invites:** Follows the two-axis model. If the contact knows Maya → mjbairey. If Steph or Lingua Ink → linguainkmedia. Relationship history can override strict role logic.

## Automation Requirements

### Unified Calendar Read
- Aggregate events from all 3 calendars into a single view
- Provide daily briefing: today's schedule, prep notes for meetings, travel time between events
- Surface conflicts (double-bookings across calendars)
- Distinguish meeting types: client call, organizational meeting, writing group, personal

### Meeting Prep
- Before a client meeting, surface:
  - Client profile from client-registry.yaml
  - Recent ClickUp tasks for that client's Project
  - Last meeting notes (from ClickUp task descriptions or Granola transcripts)
  - Correct identity for this client (which name, which email)
- For Writing Cohort: surface critique rotation schedule (alphabetical by first name: Deb, Iris, Julie, Kay, Maura, Maya)

### Calendar Event Creation
- Create events on the correct calendar based on identity context:
  - Client/business → linguainkmedia@gmail.com
  - Writing/creative → mjbairey@gmail.com
  - Personal/household → stephbairey@gmail.com
- Apply naming conventions automatically:
  - Formal client meetings: `ClientName and Steph @ Lingua Ink`
  - Informal touchpoints: `Client:Maya` or `Client:Steph`
  - Multi-person: `Name:Name:Name`
- Set timezone to America/Los_Angeles

### ClickUp ↔ Calendar Sync (Replacement)
- Sync ClickUp task due dates as calendar events (the abandoned native integration)
- Use a lightweight approach: ClickUp tasks with due dates appear as all-day events or time-blocked work sessions
- Calendar → ClickUp: when a meeting is created for a client, optionally create a ClickUp task to prepare
- Respect Peterday: never schedule work events on Saturdays

### Agenda & Cadence Awareness
- Track recurring cadences from rhythms.md:
  - Thursday mornings: Sulima call (9am), then PRG newsletter production
  - Thursday + Sunday: Writing Cohort (noon-2pm)
  - Monthly (last week): ARC board report due
  - Quarterly (1st of month): Royalty reports due
- Surface upcoming cadence deadlines in daily/weekly views
- Flag when a cadence is approaching but no calendar event exists

## Edge Cases & Constraints
- **Peterday is sacred.** Saturdays are no-work days. Never create or suggest work events on Saturday.
- **Writing Cohort duplication.** Canonical home is mjbairey. Duplicates on other calendars are accidental. Don't sync or reference the duplicates.
- **Legacy ✅-prefixed events.** Ignore these — they're abandoned ClickUp sync artifacts on linguainkmedia.
- **Legacy "Delivery:" events.** Ignore on stephbairey — Maya no longer uses calendar for delivery tracking.
- **Pete's Alexa events.** Events on stephbairey added by Alexa are legitimate. Don't treat them as anomalies.
- **Dashboard dependency.** The local dashboard reads stephbairey calendar via Python fetcher. Any changes to stephbairey events or format could affect the dashboard display.
- **HoD = The Hallway of Doorknobs.** Calendar events referencing "HoD" are Lynn Haller's book project meetings.

## Implementation Notes

### Google Calendar API
- **Authentication:** OAuth2 with access to all 3 calendar accounts, or service account with delegated access
- **Primary view account:** linguainkmedia@gmail.com (has visibility into all 3)
- **Calendar IDs:** Same as email addresses:
  - `linguainkmedia@gmail.com`
  - `mjbairey@gmail.com`
  - `stephbairey@gmail.com`
- **Timezone:** `America/Los_Angeles`

### Key Recurring Events (from calendar-map.yaml)
| Day | Time | Event | Calendar |
|-----|------|-------|----------|
| Mon | 15:00-16:00 | PRG Gender Equity (bi-weekly) | linguainkmedia |
| Tue | 13:00-14:00 | HoD meeting | linguainkmedia |
| Thu | 09:00-10:00 | Sulima call | linguainkmedia |
| Thu | 10:00-11:00 | Devon Ervin meeting | linguainkmedia |
| Thu | varies | Daniela:Maya | linguainkmedia |
| Thu+Sun | 12:00-14:00 | Writing Cohort | mjbairey (canonical) |
| Fri | 09:00-10:00 | Story Lounge (legacy — ~2 weeks remaining) | linguainkmedia |
| 3rd Sun | varies | PRG meeting | stephbairey |
| Monthly | varies | ARC Meeting, TDA Board Meeting | stephbairey |
| Quarterly | 1st of month | Royalty reports | linguainkmedia |
| Saturday | all day | PETERDAY — no work | stephbairey |

### Calendar → Client Mapping
- "Devon Ervin and Steph @ Lingua Ink" → Devon Ervin, LIM, Steph identity
- "Sulima:Maya" → Sulima Malzin, LIB, Maya identity
- "Daniela:Maya" → Daniela Morescalchi, LIB, Maya identity
- "HoD meeting" → Lynn Haller, LIB, Maya identity
- "Writing Cohort" → Free Cohort, Maya identity

## Resolved Questions
- **Calendar API auth:** Each calendar will need separate authentication. One OAuth token will not cover all 3.
- **ClickUp ↔ Calendar sync direction:** Calendar events → ClickUp only, not vice versa.
- **Dashboard impact:** Dashboard reads .ics files, so the Python fetcher will work regardless of SL changes to calendar events.
- **Story Lounge:** Legacy — approximately 2 weeks remaining. Treat as legacy; no need to build automation around it.
