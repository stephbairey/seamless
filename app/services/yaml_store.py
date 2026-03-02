"""Shared YAML read/write service with file locking."""

import fcntl
from pathlib import Path
from typing import Any

import yaml

from app.config import DATA_DIR


class YamlStore:
    """Read and write YAML data files with file-level locking.

    Single-operator system — file locking prevents corruption from
    concurrent dashboard edits and Claude Code sessions.
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR

    def read(self, filename: str) -> dict[str, Any]:
        path = self.data_dir / filename
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                data = yaml.safe_load(f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        return data or {}

    def write(self, filename: str, data: dict[str, Any]) -> None:
        path = self.data_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def update_nested(self, filename: str, key_path: list[str], value: Any) -> dict[str, Any]:
        """Update a nested value in a YAML file. Returns the full updated data."""
        data = self.read(filename)
        target = data
        for key in key_path[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[key_path[-1]] = value
        self.write(filename, data)
        return data


# Shared instance
yaml_store = YamlStore()
