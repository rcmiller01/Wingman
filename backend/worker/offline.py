"""Offline buffering and replay for worker envelopes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class OfflineBufferConfig:
    directory: Path
    max_files: int = 500
    max_age_seconds: int = 7 * 24 * 3600


class OfflineBuffer:
    def __init__(self, config: OfflineBufferConfig):
        self.config = config
        self.config.directory.mkdir(parents=True, exist_ok=True)

    def _filename(self, payload_type: str, task_id: str) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        return f"{payload_type}-{stamp}-{task_id}.json"

    def write(self, envelope: dict) -> Path:
        payload_type = envelope.get("payload_type", "unknown")
        task_id = envelope.get("task_id", "na")
        path = self.config.directory / self._filename(payload_type, task_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(envelope, sort_keys=True))
        tmp.replace(path)
        self._evict_if_needed()
        return path

    def list_pending(self) -> list[Path]:
        files = sorted(self.config.directory.glob("*.json"), reverse=True)
        return files

    def load(self, path: Path) -> dict:
        return json.loads(path.read_text())

    def ack_delete(self, path: Path) -> None:
        if path.exists():
            path.unlink()

    def backlog_size(self) -> int:
        return len(list(self.config.directory.glob("*.json")))

    def _evict_if_needed(self) -> None:
        files = sorted(self.config.directory.glob("*.json"))
        if len(files) > self.config.max_files:
            for path in files[: len(files) - self.config.max_files]:
                path.unlink(missing_ok=True)

        now = datetime.now(timezone.utc).timestamp()
        for path in self.config.directory.glob("*.json"):
            if now - path.stat().st_mtime > self.config.max_age_seconds:
                path.unlink(missing_ok=True)
