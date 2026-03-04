"""Social copy generation — multi-platform post generation with voice profiles."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import ANTHROPIC_API_KEY
from app.models.distribution import CopyBatch, CopyRequest, SocialPost
from app.services.brand_tokens import BrandTokenService
from app.services.text_checker import TextChecker
from app.services.voice_profiles import VoiceProfileService
from app.services.yaml_store import yaml_store

logger = logging.getLogger(__name__)

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-6"

# Platform + brand → account/voice/identity mapping
# Each entry: (account_label, voice_id, identity_name)
PLATFORM_CONFIGS: dict[str, dict[str, tuple[str, str, str]]] = {
    "maya-personal": {
        "facebook": ("Maya Bairey (personal)", "maya-personal", "Maya Bairey"),
        "instagram": ("mayabairey", "maya-personal", "Maya Bairey"),
        "linkedin": ("stephbairey", "job-search", "Steph Bairey"),
        "bluesky": ("@mayabairey", "maya-personal", "Maya Bairey"),
    },
    "lib": {
        "facebook": ("Lingua Ink Books", "lib", "Maya Bairey"),
        "instagram": ("linguainkbooks", "lib", "Maya Bairey"),
        "linkedin": ("Lingua Ink Books", "lib", "Maya Bairey"),
        "bluesky": ("@linguainkbooks", "lib", "Maya Bairey"),
    },
    "lim": {
        "linkedin": ("stephbairey", "lim", "Steph Bairey"),
    },
}

# Platform-specific generation rules
PLATFORM_RULES: dict[str, str] = {
    "facebook": (
        "Write a Facebook post. Rules:\n"
        "- Lead with the topic, not a hook or question\n"
        "- Keep it short (1-3 short paragraphs)\n"
        "- First person\n"
        "- End with the URL on its own line, then an engagement question\n"
        "- No hashtags\n"
        "- No emoji unless it fits the voice naturally"
    ),
    "instagram": (
        "Write an Instagram caption. Rules:\n"
        "- Same general approach as a Facebook post\n"
        "- First person\n"
        "- End with 4-8 relevant hashtags on their own line\n"
        "- Always end with: 'Link in bio, always.'\n"
        "- The URL will not be clickable, so don't include it in the caption body\n"
        "- This auto-posts to Threads too"
    ),
    "linkedin": (
        "Write a LinkedIn post. Rules:\n"
        "- Professional framing\n"
        "- Lead with an insight, claim, or observation, then provide context\n"
        "- Clean closer (no 'What do you think?' unless genuinely asking)\n"
        "- No hashtags unless 1-2 are truly relevant\n"
        "- Include the URL naturally"
    ),
    "bluesky": (
        "Write a Bluesky/Threads post. Rules:\n"
        "- STRICT 300 character maximum (including spaces and URL)\n"
        "- Punchy, conversational\n"
        "- Link at end if it fits within the 300 char limit\n"
        "- No hashtags\n"
        "- This is a microblog, not a full post"
    ),
}


class SocialCopyService:
    def __init__(self):
        self._voice_profiles = VoiceProfileService()
        self._text_checker = TextChecker()
        self._brand_tokens = BrandTokenService()

    @property
    def is_configured(self) -> bool:
        return bool(ANTHROPIC_API_KEY)

    def get_platforms_for_brand(self, brand: str) -> list[str]:
        """Return the list of platforms available for a given brand."""
        configs = PLATFORM_CONFIGS.get(brand, {})
        return list(configs.keys())

    async def generate_all_posts(self, request: CopyRequest) -> CopyBatch:
        """Generate social posts for all platforms configured for the selected brand."""
        configs = PLATFORM_CONFIGS.get(request.brand, {})
        if not configs:
            return CopyBatch(
                id=str(uuid.uuid4())[:8],
                created_at=datetime.now(timezone.utc).isoformat(),
                brand=request.brand,
                content_preview=request.content[:200],
                url=request.url,
            )

        posts: list[SocialPost] = []
        for platform, (account, voice_id, identity_name) in configs.items():
            post = await self._generate_single(
                platform=platform,
                account=account,
                voice_id=voice_id,
                identity_name=identity_name,
                content=request.content,
                url=request.url,
                notes=request.notes,
            )
            posts.append(post)

        # Generate marketing extras
        seo_description = await self._generate_seo_description(
            request.content, request.brand,
        )
        midjourney_prompt = await self._generate_midjourney_prompt(
            request.content, request.brand,
        )

        return CopyBatch(
            id=str(uuid.uuid4())[:8],
            created_at=datetime.now(timezone.utc).isoformat(),
            brand=request.brand,
            content_preview=request.content[:200],
            url=request.url,
            posts=posts,
            seo_description=seo_description,
            midjourney_prompt=midjourney_prompt,
        )

    async def regenerate_single(
        self, brand: str, platform: str, content: str, url: str = "", notes: str = "",
    ) -> SocialPost | None:
        """Regenerate copy for a single platform."""
        configs = PLATFORM_CONFIGS.get(brand, {})
        if platform not in configs:
            return None
        account, voice_id, identity_name = configs[platform]
        return await self._generate_single(
            platform=platform,
            account=account,
            voice_id=voice_id,
            identity_name=identity_name,
            content=content,
            url=url,
            notes=notes,
        )

    async def _generate_single(
        self,
        platform: str,
        account: str,
        voice_id: str,
        identity_name: str,
        content: str,
        url: str = "",
        notes: str = "",
    ) -> SocialPost:
        """Generate copy for one platform using the appropriate voice."""
        voice_profile = self._voice_profiles.get_profile(voice_id)
        system_prompt = self._build_system_prompt(voice_profile, identity_name, platform)

        user_message = self._build_user_message(content, platform, url, notes)
        copy_text = await self._call_anthropic(system_prompt, user_message)

        # Extract hashtags from Instagram copy
        hashtags: list[str] = []
        if platform == "instagram" and copy_text:
            hashtags = self._extract_hashtags(copy_text)

        # Run text checker
        violations: list[dict] = []
        if copy_text:
            raw_violations = self._text_checker.check(copy_text, voice_id)
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

        return SocialPost(
            platform=platform,
            account=account,
            voice_id=voice_id,
            identity_name=identity_name,
            body=copy_text,
            hashtags=hashtags,
            violations=violations,
        )

    async def _generate_seo_description(self, content: str, brand: str) -> str:
        """Generate a 150-160 character SEO meta description."""
        system_prompt = (
            "You are writing an SEO meta description. Rules:\n"
            "- STRICT 150-160 character limit (including spaces)\n"
            "- Lead with reader value, not the brand\n"
            "- Include a natural call to action\n"
            "- No quotes around the description\n"
            "- Write ONLY the meta description text, nothing else"
        )
        user_message = f"Write an SEO meta description for this content:\n\n{content}"
        return await self._call_anthropic(system_prompt, user_message)

    async def _generate_midjourney_prompt(self, content: str, brand: str) -> str:
        """Generate a Midjourney image prompt using brand tokens."""
        tokens = self._brand_tokens.get_token(brand)
        imagery = tokens.get("imagery", {}) if tokens else {}
        template = imagery.get("midjourney_template", "")
        style = imagery.get("style", "")
        visual_elements = imagery.get("visual_elements", [])

        system_parts = [
            "You are generating a Midjourney image prompt. Rules:\n"
            "- Write ONLY the prompt text, nothing else\n"
            "- No quotation marks around the prompt\n"
            "- End with --ar 16:9 unless the template specifies otherwise",
        ]

        if template:
            system_parts.append(
                f"\nUse this brand template, filling in the bracketed placeholders: "
                f"{template}"
            )
        elif style:
            system_parts.append(f"\nBrand imagery style: {style}")

        if visual_elements:
            system_parts.append(
                f"\nBrand visual elements to draw from: {', '.join(visual_elements)}"
            )

        system_prompt = "\n".join(system_parts)
        user_message = (
            f"Generate a Midjourney image prompt for a blog post hero image. "
            f"Content summary:\n\n{content[:500]}"
        )
        return await self._call_anthropic(system_prompt, user_message)

    async def regenerate_seo(self, content: str, brand: str) -> str:
        """Regenerate just the SEO description."""
        return await self._generate_seo_description(content, brand)

    async def regenerate_midjourney(self, content: str, brand: str) -> str:
        """Regenerate just the Midjourney prompt."""
        return await self._generate_midjourney_prompt(content, brand)

    def _build_system_prompt(
        self,
        voice_profile: dict[str, Any] | None,
        identity_name: str,
        platform: str,
    ) -> str:
        """Build system prompt with voice profile, platform rules, and AI tells."""
        parts = [
            "You are generating a social media post. Write ONLY the post text, nothing else.",
            f"You are posting as: {identity_name}",
        ]

        # Platform-specific rules
        if platform in PLATFORM_RULES:
            parts.append(f"\n## Platform Rules\n{PLATFORM_RULES[platform]}")

        # Voice profile
        if voice_profile:
            parts.append(f"\n## Voice Profile: {voice_profile.get('label', '')}")
            if voice_profile.get("register"):
                parts.append(f"Register: {voice_profile['register']}")
            if voice_profile.get("sentence_rhythm"):
                parts.append(f"Rhythm: {voice_profile['sentence_rhythm']}")
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
                parts.append(
                    "\nEM DASHES: BANNED. Do not use em dashes (\u2014) under any "
                    "circumstances. Use periods, commas, colons, or restructure."
                )
            elif em_mode == "restricted":
                parts.append(
                    "\nEM DASHES: RESTRICTED. Only use em dashes as mid-sentence "
                    "parentheticals (paired). Never use to extend a thought."
                )
            elif em_mode == "na":
                parts.append(
                    "\nEM DASHES: Do not use any personality markers including em dashes."
                )

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

        banned_patterns = [
            entry.get("label", "") for entry in ai_tells.get("banned_patterns", [])
        ]
        if banned_patterns:
            parts.append(f"\nBANNED PATTERNS: {'; '.join(banned_patterns)}")

        parts.append(
            "\nThe test: 'Does this sound like me?' not 'Does this sound like AI?' "
            "Write naturally, not generically."
        )

        return "\n".join(parts)

    def _build_user_message(
        self, content: str, platform: str, url: str = "", notes: str = "",
    ) -> str:
        """Build user message with the source content."""
        parts = [
            f"Generate a {platform} post from this content:\n",
            content,
        ]

        if url:
            parts.append(f"\nURL to include: {url}")

        if notes:
            parts.append(f"\nAdditional direction: {notes}")

        return "\n".join(parts)

    def _extract_hashtags(self, text: str) -> list[str]:
        """Pull hashtag tokens from generated Instagram copy."""
        tags = []
        for word in text.split():
            if word.startswith("#") and len(word) > 1:
                tags.append(word.rstrip(".,!?"))
        return tags

    async def _call_anthropic(self, system_prompt: str, user_message: str) -> str:
        """Call Anthropic Messages API to generate post text."""
        if not ANTHROPIC_API_KEY:
            return "(Anthropic API key not configured. Add ANTHROPIC_API_KEY to secrets.env.)"

        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 512,
            "temperature": 0.7,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    ANTHROPIC_MESSAGES_URL, json=payload, headers=headers,
                )
                if resp.status_code != 200:
                    logger.error(
                        "Anthropic API error: %s %s", resp.status_code, resp.text,
                    )
                    return f"(Generation failed: {resp.status_code})"
                data = resp.json()
                content_blocks = data.get("content", [])
                text_parts = [
                    b["text"] for b in content_blocks if b.get("type") == "text"
                ]
                return "\n".join(text_parts)
        except httpx.TimeoutException:
            logger.error("Anthropic API timeout")
            return "(Generation timed out. Try again.)"
        except Exception as e:
            logger.exception("Anthropic API call failed")
            return f"(Generation failed: {e})"


# Shared instance
social_copy_service = SocialCopyService()
