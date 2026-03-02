"""Identity routing service — context-tag matching for name/title/email/voice lookup."""

from app.models.identity import ClientOverride, IdentityContext, IdentityResult
from app.services.yaml_store import yaml_store


class IdentityRouter:
    def __init__(self):
        self._data = None
        self._contexts: list[IdentityContext] = []
        self._overrides: list[ClientOverride] = []

    def _load(self):
        self._data = yaml_store.read("identity-routing.yaml")
        self._contexts = [
            IdentityContext(**ctx) for ctx in self._data.get("contexts", [])
        ]
        self._overrides = [
            ClientOverride(**o) for o in self._data.get("client_overrides", [])
        ]

    def _ensure_loaded(self):
        if self._data is None:
            self._load()

    def reload(self):
        self._data = None
        self._load()

    def all_contexts(self) -> list[IdentityContext]:
        self._ensure_loaded()
        return self._contexts

    def search(self, query: str) -> list[IdentityResult]:
        """Search contexts by fuzzy tag matching against a query string."""
        self._ensure_loaded()
        query_lower = query.lower().strip()
        query_words = set(query_lower.split())
        results = []

        for ctx in self._contexts:
            score = 0.0
            matched_tags = []

            # Check label match
            if query_lower in ctx.label.lower():
                score += 3.0
                matched_tags.append(ctx.label)

            # Check context_id match
            if query_lower in ctx.context_id.lower():
                score += 2.0

            # Check tag matches
            for tag in ctx.tags:
                tag_lower = tag.lower()
                if query_lower == tag_lower:
                    score += 5.0
                    matched_tags.append(tag)
                elif query_lower in tag_lower:
                    score += 2.0
                    matched_tags.append(tag)
                else:
                    # Word-level matching
                    tag_words = set(tag_lower.split())
                    overlap = query_words & tag_words
                    if overlap:
                        score += len(overlap) * 1.5
                        matched_tags.append(tag)

            # Check name match
            if ctx.name and query_lower in ctx.name.lower():
                score += 2.0

            # Check email match
            if ctx.email and query_lower in ctx.email.lower():
                score += 2.0

            if score > 0:
                results.append(IdentityResult(
                    context=ctx,
                    match_score=score,
                    matched_tags=matched_tags,
                ))

        results.sort(key=lambda r: r.match_score, reverse=True)
        return results

    def get_by_id(self, context_id: str) -> IdentityContext | None:
        self._ensure_loaded()
        for ctx in self._contexts:
            if ctx.context_id == context_id:
                return ctx
        return None

    def get_client_override(self, client_name: str) -> ClientOverride | None:
        self._ensure_loaded()
        for o in self._overrides:
            if o.client.lower() == client_name.lower():
                return o
        return None
