"""HTML compilation for PRG newsletter with ToC and text checking."""

import html
import logging
import re

from app.models.newsletter import NewsletterCompilation, NewsletterIssue, NewsletterItem
from app.services.text_checker import TextChecker

logger = logging.getLogger(__name__)

CATEGORY_PRIORITY = {
    "action_item": 0,
    "team_note": 1,
    "article": 2,
    "joana_rollup": 3,
    "uncategorized": 4,
}

CATEGORY_DISPLAY = {
    "action_item": "Action Items",
    "team_note": "Team Notes",
    "article": "Articles &amp; Shares",
    "joana_rollup": "Joana's Rollup",
}


class NewsletterCompiler:
    def __init__(self):
        self._text_checker = TextChecker()

    def compile(self, issue: NewsletterIssue) -> NewsletterCompilation:
        """Compile included items into newsletter HTML."""
        # Filter to included items
        items = [i for i in issue.items if i.status == "included"]
        if not items:
            return NewsletterCompilation(
                issue=issue, html="", toc_headlines=[], item_count=0, violations=[],
            )

        # Sort: category priority, then event_date (earliest first, no-date last), then display_order
        _no_date = "9999-99-99"
        items.sort(key=lambda i: (
            CATEGORY_PRIORITY.get(i.category, 4),
            i.event_date if i.event_date else _no_date,
            i.display_order,
        ))

        # Build HTML
        toc_html, body_html, toc_headlines = self._build_html(items)

        full_html = (
            '<div class="items" style="font-family: \'Helvetica Neue\', Helvetica, Arial, sans-serif;">\n'
            f'{toc_html}\n'
            '<hr style="border: 1px solid #ddd; margin: 24px 0;">\n'
            f'{body_html}\n'
            '</div>'
        )

        # Run text checker on all text content
        all_text = " ".join(
            f"{i.headline} {i.body_text}" for i in items
        )
        raw_violations = self._text_checker.check_tier1(all_text, "prg")
        violations = [
            {
                "rule_id": v.rule_id,
                "label": v.label,
                "severity": v.severity,
                "description": v.description,
                "matched_text": v.matched_text,
                "suggestion": v.suggestion,
            }
            for v in raw_violations
        ]

        issue.compiled_html = full_html
        issue.status = "review"

        return NewsletterCompilation(
            issue=issue,
            html=full_html,
            toc_headlines=toc_headlines,
            item_count=len(items),
            violations=violations,
        )

    def _build_html(self, items: list[NewsletterItem]) -> tuple[str, str, list[str]]:
        """Build ToC and body HTML. Returns (toc_html, body_html, toc_headlines)."""
        toc_parts = []
        body_parts = []
        toc_headlines = []
        current_category = None
        item_num = 0

        for item in items:
            item_num += 1
            anchor_id = f"item-{item_num}"

            # Category header if changed
            if item.category != current_category:
                current_category = item.category
                cat_label = CATEGORY_DISPLAY.get(item.category, item.category.replace("_", " ").title())

                toc_parts.append(
                    f'<h2 style="color: #bd3435; margin: 16px 0 8px 0; font-size: 16px;">{cat_label}</h2>'
                )
                body_parts.append(
                    f'<h2 style="color: #bd3435; margin: 32px 0 16px 0;">{cat_label}</h2>'
                )

            headline = self._sanitize(item.headline or item.subject)
            toc_headlines.append(headline)

            # ToC entry
            toc_parts.append(
                f'<p style="margin: 4px 0 4px 16px;">'
                f'<a href="#{anchor_id}" style="color: #d6616c; text-decoration: none;">'
                f'&raquo; {headline}</a></p>'
            )

            # Body entry
            body_parts.append(
                f'<h3 style="color: #d6616c; margin: 24px 0 8px 0;" id="{anchor_id}">{headline}</h3>'
            )
            if item.sender_name:
                body_parts.append(
                    f'<p style="font-size: 13px; color: #888; margin: 0 0 8px 0;">From {self._sanitize(item.sender_name)}</p>'
                )

            body_text = self._format_body(item.body_text)
            body_parts.append(body_text)

        return "\n".join(toc_parts), "\n".join(body_parts), toc_headlines

    def _format_body(self, text: str) -> str:
        """Convert plain text body to HTML paragraphs."""
        if not text.strip():
            return '<p style="color: #888; font-style: italic;">(No body text)</p>'

        text = self._sanitize(text)

        # Split on double newlines for paragraphs
        paragraphs = re.split(r'\n\s*\n', text)
        html_parts = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            # Convert single newlines to <br/>
            para = para.replace("\n", "<br/>\n")
            html_parts.append(f'<p style="margin: 8px 0;">{para}</p>')

        return "\n".join(html_parts)

    def _sanitize(self, text: str) -> str:
        """Clean text: remove em dashes, convert special chars, escape HTML."""
        if not text:
            return ""

        # Escape HTML entities (but preserve existing entities)
        # First, unescape any existing entities to avoid double-escaping
        text = html.unescape(text)
        text = html.escape(text, quote=False)

        # Em dash removal (banned in PRG)
        text = text.replace("&mdash;", ",")
        # Raw em dashes that survived escaping
        text = re.sub(r'\u2014', ', ', text)
        text = re.sub(r'\u2013', ', ', text)  # en dash too

        # Ellipsis normalization
        text = text.replace("...", "&hellip;")
        text = text.replace("\u2026", "&hellip;")

        # Smart quotes to straight quotes
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2018", "'").replace("\u2019", "'")

        return text


# Shared instance
newsletter_compiler = NewsletterCompiler()
