"""File management endpoints — intake view, sorting, history, config."""

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR
from app.services.file_router import file_router

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
logger = logging.getLogger(__name__)


def _base_ctx(request: Request, active_tab: str = "") -> dict:
    return {
        "request": request,
        "modules": request.state.modules,
        "active_module": "files",
        "active_tab": active_tab,
    }


# --- Home ---

@router.get("/")
async def files_home(request: Request):
    if not file_router.is_configured:
        ctx = _base_ctx(request)
        ctx["intake_ready"] = file_router.intake_ready
        ctx["gdrive_ready"] = file_router.gdrive_ready
        return templates.TemplateResponse("files/setup.html", ctx)
    return RedirectResponse(url="/files/intake", status_code=302)


# --- Intake ---

@router.get("/intake")
async def intake_page(request: Request):
    if not file_router.is_configured:
        ctx = _base_ctx(request)
        ctx["intake_ready"] = file_router.intake_ready
        ctx["gdrive_ready"] = file_router.gdrive_ready
        return templates.TemplateResponse("files/setup.html", ctx)

    ctx = _base_ctx(request, "intake")
    files = file_router.scan_intake()
    ctx["files"] = files
    ctx["total"] = len(files)
    ctx["tagged"] = sum(1 for f in files if f.tags)
    ctx["untagged"] = sum(1 for f in files if not f.tags)
    return templates.TemplateResponse("files/intake.html", ctx)


# --- Preview (dry-run) ---

@router.post("/preview")
async def preview_sort(request: Request):
    ctx = _base_ctx(request, "intake")
    try:
        report = file_router.preview_all()
        ctx["report"] = report
        ctx["is_preview"] = True
    except Exception as e:
        logger.exception("Preview failed")
        ctx["error"] = f"Preview failed: {e}"
        ctx["report"] = None
    return templates.TemplateResponse("files/_preview_partial.html", ctx)


# --- Sort (move files) ---

@router.post("/sort")
async def sort_files(request: Request):
    ctx = _base_ctx(request, "intake")
    try:
        report = file_router.sort_all()
        ctx["report"] = report
    except Exception as e:
        logger.exception("Sort failed")
        ctx["error"] = f"Sort failed: {e}"
        ctx["report"] = None
    return templates.TemplateResponse("files/_sort_results.html", ctx)


# --- History ---

@router.get("/history")
async def history_page(request: Request):
    if not file_router.is_configured:
        ctx = _base_ctx(request)
        ctx["intake_ready"] = file_router.intake_ready
        ctx["gdrive_ready"] = file_router.gdrive_ready
        return templates.TemplateResponse("files/setup.html", ctx)

    ctx = _base_ctx(request, "history")
    ctx["history"] = file_router.get_history()
    return templates.TemplateResponse("files/history.html", ctx)


# --- Config ---

@router.get("/config")
async def config_page(request: Request):
    ctx = _base_ctx(request, "config")
    ctx["config"] = file_router.get_routing_config()
    ctx["intake_ready"] = file_router.intake_ready
    ctx["gdrive_ready"] = file_router.gdrive_ready
    return templates.TemplateResponse("files/config.html", ctx)


# --- Add Client ---

@router.post("/config/add-client")
async def add_client(request: Request, tag: str = Form(""), folder: str = Form("")):
    ctx = _base_ctx(request, "config")

    if not tag or not folder:
        ctx["client_error"] = "Both tag and folder name are required."
    else:
        ok = file_router.add_client(tag, folder)
        if ok:
            ctx["client_success"] = f"Client '{tag}' added with folder '{folder}'."
        else:
            ctx["client_error"] = f"Client '{tag}' already exists."

    ctx["config"] = file_router.get_routing_config()
    ctx["intake_ready"] = file_router.intake_ready
    ctx["gdrive_ready"] = file_router.gdrive_ready
    return templates.TemplateResponse("files/_config_client.html", ctx)


# --- Add Project ---

@router.post("/config/add-project")
async def add_project(
    request: Request,
    client_tag: str = Form(""),
    project_tag: str = Form(""),
    book_folder: str = Form(""),
):
    ctx = _base_ctx(request, "config")

    if not client_tag or not project_tag or not book_folder:
        ctx["project_error"] = "Client, project tag, and book folder are all required."
    else:
        ok = file_router.add_project(client_tag, project_tag, book_folder)
        if ok:
            ctx["project_success"] = f"Project '{project_tag}' added to {client_tag}."
        else:
            ctx["project_error"] = f"Project '{project_tag}' already exists for {client_tag}, or client not found."

    ctx["config"] = file_router.get_routing_config()
    ctx["intake_ready"] = file_router.intake_ready
    ctx["gdrive_ready"] = file_router.gdrive_ready
    return templates.TemplateResponse("files/_config_client.html", ctx)
