"""HTML compilation for PRG newsletter — full standalone email document."""

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

# --- Inline style constants ---

ITEM_CARD_STYLE = (
    'max-width: 650px;margin: 20px auto;background: #ffffff;'
    'border-radius: 6px;box-shadow: 0 0 6px rgba(0, 0, 0, .15);'
    'padding: 0 40px 40px 40px;'
)

TITLE_STYLE = (
    'font-size:20px;font-weight:700;color:#d6616c;'
    'margin:30px 0 6px 0;mso-margin-top-alt:30px;'
    'border-top:3px solid #d6616c;padding: 27px 0 27px 0;'
)

BODY_STYLE = (
    'font-size:14px;font-weight:400;line-height:1.55;margin:0 0 6px 0;'
)

TOC_LI_STYLE = (
    'list-style:disc;font-size:14px;font-weight:600;margin:0 0 8px 0;'
)


class NewsletterCompiler:
    def __init__(self):
        self._text_checker = TextChecker()

    def compile(self, issue: NewsletterIssue) -> NewsletterCompilation:
        """Compile included items into a full standalone HTML email document."""
        items = [i for i in issue.items if i.status == "included"]
        if not items:
            return NewsletterCompilation(
                issue=issue, html="", toc_headlines=[], item_count=0, violations=[],
            )

        # Sort: category priority, event_date, display_order
        _no_date = "9999-99-99"
        items.sort(key=lambda i: (
            CATEGORY_PRIORITY.get(i.category, 4),
            i.event_date if i.event_date else _no_date,
            i.display_order,
        ))

        # Merge joana_rollup items into one synthetic card
        items = self._merge_joana_items(items)

        # Build ToC and item cards
        toc_entries = []
        item_cards = []
        toc_headlines = []

        for item in items:
            headline = self._sanitize(item.headline or item.subject)
            toc_headlines.append(headline)
            toc_entries.append(self._build_toc_entry(headline))
            item_cards.append(self._build_item_card(item, headline))

        toc_html = "\n".join(toc_entries)
        items_html = "\n\n".join(item_cards)

        full_html = self._build_full_document(issue, toc_html, items_html)

        # QC checks
        qc_violations = self._run_qc_checks(toc_headlines, full_html)

        # Text checker on all prose content
        all_text = " ".join(
            f"{i.headline} {i.rewritten_body or i.body_text}" for i in items
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
        violations.extend(qc_violations)

        issue.compiled_html = full_html
        issue.status = "review"

        return NewsletterCompilation(
            issue=issue,
            html=full_html,
            toc_headlines=toc_headlines,
            item_count=len(items),
            violations=violations,
        )

    def _build_full_document(self, issue: NewsletterIssue, toc_html: str, items_html: str) -> str:
        """Assemble the full HTML email document with header, ToC, items, footer."""
        newsletter_date = issue.newsletter_date or "[DATE HERE]"
        next_meeting_day = issue.next_meeting_day or "[Day, Month Date, Year, Time]"
        next_meeting_location = issue.next_meeting_location or "[Venue Name, Address]"

        return f'''<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Portland Raging Grannies Newsletter</title>
    <style>a{{color:#0066cc;text-decoration:underline;}}a:visited{{color:#5b4ab1;}}</style>
  </head>
  <body style="margin:0;padding:0;background:#E6E0E0;font-family:'Helvetica Neue', Helvetica, Arial, sans-serif;font-size:16px;line-height:1.2;color:#000;">
    <span style="display:none !important; opacity:0; color:transparent; height:0; width:0; overflow:hidden;">Portland Raging Grannies Newsletter - latest events, actions, and reminders</span>
    <table bgcolor="#E6E0E0" width="100%" cellspacing="0" cellpadding="0">
      <tr>
        <td>
          <div bgcolor="#E6E0E0" class="frame" style="max-width:650px;margin:20px auto;padding:0 40px 5px 40px;">

            <!-- HEADER + TOC BLOCK -->
            <div class="top-items" style="max-width: 650px;margin: 20px auto;background: #ffffff;border-radius: 6px;box-shadow: 0 0 6px rgba(0, 0, 0, .15);padding: 0 40px 40px 40px;">
              <div class="header" style="font-size:22px;font-weight:700;color:#bd3435;text-align:left;margin: 0px 0 28px 0;padding: 40px 0 0 0px;">
                <img src="https://portland.raginggrannies.org/wp-content/uploads/2025/06/prg-newsletter-logo.jpg" alt="Portland Raging Grannies Newsletter" width="570" height="100" border="0" style="display:block;">
                <br/>
                <center>NEWSLETTER - {newsletter_date}</center>
              </div>
              <div class="subhead" style="font-size:18px;color:#555;line-height:1.3;margin:0 0 24px 0;text-align: center;"><strong>Next Monthly Meeting</strong>
                <br/>{next_meeting_day}
                <br/>Location: {next_meeting_location}
                <br/>
                <br/><em style="font-size:13px;color:gray;">MENTORS: remember to forward this to your mentees!<br/>Long newsletters can be cut off on tablets/phones. For best results, read on desktop/laptop.</em>
              </div>

              <!-- TABLE OF CONTENTS -->
              <div class="toc" style="margin: 0 0 30px 0px;padding: 0;border-top: 3px solid #d6616c;line-height: 14px;">
                <p style="margin: 16px 0 16px 0px;padding: 0;font-size: 20px;color: #d6616c;">IN THIS NEWSLETTER</p>
                <br/>
                <ul style="margin: 0 0 0 0;">
{toc_html}
                </ul>
              </div>
            </div>

            <!-- ITEM CARDS -->
{items_html}

          </div>
          <div class="footer" style="font-size:18px;color:#555;line-height:1.3;margin:0 0 24px 0;text-align: center;"><em>Send newsletter items to <a style="color:blue;" href="mailto:grannynewsletter@gaggle.email">grannynewsletter@gaggle.email</a></em></div>
        </td>
      </tr>
    </table>
  </body>
</html>'''

    def _build_toc_entry(self, headline: str) -> str:
        """Build one <li> for the table of contents."""
        return f'                  <li style="{TOC_LI_STYLE}">{headline}</li>'

    def _build_item_card(self, item: NewsletterItem, headline: str) -> str:
        """Build one div.items card with p.title + p.body."""
        # Use rewritten_body if available, fall back to formatted body_text
        if item.rewritten_body:
            body_content = item.rewritten_body
        else:
            body_content = self._format_body_fallback(item.body_text)

        # Attribution: all items get "From: Name" except joana_rollup
        attribution = ""
        is_joana = item.rewrite_type == "joana_rollup" or item.category == "joana_rollup"
        if not is_joana and item.sender_name:
            sender = self._sanitize(item.sender_name)
            attribution = f"From: {sender}\n    <br/>\n    <br/>"

        return f'''<div class="items" style="{ITEM_CARD_STYLE}">
  <p class="title" style="{TITLE_STYLE}">{headline}</p>
  <p class="body" style="{BODY_STYLE}">{attribution}{body_content}
  </p>
</div>'''

    def _merge_joana_items(self, items: list[NewsletterItem]) -> list[NewsletterItem]:
        """Extract joana_rollup items, merge into one synthetic card, append at end."""
        joana_items = [i for i in items if i.category == "joana_rollup"]
        if not joana_items:
            return items

        non_joana = [i for i in items if i.category != "joana_rollup"]

        # Build merged body from individual sub-item fragments
        sub_fragments = []
        for ji in joana_items:
            fragment = ji.rewritten_body if ji.rewritten_body else self._format_body_fallback(ji.body_text)
            if fragment.strip():
                sub_fragments.append(fragment)

        intro = "Joana shares the following resources and action items for grannies interested in environmental issues."
        merged_body = intro
        if sub_fragments:
            merged_body += "\n    <br/>\n    <br/>" + "\n    <br/>\n    <br/>".join(sub_fragments)

        # Create synthetic item
        synthetic = NewsletterItem(
            id="joana-rollup-merged",
            sender_name="Joana Kirchhoff",
            category="joana_rollup",
            rewrite_type="joana_rollup",
            headline=joana_items[0].headline if len(joana_items) == 1 and joana_items[0].headline else "From Joana Kirchhoff: Environmental Action Links",
            rewritten_body=merged_body,
            rewrite_status="done",
            status="included",
        )

        non_joana.append(synthetic)
        return non_joana

    def _format_body_fallback(self, text: str) -> str:
        """Convert plain text to <br/> format for items without a rewrite."""
        if not text.strip():
            return "(No body text)"

        text = self._sanitize(text)
        # Double newlines -> paragraph breaks
        text = re.sub(r'\n\s*\n', '\n<br/>\n<br/>', text)
        # Single newlines -> line breaks
        text = text.replace("\n", "\n<br/>")
        # Clean up triple+ <br/>
        text = re.sub(r'(<br/>\s*){3,}', '<br/>\n<br/>', text)
        return text.strip()

    def _run_qc_checks(self, toc_headlines: list[str], full_html: str) -> list[dict]:
        """Validate compiled output: no em dashes, no <b>, no nested <p>."""
        violations = []

        # Em dash check
        if "\u2014" in full_html or "\u2015" in full_html:
            violations.append({
                "rule_id": "qc-em-dash",
                "label": "Em dash in compiled HTML",
                "severity": "high",
                "description": "Raw em dash character found in compiled newsletter.",
                "matched_text": None,
                "suggestion": "Replace with comma, period, or restructure.",
            })

        # Double hyphen check
        if re.search(r'(?<!-)--(?!-)', full_html):
            violations.append({
                "rule_id": "qc-double-hyphen",
                "label": "Double hyphen in compiled HTML",
                "severity": "medium",
                "description": "Double hyphen (--) found. Use single hyphen with spaces.",
                "matched_text": None,
                "suggestion": "Replace -- with  -  (space-hyphen-space).",
            })

        # <b> tag check (but not <br, <body, <button, etc.)
        if re.search(r'<b\s*>|<b\s+[^r]', full_html, re.IGNORECASE):
            violations.append({
                "rule_id": "qc-b-tag",
                "label": "<b> tag found",
                "severity": "medium",
                "description": "Use <strong> instead of <b>.",
                "matched_text": None,
                "suggestion": "Replace <b> with <strong>.",
            })

        # Nested <p> check
        if re.search(r'<p[^>]*>.*?<p[^>]*>', full_html, re.DOTALL):
            violations.append({
                "rule_id": "qc-nested-p",
                "label": "Nested <p> tags",
                "severity": "high",
                "description": "Found <p> inside another <p>. This is invalid HTML for email.",
                "matched_text": None,
                "suggestion": "Remove inner <p> tags. Use <br/> for breaks inside <p>.",
            })

        return violations

    def _sanitize(self, text: str) -> str:
        """Clean text: remove em dashes, convert special chars, escape HTML."""
        if not text:
            return ""

        text = html.unescape(text)
        text = html.escape(text, quote=False)

        # Em dash removal (banned in PRG)
        text = text.replace("&mdash;", ",")
        text = re.sub(r'\u2014', ', ', text)
        text = re.sub(r'\u2013', ', ', text)

        # Double hyphens
        text = re.sub(r'(?<!-)--(?!-)', ' - ', text)

        # Ellipsis normalization
        text = text.replace("...", "&hellip;")
        text = text.replace("\u2026", "&hellip;")

        # Smart quotes to straight quotes
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2018", "'").replace("\u2019", "'")

        return text


# Shared instance
newsletter_compiler = NewsletterCompiler()
