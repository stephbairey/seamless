"""File routing engine — scan intake, resolve destinations, move files."""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.config import GDRIVE_DIR, INTAKE_DIR, SORT_LOG_FILE
from app.models.files import IntakeFile, ParsedTags, RouteResult, SortReport
from app.services.tag_parser import tag_parser
from app.services.yaml_store import yaml_store

logger = logging.getLogger(__name__)
TZ = ZoneInfo("America/Los_Angeles")

MAX_HISTORY = 100


class FileRouterService:
    """Scan MAGIC SORT intake, resolve routes, move files to Google Drive."""

    @property
    def is_configured(self) -> bool:
        return INTAKE_DIR.is_dir() and GDRIVE_DIR.is_dir()

    @property
    def intake_ready(self) -> bool:
        return INTAKE_DIR.is_dir()

    @property
    def gdrive_ready(self) -> bool:
        return GDRIVE_DIR.is_dir()

    def get_routing_config(self) -> dict[str, Any]:
        return yaml_store.read("file-routing-rules.yaml")

    def scan_intake(self) -> list[IntakeFile]:
        """List files in /intake top-level. Skip .ts dirs and hidden files."""
        if not INTAKE_DIR.is_dir():
            return []

        files = []
        for entry in sorted(INTAKE_DIR.iterdir()):
            # Skip hidden files/dirs
            if entry.name.startswith("."):
                continue

            # Skip .ts folders (TagSpaces metadata)
            if entry.is_dir() and entry.suffix == ".ts":
                continue

            # Skip directories entirely — only route files
            if entry.is_dir():
                continue

            tags = tag_parser.parse(entry.name)
            clean = tag_parser.strip_tags(entry.stem)
            stat = entry.stat()

            files.append(IntakeFile(
                filename=entry.name,
                clean_name=clean + entry.suffix if clean else entry.name,
                extension=entry.suffix,
                size_bytes=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime, tz=TZ),
                tags=tags,
                in_ts_folder=False,
            ))

        return files

    def resolve_route(self, file: IntakeFile) -> RouteResult:
        """Determine where a file should go based on its tags.

        Priority:
        1. No tags -> unroutable
        2. No client tag -> unroutable
        3. Book content tag + project tag -> book folder
        4. Content tag -> mapped subfolder
        5. Project tag alone -> book folder
        6. No content/project match -> Unsorted
        """
        config = self.get_routing_config()
        clients = config.get("clients", {})
        default_routes = config.get("default_content_routes", {})
        book_tags = [t.lower() for t in config.get("default_book_content_tags", [])]

        # No tags at all
        if not file.tags:
            return RouteResult(file=file, routed=False, reason="No tags found")

        # No client tag
        if not file.tags.client_tag:
            return RouteResult(file=file, routed=False, reason="No client tag")

        # Look up client config
        client_cfg = clients.get(file.tags.client_tag)
        if not client_cfg:
            return RouteResult(
                file=file, routed=False,
                reason=f"Client '{file.tags.client_tag}' not in config",
            )

        client_folder = client_cfg["folder"]
        projects = client_cfg.get("projects") or {}
        overrides = client_cfg.get("overrides") or {}
        unsorted = client_cfg.get("unsorted", "Unsorted")

        # Build effective content route map (defaults + overrides)
        effective_routes = dict(default_routes)
        effective_routes.update(overrides)

        # Resolve project folder name if we have a project tag
        project_folder = None
        if file.tags.project_tag:
            # Case-insensitive project lookup
            for proj_key, proj_val in projects.items():
                if proj_key.lower() == file.tags.project_tag.lower():
                    project_folder = proj_val
                    break

        subfolder = None
        reason = ""

        # Check content tags for routing
        for ctag in file.tags.content_tags:
            ctag_lower = ctag.lower()

            # Book content tag (Cover, Interior, Info) — needs project
            if ctag_lower in book_tags:
                if project_folder:
                    subfolder = project_folder
                    reason = f"Book content tag '{ctag}' + project -> {project_folder}"
                    break
                else:
                    # Book tag without project — still route to client unsorted
                    continue

            # Regular content tag — check effective routes (case-insensitive)
            for route_key, route_val in effective_routes.items():
                if route_key.lower() == ctag_lower:
                    subfolder = route_val
                    reason = f"Content tag '{ctag}' -> {route_val}"
                    break
            if subfolder:
                break

        # If no content tag matched, try project tag alone
        if not subfolder and project_folder:
            subfolder = project_folder
            reason = f"Project tag '{file.tags.project_tag}' -> {project_folder}"

        # Fallback to Unsorted
        if not subfolder:
            subfolder = unsorted
            reason = f"No routing match -> {unsorted}"

        dest = Path(GDRIVE_DIR) / client_folder / subfolder
        dest_path = str(dest)

        return RouteResult(
            file=file,
            routed=True,
            destination_path=dest_path,
            client_folder=client_folder,
            subfolder=subfolder,
            reason=reason,
        )

    def move_file(self, file: IntakeFile, route: RouteResult) -> RouteResult:
        """Move file from intake to destination. Strip tags from filename."""
        if not route.routed or not route.destination_path:
            return route

        dest_dir = Path(route.destination_path)
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            route.routed = False
            route.error = f"Cannot create directory: {e}"
            return route

        # Destination filename: tags stripped
        dest_name = file.clean_name
        dest_file = dest_dir / dest_name

        # Handle duplicates with (1), (2) suffix
        if dest_file.exists():
            stem = dest_file.stem
            suffix = dest_file.suffix
            counter = 1
            while dest_file.exists():
                dest_file = dest_dir / f"{stem} ({counter}){suffix}"
                counter += 1

        source = INTAKE_DIR / file.filename
        try:
            shutil.move(str(source), str(dest_file))
            route.reason += f" | Moved as '{dest_file.name}'"
        except OSError as e:
            route.routed = False
            route.error = f"Move failed: {e}"

        return route

    def preview_all(self) -> SortReport:
        """Dry-run: scan and resolve all files without moving."""
        files = self.scan_intake()
        results = []
        unroutable = []
        skipped_ts = 0

        for f in files:
            if f.in_ts_folder:
                skipped_ts += 1
                continue
            route = self.resolve_route(f)
            if route.routed:
                results.append(route)
            else:
                unroutable.append(route)

        return SortReport(
            timestamp=datetime.now(tz=TZ),
            total_files=len(files),
            routed_count=len(results),
            unroutable_count=len(unroutable),
            skipped_ts=skipped_ts,
            results=results,
            unroutable=unroutable,
        )

    def sort_all(self) -> SortReport:
        """Scan, route, and move all files in intake."""
        files = self.scan_intake()
        results = []
        unroutable = []
        errors = []
        skipped_ts = 0

        for f in files:
            if f.in_ts_folder:
                skipped_ts += 1
                continue

            route = self.resolve_route(f)
            if not route.routed:
                unroutable.append(route)
                continue

            route = self.move_file(f, route)
            if route.error:
                errors.append(route)
            else:
                results.append(route)

        report = SortReport(
            timestamp=datetime.now(tz=TZ),
            total_files=len(files),
            routed_count=len(results),
            unroutable_count=len(unroutable),
            skipped_ts=skipped_ts,
            error_count=len(errors),
            results=results,
            unroutable=unroutable,
            errors=errors,
        )

        self._save_history(report)
        return report

    def _save_history(self, report: SortReport):
        """Append sort report to history log (capped at MAX_HISTORY)."""
        history = self.get_history()

        entry = {
            "timestamp": report.timestamp.isoformat(),
            "total_files": report.total_files,
            "routed": report.routed_count,
            "unroutable": report.unroutable_count,
            "errors": report.error_count,
            "skipped_ts": report.skipped_ts,
            "files": [
                {
                    "filename": r.file.filename,
                    "clean_name": r.file.clean_name,
                    "destination": r.destination_path,
                    "client": r.client_folder,
                    "subfolder": r.subfolder,
                    "reason": r.reason,
                }
                for r in report.results
            ],
            "unroutable_files": [
                {"filename": r.file.filename, "reason": r.reason}
                for r in report.unroutable
            ],
            "error_files": [
                {"filename": r.file.filename, "error": r.error}
                for r in report.errors
            ],
        }

        history.insert(0, entry)
        history = history[:MAX_HISTORY]

        try:
            with open(SORT_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except OSError as e:
            logger.error("Failed to save sort history: %s", e)

    def get_history(self) -> list[dict]:
        """Read sort history from log file."""
        if not SORT_LOG_FILE.exists():
            return []
        try:
            with open(SORT_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def add_client(self, tag: str, folder: str) -> bool:
        """Add a new client to routing config. Returns True on success."""
        config = self.get_routing_config()
        clients = config.get("clients", {})
        client_tags = config.get("client_tags", [])

        if tag in clients:
            return False

        clients[tag] = {
            "folder": folder,
            "projects": {},
            "overrides": {},
            "unsorted": "Unsorted",
        }
        if tag not in client_tags:
            client_tags.append(tag)

        config["clients"] = clients
        config["client_tags"] = client_tags
        yaml_store.write("file-routing-rules.yaml", config)
        tag_parser.reload()
        return True

    def add_project(self, client_tag: str, project_tag: str, book_folder: str) -> bool:
        """Add a project to a client. Returns True on success."""
        config = self.get_routing_config()
        clients = config.get("clients", {})

        if client_tag not in clients:
            return False

        projects = clients[client_tag].get("projects") or {}
        if project_tag in projects:
            return False

        projects[project_tag] = book_folder
        clients[client_tag]["projects"] = projects
        config["clients"] = clients
        yaml_store.write("file-routing-rules.yaml", config)
        tag_parser.reload()
        return True


# Shared instance
file_router = FileRouterService()
