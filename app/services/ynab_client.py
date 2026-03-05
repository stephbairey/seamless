"""Async HTTP client for YNAB API v1."""

import logging
from typing import Any

import httpx

from app.config import YNAB_API_BASE, YNAB_API_TOKEN

logger = logging.getLogger(__name__)


class YnabClient:
    """Thin async wrapper around the YNAB REST API."""

    def __init__(self):
        self._token = YNAB_API_TOKEN

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = f"{YNAB_API_BASE}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(method, url, headers=self._headers(), **kwargs)
            if resp.status_code == 401:
                raise YnabAuthError("Invalid YNAB API token")
            if resp.status_code == 429:
                raise YnabRateLimitError("Rate limited by YNAB API")
            resp.raise_for_status()
            return resp.json()

    async def get_categories(self, budget_id: str) -> dict:
        """Fetch all category groups and their categories for a budget."""
        return await self._request("GET", f"/budgets/{budget_id}/categories")

    async def get_transactions(self, budget_id: str, since_date: str) -> dict:
        """Fetch transactions for a budget since a given date (YYYY-MM-DD)."""
        return await self._request(
            "GET",
            f"/budgets/{budget_id}/transactions",
            params={"since_date": since_date},
        )


class YnabAuthError(Exception):
    pass


class YnabRateLimitError(Exception):
    pass


# Shared instance
ynab_client = YnabClient()
