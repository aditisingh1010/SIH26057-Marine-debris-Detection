from __future__ import annotations

import secrets
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.schemas import Detection, RunResult
from app.services.geolocation import geolocate_box
from app.services.metadata import parse_metadata_text
from app.services.store import read_json, run_dir, write_csv, write_json

router = APIRouter()


def _allowed_suffixes() -> set[str]:
    return {
        item.strip().lower()
        for item in settings.allowed_suffixes.split(",")
        if item.strip()
    }


def _safe_filename(name: str | None) -> str:
    cleaned = Path(name or "upload").name
    return cleaned or "upload"


@router.get("/health")
def health(request: Request) -> dict:
    inference = getattr(request.app.state, "inference", None)
    loaded = bool(inference and getattr(inference, "loaded", False))
    mode = getattr(inference, "inference_mode", "real" if loaded else "mock")
    return {
        "status": "ok",
        "service": settings.service_name,
        "model_loaded": loaded,
        "inference_mode": mode,
        "model_path": str(settings.model_path.name),
    }


@router.post("/detect", response_model=RunResult)
def detect(
    request: Request,
    file: UploadFile = File(...),
    metadata: UploadFile | None = File(default=None),
) -> RunResult:
    filename = _safe_filename(file.filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in _allowed_suffixes():
        raise HTTPException(status_code=400, detail="unsupported file type")

    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="empty file")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=400, detail="file too large")

    image = cv2.imdecode(np.frombuffer(contents, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="unreadable image")

    parsed_meta = None
    metadata_attached = metadata is not None
    if metadata is not None:
        meta_bytes = metadata.file.read()
        try:
            text = meta_bytes.decode("utf-8")
            parsed_meta = parse_metadata_text(text, metadata.filename or "")
        except (UnicodeDecodeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="invalid metadata") from exc

    inference = getattr(request.app.state, "inference", None)
    if inference is None:
        from app.services.inference import InferenceService

        inference = InferenceService(settings.model_path)
        request.app.state.inference = inference

    height, width = image.shape[:2]
    raw_detections = inference.predict(image)
    inference_mode = getattr(
        inference, "inference_mode", "real" if getattr(inference, "loaded", False) else "mock"
    )

    detections = []
    for det in raw_detections:
        geo = geolocate_box(det["bbox"], width, height, parsed_meta)
        detections.append(
            Detection.model_validate(
                {
                    "id": det["id"],
                    "class": det["class"],
                    "confidence": det["confidence"],
                    "bbox": det["bbox"],
                    "geolocation": geo,
                    "risk_level": det.get("risk_level", "medium"),
                    "risk_score": det.get("risk_score", 0.5),
                }
            )
        )

    run_id = "run_" + secrets.token_hex(6)
    dest = run_dir(run_id) / filename
    dest.write_bytes(contents)

    result = RunResult(
        id=run_id,
        filename=filename,
        model=str(settings.model_path.name),
        inference_mode=inference_mode,
        image_width=int(width),
        image_height=int(height),
        metadata_attached=metadata_attached,
        detections=detections,
    )
    payload = result.model_dump(by_alias=True)
    write_json(run_id, payload)
    write_csv(run_id, payload)
    return result


@router.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str) -> dict:
    payload = read_json(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="run not found")
    return payload


@router.get("/runs/{run_id}/image")
def get_run_image(run_id: str) -> FileResponse:
    payload = read_json(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="run not found")
    path = run_dir(run_id, create=False) / _safe_filename(payload.get("filename"))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="image not found")
    return FileResponse(path)


@router.get("/runs/{run_id}/report.json")
def get_run_report_json(run_id: str) -> FileResponse:
    path = run_dir(run_id, create=False) / "report.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="report not found")
    return FileResponse(path, media_type="application/json")


@router.get("/runs/{run_id}/report.csv")
def get_run_report_csv(run_id: str) -> FileResponse:
    path = run_dir(run_id, create=False) / "report.csv"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="report not found")
    return FileResponse(path, media_type="text/csv")
