"""Calendar sync endpoints — today view, week view, event creation."""

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR
from app.services.gcal_client import GCalAuthError, GCalRateLimitError, gcal_client
from app.services.calendar_service import calendar_service

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
logger = logging.getLogger(__name__)

TZ = ZoneInfo("America/Los_Angeles")


def _base_ctx(request: Request, active_tab: str = "") -> dict:
    return {
        "request": request,
        "modules": request.state.modules,
        "active_module": "calendar",
        "active_tab": active_tab,
    }


def _setup_response(request: Request):
    return templates.TemplateResponse("calendar/setup.html", _base_ctx(request))


def _parse_date(date_str: str) -> date | None:
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


# --- Home ---

@router.get("/")
async def calendar_home(request: Request):
    if not gcal_client.is_configured:
        return _setup_response(request)
    return RedirectResponse(url="/calendar/today", status_code=302)


# --- Today / Day view ---

@router.get("/today")
async def today_page(request: Request):
    if not gcal_client.is_configured:
        return _setup_response(request)
    ctx = _base_ctx(request, "today")
    ctx["target_date"] = date.today()
    ctx["briefing"] = None
    return templates.TemplateResponse("calendar/today.html", ctx)


@router.get("/today/{date_str}")
async def today_date_page(request: Request, date_str: str):
    if not gcal_client.is_configured:
        return _setup_response(request)
    target = _parse_date(date_str) or date.today()
    ctx = _base_ctx(request, "today")
    ctx["target_date"] = target
    ctx["briefing"] = None
    return templates.TemplateResponse("calendar/today.html", ctx)


@router.post("/today/fetch")
async def today_fetch(request: Request, target_date: str = Form("")):
    if not gcal_client.is_configured:
        return _setup_response(request)

    target = _parse_date(target_date) or date.today()
    ctx = _base_ctx(request, "today")
    ctx["target_date"] = target

    try:
        briefing = await calendar_service.get_day_briefing(target)
        ctx["briefing"] = briefing
        ctx["error"] = None
    except (GCalAuthError, GCalRateLimitError) as e:
        ctx["briefing"] = None
        ctx["error"] = str(e)
    except Exception as e:
        logger.exception("Failed to fetch calendar events")
        ctx["briefing"] = None
        ctx["error"] = f"Failed to fetch events: {e}"

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("calendar/_today_partial.html", ctx)
    return templates.TemplateResponse("calendar/today.html", ctx)


# --- Week view ---

@router.get("/week")
async def week_page(request: Request):
    if not gcal_client.is_configured:
        return _setup_response(request)
    ctx = _base_ctx(request, "week")
    today = date.today()
    ctx["week_start"] = today - timedelta(days=(today.weekday() + 1) % 7)  # Sunday
    ctx["today_iso"] = today.isoformat()
    ctx["week_data"] = None
    return templates.TemplateResponse("calendar/week.html", ctx)


@router.post("/week/fetch")
async def week_fetch(request: Request, week_start: str = Form("")):
    if not gcal_client.is_configured:
        return _setup_response(request)

    ws = _parse_date(week_start)
    if not ws:
        today = date.today()
        ws = today - timedelta(days=(today.weekday() + 1) % 7)

    ctx = _base_ctx(request, "week")
    ctx["week_start"] = ws
    ctx["today_iso"] = date.today().isoformat()

    try:
        week_data = await calendar_service.get_week_events(ws)
        ctx["week_data"] = week_data
        ctx["error"] = None
    except (GCalAuthError, GCalRateLimitError) as e:
        ctx["week_data"] = None
        ctx["error"] = str(e)
    except Exception as e:
        logger.exception("Failed to fetch week events")
        ctx["week_data"] = None
        ctx["error"] = f"Failed to fetch events: {e}"

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("calendar/_week_partial.html", ctx)
    return templates.TemplateResponse("calendar/week.html", ctx)


# --- Event creation ---

@router.get("/create")
async def create_page(request: Request):
    if not gcal_client.is_configured:
        return _setup_response(request)
    ctx = _base_ctx(request, "create")
    ctx["accounts"] = gcal_client.accounts
    ctx["today_str"] = date.today().isoformat()
    return templates.TemplateResponse("calendar/create.html", ctx)


@router.post("/create/preview")
async def create_preview(
    request: Request,
    summary: str = Form(""),
    event_date: str = Form(""),
    start_time: str = Form(""),
    end_time: str = Form(""),
    all_day: str = Form(""),
    description: str = Form(""),
    location: str = Form(""),
    calendar_id: str = Form(""),
):
    ctx = _base_ctx(request, "create")

    target = _parse_date(event_date) or date.today()
    is_all_day = all_day == "on"

    # Determine calendar account
    account = gcal_client.get_account(calendar_id)
    calendar_label = account.label if account else "Unknown"
    identity = account.identity if account else ""

    # Peterday warning
    is_peterday = target.weekday() == 5

    ctx["preview"] = {
        "summary": summary,
        "event_date": target.isoformat(),
        "start_time": start_time,
        "end_time": end_time,
        "all_day": is_all_day,
        "description": description,
        "location": location,
        "calendar_id": calendar_id,
        "calendar_label": calendar_label,
        "identity": identity,
        "is_peterday": is_peterday,
    }

    return templates.TemplateResponse("calendar/_create_preview.html", ctx)


@router.post("/create/save")
async def create_save(
    request: Request,
    summary: str = Form(""),
    event_date: str = Form(""),
    start_time: str = Form(""),
    end_time: str = Form(""),
    all_day: str = Form(""),
    description: str = Form(""),
    location: str = Form(""),
    calendar_id: str = Form(""),
):
    if not gcal_client.is_configured:
        return HTMLResponse(
            '<div style="color: var(--red);">Calendar not configured</div>'
        )

    target = _parse_date(event_date) or date.today()
    is_all_day = all_day == "on"

    event_body: dict = {"summary": summary}
    if description:
        event_body["description"] = description
    if location:
        event_body["location"] = location

    if is_all_day:
        event_body["start"] = {"date": target.isoformat()}
        end_date = target + timedelta(days=1)
        event_body["end"] = {"date": end_date.isoformat()}
    else:
        start_dt = datetime.combine(target, datetime.strptime(start_time or "09:00", "%H:%M").time())
        end_dt = datetime.combine(target, datetime.strptime(end_time or "10:00", "%H:%M").time())
        event_body["start"] = {
            "dateTime": start_dt.replace(tzinfo=TZ).isoformat(),
            "timeZone": "America/Los_Angeles",
        }
        event_body["end"] = {
            "dateTime": end_dt.replace(tzinfo=TZ).isoformat(),
            "timeZone": "America/Los_Angeles",
        }

    try:
        created = await gcal_client.create_event(calendar_id, event_body)
        account = gcal_client.get_account(calendar_id)
        cal_label = account.label if account else calendar_id

        html = f'''<div class="card" style="border-left: 3px solid var(--green); padding: 1rem;">
          <div style="color: var(--green); font-weight: 600; margin-bottom: 0.5rem;">Event created</div>
          <div style="font-size: 0.9rem; font-weight: 600;">{created.summary}</div>
          <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem;">
            {target.strftime("%A, %b %d")} &middot; {cal_label}
          </div>
          {f'<div style="margin-top: 0.5rem;"><a href="{created.html_link}" target="_blank" class="btn btn-ghost" style="font-size: 0.8rem;">Open in Google Calendar</a></div>' if created.html_link else ''}
        </div>'''
        return HTMLResponse(html)
    except Exception as e:
        logger.exception("Failed to create event")
        return HTMLResponse(
            f'<div class="card" style="border-left: 3px solid var(--red); padding: 1rem;">'
            f'<div style="color: var(--red);">Failed to create event: {e}</div></div>'
        )
