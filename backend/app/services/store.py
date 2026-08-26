from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings


def run_dir(run_id: str) -> Path:
    path = settings.storage_dir / "runs" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(run_id: str, payload: dict) -> Path:
    path = run_dir(run_id) / "report.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_json(run_id: str) -> dict | None:
    path = run_dir(run_id) / "report.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
