"""Async HTTP client for ClickUp API v2."""

import logging
from datetime import datetime
from typing import Any

import httpx

from app.config import CLICKUP_API_BASE, CLICKUP_API_TOKEN, CLICKUP_LIST_ID

logger = logging.getLogger(__name__)


class ClickUpClient:
    """Thin async wrapper around the ClickUp REST API."""

    def __init__(self):
        self._token = CLICKUP_API_TOKEN

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._token,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = f"{CLICKUP_API_BASE}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(method, url, headers=self._headers(), **kwargs)
            if resp.status_code == 401:
                raise ClickUpAuthError("Invalid API token")
            if resp.status_code == 429:
                raise ClickUpRateLimitError("Rate limited by ClickUp API")
            resp.raise_for_status()
            return resp.json()

    async def create_task(self, name: str, due_date: datetime | None = None,
                          description: str = "", status: str = "Not Started",
                          custom_fields: list[dict] | None = None) -> dict:
        payload: dict[str, Any] = {
            "name": name,
            "status": status,
        }
        if due_date:
            payload["due_date"] = int(due_date.timestamp() * 1000)
            payload["due_date_time"] = False
        if description:
            payload["description"] = description
        if custom_fields:
            payload["custom_fields"] = custom_fields
        return await self._request("POST", f"/list/{CLICKUP_LIST_ID}/task", json=payload)

    async def get_tasks(self, page: int = 0, statuses: list[str] | None = None,
                        include_closed: bool = False) -> dict:
        params: dict[str, Any] = {
            "page": page,
            "include_closed": str(include_closed).lower(),
            "subtasks": "true",
        }
        if statuses:
            for i, s in enumerate(statuses):
                params[f"statuses[]"] = s
        return await self._request("GET", f"/list/{CLICKUP_LIST_ID}/task", params=params)

    async def get_task(self, task_id: str) -> dict:
        return await self._request("GET", f"/task/{task_id}")

    async def update_task(self, task_id: str, **fields) -> dict:
        return await self._request("PUT", f"/task/{task_id}", json=fields)

    async def update_task_status(self, task_id: str, status: str) -> dict:
        return await self.update_task(task_id, status=status)

    async def get_time_entries(self, start_date: str = "", end_date: str = "") -> dict:
        """Get time entries for the workspace. Dates are YYYY-MM-DD strings,
        converted to epoch milliseconds for the API."""
        from app.config import CLICKUP_WORKSPACE_ID
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = str(int(
                datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000
            ))
        if end_date:
            params["end_date"] = str(int(
                datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S").timestamp() * 1000
            ))
        return await self._request(
            "GET", f"/team/{CLICKUP_WORKSPACE_ID}/time_entries", params=params
        )

    async def get_task_time_tracked(self, task_id: str) -> dict:
        """Get time tracked on a specific task."""
        return await self._request("GET", f"/task/{task_id}/time")


class ClickUpAuthError(Exception):
    pass


class ClickUpRateLimitError(Exception):
    pass


# Shared instance
clickup_client = ClickUpClient()
