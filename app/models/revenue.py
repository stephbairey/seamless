"""Pydantic models for revenue tracking."""

from pydantic import BaseModel


class KdpRecord(BaseModel):
    id: str
    import_id: str
    royalty_date: str  # YYYY-MM
    title: str
    author_name: str
    asin_isbn: str = ""
    marketplace: str = ""
    royalty_type: str = ""
    transaction_type: str = ""
    format: str = ""
    net_units: int = 0
    royalty_amount: float = 0.0
    currency: str = "USD"
    raw_row: dict = {}


class KdpImport(BaseModel):
    id: str
    filename: str
    uploaded_at: str  # ISO datetime
    record_count: int = 0
    date_range: str = ""  # "2026-01 to 2026-03"
    total_royalty: float = 0.0


class RoyaltySplit(BaseModel):
    title: str
    format: str = ""
    author_name: str
    net_units: int = 0
    gross_royalty: float = 0.0
    author_pct: float = 0.0
    publisher_pct: float = 1.0
    author_amount: float = 0.0
    publisher_amount: float = 0.0
    channel: str = "KDP"


class RoyaltyReport(BaseModel):
    id: str
    author_name: str
    quarter: str  # "2026-Q1"
    quarter_start: str  # "2026-01"
    quarter_end: str  # "2026-03"
    generated_at: str  # ISO datetime
    splits: list[RoyaltySplit] = []
    total_gross: float = 0.0
    total_author: float = 0.0
    total_publisher: float = 0.0
    status: str = "draft"  # draft / reviewed / sent


class ConsignmentEntry(BaseModel):
    id: str
    venue: str
    title: str
    author_name: str
    qty_placed: int = 0
    date_placed: str = ""  # YYYY-MM-DD
    qty_sold: int = 0
    last_checked: str = ""  # YYYY-MM-DD
    revenue: float = 0.0
    notes: str = ""


class RevenueEntry(BaseModel):
    id: str
    date: str  # YYYY-MM-DD
    client: str = ""
    stream: str = ""  # consulting / publishing / products
    description: str = ""
    hours: float = 0.0
    rate: float = 0.0
    amount: float = 0.0
    source: str = "manual"  # manual / clickup


class RecurringCost(BaseModel):
    label: str
    amount: float = 0.0
    frequency: str = "monthly"


class RevenueSummary(BaseModel):
    period: str  # "month" / "quarter" / "ytd"
    period_label: str = ""
    consulting: float = 0.0
    publishing: float = 0.0
    products: float = 0.0
    gross: float = 0.0
    recurring_monthly: float = 0.0
    net: float = 0.0
    goal: float = 0.0
    goal_pct: float = 0.0
    by_client: dict = {}
    by_month: dict = {}
