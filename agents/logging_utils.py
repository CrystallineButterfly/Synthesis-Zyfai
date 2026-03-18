"""JSON logging helpers for artifacts and agent logs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_timestamp() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def append_event(
    path: Path,
    stage: str,
    actor: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    payload = read_json(path, default=[])
    payload.append(
        {
            'timestamp': utc_timestamp(),
            'stage': stage,
            'actor': actor,
            'message': message,
            'details': details or {},
        }
    )
    write_json(path, payload)
