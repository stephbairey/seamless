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

    def update_token(self, context_id: str, updates: dict[str, Any]) -> bool:
        """Update fields on a brand token and write back to YAML."""
        self._ensure_loaded()
        tokens = self._data.get("tokens", [])
        for i, t in enumerate(tokens):
            if t.get("context_id") == context_id:
                for key, value in updates.items():
                    if key == "context_id":
                        continue
                    tokens[i][key] = value
                self._data["tokens"] = tokens
                yaml_store.write(FILENAME, self._data)
                return True
        return False
