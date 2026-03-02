"""Identity-aware reply drafting with LLM generation via Anthropic API."""

import logging
from typing import Any

import httpx

from app.config import ANTHROPIC_API_KEY
from app.models.email import EmailMessage, ReplyDraft
from app.services.email_triage import email_triage
from app.services.identity_router import IdentityRouter
from app.services.text_checker import TextChecker
from app.services.voice_profiles import VoiceProfileService
from app.services.yaml_store import yaml_store

logger = logging.getLogger(__name__)

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-6"


class ReplyDrafter:
    def __init__(self):
        self._identity_router = IdentityRouter()
        self._voice_profiles = VoiceProfileService()
        self._text_checker = TextChecker()
        self._identities: list[dict] = []
        self._loaded = False

    def _load(self):
        email_data = yaml_store.read("email-identities.yaml")
        self._identities = email_data.get("identities", [])
        self._loaded = True

    def _ensure_loaded(self):
        if not self._loaded:
            self._load()

    @property
    def is_configured(self) -> bool:
        return bool(ANTHROPIC_API_KEY)

    def resolve_send_as(self, message: EmailMessage) -> dict[str, str]:
        """Determine correct Send-As identity for a reply.

        Logic:
        1. Check delivered_to header to find which address received the message
        2. Match to an identity in email-identities.yaml
        3. Check for client override (relationship-based name sticking)
        4. Return send_as email, display name, and voice_id
        """
        self._ensure_loaded()

        delivered_to = message.delivered_to.lower().strip()
        sender_email = message.sender_email.lower().strip()

        # Step 1: Find identity matching delivered_to
        identity = None
        identity_context = None
        for ident in self._identities:
            if ident["address"].lower() == delivered_to:
                identity = ident
                identity_context = ident.get("identity_context", "")
                break

        # Fallback: if no delivered_to match, use the hub account
        if not identity:
            for ident in self._identities:
                if ident["address"].lower() == "stephbairey@gmail.com":
                    identity = ident
                    identity_context = ident.get("identity_context", "")
                    break

        if not identity:
            return {
                "send_as": "stephbairey@gmail.com",
                "send_as_name": "Steph Bairey",
                "voice_id": "",
            }

        send_as = identity["address"]
        send_as_name = identity.get("display_name", "")

        # Step 2: Resolve voice_id from identity context
        voice_id = ""
        if identity_context:
            ctx = self._identity_router.get_by_id(identity_context)
            if ctx:
                voice_id = ctx.voice_id or ""
                # Use context's name if available
                if ctx.name:
                    send_as_name = ctx.name

        # Step 3: Check for client override
        classification = email_triage.classify(message)
        if classification.matched_client:
            override = self._identity_router.get_client_override(classification.matched_client)
            if override and override.known_as:
                # Override the display name but keep the email
                if override.known_as == "Maya":
                    send_as_name = "Maya Bairey"
                elif override.known_as == "Steph":
                    send_as_name = "Steph Bairey"

        return {
            "send_as": send_as,
            "send_as_name": send_as_name,
            "voice_id": voice_id,
        }

    async def generate_draft(
        self, message: EmailMessage, send_as_info: dict[str, str],
        user_instructions: str = "",
    ) -> ReplyDraft:
        """Generate an LLM reply draft using the correct voice profile."""
        voice_id = send_as_info["voice_id"]
        voice_profile = self._voice_profiles.get_profile(voice_id) if voice_id else None

        # Build system prompt
        system_prompt = self._build_system_prompt(voice_profile, send_as_info, message)

        # Build user message
        user_message = self._build_user_message(message, user_instructions)

        # Call Anthropic API
        body_text = await self._call_anthropic(system_prompt, user_message)

        # Run text checker on output
        violations = []
        if body_text:
            raw_violations = self._text_checker.check(body_text, voice_id)
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

        # Build reply subject
        subject = message.subject
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        return ReplyDraft(
            message_id=message.id,
            thread_id=message.thread_id,
            send_as=send_as_info["send_as"],
            send_as_name=send_as_info["send_as_name"],
            voice_id=voice_id,
            to=message.sender_email or message.sender,
            subject=subject,
            in_reply_to=message.message_id,
            body=body_text,
            violations=violations,
        )

    def _build_system_prompt(
        self, voice_profile: dict[str, Any] | None,
        send_as_info: dict[str, str],
        message: EmailMessage,
    ) -> str:
        """Build the system prompt with voice profile, em dash rules, and AI tells."""
        parts = [
            "You are drafting an email reply. Write ONLY the reply body text, no subject line, no greeting like 'Dear X' unless appropriate for the voice.",
            f"\nYou are replying as: {send_as_info['send_as_name']} <{send_as_info['send_as']}>",
        ]

        if voice_profile:
            parts.append(f"\n## Voice Profile: {voice_profile.get('label', '')}")
            if voice_profile.get("register"):
                parts.append(f"Register: {voice_profile['register']}")
            if voice_profile.get("rhythm"):
                parts.append(f"Rhythm: {voice_profile['rhythm']}")
            if voice_profile.get("characteristics"):
                chars = voice_profile["characteristics"]
                if isinstance(chars, list):
                    parts.append(f"Characteristics: {', '.join(chars)}")
                else:
                    parts.append(f"Characteristics: {chars}")
            if voice_profile.get("sign_off"):
                parts.append(f"Sign-off: {voice_profile['sign_off']}")

            # Em dash mode
            em_mode = voice_profile.get("em_dash_mode", "restricted")
            if em_mode == "banned":
                parts.append("\nEM DASHES: BANNED. Do not use em dashes (—) under any circumstances. Use periods, commas, colons, or restructure.")
            elif em_mode == "restricted":
                parts.append("\nEM DASHES: RESTRICTED. Only use em dashes as mid-sentence parentheticals (paired). Never use to extend a thought.")
            elif em_mode == "na":
                parts.append("\nEM DASHES: Do not use any personality markers including em dashes.")

            # Avoids
            if voice_profile.get("avoids"):
                avoids = voice_profile["avoids"]
                if isinstance(avoids, list):
                    parts.append(f"\nAVOID: {', '.join(avoids)}")
                else:
                    parts.append(f"\nAVOID: {avoids}")

        # AI tells blacklist
        ai_tells = yaml_store.read("ai-tells.yaml")
        banned_words = [entry["word"] for entry in ai_tells.get("banned_vocabulary", [])]
        if banned_words:
            parts.append(f"\nBANNED WORDS (never use): {', '.join(banned_words)}")

        banned_patterns = [entry.get("label", "") for entry in ai_tells.get("banned_patterns", [])]
        if banned_patterns:
            parts.append(f"\nBANNED PATTERNS: {'; '.join(banned_patterns)}")

        parts.append("\nThe test: 'Does this sound like me?' not 'Does this sound like AI?' Write naturally, not generically.")

        return "\n".join(parts)

    def _build_user_message(self, message: EmailMessage, user_instructions: str = "") -> str:
        """Build the user message with the original email context."""
        parts = [
            f"Reply to this email:\n",
            f"From: {message.sender}",
            f"Subject: {message.subject}",
            f"Date: {message.date.strftime('%b %d, %Y at %H:%M') if message.date else 'unknown'}",
            f"\n{message.body_text or message.snippet}",
        ]

        if user_instructions:
            parts.append(f"\n---\nInstructions for the reply: {user_instructions}")

        return "\n".join(parts)

    async def _call_anthropic(self, system_prompt: str, user_message: str) -> str:
        """Call Anthropic Messages API to generate reply text."""
        if not ANTHROPIC_API_KEY:
            return "(Anthropic API key not configured. Add ANTHROPIC_API_KEY to secrets.env.)"

        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 1024,
            "temperature": 0.7,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(ANTHROPIC_MESSAGES_URL, json=payload, headers=headers)
                if resp.status_code != 200:
                    logger.error("Anthropic API error: %s %s", resp.status_code, resp.text)
                    return f"(Draft generation failed: {resp.status_code})"
                data = resp.json()
                content_blocks = data.get("content", [])
                text_parts = [b["text"] for b in content_blocks if b.get("type") == "text"]
                return "\n".join(text_parts)
        except httpx.TimeoutException:
            logger.error("Anthropic API timeout")
            return "(Draft generation timed out. Try again.)"
        except Exception as e:
            logger.exception("Anthropic API call failed")
            return f"(Draft generation failed: {e})"

    def check_text(self, text: str, voice_id: str = "") -> list[dict]:
        """Run text checker on edited draft text."""
        violations = self._text_checker.check(text, voice_id)
        return [
            {
                "rule_id": v.rule_id,
                "label": v.label,
                "severity": v.severity,
                "description": v.description,
                "matched_text": v.matched_text,
                "suggestion": v.suggestion,
            }
            for v in violations
        ]


# Shared instance
reply_drafter = ReplyDrafter()
