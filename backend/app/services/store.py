from __future__ import annotations

import csv
import json
from pathlib import Path

from app.core.config import settings

CSV_FIELDS = [
    "id",
    "class",
    "confidence",
    "x",
    "y",
    "width",
    "height",
    "latitude",
    "longitude",
    "geolocation_status",
]


def run_dir(run_id: str) -> Path:
    path = settings.storage_dir / "runs" / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(run_id: str, payload: dict) -> Path:
    path = run_dir(run_id) / "report.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def write_csv(run_id: str, payload: dict) -> Path:
    path = run_dir(run_id) / "report.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for det in payload.get("detections") or []:
            bbox = det.get("bbox") or {}
            geo = det.get("geolocation") or {}
            lat = geo.get("latitude")
            lon = geo.get("longitude")
            writer.writerow(
                {
                    "id": det.get("id", ""),
                    "class": det.get("class", ""),
                    "confidence": det.get("confidence", ""),
                    "x": bbox.get("x", ""),
                    "y": bbox.get("y", ""),
                    "width": bbox.get("width", ""),
                    "height": bbox.get("height", ""),
                    "latitude": "" if lat is None else lat,
                    "longitude": "" if lon is None else lon,
                    "geolocation_status": geo.get("status", ""),
                }
            )
    return path


def read_json(run_id: str) -> dict | None:
    path = run_dir(run_id) / "report.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
