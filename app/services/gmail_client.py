"""Async HTTP client for Gmail REST API with OAuth2 token refresh."""

import base64
import email
import email.utils
import logging
import time
from datetime import datetime
from email.mime.text import MIMEText
from typing import Any

import httpx

from app.config import (
    GMAIL_API_BASE,
    GMAIL_CLIENT_ID,
    GMAIL_CLIENT_SECRET,
    GMAIL_REFRESH_TOKEN,
)
from app.models.email import EmailMessage

logger = logging.getLogger(__name__)

TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
LABEL_CACHE_TTL = 300  # 5 minutes

# System labels to ignore when checking if a message has user labels
SYSTEM_LABEL_PREFIXES = (
    "INBOX", "UNREAD", "STARRED", "IMPORTANT", "SENT", "DRAFT",
    "SPAM", "TRASH", "CATEGORY_",
)


class GmailClient:
    """Thin async wrapper around the Gmail REST API."""

    def __init__(self):
        self._client_id = GMAIL_CLIENT_ID
        self._client_secret = GMAIL_CLIENT_SECRET
        self._refresh_token = GMAIL_REFRESH_TOKEN
        self._access_token: str = ""
        self._token_expires: float = 0
        self._label_cache: dict[str, str] = {}  # name → id
        self._label_id_cache: dict[str, str] = {}  # id → name
        self._label_cache_time: float = 0

    @property
    def is_configured(self) -> bool:
        return bool(self._client_id and self._client_secret and self._refresh_token)

    async def _ensure_token(self):
        """Refresh the access token if expired or missing."""
        if self._access_token and time.time() < self._token_expires:
            return
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(TOKEN_ENDPOINT, data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
                "grant_type": "refresh_token",
            })
            if resp.status_code != 200:
                raise GmailAuthError(f"Token refresh failed: {resp.status_code} {resp.text}")
            data = resp.json()
            self._access_token = data["access_token"]
            self._token_expires = time.time() + data.get("expires_in", 3600) - 60

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        await self._ensure_token()
        url = f"{GMAIL_API_BASE}{path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(method, url, headers=self._headers(), **kwargs)
            if resp.status_code == 401:
                # Token may have been revoked; try one refresh
                self._access_token = ""
                self._token_expires = 0
                await self._ensure_token()
                resp = await client.request(method, url, headers=self._headers(), **kwargs)
                if resp.status_code == 401:
                    raise GmailAuthError("Authentication failed after token refresh")
            if resp.status_code == 429:
                raise GmailRateLimitError("Rate limited by Gmail API")
            resp.raise_for_status()
            return resp.json()

    # --- Labels ---

    async def get_labels(self) -> dict[str, str]:
        """Return name→ID mapping of all labels, cached for 5 minutes."""
        if self._label_cache and (time.time() - self._label_cache_time) < LABEL_CACHE_TTL:
            return self._label_cache
        data = await self._request("GET", "/me/labels")
        self._label_cache = {}
        self._label_id_cache = {}
        for label in data.get("labels", []):
            self._label_cache[label["name"]] = label["id"]
            self._label_id_cache[label["id"]] = label["name"]
        self._label_cache_time = time.time()
        return self._label_cache

    async def get_label_name(self, label_id: str) -> str:
        """Resolve a label ID to its name."""
        if not self._label_id_cache:
            await self.get_labels()
        return self._label_id_cache.get(label_id, label_id)

    async def resolve_label_names(self, label_ids: list[str]) -> list[str]:
        """Convert a list of label IDs to label names."""
        if not self._label_id_cache:
            await self.get_labels()
        return [self._label_id_cache.get(lid, lid) for lid in label_ids]

    # --- Messages ---

    async def list_messages(self, query: str = "", max_results: int = 50) -> list[dict]:
        """List message IDs matching a query. Returns list of {id, threadId}."""
        params: dict[str, Any] = {"maxResults": max_results}
        if query:
            params["q"] = query
        data = await self._request("GET", "/me/messages", params=params)
        return data.get("messages", [])

    async def get_message(self, msg_id: str, fmt: str = "full") -> EmailMessage:
        """Fetch and parse a single message."""
        data = await self._request("GET", f"/me/messages/{msg_id}", params={"format": fmt})
        return self._parse_message(data)

    def _parse_message(self, data: dict) -> EmailMessage:
        """Parse Gmail API message response into an EmailMessage."""
        headers = {}
        for h in data.get("payload", {}).get("headers", []):
            headers[h["name"].lower()] = h["value"]

        # Parse date
        msg_date = None
        date_str = headers.get("date", "")
        if date_str:
            try:
                parsed = email.utils.parsedate_to_datetime(date_str)
                msg_date = parsed
            except (ValueError, TypeError):
                pass

        # Extract sender email from "From" header
        sender = headers.get("from", "")
        sender_email = ""
        if "<" in sender and ">" in sender:
            sender_email = sender.split("<")[1].split(">")[0].strip()
        elif "@" in sender:
            sender_email = sender.strip()

        # Extract body
        body_text, body_html, is_multipart_related = self._extract_body(data.get("payload", {}))

        label_ids = data.get("labelIds", [])
        label_names = [self._label_id_cache.get(lid, lid) for lid in label_ids]

        return EmailMessage(
            id=data["id"],
            thread_id=data.get("threadId", ""),
            subject=headers.get("subject", "(no subject)"),
            sender=sender,
            sender_email=sender_email,
            to=headers.get("to", ""),
            delivered_to=headers.get("delivered-to", headers.get("x-original-to", "")),
            date=msg_date,
            snippet=data.get("snippet", ""),
            body_text=body_text,
            body_html=body_html,
            labels=label_names,
            label_ids=label_ids,
            is_unread="UNREAD" in label_ids,
            is_multipart_related=is_multipart_related,
            in_reply_to=headers.get("in-reply-to", ""),
            message_id=headers.get("message-id", ""),
        )

    def _extract_body(self, payload: dict) -> tuple[str, str, bool]:
        """Walk MIME parts to extract text and HTML body. Returns (text, html, is_multipart_related)."""
        text_parts = []
        html_parts = []
        is_multipart_related = False

        mime_type = payload.get("mimeType", "")
        if mime_type == "multipart/related":
            is_multipart_related = True

        def walk(part: dict):
            nonlocal is_multipart_related
            pt_mime = part.get("mimeType", "")
            if pt_mime == "multipart/related":
                is_multipart_related = True

            body_data = part.get("body", {}).get("data", "")
            if body_data:
                decoded = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
                if pt_mime == "text/plain":
                    text_parts.append(decoded)
                elif pt_mime == "text/html":
                    html_parts.append(decoded)

            for sub in part.get("parts", []):
                walk(sub)

        walk(payload)

        text = "\n".join(text_parts)
        html = "\n".join(html_parts)

        # Flag: if multipart/related and no text body, it's the embedded-image issue
        if is_multipart_related and not text.strip():
            is_multipart_related = True

        return text, html, is_multipart_related

    # --- Modify labels ---

    async def modify_labels(
        self, msg_id: str,
        add_ids: list[str] | None = None,
        remove_ids: list[str] | None = None,
    ) -> dict:
        """Add or remove labels from a message."""
        payload: dict[str, Any] = {}
        if add_ids:
            payload["addLabelIds"] = add_ids
        if remove_ids:
            payload["removeLabelIds"] = remove_ids
        return await self._request("POST", f"/me/messages/{msg_id}/modify", json=payload)

    # --- Drafts ---

    async def create_draft(
        self, to: str, subject: str, body: str,
        send_as: str = "", thread_id: str = "", in_reply_to: str = "",
    ) -> dict:
        """Create a Gmail draft with proper RFC 2822 message."""
        msg = MIMEText(body, "plain", "utf-8")
        msg["To"] = to
        msg["Subject"] = subject
        if send_as:
            msg["From"] = send_as
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = in_reply_to

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        payload: dict[str, Any] = {"message": {"raw": raw}}
        if thread_id:
            payload["message"]["threadId"] = thread_id
        return await self._request("POST", "/me/drafts", json=payload)


class GmailAuthError(Exception):
    pass


class GmailRateLimitError(Exception):
    pass


# Shared instance
gmail_client = GmailClient()
