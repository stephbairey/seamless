"""JSON persistence for revenue data — KDP imports, royalty reports,
consignment, manual entries, recurring costs."""

import fcntl
import json
import logging
from pathlib import Path

from app.config import DATA_DIR
from app.models.revenue import (
    ConsignmentEntry,
    KdpImport,
    KdpRecord,
    RecurringCost,
    RevenueEntry,
    RoyaltyReport,
)

logger = logging.getLogger(__name__)

REVENUE_FILE = DATA_DIR / "revenue.json"

DEFAULT_COSTS = [
    {"label": "Software subscriptions", "amount": 225.0, "frequency": "monthly"},
    {"label": "Hosting", "amount": 12.0, "frequency": "monthly"},
    {"label": "Virtual mailbox", "amount": 10.0, "frequency": "monthly"},
]


class RevenueStore:
    def __init__(self, path: Path = REVENUE_FILE):
        self._path = path
        self._data: dict = {}
        self._loaded = False

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path) as f:
                    fcntl.flock(f, fcntl.LOCK_SH)
                    self._data = json.load(f)
                    fcntl.flock(f, fcntl.LOCK_UN)
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to read revenue store: %s", e)
                self._data = {}
        else:
            self._data = {}
        # Ensure all top-level keys exist
        for key in ("kdp_imports", "kdp_records", "royalty_reports",
                     "consignment", "revenue_entries", "recurring_costs"):
            if key not in self._data:
                self._data[key] = []
        if not self._data["recurring_costs"]:
            self._data["recurring_costs"] = list(DEFAULT_COSTS)
        self._backfill_kdp_imports()
        self._loaded = True

    def _backfill_kdp_imports(self):
        """One-time migration: add kdp_account and date_range to old imports."""
        import re
        date_re = re.compile(r"-(\d{4})-(\d{2})-\d{2}-")
        # Build set of author names per import_id
        authors_by_import: dict[str, set[str]] = {}
        for rec in self._data.get("kdp_records", []):
            iid = rec.get("import_id", "")
            name = rec.get("author_name", "").lower().strip()
            if iid and name:
                authors_by_import.setdefault(iid, set()).add(name)

        bairey_authors = {"maya bairey", "sulima malzin"}
        dirty = False
        for imp in self._data.get("kdp_imports", []):
            # Backfill date_range from filename
            if not imp.get("date_range"):
                m = date_re.search(imp.get("filename", ""))
                if m:
                    imp["date_range"] = f"{m.group(1)}-{m.group(2)}"
                    dirty = True
            # Backfill kdp_account
            if not imp.get("kdp_account"):
                authors = authors_by_import.get(imp.get("id", ""), set())
                if not authors:
                    imp["kdp_account"] = "bairey.com"
                    dirty = True
                elif authors <= bairey_authors:
                    imp["kdp_account"] = "bairey.com"
                    dirty = True
                elif authors.isdisjoint(bairey_authors):
                    imp["kdp_account"] = "Lingua Ink Books"
                    dirty = True
        if dirty:
            self._save()

    def _ensure_loaded(self):
        if not self._loaded:
            self._load()

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(self._data, f, indent=2, default=str)
            fcntl.flock(f, fcntl.LOCK_UN)

    # --- KDP Imports ---

    def add_kdp_import(self, imp: KdpImport, records: list[KdpRecord]):
        self._ensure_loaded()
        self._data["kdp_imports"].append(json.loads(imp.model_dump_json()))
        for rec in records:
            self._data["kdp_records"].append(json.loads(rec.model_dump_json()))
        self._save()

    def get_kdp_imports(self) -> list[KdpImport]:
        self._ensure_loaded()
        return [KdpImport(**d) for d in self._data["kdp_imports"]]

    def get_kdp_records(
        self, quarter: str = "", author: str = "",
        start_month: str = "", end_month: str = "",
    ) -> list[KdpRecord]:
        """Filter KDP records. quarter='2026-Q1' matches months 01-03.
        start_month/end_month are YYYY-MM strings for range filtering."""
        self._ensure_loaded()
        records = [KdpRecord(**d) for d in self._data["kdp_records"]]
        if quarter:
            months = _quarter_months(quarter)
            records = [r for r in records if r.royalty_date in months]
        if start_month:
            records = [r for r in records if r.royalty_date >= start_month]
        if end_month:
            records = [r for r in records if r.royalty_date <= end_month]
        if author:
            author_lower = author.lower()
            records = [r for r in records if r.author_name.lower() == author_lower]
        return records

    def has_duplicate_records(self, records: list[KdpRecord]) -> list[str]:
        """Check for existing records matching (royalty_date, title, author_name,
        format, marketplace, units_sold, royalty_amount). Returns list of duplicate descriptions."""
        self._ensure_loaded()
        existing = set()
        for d in self._data["kdp_records"]:
            key = (d.get("royalty_date", ""), d.get("title", ""),
                   d.get("author_name", ""), d.get("format", ""),
                   d.get("marketplace", ""),
                   d.get("units_sold", 0), d.get("royalty_amount", 0.0))
            existing.add(key)
        dupes = []
        for r in records:
            key = (r.royalty_date, r.title, r.author_name,
                   r.format, r.marketplace,
                   r.units_sold, r.royalty_amount)
            if key in existing:
                dupes.append(f"{r.title} ({r.royalty_date}, {r.marketplace})")
        return dupes

    def remove_import(self, import_id: str):
        """Remove an import and its records (for re-upload)."""
        self._ensure_loaded()
        self._data["kdp_imports"] = [
            d for d in self._data["kdp_imports"] if d.get("id") != import_id
        ]
        self._data["kdp_records"] = [
            d for d in self._data["kdp_records"] if d.get("import_id") != import_id
        ]
        self._save()

    # --- Royalty Reports ---

    def save_royalty_report(self, report: RoyaltyReport):
        self._ensure_loaded()
        # Replace existing for same author+quarter
        self._data["royalty_reports"] = [
            d for d in self._data["royalty_reports"]
            if not (d.get("author_name") == report.author_name
                    and d.get("quarter") == report.quarter)
        ]
        self._data["royalty_reports"].append(json.loads(report.model_dump_json()))
        self._save()

    def list_royalty_reports(self) -> list[RoyaltyReport]:
        self._ensure_loaded()
        return [RoyaltyReport(**d) for d in self._data["royalty_reports"]]

    def get_royalty_report(self, report_id: str) -> RoyaltyReport | None:
        self._ensure_loaded()
        for d in self._data["royalty_reports"]:
            if d.get("id") == report_id:
                return RoyaltyReport(**d)
        return None

    def update_report_status(self, report_id: str, status: str) -> bool:
        self._ensure_loaded()
        for d in self._data["royalty_reports"]:
            if d.get("id") == report_id:
                d["status"] = status
                self._save()
                return True
        return False

    # --- Consignment ---

    def get_consignment(self) -> list[ConsignmentEntry]:
        self._ensure_loaded()
        return [ConsignmentEntry(**d) for d in self._data["consignment"]]

    def save_consignment_entry(self, entry: ConsignmentEntry):
        self._ensure_loaded()
        # Replace if same id exists
        self._data["consignment"] = [
            d for d in self._data["consignment"] if d.get("id") != entry.id
        ]
        self._data["consignment"].append(json.loads(entry.model_dump_json()))
        self._save()

    def add_consignment_entry(self, entry: ConsignmentEntry):
        self._ensure_loaded()
        self._data["consignment"].append(json.loads(entry.model_dump_json()))
        self._save()

    # --- Revenue Entries ---

    def add_revenue_entry(self, entry: RevenueEntry):
        self._ensure_loaded()
        self._data["revenue_entries"].append(json.loads(entry.model_dump_json()))
        self._save()

    def get_revenue_entries(self, start: str = "", end: str = "") -> list[RevenueEntry]:
        """Filter by date range (YYYY-MM-DD strings, inclusive)."""
        self._ensure_loaded()
        entries = [RevenueEntry(**d) for d in self._data["revenue_entries"]]
        if start:
            entries = [e for e in entries if e.date >= start]
        if end:
            entries = [e for e in entries if e.date <= end]
        return entries

    # --- Recurring Costs ---

    def get_recurring_costs(self) -> list[RecurringCost]:
        self._ensure_loaded()
        return [RecurringCost(**d) for d in self._data["recurring_costs"]]

    def save_recurring_costs(self, costs: list[RecurringCost]):
        self._ensure_loaded()
        self._data["recurring_costs"] = [
            json.loads(c.model_dump_json()) for c in costs
        ]
        self._save()

    def reload(self):
        self._loaded = False
        self._load()


def _quarter_months(quarter: str) -> list[str]:
    """Convert '2026-Q1' to ['2026-01', '2026-02', '2026-03']."""
    try:
        year, q = quarter.split("-Q")
        q_num = int(q)
        start_month = (q_num - 1) * 3 + 1
        return [f"{year}-{m:02d}" for m in range(start_month, start_month + 3)]
    except (ValueError, IndexError):
        return []


# Shared instance
revenue_store = RevenueStore()
