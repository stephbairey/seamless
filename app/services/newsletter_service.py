"""Newsletter collection, classification, headline generation, and editorial rewriting for PRG newsletter."""

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

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

    # --- Rewrite ---

    async def rewrite_item(self, item: NewsletterItem) -> dict:
        """Editorially rewrite a single newsletter item. Returns updates dict."""
        # Infer rewrite_type from category if not set
        rewrite_type = item.rewrite_type or self._infer_rewrite_type(item)

        # Check staleness
        is_stale, stale_reason = self._check_stale(item)

        # Personal share: skip LLM, preserve raw text
        if rewrite_type == "personal_share":
            body = self._format_as_html_fragment(item.body_text)
            return {
                "rewritten_body": body,
                "rewrite_type": rewrite_type,
                "rewrite_status": "skipped",
                "is_stale": is_stale,
                "stale_reason": stale_reason,
            }

        # Fetch external content for article_share
        fetched_content = ""
        if rewrite_type == "article_share" and item.source_url:
            fetched_content = await self._fetch_url_text(item.source_url)

        # Build prompts
        system_prompt = self._build_rewrite_prompt(rewrite_type)
        user_msg = self._build_rewrite_user_message(
            item, rewrite_type, fetched_content,
        )

        # Call LLM
        raw = await self._call_anthropic(system_prompt, user_msg, max_tokens=1500)

        # Post-process
        rewritten = self._postprocess_rewrite(raw)

        # Run text checker
        violations = self._text_checker.check_tier1(rewritten, "prg")
        if violations:
            logger.warning(
                "Rewrite has %d violations for item %s, retrying",
                len(violations), item.id,
            )
            violation_feedback = ", ".join(v.description for v in violations)
            retry_msg = (
                f"{user_msg}\n\n"
                f"Previous rewrite was rejected. Issues: {violation_feedback}\n"
                f"Rewrite again, fixing those issues."
            )
            raw = await self._call_anthropic(system_prompt, retry_msg, max_tokens=1500)
            rewritten = self._postprocess_rewrite(raw)

        return {
            "rewritten_body": rewritten,
            "rewrite_type": rewrite_type,
            "rewrite_status": "done",
            "is_stale": is_stale,
            "stale_reason": stale_reason,
        }

    async def rewrite_all(self, items: list[NewsletterItem]) -> list[NewsletterItem]:
        """Rewrite all included items with pending rewrite status."""
        updated = []
        for item in items:
            if item.status != "included":
                continue
            if item.rewrite_status not in ("pending", ""):
                continue
            result = await self.rewrite_item(item)
            newsletter_store.update_item(item.id, result)
            for k, v in result.items():
                if hasattr(item, k):
                    setattr(item, k, v)
            updated.append(item)
        return updated

    def _infer_rewrite_type(self, item: NewsletterItem) -> str:
        """Map category to default rewrite_type."""
        mapping = {
            "action_item": "action_item",
            "team_note": "meeting_notes_attachment" if item.source_url else "meeting_notes_inline",
            "article": "article_share",
            "joana_rollup": "joana_rollup",
        }
        return mapping.get(item.category, "action_item")

    def _check_stale(self, item: NewsletterItem) -> tuple[bool, str]:
        """Check if item event_date is before the next Thursday (send date)."""
        if not item.event_date:
            return False, ""
        try:
            event = datetime.strptime(item.event_date, "%Y-%m-%d").date()
        except ValueError:
            return False, ""

        # Find next Thursday
        today = datetime.now(timezone.utc).date()
        days_until_thursday = (3 - today.weekday()) % 7
        if days_until_thursday == 0 and datetime.now(timezone.utc).hour >= 12:
            days_until_thursday = 7
        next_thursday = today + timedelta(days=days_until_thursday)

        if event < next_thursday:
            return True, f"Event date {item.event_date} is before send date {next_thursday.isoformat()}"
        return False, ""

    def _format_as_html_fragment(self, text: str) -> str:
        """Convert plain text to HTML fragment with <br/> breaks (for personal_share)."""
        if not text.strip():
            return ""
        import html as html_mod
        text = html_mod.escape(text, quote=False)
        # Double newlines -> paragraph breaks
        text = re.sub(r'\n\s*\n', '\n<br/>\n<br/>', text)
        # Single newlines -> line breaks
        text = text.replace("\n", "\n<br/>")
        # Clean up any triple+ <br/>
        text = re.sub(r'(<br/>\s*){3,}', '<br/>\n<br/>', text)
        return text.strip()

    async def _fetch_url_text(self, url: str) -> str:
        """Fetch a URL and extract text content for article summaries."""
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning("URL fetch failed (%s): %s", resp.status_code, url)
                    return ""
                html_content = resp.text
                # Strip HTML tags for readable text
                text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                return text[:4000]
        except Exception as e:
            logger.warning("URL fetch error for %s: %s", url, e)
            return ""

    def _build_rewrite_user_message(
        self, item: NewsletterItem, rewrite_type: str, fetched_content: str,
    ) -> str:
        """Build the user message for the rewrite LLM call."""
        parts = [
            f"Rewrite this newsletter item (type: {rewrite_type}):",
            f"\nFrom: {item.sender_name}",
            f"Subject: {item.subject}",
        ]
        if item.event_date:
            parts.append(f"Event date: {item.event_date}")
        if item.source_url:
            parts.append(f"Source URL: {item.source_url}")

        parts.append(f"\nEmail body:\n{item.body_text[:3000]}")

        if fetched_content:
            parts.append(f"\nFetched article content:\n{fetched_content}")

        if item.extra_context:
            parts.append(f"\nAdditional context from editor:\n{item.extra_context}")

        if item.source_url:
            parts.append(
                f"\nUse this URL for the &raquo; link at the end: {item.source_url}"
            )

        return "\n".join(parts)

    def _build_rewrite_prompt(self, rewrite_type: str) -> str:
        """Build the system prompt for editorial rewriting, specific to item type."""
        voice = self._voice_profiles.get_profile("prg")

        parts = [
            "You are rewriting email content for the Portland Raging Grannies weekly newsletter.",
            "Your output is an HTML fragment that goes inside a <p class=\"body\"> tag.",
            "",
            "OUTPUT FORMAT RULES:",
            "- Use <br/> on its own line for line breaks. Use <br/> then <br/> for paragraph breaks.",
            "- Use <strong> for bold (never <b>, never markdown **bold**).",
            "- Use &raquo; INSIDE link tags: <a href=\"URL\">&raquo; Link text</a>. The &raquo; must be inside the <a>, not before it.",
            "- Use &amp; for ampersands, &hellip; for ellipsis.",
            "- When an email address appears, wrap it in a mailto link: <a href=\"mailto:user@example.com\">user@example.com</a>",
            "- NO <p> tags (your output goes inside an existing <p>).",
            "- NO em dashes. Zero. Replace with commas, periods, colons, or restructure.",
            "- NO double hyphens (--). Use single hyphen surrounded by spaces ( - ) if needed.",
            "- Do NOT include the 'From: Name' attribution line. The system adds that separately.",
            "- Do NOT include a headline/title. The system handles that separately.",
            "- Output ONLY the body content fragment.",
            "",
            "IMPORTANT: Work with whatever content you have. If the email body is thin or missing details,",
            "write the best rewrite you can from what's available. Never ask the editor to resend or provide more info.",
            "If key details (date, location) are missing, simply omit those lines rather than inserting placeholders.",
            "",
        ]

        # Type-specific instructions
        type_instructions = {
            "action_item": [
                "TYPE: ACTION ITEM / EVENT ANNOUNCEMENT",
                "Lead with what the event is and when it is.",
                "Second line: Location with full street address (grannies need GPS-ready addresses).",
                "Follow with: what to bring, what to wear, how to RSVP, contact info.",
                "Use separate lines with <br/> for scannable details.",
                "Strip email scaffolding ('Hi Steph', 'wanted to make sure', etc.).",
                "If there are multiple dates in one email, keep them all clearly labeled.",
                "Spell out acronyms on first use (except ICE, PRG).",
            ],
            "meeting_notes_inline": [
                "TYPE: MEETING NOTES (INLINE)",
                "Minimal rewrite. Preserve the original voice and informal tone.",
                "Format structure: meeting date/time/platform, attendance list, then agenda topics.",
                "Add <strong> tags to agenda topic headers to make them scannable.",
                "Do NOT clean up language. Do NOT make it sound more formal. Reproduce, don't summarize.",
                "Fix obvious typos only.",
            ],
            "meeting_notes_attachment": [
                "TYPE: MEETING NOTES (ATTACHMENT/PDF)",
                "Write ONE teaser sentence + a link. That's all.",
                "Example: 'Catch up with what the [Team Name] team discussed at their latest meeting.'",
                "End with a &raquo; link: '&raquo; Read the meeting notes'",
                "Spell out team abbreviations: RIJ = Racial and Immigration Justice, GAGH = Grannies Against Gun Harm.",
            ],
            "article_share": [
                "TYPE: ARTICLE / VIDEO SHARE",
                "Write a 2-3 paragraph summary:",
                "Paragraph 1: Who made this, what it is, why it exists. Be specific with names, events, dates.",
                "Paragraph 2: Core content. Pull 1-2 specific, visceral quotes. Not 'this is important' but the actual argument.",
                "Paragraph 3 (optional): Brief connection to grannies' work. One sentence.",
                "End with a contextual &raquo; link (e.g., '&raquo; Read on Substack', '&raquo; Watch the video').",
                "Attribution goes to whoever submitted it, not the article author (article author goes in body copy).",
                "If fetched article content is provided, summarize from that. If not, work with the email body.",
            ],
            "joana_rollup": [
                "TYPE: JOANA ROLLUP SUB-ITEM",
                "Produce ONLY one sub-item fragment. Do NOT build the full rollup card.",
                "Format: <strong>Title - Date</strong> on one line,",
                "then <br/> and one descriptive sentence about what this is and why a granny might care,",
                "then <br/> and one <a href=\"URL\">&raquo; contextual link text</a>.",
                "Use the source_url if provided for the link. If no URL is available, omit the link line.",
                "The compiler will assemble multiple sub-items into the full rollup card.",
            ],
        }

        instructions = type_instructions.get(rewrite_type, type_instructions["action_item"])
        parts.extend(instructions)

        # Voice profile
        if voice:
            parts.append("")
            if voice.get("register"):
                parts.append(f"VOICE: {voice['register']}")
            if voice.get("avoids"):
                avoids = voice["avoids"]
                if isinstance(avoids, list):
                    parts.append(f"AVOID: {', '.join(avoids)}")

        # AI tells blacklist
        ai_tells = yaml_store.read("ai-tells.yaml")
        banned_words = [entry["word"] for entry in ai_tells.get("banned_vocabulary", [])]
        if banned_words:
            parts.append(f"\nBANNED WORDS (never use): {', '.join(banned_words)}")

        banned_patterns = [
            entry.get("label", "")
            for entry in ai_tells.get("banned_patterns", [])
            if entry.get("label")
        ]
        if banned_patterns:
            parts.append(f"BANNED PATTERNS: {', '.join(banned_patterns)}")

        return "\n".join(parts)

    def _postprocess_rewrite(self, raw: str) -> str:
        """Clean up LLM rewrite output."""
        text = raw.strip()
        # Strip stray <p> tags
        text = re.sub(r'</?p[^>]*>', '', text)
        # Convert markdown bold to <strong>
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Convert markdown italic to <em>
        text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
        # Normalize <br> variants to <br/>
        text = re.sub(r'<br\s*/?>', '<br/>', text)
        # Fix raquo outside links: "&raquo; <a href=...>text</a>" -> "<a href=...>&raquo; text</a>"
        text = re.sub(r'&raquo;\s*<a\s+href="([^"]+)">', r'<a href="\1">&raquo; ', text)
        # Wrap bare email addresses in mailto links (skip ones already inside an <a> tag)
        text = re.sub(
            r'(?<!href="mailto:)(?<!">)\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b(?!</a>)',
            r'<a href="mailto:\1">\1</a>',
            text,
        )
        # Strip leading/trailing <br/>
        text = re.sub(r'^(<br/>\s*)+', '', text)
        text = re.sub(r'(<br/>\s*)+$', '', text)
        return text.strip()

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
