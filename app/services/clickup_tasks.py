"""Task business logic — creation, listing, filtering, reporting."""

import logging
from datetime import date, datetime, timedelta, timezone

from app.models.clickup import (
    ClickUpTask, FieldOption, TaskFilters, WeeklyReport,
)
from app.services.clickup_client import clickup_client
from app.services.clickup_fields import clickup_fields

logger = logging.getLogger(__name__)


def _build_custom_fields(project: FieldOption | None, effort: FieldOption | None,
                         revenue: FieldOption | None, scope: FieldOption | None,
                         approach: FieldOption | None, readiness: FieldOption | None) -> list[dict]:
    """Build the custom_fields array for the ClickUp API."""
    fields = []
    mapping = [
        ("Project", project),
        ("Effort", effort),
        ("Revenue", revenue),
        ("Scope", scope),
        ("Approach", approach),
        ("Readiness", readiness),
    ]
    for field_name, option in mapping:
        if option:
            fid = clickup_fields.field_id(field_name)
            if fid:
                fields.append({"id": fid, "value": option.id})
    return fields


async def create_task(name: str, due_date: date, description: str,
                      project: FieldOption | None, effort: FieldOption | None,
                      revenue: FieldOption | None, scope: FieldOption | None,
                      approach: FieldOption | None, readiness: FieldOption | None) -> dict:
    """Create a task in ClickUp with all custom fields."""
    custom_fields = _build_custom_fields(project, effort, revenue, scope, approach, readiness)
    due_dt = datetime.combine(due_date, datetime.min.time(), tzinfo=timezone.utc)
    return await clickup_client.create_task(
        name=name,
        due_date=due_dt,
        description=description,
        custom_fields=custom_fields,
    )


def _parse_task(raw: dict) -> ClickUpTask:
    """Parse a raw ClickUp API task into our model."""
    status = raw.get("status", {})
    status_name = status.get("status", "") if isinstance(status, dict) else str(status)
    status_color = status.get("color", "") if isinstance(status, dict) else ""

    # Parse dates
    due_date = None
    if raw.get("due_date"):
        try:
            due_date = datetime.fromtimestamp(int(raw["due_date"]) / 1000, tz=timezone.utc)
        except (ValueError, TypeError):
            pass

    date_created = None
    if raw.get("date_created"):
        try:
            date_created = datetime.fromtimestamp(int(raw["date_created"]) / 1000, tz=timezone.utc)
        except (ValueError, TypeError):
            pass

    # Parse custom fields
    field_values = {}
    for cf in raw.get("custom_fields", []):
        name = cf.get("name", "")
        value = cf.get("value")
        if isinstance(value, dict):
            # dropdown with value object
            field_values[name] = value.get("name", "")
        elif isinstance(value, int) and cf.get("type_config", {}).get("options"):
            # dropdown by orderindex
            opts = cf["type_config"]["options"]
            field_values[name] = opts[value]["name"] if value < len(opts) else ""
        elif value is not None:
            # Try to resolve option ID to name
            opts = cf.get("type_config", {}).get("options", [])
            matched = [o for o in opts if o.get("id") == value]
            field_values[name] = matched[0]["name"] if matched else str(value)
        else:
            field_values[name] = ""

    now = datetime.now(tz=timezone.utc)
    is_overdue = (
        due_date is not None
        and due_date < now
        and status_name.lower() in ("not started", "on hold", "waiting", "begun")
    )

    return ClickUpTask(
        id=raw.get("id", ""),
        name=raw.get("name", ""),
        status=status_name,
        status_color=status_color,
        due_date=due_date,
        date_created=date_created,
        description=raw.get("description", ""),
        url=raw.get("url", ""),
        project=field_values.get("Project", ""),
        effort=field_values.get("Effort", ""),
        revenue=field_values.get("Revenue", ""),
        scope=field_values.get("Scope", ""),
        approach=field_values.get("Approach", ""),
        readiness=field_values.get("Readiness", ""),
        is_overdue=is_overdue,
    )


async def list_tasks(filters: TaskFilters | None = None,
                     include_closed: bool = False) -> list[ClickUpTask]:
    """Fetch tasks from ClickUp, apply local filters, return sorted list."""
    all_tasks: list[ClickUpTask] = []
    page = 0
    while True:
        data = await clickup_client.get_tasks(page=page, include_closed=include_closed)
        raw_tasks = data.get("tasks", [])
        if not raw_tasks:
            break
        for raw in raw_tasks:
            all_tasks.append(_parse_task(raw))
        if data.get("last_page", True):
            break
        page += 1

    if filters:
        all_tasks = _apply_filters(all_tasks, filters)
        all_tasks = _sort_tasks(all_tasks, filters.sort_by)

    return all_tasks


def _apply_filters(tasks: list[ClickUpTask], f: TaskFilters) -> list[ClickUpTask]:
    result = tasks
    if f.project:
        result = [t for t in result if t.project.lower() == f.project.lower()]
    if f.status:
        result = [t for t in result if t.status.lower() == f.status.lower()]
    if f.effort:
        result = [t for t in result if t.effort.lower() == f.effort.lower()]
    if f.revenue:
        result = [t for t in result if t.revenue.lower() == f.revenue.lower()]
    if f.scope:
        result = [t for t in result if t.scope.lower() == f.scope.lower()]
    if f.approach:
        result = [t for t in result if t.approach.lower() == f.approach.lower()]
    if f.readiness:
        result = [t for t in result if t.readiness.lower() == f.readiness.lower()]
    if f.search:
        q = f.search.lower()
        result = [t for t in result if q in t.name.lower() or q in t.description.lower()]
    if f.overdue_only:
        result = [t for t in result if t.is_overdue]
    return result


_APPROACH_ORDER = {"dread": 0, "reluctant": 1, "indifferent": 2, "interested": 3, "excited": 4}


def _sort_tasks(tasks: list[ClickUpTask], sort_by: str) -> list[ClickUpTask]:
    if sort_by == "approach":
        return sorted(tasks, key=lambda t: _APPROACH_ORDER.get(t.approach.lower(), 99))
    # Default: due_date ascending, None at end
    return sorted(tasks, key=lambda t: t.due_date or datetime.max.replace(tzinfo=timezone.utc))


async def get_task(task_id: str) -> ClickUpTask:
    raw = await clickup_client.get_task(task_id)
    return _parse_task(raw)


async def update_status(task_id: str, status: str) -> dict:
    return await clickup_client.update_task_status(task_id, status)


async def bulk_update_status(task_ids: list[str], status: str) -> list[dict]:
    results = []
    for tid in task_ids:
        r = await clickup_client.update_task_status(tid, status)
        results.append(r)
    return results


async def generate_report(include_closed: bool = True) -> WeeklyReport:
    """Generate a weekly report for the current week (Mon-Sun)."""
    today = date.today()
    # Monday of current week
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    tasks = await list_tasks(include_closed=include_closed)

    report = WeeklyReport(week_start=week_start, week_end=week_end)

    ws = datetime.combine(week_start, datetime.min.time(), tzinfo=timezone.utc)
    we = datetime.combine(week_end, datetime.max.time(), tzinfo=timezone.utc)
    now = datetime.now(tz=timezone.utc)

    for t in tasks:
        # Count by project
        if t.project:
            report.by_project[t.project] = report.by_project.get(t.project, 0) + 1

        # Count by status
        if t.status:
            report.by_status[t.status] = report.by_status.get(t.status, 0) + 1

        # Count by approach (active tasks only)
        if t.approach and t.status.lower() not in ("complete", "scratch"):
            report.by_approach[t.approach] = report.by_approach.get(t.approach, 0) + 1

        # Count by revenue (active tasks only)
        if t.revenue and t.status.lower() not in ("complete", "scratch"):
            report.by_revenue[t.revenue] = report.by_revenue.get(t.revenue, 0) + 1

        # Completed this week
        if t.status.lower() == "complete" and t.due_date and ws <= t.due_date <= we:
            report.completed_count += 1

        # Overdue
        if t.is_overdue:
            report.overdue_count += 1
            report.overdue_tasks.append(t)

        # Active (not complete, not scratch)
        if t.status.lower() not in ("complete", "scratch"):
            report.total_active += 1

        # Created this week
        if t.date_created and ws <= t.date_created <= we:
            report.created_count += 1

    return report
