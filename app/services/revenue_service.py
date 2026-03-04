"""Revenue business logic — KDP CSV parsing, royalty calculation,
consignment seeding, dashboard aggregation, ClickUp time tracking."""

import csv
import io
import logging
import re
import uuid
from datetime import datetime, timezone

import yaml

from app.config import DATA_DIR
from app.models.revenue import (
    ConsignmentEntry,
    KdpImport,
    KdpRecord,
    RevenueSummary,
    RoyaltyReport,
    RoyaltySplit,
    TransactionsRow,
)
from app.services.revenue_store import revenue_store

logger = logging.getLogger(__name__)

# Column name normalization — KDP CSV headers vary across report types.
# "Prior Month Royalties" format has: Title, Author, ASIN/ISBN, Marketplace,
# Units Sold, Units Refunded, Net Units Sold or Combined KENP, Royalty Type,
# Payout Plan, Currency, Avg. List Price without tax, ..., Earnings.
# Row 1 is metadata: "Sales Period,January 2025,,,,..."
# Row 2 is actual column headers.
KDP_COLUMN_MAP = {
    # Combined Sales report columns
    "royalty date": "royalty_date",
    "title": "title",
    "author name": "author_name",
    "author": "author_name",
    "asin/isbn": "asin_isbn",
    "asin": "asin_isbn",
    "isbn": "asin_isbn",
    "marketplace": "marketplace",
    "royalty type": "royalty_type",
    "payout plan": "payout_plan",
    "transaction type": "transaction_type",
    "units sold": "units_sold",
    "units refunded": "units_refunded",
    "net units sold": "net_units",
    "net units sold or combined kenp": "net_units",
    "currency": "currency",
    "royalty": "royalty_amount",
    "earnings": "royalty_amount",
}

# KENP daily CSV columns (separate export from KDP)
KENP_COLUMN_MAP = {
    "date": "date",
    "title": "title",
    "author name": "author_name",
    "author": "author_name",
    "asin": "asin_isbn",
    "marketplace": "marketplace",
    "kenp read": "kenp_read",
    "kenp paid": "kenp_paid",
}

# Hardcoded KEEP% — what the AUTHOR keeps from earnings.
# Sulima=100% (labor of love, she keeps all), Maya=0% (Maya is the publisher),
# Carolyn=50/50, Daniela/Wren=60/40 author/publisher.
KEEP_PCT = {
    "maya bairey": 0.0,
    "sulima malzin": 1.0,
    "carolyn martin": 0.5,
    "daniela morescalchi": 0.6,
    "wren cavanagh": 0.6,
}


def parse_kdp_csv(filename: str, content_bytes: bytes) -> tuple[KdpImport, list[KdpRecord]]:
    """Parse a KDP royalty CSV. Handles three formats:
    - "Prior Month Royalties": metadata row 1 (Sales Period), headers row 2, data row 3+
    - "Combined Sales": headers row 1, data row 2+
    - "KENP Daily": Date, Title, Author Name, ASIN, Marketplace, KENP Read, KENP PAID
    """
    # Try UTF-8 first, fall back to Latin-1
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = content_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = content_bytes.decode("latin-1", errors="replace")

    import_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()

    lines = text.splitlines()
    if not lines:
        return KdpImport(id=import_id, filename=filename, uploaded_at=now), []

    # Auto-detect KENP daily CSV by checking headers for "KENP PAID"
    header_check = lines[0].lower()
    if "kenp paid" in header_check or "kenp read" in header_check:
        return _parse_kenp_csv(import_id, now, filename, lines)

    # Detect "Prior Month Royalties" format: row 1 starts with "Sales Period"
    metadata_date = ""
    header_line_idx = 0
    first_cell = lines[0].split(",")[0].strip().strip('"').lower()
    if first_cell == "sales period" and len(lines) > 1:
        # Extract date from metadata row: "Sales Period,January 2025,,,"
        parts = lines[0].split(",")
        if len(parts) > 1:
            metadata_date = parts[1].strip().strip('"')
        header_line_idx = 1

    # Parse from the header line onward
    csv_text = "\n".join(lines[header_line_idx:])
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames:
        reader.fieldnames = [h.strip() for h in reader.fieldnames]

    records: list[KdpRecord] = []
    dates_seen: set[str] = set()
    total_royalty = 0.0

    for row in reader:
        mapped = _map_row(row)
        if not mapped.get("title"):
            continue

        # Royalty date: use row value if present, else metadata row date
        raw_date = mapped.get("royalty_date", "").strip()
        if raw_date:
            royalty_date = _normalize_date(raw_date)
        elif metadata_date:
            royalty_date = _normalize_date(metadata_date)
        else:
            royalty_date = ""
        dates_seen.add(royalty_date)

        units_sold = _parse_int(mapped.get("units_sold", "0"))
        units_refunded = _parse_int(mapped.get("units_refunded", "0"))
        net_units = _parse_int(mapped.get("net_units", "0"))
        royalty_amount = _parse_float(mapped.get("royalty_amount", "0"))
        payout_plan = mapped.get("payout_plan", "").strip()
        total_royalty += royalty_amount

        record = KdpRecord(
            id=str(uuid.uuid4())[:8],
            import_id=import_id,
            royalty_date=royalty_date,
            title=mapped.get("title", "").strip(),
            author_name=mapped.get("author_name", "").strip(),
            asin_isbn=mapped.get("asin_isbn", "").strip(),
            marketplace=mapped.get("marketplace", "").strip(),
            royalty_type=mapped.get("royalty_type", "").strip(),
            payout_plan=payout_plan,
            transaction_type=mapped.get("transaction_type", "").strip(),
            format=_infer_format(payout_plan),
            units_sold=units_sold,
            units_refunded=units_refunded,
            net_units=net_units,
            royalty_amount=royalty_amount,
            currency=mapped.get("currency", "USD").strip(),
            raw_row=row,
        )
        records.append(record)

    sorted_dates = sorted(dates_seen)
    date_range = ""
    if sorted_dates:
        date_range = f"{sorted_dates[0]} to {sorted_dates[-1]}" if len(sorted_dates) > 1 else sorted_dates[0]

    imp = KdpImport(
        id=import_id,
        filename=filename,
        uploaded_at=now,
        record_count=len(records),
        date_range=date_range,
        total_royalty=round(total_royalty, 2),
    )
    return imp, records


def _parse_kenp_csv(
    import_id: str, now: str, filename: str, lines: list[str]
) -> tuple[KdpImport, list[KdpRecord]]:
    """Parse a KENP daily CSV (Date, Title, Author, ASIN, Marketplace, KENP Read, KENP PAID)."""
    csv_text = "\n".join(lines)
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames:
        reader.fieldnames = [h.strip() for h in reader.fieldnames]

    records: list[KdpRecord] = []
    dates_seen: set[str] = set()
    total_royalty = 0.0

    for row in reader:
        mapped: dict[str, str] = {}
        for raw_key, value in row.items():
            normalized = raw_key.strip().lower()
            if normalized in KENP_COLUMN_MAP:
                mapped[KENP_COLUMN_MAP[normalized]] = value

        if not mapped.get("title"):
            continue

        raw_date = mapped.get("date", "").strip()
        royalty_date = _normalize_date(raw_date) if raw_date else ""
        dates_seen.add(royalty_date)

        kenp_read = _parse_int(mapped.get("kenp_read", "0"))
        kenp_paid = _parse_float(mapped.get("kenp_paid", "0"))
        total_royalty += kenp_paid

        payout_plan = "Kindle Edition Normalized Pages (KENP)"
        record = KdpRecord(
            id=str(uuid.uuid4())[:8],
            import_id=import_id,
            royalty_date=royalty_date,
            title=mapped.get("title", "").strip(),
            author_name=mapped.get("author_name", "").strip(),
            asin_isbn=mapped.get("asin_isbn", "").strip(),
            marketplace=mapped.get("marketplace", "").strip(),
            royalty_type="",
            payout_plan=payout_plan,
            transaction_type="",
            format="Ebook",
            units_sold=kenp_read,
            units_refunded=0,
            net_units=kenp_read,
            royalty_amount=kenp_paid,
            currency="USD",
            raw_row=row,
        )
        records.append(record)

    sorted_dates = sorted(d for d in dates_seen if d)
    date_range = ""
    if sorted_dates:
        date_range = f"{sorted_dates[0]} to {sorted_dates[-1]}" if len(sorted_dates) > 1 else sorted_dates[0]

    imp = KdpImport(
        id=import_id,
        filename=filename,
        uploaded_at=now,
        record_count=len(records),
        date_range=date_range,
        total_royalty=round(total_royalty, 2),
    )
    return imp, records


def generate_royalty_reports(quarter: str) -> list[RoyaltyReport]:
    """Generate per-author royalty reports for a quarter (e.g. '2026-Q1')."""
    records = revenue_store.get_kdp_records(quarter=quarter)
    if not records:
        return []

    # Load client registry for split info
    splits_config = _load_royalty_splits()

    # Group by author
    by_author: dict[str, list[KdpRecord]] = {}
    for r in records:
        by_author.setdefault(r.author_name, []).append(r)

    now = datetime.now(timezone.utc).isoformat()
    year, q = quarter.split("-Q")
    q_num = int(q)
    start_month = f"{year}-{(q_num - 1) * 3 + 1:02d}"
    end_month = f"{year}-{(q_num - 1) * 3 + 3:02d}"

    reports: list[RoyaltyReport] = []
    for author_name, author_records in by_author.items():
        author_pct, publisher_pct = _resolve_split(author_name, splits_config)

        # Group by (title, format)
        by_title: dict[tuple[str, str], list[KdpRecord]] = {}
        for r in author_records:
            by_title.setdefault((r.title, r.format), []).append(r)

        splits: list[RoyaltySplit] = []
        total_gross = 0.0
        for (title, fmt), title_records in by_title.items():
            units = sum(r.net_units for r in title_records)
            gross = sum(r.royalty_amount for r in title_records)
            total_gross += gross

            splits.append(RoyaltySplit(
                title=title,
                format=fmt,
                author_name=author_name,
                net_units=units,
                gross_royalty=round(gross, 2),
                author_pct=author_pct,
                publisher_pct=publisher_pct,
                author_amount=round(gross * author_pct, 2),
                publisher_amount=round(gross * publisher_pct, 2),
            ))

        total_author = round(sum(s.author_amount for s in splits), 2)
        total_publisher = round(sum(s.publisher_amount for s in splits), 2)

        report = RoyaltyReport(
            id=str(uuid.uuid4())[:8],
            author_name=author_name,
            quarter=quarter,
            quarter_start=start_month,
            quarter_end=end_month,
            generated_at=now,
            splits=splits,
            total_gross=round(total_gross, 2),
            total_author=total_author,
            total_publisher=total_publisher,
            status="draft",
        )
        reports.append(report)
        revenue_store.save_royalty_report(report)

    return reports


def get_consignment_summary() -> list[ConsignmentEntry]:
    """All consignment entries sorted by venue then title."""
    entries = revenue_store.get_consignment()
    return sorted(entries, key=lambda e: (e.venue, e.title))


def init_consignment_from_registry() -> list[ConsignmentEntry]:
    """Seed consignment entries from client-registry.yaml. Only runs if
    store is empty."""
    existing = revenue_store.get_consignment()
    if existing:
        return existing

    registry = _load_client_registry()
    entries: list[ConsignmentEntry] = []

    # Publishing clients
    for client in registry.get("clients", []):
        consignment = client.get("consignment", [])
        author_name = client.get("name", "")
        books = client.get("books", [])
        for c in consignment:
            venue = c.get("venue", "")
            titles = c.get("titles", [])
            if titles == "all published":
                titles = books
            if isinstance(titles, str):
                titles = [titles]
            for title in titles:
                entry = ConsignmentEntry(
                    id=str(uuid.uuid4())[:8],
                    venue=venue,
                    title=title,
                    author_name=author_name,
                )
                entries.append(entry)
                revenue_store.add_consignment_entry(entry)

    # Maya's own books
    for personal in registry.get("personal", []):
        consignment = personal.get("consignment", [])
        author_name = personal.get("name", "")
        books = [b.get("title", b) if isinstance(b, dict) else b
                 for b in personal.get("books", [])]
        for c in consignment:
            venue = c.get("venue", "")
            titles = c.get("titles", [])
            if titles == "all published":
                titles = [b for b in books]
            if isinstance(titles, str):
                titles = [titles]
            for title in titles:
                entry = ConsignmentEntry(
                    id=str(uuid.uuid4())[:8],
                    venue=venue,
                    title=title,
                    author_name=author_name,
                )
                entries.append(entry)
                revenue_store.add_consignment_entry(entry)

    return entries


def build_summary(period: str = "month") -> RevenueSummary:
    """Aggregate revenue data for dashboard display."""
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month

    if period == "month":
        start = f"{year}-{month:02d}-01"
        end = f"{year}-{month:02d}-31"
        period_label = now.strftime("%B %Y")
        kdp_months = [f"{year}-{month:02d}"]
        cost_months = 1
    elif period == "quarter":
        q = (month - 1) // 3 + 1
        start_m = (q - 1) * 3 + 1
        end_m = start_m + 2
        start = f"{year}-{start_m:02d}-01"
        end = f"{year}-{end_m:02d}-31"
        period_label = f"Q{q} {year}"
        kdp_months = [f"{year}-{m:02d}" for m in range(start_m, end_m + 1)]
        cost_months = month - start_m + 1  # months elapsed in quarter
    else:  # ytd
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        period_label = f"YTD {year}"
        kdp_months = [f"{year}-{m:02d}" for m in range(1, month + 1)]
        cost_months = month

    # Manual revenue entries
    entries = revenue_store.get_revenue_entries(start, end)
    consulting = sum(e.amount for e in entries if e.stream == "consulting")
    products = sum(e.amount for e in entries if e.stream == "products")
    entry_publishing = sum(e.amount for e in entries if e.stream == "publishing")

    # KDP revenue for period
    all_kdp = revenue_store.get_kdp_records()
    kdp_revenue = sum(r.royalty_amount for r in all_kdp if r.royalty_date in kdp_months)
    publishing = entry_publishing + kdp_revenue

    # Consignment revenue
    consignment_rev = sum(c.revenue for c in revenue_store.get_consignment())
    publishing += consignment_rev

    gross = consulting + publishing + products

    # Recurring costs
    costs = revenue_store.get_recurring_costs()
    monthly_cost = sum(c.amount for c in costs if c.frequency == "monthly")
    total_costs = monthly_cost * cost_months
    net = gross - total_costs

    # Goal: $5K/month consulting target
    goal = 5000.0 * cost_months
    goal_pct = round((consulting / goal * 100) if goal else 0, 1)

    # By client
    by_client: dict[str, float] = {}
    for e in entries:
        if e.client:
            by_client[e.client] = by_client.get(e.client, 0) + e.amount

    # By month
    by_month: dict[str, float] = {}
    for e in entries:
        m = e.date[:7]
        by_month[m] = by_month.get(m, 0) + e.amount
    for r in all_kdp:
        if r.royalty_date in kdp_months:
            by_month[r.royalty_date] = by_month.get(r.royalty_date, 0) + r.royalty_amount

    return RevenueSummary(
        period=period,
        period_label=period_label,
        consulting=round(consulting, 2),
        publishing=round(publishing, 2),
        products=round(products, 2),
        gross=round(gross, 2),
        recurring_monthly=round(monthly_cost, 2),
        net=round(net, 2),
        goal=round(goal, 2),
        goal_pct=goal_pct,
        by_client=by_client,
        by_month=by_month,
    )


def get_client_rates() -> dict:
    """Read consulting client rates from client-registry.yaml."""
    registry = _load_client_registry()
    rates = {}
    for client in registry.get("clients", []):
        rate = client.get("rate_per_hour")
        if rate:
            rates[client["name"]] = {
                "rate": rate,
                "retainer": client.get("retainer", 0),
                "ceiling": client.get("project_ceiling", 0),
            }
    # TDA website work
    for org in registry.get("organizations", []):
        website = org.get("roles", {}).get("website", {})
        if website.get("budget_rebuild"):
            rates[org["name"] + " (website)"] = {
                "rate": 0,
                "retainer": 0,
                "ceiling": website.get("budget_rebuild", 0),
                "owed": website.get("owed", 0),
            }
    return rates


# --- Private helpers ---

def _map_row(row: dict) -> dict:
    """Map raw CSV column names to our normalized keys."""
    mapped = {}
    for raw_key, value in row.items():
        normalized = raw_key.strip().lower()
        if normalized in KDP_COLUMN_MAP:
            mapped[KDP_COLUMN_MAP[normalized]] = value
    return mapped


def _normalize_date(raw: str) -> str:
    """Convert various date formats to YYYY-MM."""
    raw = raw.strip()
    # Already YYYY-MM
    if re.match(r"^\d{4}-\d{2}$", raw):
        return raw
    # Month/Year like "January 2026" or "Jan 2026"
    for fmt in ("%B %Y", "%b %Y", "%m/%Y", "%m-%Y"):
        try:
            dt = datetime.strptime(raw, fmt)
            return f"{dt.year}-{dt.month:02d}"
        except ValueError:
            continue
    # Full date
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(raw, fmt)
            return f"{dt.year}-{dt.month:02d}"
        except ValueError:
            continue
    return raw


def _parse_float(raw: str) -> float:
    """Parse a currency/number string to float."""
    cleaned = re.sub(r"[,$\s]", "", raw.strip())
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def _parse_int(raw: str) -> int:
    """Parse an integer string, handling commas."""
    cleaned = re.sub(r"[,\s]", "", raw.strip())
    try:
        return int(float(cleaned))
    except (ValueError, TypeError):
        return 0


def _infer_format(payout_plan: str) -> str:
    """Infer book format from payout_plan column."""
    pp = payout_plan.lower()
    if "paperback" in pp:
        return "Paperback"
    if "hardcover" in pp:
        return "Hardcover"
    if "kenp" in pp or "standard" in pp or not pp:
        return "Ebook"
    return "Ebook"


def _infer_type(payout_plan: str, net_units: int, royalty_amount: float) -> str:
    """Infer transaction type: KENP, Free promo, or Purchase."""
    if "kenp" in payout_plan.lower():
        return "KENP"
    if net_units > 0 and royalty_amount == 0.0:
        return "Free promo"
    return "Purchase"


def _infer_payout(royalty_type: str, payout_plan: str) -> float:
    """Infer payout rate from royalty_type string."""
    if "kenp" in payout_plan.lower():
        return 0.0
    rt = royalty_type.lower()
    if "35%" in rt:
        return 0.35
    if "60%" in rt:
        return 0.60
    if "70%" in rt:
        return 0.70
    return 0.0


def _resolve_keep_pct(author_name: str) -> float:
    """Look up KEEP% for an author. Unmatched defaults to 0.0 (Maya's own books)."""
    name_lower = author_name.strip().lower()
    if name_lower in KEEP_PCT:
        return KEEP_PCT[name_lower]
    for config_name, pct in KEEP_PCT.items():
        if config_name in name_lower or name_lower in config_name:
            return pct
    return 0.0


def transform_to_transactions(records: list[KdpRecord]) -> list[TransactionsRow]:
    """Transform KdpRecords into TransactionsRows matching spreadsheet schema."""
    rows: list[TransactionsRow] = []
    for r in records:
        # Date as YYYY-MM-01
        date = f"{r.royalty_date}-01" if r.royalty_date else ""
        rows.append(TransactionsRow(
            date=date,
            title=r.title,
            author=r.author_name,
            format=r.format,
            type=_infer_type(r.payout_plan, r.net_units, r.royalty_amount),
            marketplace=r.marketplace,
            units_sold=r.units_sold,
            units_refunded=r.units_refunded,
            net_units_sold=r.net_units,
            payout=_infer_payout(r.royalty_type, r.payout_plan),
            earnings=r.royalty_amount,
            keep_pct=_resolve_keep_pct(r.author_name),
        ))
    return rows


def export_transactions_tsv(rows: list[TransactionsRow]) -> str:
    """Export TransactionsRows as tab-separated text (no header row).
    Maya pastes directly into existing spreadsheet columns."""
    lines: list[str] = []
    for r in rows:
        line = "\t".join([
            r.date,
            r.title,
            r.author,
            r.format,
            r.type,
            r.marketplace,
            str(r.units_sold),
            str(r.units_refunded),
            str(r.net_units_sold),
            f"{r.payout:.2f}",
            f"{r.earnings:.2f}",
            f"{r.keep_pct:.0%}",
        ])
        lines.append(line)
    return "\n".join(lines)


def _load_client_registry() -> dict:
    """Load client-registry.yaml."""
    path = DATA_DIR / "client-registry.yaml"
    if not path.exists():
        logger.warning("client-registry.yaml not found")
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _load_royalty_splits() -> dict[str, tuple[float, float]]:
    """Parse royalty_split strings from client-registry.yaml into
    (author_pct, publisher_pct) tuples keyed by author name."""
    registry = _load_client_registry()
    splits: dict[str, tuple[float, float]] = {}

    for client in registry.get("clients", []):
        name = client.get("name", "")
        pen_name = client.get("pen_name", "")
        raw = client.get("royalty_split", "")
        if not raw:
            continue

        author_pct, publisher_pct = _parse_split_string(raw)
        splits[name.lower()] = (author_pct, publisher_pct)
        if pen_name:
            splits[pen_name.lower()] = (author_pct, publisher_pct)

    return splits


def _parse_split_string(raw: str) -> tuple[float, float]:
    """Parse royalty split strings:
    - '0%' or '0% — labor of love' -> (0.0, 1.0)
    - '50/50 Amazon' -> (0.5, 0.5)
    - '60/40 author/publisher' -> (0.6, 0.4)
    """
    raw = raw.strip().lower()

    # "0%" pattern
    match = re.match(r"^(\d+)%", raw)
    if match:
        pct = int(match.group(1)) / 100.0
        return (pct, 1.0 - pct)

    # "50/50" or "60/40" pattern
    match = re.match(r"(\d+)\s*/\s*(\d+)", raw)
    if match:
        a, b = int(match.group(1)), int(match.group(2))
        total = a + b
        return (a / total, b / total)

    # Default: author keeps all
    return (1.0, 0.0)


def _resolve_split(author_name: str, splits_config: dict) -> tuple[float, float]:
    """Look up the royalty split for an author. Unmatched authors are
    assumed to be Maya's own books (author keeps 100%)."""
    name_lower = author_name.lower()
    if name_lower in splits_config:
        return splits_config[name_lower]
    # Check partial matches
    for config_name, split in splits_config.items():
        if config_name in name_lower or name_lower in config_name:
            return split
    # Default: Maya's own books
    return (1.0, 0.0)
