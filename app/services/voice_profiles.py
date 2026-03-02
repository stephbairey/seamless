"""Voice profile service — read and update voice profile YAML."""

from typing import Any

from app.services.yaml_store import yaml_store

FILENAME = "voice-profiles.yaml"


class VoiceProfileService:
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

    def list_profiles(self) -> list[dict[str, Any]]:
        self._ensure_loaded()
        return self._data.get("profiles", [])

    def get_profile(self, voice_id: str) -> dict[str, Any] | None:
        self._ensure_loaded()
        for p in self._data.get("profiles", []):
            if p.get("voice_id") == voice_id:
                return p
        return None

    def update_profile(self, voice_id: str, updates: dict[str, Any]) -> bool:
        """Update fields on a voice profile and write back to YAML."""
        self._ensure_loaded()
        profiles = self._data.get("profiles", [])
        for i, p in enumerate(profiles):
            if p.get("voice_id") == voice_id:
                for key, value in updates.items():
                    # Don't allow changing voice_id
                    if key == "voice_id":
                        continue
                    profiles[i][key] = value
                self._data["profiles"] = profiles
                yaml_store.write(FILENAME, self._data)
                return True
        return False
