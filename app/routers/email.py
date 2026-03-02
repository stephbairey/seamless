"""Email triage endpoints — inbox, classification, digest, reply drafting."""

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR

from app.services.gmail_client import GmailAuthError, GmailRateLimitError, gmail_client
from app.services.email_triage import email_triage
from app.services.reply_drafter import reply_drafter

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
logger = logging.getLogger(__name__)


def _base_ctx(request: Request, active_tab: str = "") -> dict:
    return {
        "request": request,
        "modules": request.state.modules,
        "active_module": "email",
        "active_tab": active_tab,
    }


def _setup_response(request: Request):
    return templates.TemplateResponse("email/setup.html", _base_ctx(request))


# --- Inbox ---

@router.get("/")
async def email_home(request: Request):
    if not gmail_client.is_configured:
        return _setup_response(request)
    return RedirectResponse(url="/email/inbox", status_code=302)


@router.get("/inbox")
async def inbox_page(request: Request):
    if not gmail_client.is_configured:
        return _setup_response(request)
    ctx = _base_ctx(request, "inbox")
    ctx["loaded"] = False
    ctx["query"] = ""
    ctx["max_results"] = "25"
    return templates.TemplateResponse("email/inbox.html", ctx)


@router.post("/inbox/fetch")
async def inbox_fetch(
    request: Request,
    query: str = Form(""),
    max_results: str = Form("25"),
):
    if not gmail_client.is_configured:
        return _setup_response(request)

    try:
        max_n = min(int(max_results), 100)
    except ValueError:
        max_n = 25

    ctx = _base_ctx(request, "inbox")
    ctx["loaded"] = True
    ctx["query"] = query
    ctx["max_results"] = str(max_n)

    try:
        # Ensure label cache is populated
        await gmail_client.get_labels()

        # Fetch message IDs
        msg_refs = await gmail_client.list_messages(query=query, max_results=max_n)

        # Fetch full messages
        messages = []
        for ref in msg_refs:
            msg = await gmail_client.get_message(ref["id"])
            messages.append(msg)

        # Classify unlabeled messages
        classifications = {}
        has_user_labels = {}
        unlabeled_count = 0
        for msg in messages:
            has_labels = email_triage.has_user_labels(msg)
            has_user_labels[msg.id] = has_labels
            if not has_labels:
                unlabeled_count += 1
                cls = email_triage.classify(msg)
                classifications[msg.id] = cls

        ctx["messages"] = messages
        ctx["classifications"] = classifications
        ctx["has_user_labels"] = has_user_labels
        ctx["unlabeled_count"] = unlabeled_count
        ctx["error"] = None

    except (GmailAuthError, GmailRateLimitError) as e:
        ctx["messages"] = []
        ctx["classifications"] = {}
        ctx["has_user_labels"] = {}
        ctx["unlabeled_count"] = 0
        ctx["error"] = str(e)
    except Exception as e:
        logger.exception("Failed to fetch messages")
        ctx["messages"] = []
        ctx["classifications"] = {}
        ctx["has_user_labels"] = {}
        ctx["unlabeled_count"] = 0
        ctx["error"] = f"Failed to fetch messages: {e}"

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("email/_inbox_partial.html", ctx)
    return templates.TemplateResponse("email/inbox.html", ctx)


# --- Label application ---

@router.post("/label/{msg_id}")
async def apply_label(
    request: Request,
    msg_id: str,
    label_name: str = Form(""),
):
    if not gmail_client.is_configured:
        return _setup_response(request)

    try:
        label_map = await gmail_client.get_labels()
        label_id = label_map.get(label_name)
        if not label_id:
            return templates.TemplateResponse("email/_inbox_partial.html", {
                **_base_ctx(request, "inbox"),
                "error": f"Label '{label_name}' not found in Gmail",
                "messages": [], "classifications": {}, "has_user_labels": {},
                "unlabeled_count": 0, "loaded": True,
            })

        await gmail_client.modify_labels(msg_id, add_ids=[label_id])

        # Return updated message card
        msg = await gmail_client.get_message(msg_id)

        # Build a minimal single-message partial response
        ctx = _base_ctx(request, "inbox")
        ctx["messages"] = [msg]
        ctx["classifications"] = {}
        ctx["has_user_labels"] = {msg.id: True}
        ctx["unlabeled_count"] = 0
        ctx["loaded"] = True
        ctx["success_label"] = label_name

        # Return just the card HTML for the labeled message
        html = f'''<div class="card" style="padding: 1rem; margin-bottom: 0.5rem;">
          <div style="display: flex; justify-content: space-between; align-items: start; gap: 1rem;">
            <div style="flex: 1; min-width: 0;">
              <div style="font-weight: 600; font-size: 0.9rem;">{msg.subject}</div>
              <div style="font-size: 0.8rem; color: var(--text-muted);">{msg.sender}</div>
            </div>
            <div style="flex-shrink: 0;">
              <span class="tag matched">{label_name}</span>
            </div>
          </div>
          <div style="margin-top: 0.5rem; font-size: 0.8rem; color: var(--green);">Label applied.</div>
        </div>'''
        return HTMLResponse(html)

    except Exception as e:
        logger.exception("Failed to apply label")
        return HTMLResponse(
            f'<div class="card" style="border-left: 3px solid var(--red); padding: 1rem;">'
            f'<div style="color: var(--red); font-size: 0.85rem;">Failed to apply label: {e}</div></div>'
        )


# --- Digest ---

@router.get("/digest")
async def digest_page(request: Request):
    if not gmail_client.is_configured:
        return _setup_response(request)
    ctx = _base_ctx(request, "digest")
    ctx["digest"] = None
    return templates.TemplateResponse("email/digest.html", ctx)


@router.post("/digest/generate")
async def digest_generate(
    request: Request,
    query: str = Form("newer_than:1d"),
    max_results: str = Form("100"),
):
    if not gmail_client.is_configured:
        return _setup_response(request)

    try:
        max_n = min(int(max_results), 200)
    except ValueError:
        max_n = 100

    ctx = _base_ctx(request, "digest")

    try:
        await gmail_client.get_labels()
        msg_refs = await gmail_client.list_messages(query=query, max_results=max_n)

        messages = []
        for ref in msg_refs:
            msg = await gmail_client.get_message(ref["id"])
            messages.append(msg)

        # Classify all messages
        classifications = []
        for msg in messages:
            classifications.append(email_triage.classify(msg))

        digest = await email_triage.generate_digest(messages, classifications)
        ctx["digest"] = digest
        ctx["error"] = None

    except (GmailAuthError, GmailRateLimitError) as e:
        ctx["digest"] = None
        ctx["error"] = str(e)
    except Exception as e:
        logger.exception("Digest generation failed")
        ctx["digest"] = None
        ctx["error"] = f"Failed to generate digest: {e}"

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("email/_digest_partial.html", ctx)
    return templates.TemplateResponse("email/digest.html", ctx)


# --- Reply Drafting ---

@router.get("/reply")
async def reply_landing(request: Request):
    """Reply page without a message — redirect to inbox."""
    if not gmail_client.is_configured:
        return _setup_response(request)
    ctx = _base_ctx(request, "reply")
    ctx["msg_id"] = None
    ctx["original"] = None
    ctx["draft"] = None
    return templates.TemplateResponse("email/reply.html", ctx)


@router.get("/reply/{msg_id}")
async def reply_page(request: Request, msg_id: str):
    """Reply page with the original message loaded."""
    if not gmail_client.is_configured:
        return _setup_response(request)

    ctx = _base_ctx(request, "reply")
    ctx["msg_id"] = msg_id

    try:
        await gmail_client.get_labels()
        original = await gmail_client.get_message(msg_id)
        send_as_info = reply_drafter.resolve_send_as(original)

        ctx["original"] = original
        ctx["send_as_info"] = send_as_info
        ctx["draft"] = None

    except Exception as e:
        logger.exception("Failed to load message for reply")
        ctx["original"] = None
        ctx["send_as_info"] = {}
        ctx["draft"] = None
        ctx["error"] = f"Failed to load message: {e}"

    return templates.TemplateResponse("email/reply.html", ctx)


@router.post("/reply/{msg_id}/generate")
async def reply_generate(
    request: Request,
    msg_id: str,
    instructions: str = Form(""),
):
    """Generate an LLM reply draft."""
    if not gmail_client.is_configured:
        return _setup_response(request)

    ctx = _base_ctx(request, "reply")
    ctx["msg_id"] = msg_id

    try:
        await gmail_client.get_labels()
        original = await gmail_client.get_message(msg_id)
        send_as_info = reply_drafter.resolve_send_as(original)
        draft = await reply_drafter.generate_draft(original, send_as_info, instructions)

        ctx["original"] = original
        ctx["send_as_info"] = send_as_info
        ctx["draft"] = draft
        ctx["error"] = None

    except Exception as e:
        logger.exception("Reply generation failed")
        ctx["original"] = None
        ctx["send_as_info"] = {}
        ctx["draft"] = None
        ctx["error"] = f"Failed to generate reply: {e}"

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("email/_reply_preview.html", ctx)
    return templates.TemplateResponse("email/reply.html", ctx)


@router.post("/reply/{msg_id}/check")
async def reply_check(
    request: Request,
    msg_id: str,
    text: str = Form(""),
    voice_id: str = Form(""),
):
    """Re-check edited text against text checker."""
    violations = reply_drafter.check_text(text, voice_id)
    return JSONResponse({"violations": violations})


@router.post("/reply/{msg_id}/save")
async def reply_save(
    request: Request,
    msg_id: str,
    body: str = Form(""),
):
    """Save the reply as a Gmail draft."""
    if not gmail_client.is_configured:
        return JSONResponse({"ok": False, "message": "Gmail not configured"})

    try:
        await gmail_client.get_labels()
        original = await gmail_client.get_message(msg_id)
        send_as_info = reply_drafter.resolve_send_as(original)

        # Build subject
        subject = original.subject
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        # Build From header with display name
        send_as_header = f"{send_as_info['send_as_name']} <{send_as_info['send_as']}>"

        result = await gmail_client.create_draft(
            to=original.sender_email or original.sender,
            subject=subject,
            body=body,
            send_as=send_as_header,
            thread_id=original.thread_id,
            in_reply_to=original.message_id,
        )

        draft_id = result.get("id", "")
        return JSONResponse({
            "ok": True,
            "message": f"Draft saved. (ID: {draft_id})",
        })

    except Exception as e:
        logger.exception("Failed to save draft")
        return JSONResponse({
            "ok": False,
            "message": f"Failed to save draft: {e}",
        })
