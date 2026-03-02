"""Pydantic models for ClickUp task management."""

from datetime import date, datetime
from pydantic import BaseModel, Field


class FieldOption(BaseModel):
    name: str
    id: str
    color: str = ""
    orderindex: int = 0


class CustomFieldValue(BaseModel):
    field_id: str
    field_name: str
    value_id: str | None = None
    value_name: str | None = None


class TaskCreateInput(BaseModel):
    name: str
    due_date: date
    description: str = ""


class InferredFields(BaseModel):
    project: FieldOption | None = None
    project_confident: bool = False
    effort: FieldOption | None = None
    revenue: FieldOption | None = None
    scope: FieldOption | None = None
    approach: FieldOption | None = None
    readiness: FieldOption | None = None


class TaskPreview(BaseModel):
    name: str
    due_date: date
    description: str = ""
    project: FieldOption | None = None
    effort: FieldOption | None = None
    revenue: FieldOption | None = None
    scope: FieldOption | None = None
    approach: FieldOption | None = None
    readiness: FieldOption | None = None


class ClickUpTask(BaseModel):
    id: str
    name: str
    status: str = ""
    status_color: str = ""
    due_date: datetime | None = None
    date_created: datetime | None = None
    description: str = ""
    url: str = ""
    project: str = ""
    effort: str = ""
    revenue: str = ""
    scope: str = ""
    approach: str = ""
    readiness: str = ""
    is_overdue: bool = False


class TaskFilters(BaseModel):
    project: str = ""
    status: str = ""
    effort: str = ""
    revenue: str = ""
    scope: str = ""
    approach: str = ""
    readiness: str = ""
    search: str = ""
    sort_by: str = "due_date"
    overdue_only: bool = False


class WeeklyReport(BaseModel):
    week_start: date
    week_end: date
    completed_count: int = 0
    overdue_count: int = 0
    created_count: int = 0
    total_active: int = 0
    by_project: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)
    by_approach: dict[str, int] = Field(default_factory=dict)
    by_revenue: dict[str, int] = Field(default_factory=dict)
    overdue_tasks: list[ClickUpTask] = Field(default_factory=list)
