"""PRG Newsletter endpoints — collect, compose, export, history."""

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR
from app.services.gmail_client import GmailAuthError, GmailRateLimitError, gmail_client
from app.services.newsletter_compiler import newsletter_compiler
from app.services.newsletter_service import newsletter_service
from app.services.newsletter_store import newsletter_store

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
logger = logging.getLogger(__name__)

CATEGORY_PRIORITY = {
    "action_item": 0,
    "team_note": 1,
    "article": 2,
    "joana_rollup": 3,
    "uncategorized": 4,
}

# Sentinel for items without an event date — sorts after all real dates
_NO_DATE = "9999-99-99"


def _sort_items(items):
    """Sort by category priority, then event_date (earliest first, no-date last), then display_order."""
    items.sort(key=lambda i: (
        CATEGORY_PRIORITY.get(i.category, 4),
        i.event_date if i.event_date else _NO_DATE,
        i.display_order,
    ))


def _base_ctx(request: Request, active_tab: str = "") -> dict:
    return {
        "request": request,
        "modules": request.state.modules,
        "active_module": "newsletter",
        "active_tab": active_tab,
    }


def _setup_response(request: Request):
    return templates.TemplateResponse("newsletter/setup.html", _base_ctx(request))


# --- Home redirect ---

@router.get("/")
async def newsletter_home(request: Request):
    if not gmail_client.is_configured:
        return _setup_response(request)
    return RedirectResponse(url="/newsletter/collect", status_code=302)


# --- Collect ---

@router.get("/collect")
async def collect_page(request: Request):
    if not gmail_client.is_configured:
        return _setup_response(request)
    ctx = _base_ctx(request, "collect")
    issue = newsletter_store.get_current_issue()
    ctx["issue"] = issue
    ctx["items"] = [i for i in issue.items if i.status != "excluded"]
    return templates.TemplateResponse("newsletter/collect.html", ctx)


@router.post("/collect/fetch")
async def collect_fetch(request: Request, days_back: str = Form("7")):
    if not gmail_client.is_configured:
        return _setup_response(request)

    try:
        days = min(int(days_back), 30)
    except ValueError:
        days = 7

    ctx = _base_ctx(request, "collect")

    try:
        await gmail_client.get_labels()
        new_items = await newsletter_service.collect_from_gmail(days_back=days)
        issue = newsletter_store.get_current_issue()
        ctx["issue"] = issue
        ctx["items"] = [i for i in issue.items if i.status != "excluded"]
        ctx["new_count"] = len(new_items)
        ctx["error"] = None
    except (GmailAuthError, GmailRateLimitError) as e:
        issue = newsletter_store.get_current_issue()
        ctx["issue"] = issue
        ctx["items"] = [i for i in issue.items if i.status != "excluded"]
        ctx["new_count"] = 0
        ctx["error"] = str(e)
    except Exception as e:
        logger.exception("Newsletter fetch failed")
        issue = newsletter_store.get_current_issue()
        ctx["issue"] = issue
        ctx["items"] = [i for i in issue.items if i.status != "excluded"]
        ctx["new_count"] = 0
        ctx["error"] = f"Failed to fetch: {e}"

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("newsletter/_collect_partial.html", ctx)
    return templates.TemplateResponse("newsletter/collect.html", ctx)


@router.post("/collect/manual")
async def collect_manual(
    request: Request,
    sender_name: str = Form(""),
    subject: str = Form(""),
    body_text: str = Form(""),
    category: str = Form("uncategorized"),
):
    ctx = _base_ctx(request, "collect")

    if not subject.strip():
        issue = newsletter_store.get_current_issue()
        ctx["issue"] = issue
        ctx["items"] = [i for i in issue.items if i.status != "excluded"]
        ctx["error"] = "Subject is required."
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse("newsletter/_collect_partial.html", ctx)
        return templates.TemplateResponse("newsletter/collect.html", ctx)

    newsletter_service.create_manual_item(
        sender_name=sender_name.strip(),
        subject=subject.strip(),
        body_text=body_text.strip(),
        category=category,
    )

    issue = newsletter_store.get_current_issue()
    ctx["issue"] = issue
    ctx["items"] = [i for i in issue.items if i.status != "excluded"]
    ctx["new_count"] = 1
    ctx["error"] = None

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("newsletter/_collect_partial.html", ctx)
    return templates.TemplateResponse("newsletter/collect.html", ctx)


@router.post("/collect/classify-all")
async def collect_classify_all(request: Request):
    ctx = _base_ctx(request, "collect")

    try:
        issue = newsletter_store.get_current_issue()
        uncategorized = [i for i in issue.items if i.category == "uncategorized" or not i.headline]
        updated = await newsletter_service.classify_and_headline_all(uncategorized)

        # Reload after updates
        issue = newsletter_store.get_current_issue()
        ctx["issue"] = issue
        ctx["items"] = [i for i in issue.items if i.status != "excluded"]
        ctx["classified_count"] = len(updated)
        ctx["error"] = None
    except Exception as e:
        logger.exception("Classification failed")
        issue = newsletter_store.get_current_issue()
        ctx["issue"] = issue
        ctx["items"] = [i for i in issue.items if i.status != "excluded"]
        ctx["classified_count"] = 0
        ctx["error"] = f"Classification failed: {e}"

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("newsletter/_collect_partial.html", ctx)
    return templates.TemplateResponse("newsletter/collect.html", ctx)


# --- Compose ---

@router.get("/compose")
async def compose_page(request: Request):
    ctx = _base_ctx(request, "compose")
    issue = newsletter_store.get_current_issue()
    items = [i for i in issue.items if i.status == "included"]
    _sort_items(items)
    ctx["issue"] = issue
    ctx["items"] = items
    return templates.TemplateResponse("newsletter/compose.html", ctx)


@router.post("/compose/update/{item_id}")
async def compose_update(
    request: Request,
    item_id: str,
    headline: str = Form(None),
    category: str = Form(None),
    status: str = Form(None),
    body_text: str = Form(None),
    event_date: str = Form(None),
    rewritten_body: str = Form(None),
    rewrite_type: str = Form(None),
    source_url: str = Form(None),
    extra_context: str = Form(None),
):
    updates = {}
    if headline is not None:
        updates["headline"] = headline.strip()
    if category is not None:
        updates["category"] = category
    if status is not None:
        updates["status"] = status
    if body_text is not None:
        updates["body_text"] = body_text
    if event_date is not None:
        updates["event_date"] = event_date.strip()
    if rewritten_body is not None:
        updates["rewritten_body"] = rewritten_body
        updates["rewrite_status"] = "edited"
    if rewrite_type is not None:
        updates["rewrite_type"] = rewrite_type
    if source_url is not None:
        updates["source_url"] = source_url.strip()
    if extra_context is not None:
        updates["extra_context"] = extra_context

    newsletter_store.update_item(item_id, updates)

    ctx = _base_ctx(request, "compose")
    issue = newsletter_store.get_current_issue()
    items = [i for i in issue.items if i.status == "included"]
    _sort_items(items)
    ctx["issue"] = issue
    ctx["items"] = items

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("newsletter/_compose_partial.html", ctx)
    return templates.TemplateResponse("newsletter/compose.html", ctx)


@router.post("/compose/reorder")
async def compose_reorder(request: Request):
    form = await request.form()
    item_ids = form.getlist("item_ids")

    newsletter_store.reorder_items(item_ids)

    ctx = _base_ctx(request, "compose")
    issue = newsletter_store.get_current_issue()
    items = [i for i in issue.items if i.status == "included"]
    _sort_items(items)
    ctx["issue"] = issue
    ctx["items"] = items

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("newsletter/_compose_partial.html", ctx)
    return templates.TemplateResponse("newsletter/compose.html", ctx)


# --- Rewrite ---

@router.post("/compose/rewrite/{item_id}")
async def compose_rewrite_item(request: Request, item_id: str):
    """Rewrite a single item and return its updated card via HTMX."""
    ctx = _base_ctx(request, "compose")

    try:
        issue = newsletter_store.get_current_issue()
        item = next((i for i in issue.items if i.id == item_id), None)
        if not item:
            ctx["error"] = f"Item {item_id} not found."
            issue = newsletter_store.get_current_issue()
            items = [i for i in issue.items if i.status == "included"]
            _sort_items(items)
            ctx["issue"] = issue
            ctx["items"] = items
            return templates.TemplateResponse("newsletter/_compose_partial.html", ctx)

        result = await newsletter_service.rewrite_item(item)
        newsletter_store.update_item(item_id, result)

        # Reload the item for single-item partial
        issue = newsletter_store.get_current_issue()
        updated_item = next((i for i in issue.items if i.id == item_id), None)

        if request.headers.get("HX-Request"):
            ctx["item"] = updated_item
            return templates.TemplateResponse("newsletter/_compose_item.html", ctx)

        items = [i for i in issue.items if i.status == "included"]
        _sort_items(items)
        ctx["issue"] = issue
        ctx["items"] = items
        return templates.TemplateResponse("newsletter/compose.html", ctx)
    except Exception as e:
        logger.exception("Rewrite failed for item %s", item_id)
        issue = newsletter_store.get_current_issue()
        items = [i for i in issue.items if i.status == "included"]
        _sort_items(items)
        ctx["issue"] = issue
        ctx["items"] = items
        ctx["error"] = f"Rewrite failed: {e}"
        return templates.TemplateResponse("newsletter/_compose_partial.html", ctx)


@router.post("/compose/rewrite-all")
async def compose_rewrite_all(request: Request):
    """Rewrite all pending items and return the full compose partial."""
    ctx = _base_ctx(request, "compose")

    try:
        issue = newsletter_store.get_current_issue()
        items = [i for i in issue.items if i.status == "included"]
        await newsletter_service.rewrite_all(items)

        issue = newsletter_store.get_current_issue()
        items = [i for i in issue.items if i.status == "included"]
        _sort_items(items)
        ctx["issue"] = issue
        ctx["items"] = items
        ctx["rewrite_count"] = len([i for i in items if i.rewrite_status in ("done", "skipped")])
    except Exception as e:
        logger.exception("Rewrite-all failed")
        issue = newsletter_store.get_current_issue()
        items = [i for i in issue.items if i.status == "included"]
        _sort_items(items)
        ctx["issue"] = issue
        ctx["items"] = items
        ctx["error"] = f"Rewrite failed: {e}"

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("newsletter/_compose_partial.html", ctx)
    return templates.TemplateResponse("newsletter/compose.html", ctx)


# --- Export ---

@router.get("/export")
async def export_page(request: Request):
    ctx = _base_ctx(request, "export")
    issue = newsletter_store.get_current_issue()
    ctx["issue"] = issue
    ctx["compilation"] = None
    return templates.TemplateResponse("newsletter/export.html", ctx)


@router.post("/export/compile")
async def export_compile(
    request: Request,
    newsletter_date: str = Form(""),
    next_meeting_day: str = Form(""),
    next_meeting_location: str = Form(""),
):
    ctx = _base_ctx(request, "export")

    try:
        issue = newsletter_store.get_current_issue()

        # Save metadata to issue before compiling
        meta_updates = {}
        if newsletter_date.strip():
            meta_updates["newsletter_date"] = newsletter_date.strip()
        if next_meeting_day.strip():
            meta_updates["next_meeting_day"] = next_meeting_day.strip()
        if next_meeting_location.strip():
            meta_updates["next_meeting_location"] = next_meeting_location.strip()
        if meta_updates:
            for k, v in meta_updates.items():
                setattr(issue, k, v)
            newsletter_store.save_issue(issue)

        compilation = newsletter_compiler.compile(issue)
        newsletter_store.save_issue(compilation.issue)
        ctx["issue"] = compilation.issue
        ctx["compilation"] = compilation
        ctx["error"] = None
    except Exception as e:
        logger.exception("Compilation failed")
        issue = newsletter_store.get_current_issue()
        ctx["issue"] = issue
        ctx["compilation"] = None
        ctx["error"] = f"Compilation failed: {e}"

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("newsletter/_export_partial.html", ctx)
    return templates.TemplateResponse("newsletter/export.html", ctx)


# --- History ---

@router.get("/history")
async def history_page(request: Request):
    ctx = _base_ctx(request, "history")
    ctx["issues"] = newsletter_store.list_issues()
    return templates.TemplateResponse("newsletter/history.html", ctx)
