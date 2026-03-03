"""TagSpaces filename parser for file routing."""

import re
from typing import Any

from app.models.files import ParsedTags
from app.services.yaml_store import yaml_store

# Matches bracketed tags: filename[Tag1 Tag2 Tag3].ext
TAG_BRACKET_RE = re.compile(r"\[([^\]]+)\]")


class TagParser:
    """Parse TagSpaces-style bracketed tags from filenames.

    Tag format: filename[Client Project Content].ext
    Tags are space-separated, hyphens for multi-word tokens.
    """

    def __init__(self):
        self._config: dict[str, Any] | None = None
        self._client_tags_lower: dict[str, str] = {}  # lowercase -> original
        self._project_to_client: dict[str, str] = {}  # lowercase project -> client tag
        self._project_tags_lower: dict[str, str] = {}  # lowercase -> original

    def _load_config(self):
        self._config = yaml_store.read("file-routing-rules.yaml")
        self._client_tags_lower = {}
        self._project_to_client = {}
        self._project_tags_lower = {}

        for ct in self._config.get("client_tags", []):
            self._client_tags_lower[ct.lower()] = ct

        for client_tag, client_cfg in self._config.get("clients", {}).items():
            for proj_tag in (client_cfg.get("projects") or {}):
                self._project_tags_lower[proj_tag.lower()] = proj_tag
                self._project_to_client[proj_tag.lower()] = client_tag

    @property
    def config(self) -> dict[str, Any]:
        if self._config is None:
            self._load_config()
        return self._config

    def reload(self):
        self._config = None

    def parse(self, filename: str) -> ParsedTags | None:
        """Extract tags from a filename like `file[Maya Painting-Celia Cover].ext`.

        Returns None if no bracket found.
        """
        match = TAG_BRACKET_RE.search(filename)
        if not match:
            return None

        # Lazy-load config
        if self._config is None:
            self._load_config()

        raw = match.group(1)
        all_tags = raw.split()

        client_tag = None
        project_tag = None
        content_tags = []

        for tag in all_tags:
            tag_lower = tag.lower()
            if tag_lower in self._client_tags_lower:
                client_tag = self._client_tags_lower[tag_lower]
            elif tag_lower in self._project_tags_lower:
                project_tag = self._project_tags_lower[tag_lower]
            else:
                content_tags.append(tag)

        # If project found but no client, infer client from project
        if project_tag and not client_tag:
            inferred = self._project_to_client.get(project_tag.lower())
            if inferred:
                client_tag = inferred

        return ParsedTags(
            raw_bracket=raw,
            client_tag=client_tag,
            project_tag=project_tag,
            content_tags=content_tags,
            all_tags=all_tags,
        )

    def strip_tags(self, filename: str) -> str:
        """Remove the [...] bracket from a filename."""
        return TAG_BRACKET_RE.sub("", filename).strip()


# Shared instance
tag_parser = TagParser()
