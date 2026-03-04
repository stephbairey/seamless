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
        self.reload()
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

    def add_token(self, token: dict[str, Any]) -> str:
        """Append a new token and write YAML. Returns context_id."""
        self.reload()
        tokens = self._data.get("tokens", [])
        tokens.append(token)
        self._data["tokens"] = tokens
        yaml_store.write(FILENAME, self._data)
        return token["context_id"]

    def delete_token(self, context_id: str) -> bool:
        """Remove a token by context_id and write YAML."""
        self.reload()
        tokens = self._data.get("tokens", [])
        before = len(tokens)
        tokens = [t for t in tokens if t.get("context_id") != context_id]
        if len(tokens) == before:
            return False
        self._data["tokens"] = tokens
        yaml_store.write(FILENAME, self._data)
        return True

    def reorder_tokens(self, context_ids: list[str]) -> bool:
        """Rebuild token list in the given order and write YAML."""
        self.reload()
        tokens = self._data.get("tokens", [])
        by_id = {t["context_id"]: t for t in tokens}
        if set(context_ids) != set(by_id.keys()):
            return False
        self._data["tokens"] = [by_id[cid] for cid in context_ids]
        yaml_store.write(FILENAME, self._data)
        return True
