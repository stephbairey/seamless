"""Pydantic models for file management."""

from datetime import datetime

from pydantic import BaseModel


class ParsedTags(BaseModel):
    raw_bracket: str  # original [...] content
    client_tag: str | None = None
    project_tag: str | None = None
    content_tags: list[str] = []
    all_tags: list[str] = []


class IntakeFile(BaseModel):
    filename: str
    clean_name: str  # filename with tags stripped
    extension: str
    size_bytes: int
    modified: datetime
    tags: ParsedTags | None = None
    in_ts_folder: bool = False


class RouteResult(BaseModel):
    file: IntakeFile
    routed: bool = False
    destination_path: str | None = None
    client_folder: str | None = None
    subfolder: str | None = None
    reason: str = ""
    error: str | None = None


class SortReport(BaseModel):
    timestamp: datetime
    total_files: int = 0
    routed_count: int = 0
    unroutable_count: int = 0
    skipped_ts: int = 0
    error_count: int = 0
    results: list[RouteResult] = []
    unroutable: list[RouteResult] = []
    errors: list[RouteResult] = []
