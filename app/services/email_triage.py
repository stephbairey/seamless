"""Email classification, contact matching, label inference, and digest generation."""

import logging
import re
from datetime import datetime
from typing import Any

from app.models.email import DailyDigest, DigestGroup, EmailClassification, EmailMessage
from app.services.gmail_client import SYSTEM_LABEL_PREFIXES, gmail_client
from app.services.yaml_store import yaml_store

logger = logging.getLogger(__name__)

# Client name → Gmail label mapping (from domain plan)
CLIENT_LABEL_MAP = {
    "sulima malzin": "Sulima",
    "carolyn martin": "Carolyn",
    "lynn haller": "Lynn",
    "devon ervin": "Devon",
    "daniela morescalchi": "Daniela",
    "nicole dalton": "Nicole",
}

# Keywords that indicate urgency
PRIORITY_KEYWORDS = re.compile(
    r"\b(urgent|deadline|overdue|invoice|past due|asap|time.?sensitive|payment)\b",
    re.IGNORECASE,
)

# High-priority senders (always flag)
HIGH_PRIORITY_SENDERS = {"sulima"}


class EmailTriageService:
    def __init__(self):
        self._clients: list[dict] = []
        self._identities: list[dict] = []
        self._labels: list[str] = []
        self._prg_members: list[str] = []
        self._prg_gaggle_lists: list[str] = []
        self._loaded = False

    def _load(self):
        client_data = yaml_store.read("client-registry.yaml")
        email_data = yaml_store.read("email-identities.yaml")

        self._clients = client_data.get("clients", [])
        self._identities = email_data.get("identities", [])
        self._labels = [lbl for lbl in email_data.get("labels", [])]
        self._prg_members = email_data.get("prg_members", [])

        # Extract PRG gaggle lists from client registry
        for org in client_data.get("organizations", []):
            if org.get("name") == "Portland Raging Grannies":
                self._prg_gaggle_lists = org.get("gaggle_lists", [])
                break

        self._loaded = True

    def _ensure_loaded(self):
        if not self._loaded:
            self._load()

    def reload(self):
        self._loaded = False
        self._load()

    def has_user_labels(self, message: EmailMessage) -> bool:
        """Check if a message already has user-applied labels (not system labels)."""
        for label in message.labels:
            if not any(label.startswith(prefix) for prefix in SYSTEM_LABEL_PREFIXES):
                return True
        return False

    def classify(self, message: EmailMessage) -> EmailClassification:
        """Classify a single message: match contact, suggest label, detect priority."""
        self._ensure_loaded()

        classification = EmailClassification(message_id=message.id)

        # Check for multipart/related with empty body
        if message.is_multipart_related and not message.body_text.strip():
            classification.needs_manual_review = True
            classification.review_reason = "Multipart/related message with no text body (likely embedded images)"
            classification.confidence = "low"

        # Contact matching cascade
        match = self._match_contact(message)
        if match:
            classification.matched_client = match["client"]
            classification.match_method = match["method"]
            classification.suggested_label = match.get("label")
            classification.confidence = match.get("confidence", "high")

            # Resolve label ID
            if classification.suggested_label:
                classification.suggested_label_id = self._resolve_label_id(
                    classification.suggested_label
                )

        # PRG newsletter detection
        if self._is_prg_newsletter(message):
            classification.is_prg_newsletter = True
            if not classification.suggested_label:
                classification.suggested_label = "PRG/Newsletter"
                classification.suggested_label_id = self._resolve_label_id("PRG/Newsletter")
                classification.match_method = "prg_member"

        # Priority detection
        priority_info = self._detect_priority(message, classification)
        classification.priority = priority_info["level"]
        classification.priority_reason = priority_info.get("reason")

        return classification

    def _match_contact(self, message: EmailMessage) -> dict[str, Any] | None:
        """Three-step contact matching: exact email → domain → name fragment."""

        sender_email = message.sender_email.lower()
        sender_name = message.sender.lower()

        # Step 1: Exact email match against client registry
        for client in self._clients:
            client_email = client.get("email", "").lower()
            if client_email and client_email == sender_email:
                label = CLIENT_LABEL_MAP.get(client["name"].lower())
                return {
                    "client": client["name"],
                    "method": "exact_email",
                    "label": label,
                    "confidence": "high",
                }

        # Step 2: Domain match
        if "@" in sender_email:
            sender_domain = sender_email.split("@")[1]
            for client in self._clients:
                # Check websites
                websites = []
                if client.get("website"):
                    websites.append(client["website"])
                if client.get("websites"):
                    websites.extend(client["websites"])
                for site in websites:
                    site_domain = site.lower().replace("www.", "")
                    if sender_domain == site_domain or sender_domain.endswith("." + site_domain):
                        label = CLIENT_LABEL_MAP.get(client["name"].lower())
                        return {
                            "client": client["name"],
                            "method": "domain",
                            "label": label,
                            "confidence": "high",
                        }

        # Step 3: Name fragment match in sender display name
        for client in self._clients:
            client_name = client["name"].lower()
            # Check both full name and individual name parts
            name_parts = client_name.split()
            if len(name_parts) >= 2:
                # Match on last name (more specific)
                last_name = name_parts[-1]
                if len(last_name) > 2 and last_name in sender_name:
                    label = CLIENT_LABEL_MAP.get(client_name)
                    return {
                        "client": client["name"],
                        "method": "name_fragment",
                        "label": label,
                        "confidence": "medium",
                    }
            # Check pen name
            pen_name = client.get("pen_name", "").lower()
            if pen_name and pen_name in sender_name:
                label = CLIENT_LABEL_MAP.get(client_name)
                return {
                    "client": client["name"],
                    "method": "name_fragment",
                    "label": label,
                    "confidence": "medium",
                }

        return None

    def _is_prg_newsletter(self, message: EmailMessage) -> bool:
        """Detect PRG newsletter content: known PRG members emailing the hub."""
        sender_email = message.sender_email.lower()

        # Check if sender is on a PRG gaggle list (in CC/To or sender)
        for gaggle in self._prg_gaggle_lists:
            if gaggle.lower() in message.to.lower():
                return True

        # Check if sender is a known PRG member
        for member_email in self._prg_members:
            if member_email.lower() == sender_email:
                return True

        # Check if delivered to PRG-related addresses
        delivered_to = message.delivered_to.lower()
        prg_addresses = {"grannynewsletter@gmail.com", "pdxraginggrannies@gmail.com"}
        if delivered_to in prg_addresses:
            return True

        return False

    def _detect_priority(
        self, message: EmailMessage, classification: EmailClassification
    ) -> dict[str, Any]:
        """Determine message priority."""
        # High-priority sender
        if classification.matched_client:
            client_lower = classification.matched_client.lower()
            for name_frag in HIGH_PRIORITY_SENDERS:
                if name_frag in client_lower:
                    return {
                        "level": "high",
                        "reason": f"{classification.matched_client} is a high-priority contact",
                    }

        # Keyword scan in subject + snippet
        text_to_scan = f"{message.subject} {message.snippet}"
        match = PRIORITY_KEYWORDS.search(text_to_scan)
        if match:
            return {
                "level": "high",
                "reason": f"Contains priority keyword: {match.group()}",
            }

        return {"level": "normal"}

    def _resolve_label_id(self, label_name: str) -> str | None:
        """Look up a label ID from the cached label map. Returns None if not cached yet."""
        # This will be populated after gmail_client.get_labels() has been called
        label_map = gmail_client._label_cache
        return label_map.get(label_name)

    async def classify_batch(self, messages: list[EmailMessage]) -> list[EmailClassification]:
        """Classify a batch of messages, skipping those with existing user labels."""
        results = []
        for msg in messages:
            if self.has_user_labels(msg):
                continue
            results.append(self.classify(msg))
        return results

    async def generate_digest(
        self,
        messages: list[EmailMessage],
        classifications: list[EmailClassification],
    ) -> DailyDigest:
        """Build a daily digest from messages and their classifications."""
        class_map = {c.message_id: c for c in classifications}

        priority_items = []
        newsletter_candidates = []
        needs_review = []
        label_groups: dict[str, list[EmailMessage]] = {}

        for msg in messages:
            cls = class_map.get(msg.id)

            # Priority items
            if cls and cls.priority in ("high", "urgent"):
                priority_items.append(cls)

            # Newsletter candidates
            if cls and cls.is_prg_newsletter:
                newsletter_candidates.append(msg)

            # Needs manual review
            if cls and cls.needs_manual_review:
                needs_review.append(msg)

            # Group by label
            user_labels = [
                lbl for lbl in msg.labels
                if not any(lbl.startswith(prefix) for prefix in SYSTEM_LABEL_PREFIXES)
            ]
            if user_labels:
                for lbl in user_labels:
                    label_groups.setdefault(lbl, []).append(msg)
            elif cls and cls.suggested_label:
                label_groups.setdefault(f"(suggested) {cls.suggested_label}", []).append(msg)
            else:
                label_groups.setdefault("(unlabeled)", []).append(msg)

        by_label = [
            DigestGroup(label=lbl, messages=msgs, count=len(msgs))
            for lbl, msgs in sorted(label_groups.items())
        ]

        return DailyDigest(
            generated_at=datetime.now(),
            total_messages=len(messages),
            priority_items=priority_items,
            newsletter_candidates=newsletter_candidates,
            needs_review=needs_review,
            by_label=by_label,
        )


# Shared instance
email_triage = EmailTriageService()
