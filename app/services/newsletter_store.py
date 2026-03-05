"""JSON persistence for newsletter issues, keyed by ISO week."""

import fcntl
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from app.config import DATA_DIR
from app.models.newsletter import NewsletterIssue, NewsletterItem

logger = logging.getLogger(__name__)

NEWSLETTER_FILE = DATA_DIR / "newsletter-items.json"


def _current_week_key() -> str:
    """Return ISO week key like '2026-W10'."""
    now = datetime.now(timezone.utc)
    return f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"


class NewsletterStore:
    def __init__(self, path: Path = NEWSLETTER_FILE):
        self._path = path
        self._data: dict[str, dict] = {}
        self._loaded = False

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path) as f:
                    fcntl.flock(f, fcntl.LOCK_SH)
                    self._data = json.load(f)
                    fcntl.flock(f, fcntl.LOCK_UN)
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to read newsletter store: %s", e)
                self._data = {}
        else:
            self._data = {}
        self._loaded = True

    def _ensure_loaded(self):
        if not self._loaded:
            self._load()

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            json.dump(self._data, f, indent=2, default=str)
            fcntl.flock(f, fcntl.LOCK_UN)

    def _issue_from_dict(self, d: dict) -> NewsletterIssue:
        return NewsletterIssue(**d)

    def _issue_to_dict(self, issue: NewsletterIssue) -> dict:
        return json.loads(issue.model_dump_json())

    def get_current_issue(self) -> NewsletterIssue:
        """Get or create the issue for the current ISO week."""
        self._ensure_loaded()
        key = _current_week_key()
        if key in self._data:
            return self._issue_from_dict(self._data[key])
        now = datetime.now(timezone.utc).isoformat()
        issue = NewsletterIssue(
            week_key=key,
            items=[],
            created_at=now,
            updated_at=now,
            status="draft",
        )
        self._data[key] = self._issue_to_dict(issue)
        self._save()
        return issue

    def get_issue(self, week_key: str) -> NewsletterIssue | None:
        """Get a specific issue by week key."""
        self._ensure_loaded()
        if week_key in self._data:
            return self._issue_from_dict(self._data[week_key])
        return None

    def save_issue(self, issue: NewsletterIssue):
        """Write issue back to JSON."""
        self._ensure_loaded()
        issue.updated_at = datetime.now(timezone.utc)
        self._data[issue.week_key] = self._issue_to_dict(issue)
        self._save()

    def add_item(self, item: NewsletterItem) -> NewsletterIssue:
        """Append item to the current week's issue."""
        issue = self.get_current_issue()
        # Assign display_order
        max_order = max((i.display_order for i in issue.items), default=-1)
        item.display_order = max_order + 1
        issue.items.append(item)
        self.save_issue(issue)
        return issue

    def update_item(self, item_id: str, updates: dict) -> NewsletterIssue | None:
        """Update fields on an item in the current issue."""
        issue = self.get_current_issue()
        for item in issue.items:
            if item.id == item_id:
                for k, v in updates.items():
                    if hasattr(item, k):
                        setattr(item, k, v)
                self.save_issue(issue)
                return issue
        return None

    def remove_item(self, item_id: str) -> NewsletterIssue | None:
        """Delete item from the issue entirely."""
        issue = self.get_current_issue()
        original_len = len(issue.items)
        issue.items = [i for i in issue.items if i.id != item_id]
        if len(issue.items) < original_len:
            self.save_issue(issue)
            return issue
        return None

    def reorder_items(self, item_ids: list[str]) -> NewsletterIssue:
        """Rewrite display_order based on the given ID sequence."""
        issue = self.get_current_issue()
        order_map = {uid: idx for idx, uid in enumerate(item_ids)}
        for item in issue.items:
            if item.id in order_map:
                item.display_order = order_map[item.id]
        self.save_issue(issue)
        return issue

    def list_issues(self) -> list[dict]:
        """Summary list of all issues."""
        self._ensure_loaded()
        summaries = []
        for key in sorted(self._data.keys(), reverse=True):
            issue = self._issue_from_dict(self._data[key])
            summaries.append({
                "week_key": issue.week_key,
                "item_count": len(issue.items),
                "included_count": len([i for i in issue.items if i.status == "included"]),
                "status": issue.status,
                "created_at": issue.created_at,
                "updated_at": issue.updated_at,
            })
        return summaries

    def reload(self):
        """Force reload from disk."""
        self._loaded = False
        self._load()


# Shared instance
newsletter_store = NewsletterStore()
