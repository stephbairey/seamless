"""Newsletter collection, classification, and headline generation for PRG newsletter."""

import logging
import re
import uuid
from datetime import datetime, timezone

import httpx

from app.config import ANTHROPIC_API_KEY
from app.models.newsletter import NewsletterItem
from app.services.gmail_client import gmail_client
from app.services.newsletter_store import newsletter_store
from app.services.text_checker import TextChecker
from app.services.voice_profiles import VoiceProfileService
from app.services.yaml_store import yaml_store

logger = logging.getLogger(__name__)

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-6"

CATEGORY_LABELS = {
    "action_item": "Action Item",
    "team_note": "Team Note",
    "article": "Article",
    "joana_rollup": "Joana Rollup",
    "uncategorized": "Uncategorized",
}


class NewsletterService:
    def __init__(self):
        self._voice_profiles = VoiceProfileService()
        self._text_checker = TextChecker()

    async def collect_from_gmail(self, days_back: int = 7) -> list[NewsletterItem]:
        """Fetch emails labeled PRG/Newsletter and add new ones to the current issue."""
        query = f"label:PRG/Newsletter newer_than:{days_back}d"
        msg_stubs = await gmail_client.list_messages(query=query, max_results=100)

        if not msg_stubs:
            return []

        # Get existing gmail_msg_ids to dedup
        issue = newsletter_store.get_current_issue()
        existing_ids = {i.gmail_msg_id for i in issue.items if i.gmail_msg_id}

        new_items = []
        for stub in msg_stubs:
            if stub["id"] in existing_ids:
                continue

            msg = await gmail_client.get_message(stub["id"])

            # Parse sender display name
            sender_name = msg.sender
            if "<" in sender_name:
                sender_name = sender_name.split("<")[0].strip().strip('"')

            item = NewsletterItem(
                id=uuid.uuid4().hex,
                source="gmail",
                gmail_msg_id=msg.id,
                sender_name=sender_name,
                sender_email=msg.sender_email,
                subject=msg.subject,
                body_text=msg.body_text,
                body_html=msg.body_html,
                is_multipart_related=msg.is_multipart_related,
                category="uncategorized",
                headline="",
                status="collected",
                collected_at=datetime.now(timezone.utc),
                email_date=msg.date,
            )
            newsletter_store.add_item(item)
            new_items.append(item)

        return new_items

    def create_manual_item(
        self, sender_name: str, subject: str, body_text: str,
        category: str = "uncategorized",
    ) -> NewsletterItem:
        """Create a manually-entered newsletter item."""
        item = NewsletterItem(
            id=uuid.uuid4().hex,
            source="manual",
            sender_name=sender_name,
            subject=subject,
            body_text=body_text,
            category=category if category in CATEGORY_LABELS else "uncategorized",
            headline="",
            status="collected",
            collected_at=datetime.now(timezone.utc),
        )
        newsletter_store.add_item(item)
        return item

    async def classify_item(self, item: NewsletterItem) -> tuple[str, str]:
        """Classify a newsletter item and extract event date.

        Returns (category, event_date) where event_date is YYYY-MM-DD or empty.
        """
        # Joana shortcut
        name_lower = item.sender_name.lower()
        if "joana" in name_lower or "kirchhoff" in name_lower:
            return "joana_rollup", ""

        system_prompt = self._build_classify_prompt()
        user_message = (
            f"Classify this newsletter item:\n\n"
            f"From: {item.sender_name}\n"
            f"Subject: {item.subject}\n\n"
            f"{item.body_text[:2000]}"
        )

        result = await self._call_anthropic(system_prompt, user_message, max_tokens=80)
        result = result.strip()

        # Parse "category|YYYY-MM-DD" or just "category"
        category = "uncategorized"
        event_date = ""
        parts = result.split("|", 1)
        cat_part = parts[0].strip().lower().replace(" ", "_")
        if cat_part in CATEGORY_LABELS:
            category = cat_part
        if len(parts) > 1:
            date_part = parts[1].strip()
            if re.match(r"^\d{4}-\d{2}-\d{2}$", date_part) and date_part != "none":
                event_date = date_part

        return category, event_date

    async def generate_headline(self, item: NewsletterItem) -> str:
        """Generate a 5-12 word headline for a newsletter item."""
        system_prompt = self._build_headline_prompt()
        user_message = (
            f"Write a headline for this newsletter item:\n\n"
            f"From: {item.sender_name}\n"
            f"Subject: {item.subject}\n\n"
            f"{item.body_text[:2000]}"
        )

        headline = await self._call_anthropic(system_prompt, user_message, max_tokens=100)
        headline = headline.strip().strip('"').strip("'")

        # Post-check with text checker
        violations = self._text_checker.check_tier1(headline, "prg")
        if violations:
            logger.warning(
                "Headline has %d violations, regenerating: %s",
                len(violations), headline,
            )
            # Try once more with explicit violation feedback
            retry_prompt = (
                f"{user_message}\n\n"
                f"Previous headline was rejected: \"{headline}\"\n"
                f"Issues: {', '.join(v.description for v in violations)}\n"
                f"Write a corrected headline."
            )
            headline = await self._call_anthropic(system_prompt, retry_prompt, max_tokens=100)
            headline = headline.strip().strip('"').strip("'")

        return headline

    async def classify_and_headline_all(self, items: list[NewsletterItem]) -> list[NewsletterItem]:
        """Classify and generate headlines for all uncategorized items."""
        updated = []
        for item in items:
            if item.category == "uncategorized" or not item.headline:
                category, event_date = await self.classify_item(item)
                headline = await self.generate_headline(item)
                newsletter_store.update_item(item.id, {
                    "category": category,
                    "headline": headline,
                    "event_date": event_date,
                    "status": "included",
                })
                item.category = category
                item.headline = headline
                item.event_date = event_date
                item.status = "included"
                updated.append(item)
        return updated

    def _build_classify_prompt(self) -> str:
        """Build system prompt for classification + event date extraction."""
        voice = self._voice_profiles.get_profile("prg")
        parts = [
            "You are classifying items for the Portland Raging Grannies weekly newsletter.",
            "",
            "Categories:",
            "- action_item: Events, rallies, calls to action, things grannies should DO",
            "- team_note: Committee updates, organizational business, internal granny matters",
            "- article: News articles, opinion pieces, poetry, forwarded content, shared links",
            "- joana_rollup: Items from Joana Kirchhoff (handled separately, you should not see these)",
            "",
            "Also extract the event date if the content mentions a specific date for an event, meeting, rally, or deadline.",
            "",
            "Response format: category|YYYY-MM-DD",
            "If no event date: category|none",
            "Examples: action_item|2026-03-15   team_note|none   article|none",
            "",
            "Respond with ONLY the category and date in the format above, nothing else.",
            "If unsure of category, respond: uncategorized|none",
        ]
        if voice and voice.get("register"):
            parts.insert(1, f"Newsletter voice: {voice['register']}")
        return "\n".join(parts)

    def _build_headline_prompt(self) -> str:
        """Build system prompt for headline generation."""
        voice = self._voice_profiles.get_profile("prg")
        parts = [
            "You are writing a headline for the Portland Raging Grannies weekly newsletter.",
            "Write ONLY the headline text, nothing else.",
            "",
            "Rules:",
            "- 5-12 words",
            "- Direct and clear",
            "- No clickbait",
            "- No em dashes",
            "- No quotation marks around your response",
            "- Match the granny voice: direct, political, no sanitizing",
        ]

        # AI tells blacklist
        ai_tells = yaml_store.read("ai-tells.yaml")
        banned_words = [entry["word"] for entry in ai_tells.get("banned_vocabulary", [])]
        if banned_words:
            parts.append(f"\nBANNED WORDS (never use): {', '.join(banned_words)}")

        if voice:
            if voice.get("avoids"):
                avoids = voice["avoids"]
                if isinstance(avoids, list):
                    parts.append(f"\nAVOID: {', '.join(avoids)}")

        return "\n".join(parts)

    async def _call_anthropic(self, system_prompt: str, user_message: str, max_tokens: int = 1024) -> str:
        """Call Anthropic Messages API."""
        if not ANTHROPIC_API_KEY:
            return "(Anthropic API key not configured. Add ANTHROPIC_API_KEY to secrets.env.)"

        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(ANTHROPIC_MESSAGES_URL, json=payload, headers=headers)
                if resp.status_code != 200:
                    logger.error("Anthropic API error: %s %s", resp.status_code, resp.text)
                    return f"(Classification failed: {resp.status_code})"
                data = resp.json()
                content_blocks = data.get("content", [])
                text_parts = [b["text"] for b in content_blocks if b.get("type") == "text"]
                return "\n".join(text_parts)
        except httpx.TimeoutException:
            logger.error("Anthropic API timeout")
            return "(Request timed out. Try again.)"
        except Exception as e:
            logger.exception("Anthropic API call failed")
            return f"(Request failed: {e})"


# Shared instance
newsletter_service = NewsletterService()
