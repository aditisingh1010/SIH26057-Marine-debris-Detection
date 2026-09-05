from __future__ import annotations

import csv
import json
from pathlib import Path

from app.core.config import settings

CSV_FIELDS = [
    "detection_id",
    "id",
    "image_name",
    "class",
    "confidence",
    "risk_level",
    "risk_score",
    "bbox_x1",
    "bbox_y1",
    "bbox_x2",
    "bbox_y2",
    "bbox_width",
    "bbox_height",
    "width_m",
    "height_m",
    "acoustic_shadow_overlap",
    "review_priority",
    "latitude",
    "longitude",
    "geolocation_status",
]


def run_dir(run_id: str, create: bool = True) -> Path:
    path = settings.storage_dir / "runs" / run_id
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(run_id: str, payload: dict) -> Path:
    path = run_dir(run_id) / "report.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def write_csv(run_id: str, payload: dict) -> Path:
    path = run_dir(run_id) / "report.csv"
    img_name = payload.get("filename", "sonar_image.jpg")

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()

        dets = payload.get("filtered_detections") or payload.get("detections") or []
        for det in dets:
            bbox = det.get("bbox") or {}
            geo = det.get("geolocation") or {}
            lat = geo.get("latitude")
            lon = geo.get("longitude")

            x1 = bbox.get("x1", bbox.get("x", 0))
            y1 = bbox.get("y1", bbox.get("y", 0))
            w = bbox.get("width", 0)
            h = bbox.get("height", 0)
            x2 = bbox.get("x2", x1 + w)
            y2 = bbox.get("y2", y1 + h)

            writer.writerow(
                {
                    "detection_id": det.get("id", ""),
                    "id": det.get("id", ""),
                    "image_name": img_name,
                    "class": det.get("class") or det.get("class_name", ""),
                    "confidence": det.get("confidence", ""),
                    "risk_level": det.get("risk_level", "medium"),
                    "risk_score": det.get("risk_score", 0.5),
                    "bbox_x1": x1,
                    "bbox_y1": y1,
                    "bbox_x2": x2,
                    "bbox_y2": y2,
                    "bbox_width": w,
                    "bbox_height": h,
                    "width_m": det.get("width_m", ""),
                    "height_m": det.get("height_m", ""),
                    "acoustic_shadow_overlap": det.get("acoustic_shadow_overlap", False),
                    "review_priority": det.get("review_priority", "standard"),
                    "latitude": "" if lat is None else lat,
                    "longitude": "" if lon is None else lon,
                    "geolocation_status": geo.get("status", "unavailable"),
                }
            )
    return path


def read_json(run_id: str) -> dict | None:
    path = run_dir(run_id, create=False) / "report.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
