"""Revenue workflow endpoints — KDP import, royalty reports, consignment,
dashboard, manual entries, ClickUp time tracking."""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import TEMPLATES_DIR
from app.models.revenue import ConsignmentEntry, RecurringCost, RevenueEntry
from app.services.revenue_service import (
    build_summary,
    export_transactions_tsv,
    generate_royalty_reports,
    get_client_rates,
    get_consignment_summary,
    init_consignment_from_registry,
    parse_kdp_csv,
    transform_to_transactions,
)
from app.services.revenue_store import revenue_store

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
logger = logging.getLogger(__name__)


def _base_ctx(request: Request, active_tab: str = "") -> dict:
    return {
        "request": request,
        "modules": request.state.modules,
        "active_module": "revenue",
        "active_tab": active_tab,
    }


# --- Dashboard ---

@router.get("/")
async def revenue_home(request: Request):
    return RedirectResponse(url="/revenue/dashboard", status_code=302)


@router.get("/dashboard")
async def dashboard_page(request: Request):
    ctx = _base_ctx(request, "dashboard")
    ctx["summary"] = build_summary("month")
    ctx["rates"] = get_client_rates()
    ctx["costs"] = revenue_store.get_recurring_costs()
    return templates.TemplateResponse("revenue/dashboard.html", ctx)


@router.post("/dashboard/refresh")
async def dashboard_refresh(request: Request, period: str = Form("month")):
    ctx = _base_ctx(request, "dashboard")
    ctx["summary"] = build_summary(period)
    ctx["rates"] = get_client_rates()
    ctx["costs"] = revenue_store.get_recurring_costs()
    return templates.TemplateResponse("revenue/_dashboard_partial.html", ctx)


@router.post("/entry/add")
async def add_entry(
    request: Request,
    date: str = Form(""),
    client: str = Form(""),
    stream: str = Form("consulting"),
    description: str = Form(""),
    hours: float = Form(0),
    rate: float = Form(0),
    amount: float = Form(0),
):
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if hours and rate and not amount:
        amount = round(hours * rate, 2)
    entry = RevenueEntry(
        id=str(uuid.uuid4())[:8],
        date=date,
        client=client,
        stream=stream,
        description=description,
        hours=hours,
        rate=rate,
        amount=amount,
        source="manual",
    )
    revenue_store.add_revenue_entry(entry)
    ctx = _base_ctx(request, "dashboard")
    ctx["summary"] = build_summary("month")
    ctx["rates"] = get_client_rates()
    ctx["costs"] = revenue_store.get_recurring_costs()
    return templates.TemplateResponse("revenue/_dashboard_partial.html", ctx)


@router.post("/costs/update")
async def update_costs(request: Request):
    form = await request.form()
    costs = []
    i = 0
    while f"label_{i}" in form:
        label = form.get(f"label_{i}", "")
        amount = float(form.get(f"amount_{i}", 0))
        freq = form.get(f"frequency_{i}", "monthly")
        if label:
            costs.append(RecurringCost(label=label, amount=amount, frequency=freq))
        i += 1
    # Check for new entry
    new_label = form.get("new_label", "")
    new_amount = form.get("new_amount", "")
    if new_label and new_amount:
        costs.append(RecurringCost(
            label=new_label,
            amount=float(new_amount),
            frequency=form.get("new_frequency", "monthly"),
        ))
    revenue_store.save_recurring_costs(costs)
    ctx = _base_ctx(request, "dashboard")
    ctx["summary"] = build_summary("month")
    ctx["rates"] = get_client_rates()
    ctx["costs"] = revenue_store.get_recurring_costs()
    return templates.TemplateResponse("revenue/_dashboard_partial.html", ctx)


# --- KDP Import ---

@router.get("/kdp")
async def kdp_page(request: Request):
    ctx = _base_ctx(request, "kdp")
    ctx["imports"] = revenue_store.get_kdp_imports()
    return templates.TemplateResponse("revenue/kdp.html", ctx)


@router.post("/kdp/upload")
async def kdp_upload(request: Request, file: UploadFile = File(...)):
    ctx = _base_ctx(request, "kdp")
    try:
        content = await file.read()
        imp, records = parse_kdp_csv(file.filename or "upload.csv", content)

        # Duplicate check
        dupes = revenue_store.has_duplicate_records(records)
        if dupes:
            ctx["warning"] = f"Found {len(dupes)} duplicate record(s). Re-uploading will overwrite."
            ctx["dupes"] = dupes[:10]

        revenue_store.add_kdp_import(imp, records)
        ctx["import_result"] = imp
        ctx["records"] = records

        # Transform to Transactions format
        tx_rows = transform_to_transactions(records)
        ctx["tx_rows"] = tx_rows
        ctx["tx_tsv"] = export_transactions_tsv(tx_rows)
    except Exception as e:
        logger.exception("KDP upload failed")
        ctx["error"] = f"Upload failed: {e}"
        ctx["records"] = []

    ctx["imports"] = revenue_store.get_kdp_imports()
    return templates.TemplateResponse("revenue/_kdp_partial.html", ctx)


@router.post("/kdp/export")
async def kdp_export(request: Request, import_id: str = Form("")):
    """Re-export an existing import as Transactions rows."""
    ctx = _base_ctx(request, "kdp")
    if not import_id:
        ctx["error"] = "No import selected."
        ctx["imports"] = revenue_store.get_kdp_imports()
        return templates.TemplateResponse("revenue/_kdp_partial.html", ctx)

    records = [r for r in revenue_store.get_kdp_records() if r.import_id == import_id]
    if not records:
        ctx["error"] = f"No records found for import {import_id}."
        ctx["imports"] = revenue_store.get_kdp_imports()
        return templates.TemplateResponse("revenue/_kdp_partial.html", ctx)

    tx_rows = transform_to_transactions(records)
    ctx["tx_rows"] = tx_rows
    ctx["tx_tsv"] = export_transactions_tsv(tx_rows)
    ctx["records"] = records
    ctx["imports"] = revenue_store.get_kdp_imports()
    return templates.TemplateResponse("revenue/_kdp_partial.html", ctx)


# --- Book Sales (formerly Royalty Reports) ---

@router.get("/book-sales")
async def book_sales_page(request: Request):
    ctx = _base_ctx(request, "book-sales")
    ctx["reports"] = revenue_store.list_royalty_reports()
    return templates.TemplateResponse("revenue/book_sales.html", ctx)


@router.get("/royalties")
async def royalties_redirect(request: Request):
    return RedirectResponse(url="/revenue/book-sales", status_code=301)


@router.post("/book-sales/generate")
async def generate_reports(request: Request, quarter: str = Form("")):
    ctx = _base_ctx(request, "book-sales")
    if not quarter:
        now = datetime.now(timezone.utc)
        q = (now.month - 1) // 3 + 1
        quarter = f"{now.year}-Q{q}"

    try:
        reports = generate_royalty_reports(quarter)
        ctx["generated"] = reports
        ctx["quarter"] = quarter
        if not reports:
            ctx["warning"] = f"No KDP data found for {quarter}. Upload a CSV first."
    except Exception as e:
        logger.exception("Report generation failed")
        ctx["error"] = f"Generation failed: {e}"

    ctx["reports"] = revenue_store.list_royalty_reports()
    return templates.TemplateResponse("revenue/_book_sales_partial.html", ctx)


@router.get("/book-sales/{report_id}")
async def book_sale_detail(request: Request, report_id: str):
    ctx = _base_ctx(request, "book-sales")
    report = revenue_store.get_royalty_report(report_id)
    if not report:
        ctx["error"] = "Report not found."
        ctx["reports"] = revenue_store.list_royalty_reports()
        return templates.TemplateResponse("revenue/book_sales.html", ctx)
    ctx["report"] = report
    return templates.TemplateResponse("revenue/book_sale_detail.html", ctx)


@router.get("/royalties/{report_id}")
async def royalty_detail_redirect(request: Request, report_id: str):
    return RedirectResponse(url=f"/revenue/book-sales/{report_id}", status_code=301)


@router.post("/book-sales/update/{report_id}")
async def update_report_status(request: Request, report_id: str, status: str = Form("")):
    if status:
        revenue_store.update_report_status(report_id, status)
    return RedirectResponse(url=f"/revenue/book-sales/{report_id}", status_code=302)


# --- Consignment ---

@router.get("/consignment")
async def consignment_page(request: Request):
    ctx = _base_ctx(request, "consignment")
    ctx["entries"] = get_consignment_summary()
    return templates.TemplateResponse("revenue/consignment.html", ctx)


@router.post("/consignment/seed")
async def seed_consignment(request: Request):
    ctx = _base_ctx(request, "consignment")
    entries = init_consignment_from_registry()
    ctx["entries"] = sorted(entries, key=lambda e: (e.venue, e.title))
    ctx["seeded"] = True
    return templates.TemplateResponse("revenue/_consignment_partial.html", ctx)


@router.post("/consignment/add")
async def add_consignment(
    request: Request,
    venue: str = Form(""),
    title: str = Form(""),
    author_name: str = Form(""),
    qty_placed: int = Form(0),
    date_placed: str = Form(""),
    notes: str = Form(""),
):
    entry = ConsignmentEntry(
        id=str(uuid.uuid4())[:8],
        venue=venue,
        title=title,
        author_name=author_name,
        qty_placed=qty_placed,
        date_placed=date_placed,
        notes=notes,
    )
    revenue_store.add_consignment_entry(entry)
    ctx = _base_ctx(request, "consignment")
    ctx["entries"] = get_consignment_summary()
    return templates.TemplateResponse("revenue/_consignment_partial.html", ctx)


@router.post("/consignment/update/{entry_id}")
async def update_consignment(
    request: Request,
    entry_id: str,
    qty_sold: int = Form(0),
    last_checked: str = Form(""),
    revenue: float = Form(0),
    notes: str = Form(""),
):
    entries = revenue_store.get_consignment()
    for e in entries:
        if e.id == entry_id:
            e.qty_sold = qty_sold
            if last_checked:
                e.last_checked = last_checked
            e.revenue = revenue
            e.notes = notes
            revenue_store.save_consignment_entry(e)
            break
    ctx = _base_ctx(request, "consignment")
    ctx["entries"] = get_consignment_summary()
    return templates.TemplateResponse("revenue/_consignment_partial.html", ctx)


# --- ClickUp Time Tracking ---

@router.post("/time/pull")
async def pull_time(request: Request, start: str = Form(""), end: str = Form("")):
    ctx = _base_ctx(request, "dashboard")
    try:
        from app.services.clickup_client import clickup_client
        if not clickup_client.is_configured:
            ctx["time_error"] = "ClickUp API token not configured."
            return templates.TemplateResponse("revenue/_time_partial.html", ctx)

        from app.services.revenue_service import get_client_rates
        time_data = await clickup_client.get_time_entries(start, end)
        entries = time_data.get("data", [])

        rates = get_client_rates()
        by_client: dict[str, dict] = {}
        for entry in entries:
            task = entry.get("task", {}) or {}
            task_name = task.get("name", "Unknown")
            # Try to match to a client from task tags or name
            client_name = _match_client_from_task(task, rates)
            duration_ms = int(entry.get("duration", 0))
            hours = round(duration_ms / 3600000, 2)

            if client_name not in by_client:
                rate_info = rates.get(client_name, {})
                by_client[client_name] = {
                    "hours": 0,
                    "rate": rate_info.get("rate", 0),
                    "amount": 0,
                    "retainer": rate_info.get("retainer", 0),
                    "ceiling": rate_info.get("ceiling", 0),
                    "tasks": [],
                }
            by_client[client_name]["hours"] += hours
            by_client[client_name]["amount"] = round(
                by_client[client_name]["hours"] * by_client[client_name]["rate"], 2
            )
            by_client[client_name]["tasks"].append({
                "name": task_name,
                "hours": hours,
            })

        ctx["time_entries"] = by_client
        ctx["time_start"] = start
        ctx["time_end"] = end
    except Exception as e:
        logger.exception("Time pull failed")
        ctx["time_error"] = f"Failed to pull time entries: {e}"

    return templates.TemplateResponse("revenue/_time_partial.html", ctx)


def _match_client_from_task(task: dict, rates: dict) -> str:
    """Try to match a ClickUp task to a client name."""
    # Check custom fields for Project
    for field in task.get("custom_fields", []):
        if field.get("name", "").lower() == "project":
            options = field.get("type_config", {}).get("options", [])
            selected = field.get("value")
            if selected:
                for opt in options:
                    if opt.get("id") == selected:
                        project_name = opt.get("name", "")
                        # Match project name to client
                        for client_name in rates:
                            if project_name.lower() in client_name.lower() or \
                               client_name.lower() in project_name.lower():
                                return client_name
                        return project_name

    # Fallback: check task name against client names
    task_name = task.get("name", "").lower()
    for client_name in rates:
        if client_name.lower().split()[0] in task_name:
            return client_name

    return "Unassigned"
