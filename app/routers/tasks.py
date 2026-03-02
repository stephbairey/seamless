"""ClickUp task management endpoints."""

import logging
from datetime import date

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR
from app.models.clickup import TaskFilters
from app.services.clickup_client import clickup_client, ClickUpAuthError, ClickUpRateLimitError
from app.services.clickup_fields import clickup_fields
from app.services.clickup_tasks import (
    create_task, generate_report, get_task, list_tasks, update_status, bulk_update_status,
)
from app.services.field_inference import infer_fields

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
logger = logging.getLogger(__name__)


def _base_ctx(request: Request, active_tab: str = "") -> dict:
    return {
        "request": request,
        "modules": request.state.modules,
        "active_module": "tasks",
        "active_tab": active_tab,
    }


def _setup_response(request: Request):
    """Render setup page when API token is missing."""
    return templates.TemplateResponse("tasks/setup.html", _base_ctx(request))


# --- Task Creation (two-step: form → preview → submit) ---

@router.get("/")
async def tasks_home(request: Request):
    if not clickup_client.is_configured:
        return _setup_response(request)
    return RedirectResponse(url="/tasks/list", status_code=302)


@router.get("/create")
async def create_form(request: Request):
    if not clickup_client.is_configured:
        return _setup_response(request)
    ctx = _base_ctx(request, "create")
    return templates.TemplateResponse("tasks/task_create.html", ctx)


@router.post("/create/preview")
async def create_preview(
    request: Request,
    name: str = Form(""),
    due_date: str = Form(""),
    description: str = Form(""),
):
    if not clickup_client.is_configured:
        return _setup_response(request)

    errors = []
    if not name.strip():
        errors.append("Task name is required.")
    if not due_date:
        errors.append("Due date is required.")

    if errors:
        ctx = _base_ctx(request, "create")
        ctx["errors"] = errors
        ctx["name"] = name
        ctx["due_date"] = due_date
        ctx["description"] = description
        return templates.TemplateResponse("tasks/task_create.html", ctx)

    parsed_date = date.fromisoformat(due_date)
    inferred = infer_fields(name, description)

    ctx = _base_ctx(request, "create")
    ctx["name"] = name
    ctx["due_date"] = due_date
    ctx["description"] = description
    ctx["inferred"] = inferred
    ctx["project_options"] = clickup_fields.project_options()
    ctx["effort_options"] = clickup_fields.options("Effort")
    ctx["revenue_options"] = clickup_fields.options("Revenue")
    ctx["scope_options"] = clickup_fields.options("Scope")
    ctx["approach_options"] = clickup_fields.options("Approach")
    ctx["readiness_options"] = clickup_fields.options("Readiness")

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("tasks/_task_preview.html", ctx)
    return templates.TemplateResponse("tasks/_task_preview.html", ctx)


@router.post("/create/submit")
async def create_submit(
    request: Request,
    name: str = Form(""),
    due_date: str = Form(""),
    description: str = Form(""),
    project_id: str = Form(""),
    effort_id: str = Form(""),
    revenue_id: str = Form(""),
    scope_id: str = Form(""),
    approach_id: str = Form(""),
    readiness_id: str = Form(""),
):
    if not clickup_client.is_configured:
        return _setup_response(request)

    parsed_date = date.fromisoformat(due_date)

    project = clickup_fields.option_by_id("Project", project_id) if project_id else None
    effort = clickup_fields.option_by_id("Effort", effort_id) if effort_id else None
    revenue = clickup_fields.option_by_id("Revenue", revenue_id) if revenue_id else None
    scope = clickup_fields.option_by_id("Scope", scope_id) if scope_id else None
    readiness = clickup_fields.option_by_id("Readiness", readiness_id) if readiness_id else None

    # Approach: default to Indifferent if not set
    approach = None
    if approach_id:
        approach = clickup_fields.option_by_id("Approach", approach_id)
    if not approach:
        approach = clickup_fields.option_by_name("Approach", "Indifferent")

    try:
        result = await create_task(
            name=name, due_date=parsed_date, description=description,
            project=project, effort=effort, revenue=revenue,
            scope=scope, approach=approach, readiness=readiness,
        )
        ctx = _base_ctx(request, "create")
        ctx["success"] = True
        ctx["task_url"] = result.get("url", "")
        ctx["task_id"] = result.get("id", "")
        ctx["task_name"] = name
        return templates.TemplateResponse("tasks/task_create.html", ctx)
    except (ClickUpAuthError, ClickUpRateLimitError) as e:
        ctx = _base_ctx(request, "create")
        ctx["errors"] = [str(e)]
        ctx["name"] = name
        ctx["due_date"] = due_date
        ctx["description"] = description
        return templates.TemplateResponse("tasks/task_create.html", ctx)
    except Exception as e:
        logger.exception("Task creation failed")
        ctx = _base_ctx(request, "create")
        ctx["errors"] = [f"Failed to create task: {e}"]
        ctx["name"] = name
        ctx["due_date"] = due_date
        ctx["description"] = description
        return templates.TemplateResponse("tasks/task_create.html", ctx)


# --- Task List + Filtering ---

@router.get("/list")
async def task_list_page(request: Request):
    if not clickup_client.is_configured:
        return _setup_response(request)

    ctx = _base_ctx(request, "list")
    ctx["project_options"] = clickup_fields.project_options()
    ctx["effort_options"] = clickup_fields.options("Effort")
    ctx["revenue_options"] = clickup_fields.options("Revenue")
    ctx["scope_options"] = clickup_fields.options("Scope")
    ctx["approach_options"] = clickup_fields.options("Approach")
    ctx["readiness_options"] = clickup_fields.options("Readiness")
    ctx["statuses"] = clickup_fields.statuses()
    ctx["filters"] = TaskFilters()
    ctx["tasks"] = []
    ctx["loaded"] = False
    return templates.TemplateResponse("tasks/task_list.html", ctx)


@router.post("/list/filter")
async def task_list_filter(
    request: Request,
    project: str = Form(""),
    status: str = Form(""),
    effort: str = Form(""),
    revenue: str = Form(""),
    scope: str = Form(""),
    approach: str = Form(""),
    readiness: str = Form(""),
    search: str = Form(""),
    sort_by: str = Form("due_date"),
    overdue_only: bool = Form(False),
):
    if not clickup_client.is_configured:
        return _setup_response(request)

    filters = TaskFilters(
        project=project, status=status, effort=effort, revenue=revenue,
        scope=scope, approach=approach, readiness=readiness,
        search=search, sort_by=sort_by, overdue_only=overdue_only,
    )

    try:
        tasks = await list_tasks(filters=filters, include_closed=(status.lower() == "complete"))
        ctx = _base_ctx(request, "list")
        ctx["tasks"] = tasks
        ctx["filters"] = filters
        ctx["loaded"] = True
        ctx["error"] = None

        if request.headers.get("HX-Request"):
            return templates.TemplateResponse("tasks/_task_list_partial.html", ctx)

        ctx["project_options"] = clickup_fields.project_options()
        ctx["effort_options"] = clickup_fields.options("Effort")
        ctx["revenue_options"] = clickup_fields.options("Revenue")
        ctx["scope_options"] = clickup_fields.options("Scope")
        ctx["approach_options"] = clickup_fields.options("Approach")
        ctx["readiness_options"] = clickup_fields.options("Readiness")
        ctx["statuses"] = clickup_fields.statuses()
        return templates.TemplateResponse("tasks/task_list.html", ctx)

    except (ClickUpAuthError, ClickUpRateLimitError) as e:
        ctx = _base_ctx(request, "list")
        ctx["tasks"] = []
        ctx["filters"] = filters
        ctx["loaded"] = True
        ctx["error"] = str(e)
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse("tasks/_task_list_partial.html", ctx)
        ctx["project_options"] = clickup_fields.project_options()
        ctx["effort_options"] = clickup_fields.options("Effort")
        ctx["revenue_options"] = clickup_fields.options("Revenue")
        ctx["scope_options"] = clickup_fields.options("Scope")
        ctx["approach_options"] = clickup_fields.options("Approach")
        ctx["readiness_options"] = clickup_fields.options("Readiness")
        ctx["statuses"] = clickup_fields.statuses()
        return templates.TemplateResponse("tasks/task_list.html", ctx)


@router.get("/detail/{task_id}")
async def task_detail(request: Request, task_id: str):
    if not clickup_client.is_configured:
        return _setup_response(request)

    try:
        task = await get_task(task_id)
        ctx = _base_ctx(request, "detail")
        ctx["task"] = task
        ctx["statuses"] = clickup_fields.statuses()
        return templates.TemplateResponse("tasks/task_detail.html", ctx)
    except Exception as e:
        logger.exception("Failed to load task detail")
        ctx = _base_ctx(request, "list")
        ctx["errors"] = [f"Failed to load task: {e}"]
        return RedirectResponse(url="/tasks/list", status_code=302)


@router.post("/detail/{task_id}/status")
async def update_task_status(request: Request, task_id: str, status: str = Form("")):
    if not clickup_client.is_configured:
        return _setup_response(request)

    try:
        await update_status(task_id, status)
        task = await get_task(task_id)
        ctx = _base_ctx(request, "detail")
        ctx["task"] = task
        ctx["statuses"] = clickup_fields.statuses()
        ctx["success_message"] = f"Status updated to {status}"
        return templates.TemplateResponse("tasks/task_detail.html", ctx)
    except Exception as e:
        logger.exception("Failed to update task status")
        task = await get_task(task_id)
        ctx = _base_ctx(request, "detail")
        ctx["task"] = task
        ctx["statuses"] = clickup_fields.statuses()
        ctx["error"] = f"Failed to update status: {e}"
        return templates.TemplateResponse("tasks/task_detail.html", ctx)


@router.post("/bulk-status")
async def bulk_status_update(request: Request):
    if not clickup_client.is_configured:
        return _setup_response(request)

    form = await request.form()
    task_ids = form.getlist("task_ids")
    status = form.get("status", "")

    if not task_ids or not status:
        return RedirectResponse(url="/tasks/list", status_code=302)

    try:
        await bulk_update_status(task_ids, status)
    except Exception as e:
        logger.exception("Bulk status update failed")

    return RedirectResponse(url="/tasks/list", status_code=302)


# --- Weekly Report ---

@router.get("/report")
async def report_page(request: Request):
    if not clickup_client.is_configured:
        return _setup_response(request)

    ctx = _base_ctx(request, "report")
    ctx["report"] = None
    ctx["loaded"] = False
    return templates.TemplateResponse("tasks/weekly_report.html", ctx)


@router.post("/report/generate")
async def report_generate(request: Request):
    if not clickup_client.is_configured:
        return _setup_response(request)

    try:
        report = await generate_report(include_closed=True)
        ctx = _base_ctx(request, "report")
        ctx["report"] = report
        ctx["loaded"] = True

        if request.headers.get("HX-Request"):
            return templates.TemplateResponse("tasks/_report_partial.html", ctx)
        return templates.TemplateResponse("tasks/weekly_report.html", ctx)

    except Exception as e:
        logger.exception("Report generation failed")
        ctx = _base_ctx(request, "report")
        ctx["report"] = None
        ctx["loaded"] = True
        ctx["error"] = f"Failed to generate report: {e}"
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse("tasks/_report_partial.html", ctx)
        return templates.TemplateResponse("tasks/weekly_report.html", ctx)
