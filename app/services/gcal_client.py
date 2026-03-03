"""Async HTTP client for Google Calendar REST API with multi-account OAuth2."""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.config import (
    GMAIL_CLIENT_ID,
    GMAIL_CLIENT_SECRET,
    GCAL_LINGUAINKMEDIA_TOKEN,
    GCAL_MJBAIREY_TOKEN,
    GCAL_STEPHBAIREY_TOKEN,
)
from app.models.calendar import CalendarEvent

logger = logging.getLogger(__name__)

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GCAL_API_BASE = "https://www.googleapis.com/calendar/v3"
TZ = ZoneInfo("America/Los_Angeles")

CALENDAR_ACCOUNTS = [
    {
        "calendar_id": "linguainkmedia@gmail.com",
        "label": "Business",
        "identity": "lingua-ink-media",
        "env_token": "GCAL_LINGUAINKMEDIA_TOKEN",
    },
    {
        "calendar_id": "mjbairey@gmail.com",
        "label": "Creative",
        "identity": "maya-bairey",
        "env_token": "GCAL_MJBAIREY_TOKEN",
    },
    {
        "calendar_id": "stephbairey@gmail.com",
        "label": "Personal",
        "identity": "steph-bairey",
        "env_token": "GCAL_STEPHBAIREY_TOKEN",
    },
]


@dataclass
class CalendarAccount:
    calendar_id: str
    label: str
    identity: str
    refresh_token: str
    access_token: str = ""
    token_expires: float = 0


class GCalClient:
    """Multi-account async wrapper around the Google Calendar REST API."""

    def __init__(self):
        self._client_id = GMAIL_CLIENT_ID
        self._client_secret = GMAIL_CLIENT_SECRET
        self._accounts: list[CalendarAccount] = []

        tokens = {
            "linguainkmedia@gmail.com": GCAL_LINGUAINKMEDIA_TOKEN,
            "mjbairey@gmail.com": GCAL_MJBAIREY_TOKEN,
            "stephbairey@gmail.com": GCAL_STEPHBAIREY_TOKEN,
        }

        for acct_cfg in CALENDAR_ACCOUNTS:
            token = tokens.get(acct_cfg["calendar_id"], "")
            if token:
                self._accounts.append(CalendarAccount(
                    calendar_id=acct_cfg["calendar_id"],
                    label=acct_cfg["label"],
                    identity=acct_cfg["identity"],
                    refresh_token=token,
                ))

    @property
    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret and self._accounts)

    @property
    def accounts(self) -> list[CalendarAccount]:
        return self._accounts

    def get_account(self, calendar_id: str) -> CalendarAccount | None:
        for acct in self._accounts:
            if acct.calendar_id == calendar_id:
                return acct
        return None

    async def _ensure_token(self, account: CalendarAccount):
        if account.access_token and time.time() < account.token_expires:
            return
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(TOKEN_ENDPOINT, data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": account.refresh_token,
                "grant_type": "refresh_token",
            })
            if resp.status_code != 200:
                raise GCalAuthError(
                    f"Token refresh failed for {account.calendar_id}: "
                    f"{resp.status_code} {resp.text}"
                )
            data = resp.json()
            account.access_token = data["access_token"]
            account.token_expires = time.time() + data.get("expires_in", 3600) - 60

    def _headers(self, account: CalendarAccount) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {account.access_token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self, account: CalendarAccount, method: str, path: str, **kwargs
    ) -> dict[str, Any]:
        await self._ensure_token(account)
        url = f"{GCAL_API_BASE}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method, url, headers=self._headers(account), **kwargs
            )
            if resp.status_code == 401:
                account.access_token = ""
                account.token_expires = 0
                await self._ensure_token(account)
                resp = await client.request(
                    method, url, headers=self._headers(account), **kwargs
                )
                if resp.status_code == 401:
                    raise GCalAuthError(
                        f"Auth failed for {account.calendar_id} after refresh"
                    )
            if resp.status_code == 429:
                raise GCalRateLimitError("Rate limited by Calendar API")
            resp.raise_for_status()
            if resp.status_code == 204:
                return {}
            return resp.json()

    # --- Events ---

    async def list_events(
        self,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
        max_results: int = 250,
    ) -> list[CalendarEvent]:
        account = self.get_account(calendar_id)
        if not account:
            raise GCalAuthError(f"No account configured for {calendar_id}")

        params = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "maxResults": max_results,
            "singleEvents": "true",
            "orderBy": "startTime",
            "timeZone": "America/Los_Angeles",
        }

        data = await self._request(
            account, "GET", f"/calendars/{calendar_id}/events", params=params
        )

        events = []
        for item in data.get("items", []):
            events.append(self._parse_event(item, account))
        return events

    async def get_event(self, calendar_id: str, event_id: str) -> CalendarEvent:
        account = self.get_account(calendar_id)
        if not account:
            raise GCalAuthError(f"No account configured for {calendar_id}")

        data = await self._request(
            account, "GET", f"/calendars/{calendar_id}/events/{event_id}"
        )
        return self._parse_event(data, account)

    async def create_event(self, calendar_id: str, event_body: dict) -> CalendarEvent:
        account = self.get_account(calendar_id)
        if not account:
            raise GCalAuthError(f"No account configured for {calendar_id}")

        data = await self._request(
            account, "POST", f"/calendars/{calendar_id}/events", json=event_body
        )
        return self._parse_event(data, account)

    async def update_event(
        self, calendar_id: str, event_id: str, event_body: dict
    ) -> CalendarEvent:
        account = self.get_account(calendar_id)
        if not account:
            raise GCalAuthError(f"No account configured for {calendar_id}")

        data = await self._request(
            account, "PUT",
            f"/calendars/{calendar_id}/events/{event_id}",
            json=event_body,
        )
        return self._parse_event(data, account)

    async def delete_event(self, calendar_id: str, event_id: str) -> None:
        account = self.get_account(calendar_id)
        if not account:
            raise GCalAuthError(f"No account configured for {calendar_id}")

        await self._request(
            account, "DELETE", f"/calendars/{calendar_id}/events/{event_id}"
        )

    async def list_all_events(
        self, time_min: datetime, time_max: datetime
    ) -> list[CalendarEvent]:
        all_events = []
        for account in self._accounts:
            try:
                events = await self.list_events(
                    account.calendar_id, time_min, time_max
                )
                all_events.extend(events)
            except Exception as e:
                logger.warning(
                    "Failed to fetch events from %s: %s",
                    account.calendar_id, e,
                )
        all_events.sort(key=lambda e: e.start or datetime.min.replace(tzinfo=TZ))
        return all_events

    def _parse_event(self, item: dict, account: CalendarAccount) -> CalendarEvent:
        start_raw = item.get("start", {})
        end_raw = item.get("end", {})

        all_day = "date" in start_raw and "dateTime" not in start_raw

        start_dt = self._parse_dt(start_raw)
        end_dt = self._parse_dt(end_raw)

        attendees = []
        for att in item.get("attendees", []):
            email = att.get("email", "")
            if email and email != account.calendar_id:
                attendees.append(email)

        creator = item.get("creator", {}).get("email", "")

        return CalendarEvent(
            id=item.get("id", ""),
            calendar_id=account.calendar_id,
            calendar_label=account.label,
            summary=item.get("summary", ""),
            description=item.get("description", ""),
            location=item.get("location", ""),
            start=start_dt,
            end=end_dt,
            all_day=all_day,
            recurring=bool(item.get("recurringEventId")),
            attendees=attendees,
            creator=creator,
            identity=account.identity,
            color_id=item.get("colorId", ""),
            html_link=item.get("htmlLink", ""),
        )

    def _parse_dt(self, raw: dict) -> datetime | None:
        if "dateTime" in raw:
            dt_str = raw["dateTime"]
            try:
                return datetime.fromisoformat(dt_str)
            except ValueError:
                return None
        elif "date" in raw:
            try:
                return datetime.fromisoformat(raw["date"] + "T00:00:00").replace(
                    tzinfo=TZ
                )
            except ValueError:
                return None
        return None


class GCalAuthError(Exception):
    pass


class GCalRateLimitError(Exception):
    pass


# Shared instance
gcal_client = GCalClient()
