"""Brand token service — read brand visual tokens from YAML."""

from typing import Any

from app.services.yaml_store import yaml_store

FILENAME = "brand-tokens.yaml"


class BrandTokenService:
    def __init__(self):
        self._data = None

    def _load(self):
        self._data = yaml_store.read(FILENAME)

    def _ensure_loaded(self):
        if self._data is None:
            self._load()

    def reload(self):
        self._data = None
        self._load()

    def list_tokens(self) -> list[dict[str, Any]]:
        self._ensure_loaded()
        return self._data.get("tokens", [])

    def get_token(self, context_id: str) -> dict[str, Any] | None:
        self._ensure_loaded()
        for t in self._data.get("tokens", []):
            if t.get("context_id") == context_id:
                return t
        return None
