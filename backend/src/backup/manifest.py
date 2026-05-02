"""SHA-256 manifest helpers for curriculum backups."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


@dataclass
class ManifestEntry:
    path: str
    sha256: str
    size_bytes: int


@dataclass
class BackupManifest:
    backup_id: str
    school_id: str
    scope_type: str
    scope_value: str | None
    created_at: str
    entries: list[ManifestEntry] = field(default_factory=list)
    db_row_counts: dict = field(default_factory=dict)

    def to_json(self) -> bytes:
        return json.dumps(
            {
                "backup_id": self.backup_id,
                "school_id": self.school_id,
                "scope_type": self.scope_type,
                "scope_value": self.scope_value,
                "created_at": self.created_at,
                "db_row_counts": self.db_row_counts,
                "entries": [
                    {"path": e.path, "sha256": e.sha256, "size_bytes": e.size_bytes}
                    for e in self.entries
                ],
            },
            indent=2,
        ).encode()

    @classmethod
    def from_json(cls, data: bytes) -> BackupManifest:
        d = json.loads(data)
        entries = [ManifestEntry(**e) for e in d.get("entries", [])]
        return cls(
            backup_id=d["backup_id"],
            school_id=d["school_id"],
            scope_type=d["scope_type"],
            scope_value=d.get("scope_value"),
            created_at=d["created_at"],
            entries=entries,
            db_row_counts=d.get("db_row_counts", {}),
        )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
