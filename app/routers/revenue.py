"""Revenue workflow endpoints — KDP import, royalty reports, consignment,
dashboard, manual entries, ClickUp time tracking."""

import asyncio
import fcntl
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import CLICKUP_TASK_CACHE, TEMPLATES_DIR, YNAB_BUDGET_ID, YNAB_CATEGORY_GROUP
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
    today = datetime.now(timezone.utc)
    ctx["start_date"] = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    ctx["end_date"] = today.strftime("%Y-%m-%d")
    return templates.TemplateResponse("revenue/dashboard.html", ctx)


@router.post("/dashboard/refresh")
async def dashboard_refresh(
    request: Request,
    start: str = Form(""),
    end: str = Form(""),
):
    ctx = _base_ctx(request, "dashboard")
    today = datetime.now(timezone.utc)
    if not start:
        start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end:
        end = today.strftime("%Y-%m-%d")

    # Fetch YNAB and ClickUp concurrently
    ynab_coro = _fetch_ynab_summary(start, end)
    clickup_coro = _fetch_clickup_time(start, end)
    ynab_result, clickup_result = await asyncio.gather(
        ynab_coro, clickup_coro, return_exceptions=True,
    )

    # Unpack YNAB
    if isinstance(ynab_result, Exception):
        logger.exception("YNAB fetch failed in dashboard", exc_info=ynab_result)
        ctx["ynab_error"] = f"Failed to fetch YNAB data: {ynab_result}"
    elif isinstance(ynab_result, dict) and "error" in ynab_result:
        ctx["ynab_error"] = ynab_result["error"]
    else:
        ctx.update(ynab_result)

    # Unpack ClickUp
    if isinstance(clickup_result, Exception):
        logger.exception("ClickUp fetch failed in dashboard", exc_info=clickup_result)
        ctx["clickup_error"] = f"Failed to fetch time entries: {clickup_result}"
    elif isinstance(clickup_result, dict) and "error" in clickup_result:
        ctx["clickup_error"] = clickup_result["error"]
    else:
        ctx.update(clickup_result)

    # Always pass cache timestamp for display (even if ClickUp fetch failed)
    if "task_cache_synced" not in ctx:
        cache = _load_task_cache()
        ctx["task_cache_synced"] = cache.get("last_synced")

    return templates.TemplateResponse("revenue/_dashboard_partial.html", ctx)


@router.post("/dashboard/sync-tasks")
async def dashboard_sync_tasks(request: Request):
    """Full sync: bulk-fetch all tasks from ClickUp, rebuild the cache entirely."""
    from app.services.clickup_client import clickup_client

    ctx = _base_ctx(request, "dashboard")

    if not clickup_client.is_configured:
        ctx["sync_error"] = "ClickUp API token not configured."
        return templates.TemplateResponse("revenue/_sync_result.html", ctx)

    try:
        project_rates = _load_project_rates()
        await _build_task_project_map(clickup_client, project_rates)
        cache = _load_task_cache()
        ctx["sync_count"] = len(cache.get("tasks", {}))
        ctx["sync_time"] = cache.get("last_synced", "")
    except Exception as e:
        logger.exception("Task sync failed")
        ctx["sync_error"] = f"Sync failed: {e}"

    return templates.TemplateResponse("revenue/_sync_result.html", ctx)


async def _fetch_ynab_summary(start: str, end: str) -> dict:
    """Fetch YNAB transactions and return headline numbers."""
    from app.services.ynab_client import ynab_client, YnabAuthError, YnabRateLimitError

    if not ynab_client.is_configured:
        return {"error": "YNAB API token not configured. Add YNAB_API_TOKEN to secrets.env."}

    try:
        cat_data = await ynab_client.get_categories(YNAB_BUDGET_ID)
        cat_groups = cat_data.get("data", {}).get("category_groups", [])
        li_category_ids: set[str] = set()
        cat_id_to_name: dict[str, str] = {}
        for group in cat_groups:
            if group.get("name") == YNAB_CATEGORY_GROUP:
                for cat in group.get("categories", []):
                    li_category_ids.add(cat["id"])
                    cat_id_to_name[cat["id"]] = cat.get("name", "Uncategorized")
                break

        data = await ynab_client.get_transactions(YNAB_BUDGET_ID, since_date=start)
        transactions = data.get("data", {}).get("transactions", [])

        filtered = [
            t for t in transactions
            if t.get("category_id") in li_category_ids
            and t.get("date", "") <= end
        ]

        # Aggregate: 💵-prefixed = income, rest = expenses
        income_milliunits = 0
        expense_milliunits = 0
        for t in filtered:
            cat_name = cat_id_to_name.get(t.get("category_id", ""), "")
            amt = t.get("amount", 0)
            if cat_name.lstrip().startswith("\U0001f4b5"):
                income_milliunits += amt
            else:
                expense_milliunits += amt

        income_net = round(income_milliunits / 1000, 2)
        expense_total = round(abs(expense_milliunits) / 1000, 2)
        net_total = round((income_milliunits + expense_milliunits) / 1000, 2)

        return {
            "ynab_income": income_net,
            "ynab_expenses": expense_total,
            "ynab_net": net_total,
            "ynab_tx_count": len(filtered),
        }
    except YnabAuthError:
        return {"error": "YNAB authentication failed. Check your API token."}
    except YnabRateLimitError:
        return {"error": "YNAB rate limit reached. Try again in a minute."}


def _load_task_cache() -> dict:
    """Read the task→project cache from disk."""
    if not CLICKUP_TASK_CACHE.exists():
        return {"tasks": {}, "last_synced": None}
    try:
        with open(CLICKUP_TASK_CACHE) as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f, fcntl.LOCK_UN)
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to read task cache: %s", e)
        return {"tasks": {}, "last_synced": None}


def _save_task_cache(cache: dict):
    """Write the task→project cache to disk."""
    CLICKUP_TASK_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(CLICKUP_TASK_CACHE, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(cache, f, indent=2)
        fcntl.flock(f, fcntl.LOCK_UN)


async def _fetch_clickup_time(start: str, end: str) -> dict:
    """Fetch ClickUp time entries and return by-project breakdown.
    Uses a local task cache to avoid bulk-fetching all tasks on every refresh."""
    from app.services.clickup_client import clickup_client

    if not clickup_client.is_configured:
        return {"error": "ClickUp API token not configured."}

    time_data = await clickup_client.get_time_entries(start, end)
    entries = time_data.get("data", [])

    project_rates = _load_project_rates()
    cache = _load_task_cache()
    cached_tasks = cache.get("tasks", {})

    # Collect task IDs not in cache
    uncached_ids = set()
    for entry in entries:
        task = entry.get("task", {}) or {}
        tid = task.get("id")
        if tid and tid not in cached_tasks:
            uncached_ids.add(tid)

    # Fetch uncached tasks individually (sequential to avoid rate limits)
    if uncached_ids:
        for tid in uncached_ids:
            try:
                task_data = await clickup_client.get_task(tid)
                project_name, _rate_info = _resolve_project(task_data, project_rates)
                cached_tasks[tid] = {
                    "project": project_name,
                    "task_name": task_data.get("name", "Unknown"),
                }
            except Exception as e:
                logger.warning("Failed to fetch task %s: %s", tid, e)
        cache["tasks"] = cached_tasks
        _save_task_cache(cache)

    by_project: dict[str, dict] = {}
    for entry in entries:
        task = entry.get("task", {}) or {}
        task_name = task.get("name", "Unknown")
        tid = task.get("id")

        if tid and tid in cached_tasks:
            project_name = cached_tasks[tid]["project"]
            task_name = cached_tasks[tid].get("task_name", task_name)
        else:
            project_name = "Unassigned"

        # Look up rate from project_rates by name
        rate_info = _NO_RATE
        for info in project_rates.get("by_id", {}).values():
            if info["name"] == project_name:
                rate_info = info
                break

        duration_ms = int(entry.get("duration", 0))
        hours = round(duration_ms / 3600000, 2)

        if project_name not in by_project:
            by_project[project_name] = {
                "hours": 0,
                "rate": rate_info.get("rate", 0),
                "amount": 0,
                "retainer": rate_info.get("retainer", 0),
                "ceiling": rate_info.get("ceiling", 0),
                "tasks": [],
            }
        by_project[project_name]["hours"] += hours
        by_project[project_name]["amount"] = round(
            by_project[project_name]["hours"] * by_project[project_name]["rate"], 2
        )
        by_project[project_name]["tasks"].append({
            "name": task_name,
            "hours": hours,
        })

    return {
        "time_entries": by_project,
        "task_cache_synced": cache.get("last_synced"),
    }


def _load_project_rates() -> dict[str, dict]:
    """Load Project dropdown options from clickup-fields.yaml.
    Returns {"by_id": {uuid: info}, "by_orderindex": {int: info}}."""
    import yaml
    from app.config import DATA_DIR

    path = DATA_DIR / "clickup-fields.yaml"
    if not path.exists():
        return {"by_id": {}, "by_orderindex": {}}
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    for field in data.get("custom_fields", []):
        if field.get("name") == "Project":
            by_id = {}
            by_orderindex = {}
            for opt in field.get("options", []):
                info = {
                    "name": opt["name"],
                    "rate": opt.get("rate", 0),
                    "ceiling": opt.get("ceiling", 0),
                    "retainer": opt.get("retainer", 0),
                }
                by_id[opt["id"]] = info
                by_orderindex[opt.get("orderindex", -1)] = info
            return {"by_id": by_id, "by_orderindex": by_orderindex}
    return {"by_id": {}, "by_orderindex": {}}


_NO_RATE = {"rate": 0, "ceiling": 0, "retainer": 0}


def _resolve_project(task: dict, project_rates: dict) -> tuple[str, dict]:
    """Resolve a task's Project dropdown to (project_name, rate_info).
    ClickUp may return value as option UUID (str) or orderindex (int)."""
    by_id = project_rates.get("by_id", {})
    by_orderindex = project_rates.get("by_orderindex", {})

    for field in task.get("custom_fields", []):
        if field.get("name", "").lower() == "project":
            selected = field.get("value")
            if selected is None:
                break
            # Try as option UUID
            if isinstance(selected, str) and selected in by_id:
                info = by_id[selected]
                return info["name"], info
            # Try as orderindex (int or stringified int)
            try:
                idx = int(selected)
            except (ValueError, TypeError):
                idx = None
            if idx is not None and idx in by_orderindex:
                info = by_orderindex[idx]
                return info["name"], info
            # Fallback: check type_config.options from the API response itself
            for opt in field.get("type_config", {}).get("options", []):
                if opt.get("orderindex") == selected or opt.get("id") == selected:
                    return opt.get("name", "Unknown"), _NO_RATE
            break
    return "Unassigned", _NO_RATE


async def _build_task_project_map(clickup_client, project_rates: dict) -> dict[str, tuple[str, dict]]:
    """Fetch all tasks from the master list and build task_id → (project, rates).
    Uses paginated get_tasks (100/page) instead of individual get_task calls.
    Saves results to the task cache for future use."""
    result: dict[str, tuple[str, dict]] = {}
    cache_tasks: dict[str, dict] = {}
    page = 0
    while True:
        data = await clickup_client.get_tasks(page=page, include_closed=True)
        tasks = data.get("tasks", [])
        if not tasks:
            break
        for task in tasks:
            tid = task.get("id")
            if tid:
                project_name, rate_info = _resolve_project(task, project_rates)
                result[tid] = (project_name, rate_info)
                cache_tasks[tid] = {
                    "project": project_name,
                    "task_name": task.get("name", "Unknown"),
                }
        if len(tasks) < 100:
            break
        page += 1

    # Save to cache
    cache = {
        "tasks": cache_tasks,
        "last_synced": datetime.now(timezone.utc).isoformat(),
    }
    _save_task_cache(cache)

    return result


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
async def kdp_upload(
    request: Request,
    file: UploadFile = File(...),
    kdp_account: str = Form(""),
):
    ctx = _base_ctx(request, "kdp")
    try:
        content = await file.read()
        imp, records = parse_kdp_csv(
            file.filename or "upload.csv", content, kdp_account=kdp_account,
        )

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


@router.post("/kdp/delete")
async def kdp_delete(request: Request, import_id: str = Form("")):
    """Delete a KDP import and all its records."""
    if import_id:
        revenue_store.remove_import(import_id)
    ctx = _base_ctx(request, "kdp")
    ctx["imports"] = revenue_store.get_kdp_imports()
    return templates.TemplateResponse("revenue/kdp.html", ctx)


@router.post("/kdp/export-range")
async def kdp_export_range(
    request: Request,
    start_month: str = Form(""),
    end_month: str = Form(""),
):
    """Export all KDP records in a date range as Transactions rows."""
    ctx = _base_ctx(request, "kdp")
    if not start_month or not end_month:
        ctx["error"] = "Both start and end month are required."
        ctx["imports"] = revenue_store.get_kdp_imports()
        return templates.TemplateResponse("revenue/_kdp_partial.html", ctx)

    records = revenue_store.get_kdp_records(
        start_month=start_month, end_month=end_month,
    )
    tx_rows = transform_to_transactions(records)
    ctx["tx_rows"] = tx_rows
    ctx["tx_tsv"] = export_transactions_tsv(tx_rows)
    ctx["records"] = records
    ctx["export_range"] = f"{start_month} to {end_month}"
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


# --- YNAB ---

@router.get("/ynab")
async def ynab_page(request: Request):
    ctx = _base_ctx(request, "ynab")
    ctx["start_date"] = "2025-01-01"
    ctx["end_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return templates.TemplateResponse("revenue/ynab.html", ctx)


@router.post("/ynab/refresh")
async def ynab_refresh(
    request: Request,
    start: str = Form("2025-01-01"),
    end: str = Form(""),
):
    ctx = _base_ctx(request, "ynab")
    if not end:
        end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ctx["start_date"] = start
    ctx["end_date"] = end

    try:
        from app.services.ynab_client import ynab_client, YnabAuthError, YnabRateLimitError

        if not ynab_client.is_configured:
            ctx["error"] = "YNAB API token not configured. Add YNAB_API_TOKEN to secrets.env."
            return templates.TemplateResponse("revenue/_ynab_partial.html", ctx)

        # Fetch categories to find IDs belonging to "Lingua Ink" group
        cat_data = await ynab_client.get_categories(YNAB_BUDGET_ID)
        cat_groups = cat_data.get("data", {}).get("category_groups", [])
        li_category_ids: set[str] = set()
        cat_id_to_name: dict[str, str] = {}
        for group in cat_groups:
            if group.get("name") == YNAB_CATEGORY_GROUP:
                for cat in group.get("categories", []):
                    li_category_ids.add(cat["id"])
                    cat_id_to_name[cat["id"]] = cat.get("name", "Uncategorized")
                break

        data = await ynab_client.get_transactions(YNAB_BUDGET_ID, since_date=start)
        transactions = data.get("data", {}).get("transactions", [])

        # Filter to Lingua Ink categories and date range
        filtered = [
            t for t in transactions
            if t.get("category_id") in li_category_ids
            and t.get("date", "") <= end
        ]

        # Aggregate milliunits per category, tracking inflows/outflows separately
        by_category: dict[str, dict[str, int]] = {}
        for t in filtered:
            cat = cat_id_to_name.get(t.get("category_id", ""), t.get("category_name", "Uncategorized"))
            if cat not in by_category:
                by_category[cat] = {"inflow": 0, "outflow": 0}
            amt = t.get("amount", 0)
            if amt >= 0:
                by_category[cat]["inflow"] += amt
            else:
                by_category[cat]["outflow"] += amt

        # Split by category name: 💵-prefixed categories are income, rest are expenses
        income_cats = {}
        expense_cats = {}
        for cat, totals in sorted(by_category.items()):
            if cat.lstrip().startswith("\U0001f4b5"):  # 💵
                income_cats[cat] = totals
            else:
                expense_cats[cat] = totals

        # Group expenses by emoji prefix (first character if emoji, else "Other")
        expense_groups: dict[str, list[tuple[str, float]]] = {}
        for cat, totals in expense_cats.items():
            net_dollars = round((totals["inflow"] + totals["outflow"]) / 1000, 2)
            stripped = cat.lstrip()
            if stripped and ord(stripped[0]) > 127:
                prefix = stripped[0]
                display_name = stripped[1:].strip()
            else:
                prefix = ""
                display_name = stripped

            group = _emoji_group_name(prefix) if prefix else "Other"
            expense_groups.setdefault(group, []).append((display_name, net_dollars))

        # Income categories with inflow/outflow/total breakdown
        clean_income = []
        for cat, totals in income_cats.items():
            inflow = round(totals["inflow"] / 1000, 2)
            outflow = round(totals["outflow"] / 1000, 2)
            net = round((totals["inflow"] + totals["outflow"]) / 1000, 2)
            stripped = cat.lstrip()
            if stripped and ord(stripped[0]) > 127:
                display_name = stripped[1:].strip()
            else:
                display_name = stripped
            clean_income.append((display_name, inflow, outflow, net))

        income_total = round(sum(row[1] for row in clean_income), 2)
        income_expenses = round(sum(row[2] for row in clean_income), 2)
        income_net = round(sum(row[3] for row in clean_income), 2)
        expense_total = round(sum(
            (t["inflow"] + t["outflow"]) / 1000 for t in expense_cats.values()
        ), 2)
        net_total = round(income_net + expense_total, 2)

        # Compute expense group subtotals
        expense_group_data = {}
        for group, items in sorted(expense_groups.items()):
            subtotal = round(sum(d for _, d in items), 2)
            expense_group_data[group] = {
                "items": sorted(items, key=lambda x: x[1]),
                "subtotal": subtotal,
            }

        ctx["income"] = clean_income
        ctx["income_total"] = income_total
        ctx["income_expenses"] = income_expenses
        ctx["income_net"] = income_net
        ctx["expense_groups"] = expense_group_data
        ctx["expense_total"] = expense_total
        ctx["net_total"] = net_total
        ctx["tx_count"] = len(filtered)

    except YnabAuthError:
        ctx["error"] = "YNAB authentication failed. Check your API token."
    except YnabRateLimitError:
        ctx["error"] = "YNAB rate limit reached. Try again in a minute."
    except Exception as e:
        logger.exception("YNAB fetch failed")
        ctx["error"] = f"Failed to fetch YNAB data: {e}"

    return templates.TemplateResponse("revenue/_ynab_partial.html", ctx)


@router.post("/ynab/recurring")
async def ynab_recurring(request: Request):
    """Detect recurring monthly fees from YNAB expense transactions."""
    ctx = _base_ctx(request, "ynab")

    try:
        from app.services.ynab_client import ynab_client, YnabAuthError, YnabRateLimitError

        if not ynab_client.is_configured:
            ctx["recurring_error"] = "YNAB API token not configured."
            return templates.TemplateResponse("revenue/_ynab_recurring_partial.html", ctx)

        # Fetch 6 months of data to detect patterns
        lookback = datetime.now(timezone.utc) - timedelta(days=180)
        start = lookback.strftime("%Y-%m-%d")

        cat_data = await ynab_client.get_categories(YNAB_BUDGET_ID)
        cat_groups = cat_data.get("data", {}).get("category_groups", [])
        li_category_ids: set[str] = set()
        cat_id_to_name: dict[str, str] = {}
        for group in cat_groups:
            if group.get("name") == YNAB_CATEGORY_GROUP:
                for cat in group.get("categories", []):
                    li_category_ids.add(cat["id"])
                    cat_id_to_name[cat["id"]] = cat.get("name", "Uncategorized")
                break

        data = await ynab_client.get_transactions(YNAB_BUDGET_ID, since_date=start)
        transactions = data.get("data", {}).get("transactions", [])

        # Filter to LI expense categories (not income/💵-prefixed)
        expense_txs = []
        for t in transactions:
            cid = t.get("category_id")
            if cid not in li_category_ids:
                continue
            cat_name = cat_id_to_name.get(cid, "")
            if cat_name.lstrip().startswith("\U0001f4b5"):
                continue  # skip income categories
            amt = t.get("amount", 0)
            if amt >= 0:
                continue  # skip inflows/refunds
            expense_txs.append(t)

        # Group by payee → {payee: {months: set, total: int, count: int, category: str, last_date: str}}
        by_payee: dict[str, dict] = {}
        for t in expense_txs:
            payee = t.get("payee_name", "Unknown") or "Unknown"
            date_str = t.get("date", "")
            month_key = date_str[:7]  # YYYY-MM
            cat_name = cat_id_to_name.get(t.get("category_id", ""), "")

            if payee not in by_payee:
                by_payee[payee] = {
                    "months": set(),
                    "total_milliunits": 0,
                    "count": 0,
                    "category": cat_name,
                    "last_date": "",
                }
            by_payee[payee]["months"].add(month_key)
            by_payee[payee]["total_milliunits"] += t.get("amount", 0)
            by_payee[payee]["count"] += 1
            if date_str > by_payee[payee]["last_date"]:
                by_payee[payee]["last_date"] = date_str

        # Filter to recurring (2+ distinct months) and compute monthly average
        recurring = []
        for payee, info in by_payee.items():
            n_months = len(info["months"])
            if n_months < 2:
                continue
            total_abs = abs(info["total_milliunits"])
            monthly_avg = round(total_abs / n_months / 1000, 2)
            # Clean category name (strip emoji prefix)
            cat_display = info["category"].lstrip()
            if cat_display and ord(cat_display[0]) > 127:
                cat_display = cat_display[1:].strip()
                # Strip subcategory group prefix if present
                if ":" in cat_display:
                    cat_display = cat_display.split(":", 1)[1].strip()

            recurring.append({
                "payee": payee,
                "category": cat_display,
                "monthly_avg": monthly_avg,
                "months_seen": n_months,
                "last_date": info["last_date"],
                "total": round(total_abs / 1000, 2),
            })

        recurring.sort(key=lambda r: r["monthly_avg"], reverse=True)
        monthly_total = round(sum(r["monthly_avg"] for r in recurring), 2)

        ctx["recurring"] = recurring
        ctx["recurring_total"] = monthly_total
        ctx["recurring_months"] = 6

    except YnabAuthError:
        ctx["recurring_error"] = "YNAB authentication failed."
    except YnabRateLimitError:
        ctx["recurring_error"] = "YNAB rate limit reached."
    except Exception as e:
        logger.exception("YNAB recurring fetch failed")
        ctx["recurring_error"] = f"Failed: {e}"

    return templates.TemplateResponse("revenue/_ynab_recurring_partial.html", ctx)


def _emoji_group_name(emoji: str) -> str:
    """Map emoji prefixes to human-readable group names."""
    mapping = {
        "\U0001f4cb": "Administrative",     # clipboard
        "\U0001f4c4": "Administrative",     # page facing up
        "\U0001f4dd": "Administrative",     # memo
        "\U0001f4e3": "Marketing",          # megaphone
        "\U0001f4e2": "Marketing",          # loudspeaker
        "\U0001f4f0": "Marketing",          # newspaper
        "\U0001f528": "Operational",        # hammer
        "\U0001f527": "Operational",        # wrench
        "\U0001f6e0": "Operational",        # hammer and wrench
        "\u2699": "Operational",            # gear
        "\U0001f4da": "Publishing",         # books
        "\U0001f4d6": "Publishing",         # open book
        "\U0001f4d3": "Publishing",         # notebook
        "\U0001f58a": "Publishing",         # pen
        "\U0001f58d": "Publishing",         # crayon
        "\U0001f4b0": "Income",             # money bag
        "\U0001f4b5": "Income",             # dollar
        "\U0001f4b3": "Payments",           # credit card
        "\U0001f3e2": "Business",           # office building
        "\U0001f4bb": "Technology",         # laptop
        "\U0001f310": "Technology",         # globe
    }
    return mapping.get(emoji, "Other")


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
