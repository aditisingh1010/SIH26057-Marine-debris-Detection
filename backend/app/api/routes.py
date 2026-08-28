from __future__ import annotations

import secrets
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.schemas import (
    BatchResult,
    BBox,
    Detection,
    Geolocation,
    RunResult,
    RunSummary,
    ShadowZone,
    SystemInfo,
)
from app.services.filtering import filter_detections
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


def _get_inference(request: Request):
    inference = getattr(request.app.state, "inference", None)
    if inference is None:
        from app.services.inference import InferenceService
        inference = InferenceService(settings.model_path)
        request.app.state.inference = inference
    return inference


def _process_image(
    contents: bytes,
    filename: str,
    inference,
    parsed_meta: dict | None,
    conf_threshold: float = 0.25,
) -> RunResult:
    """Core detection, noise filtering, annotation drawing, and report generation logic."""
    image = cv2.imdecode(np.frombuffer(contents, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="unreadable or invalid image")

    height, width = image.shape[:2]

    # 1. Raw YOLO inference
    raw_preds = inference.predict(image, conf=0.05)  # low threshold for raw detections

    # 2. Transparent confidence + noise post-processing filter
    filter_res = filter_detections(
        raw_detections=raw_preds,
        image_width=width,
        image_height=height,
        conf_threshold=conf_threshold,
    )

    raw_det_dicts = filter_res["raw_detections"]
    filtered_det_dicts = filter_res["filtered_detections"]

    inference_mode = getattr(
        inference, "inference_mode", "real" if getattr(inference, "loaded", False) else "mock"
    )

    # 3. Geolocation handling
    geo_available = False
    geo_note = "Geolocation unavailable: sonar metadata not provided."

    if parsed_meta and ("latitude" in parsed_meta or "lat" in parsed_meta):
        geo_available = True
        geo_note = "Sonar metadata attached."

    # Convert detection dicts to Pydantic models
    raw_models: list[Detection] = []
    for det in raw_det_dicts:
        geo = geolocate_box(det["bbox"], width, height, parsed_meta)
        b = det["bbox"]
        bbox_obj = BBox(
            x=int(b.get("x", 0)),
            y=int(b.get("y", 0)),
            width=int(b.get("width", 0)),
            height=int(b.get("height", 0)),
            x1=int(b.get("x1", b.get("x", 0))),
            y1=int(b.get("y1", b.get("y", 0))),
            x2=int(b.get("x2", b.get("x", 0) + b.get("width", 0))),
            y2=int(b.get("y2", b.get("y", 0) + b.get("height", 0))),
        )
        raw_models.append(
            Detection(
                id=det["id"],
                class_name=det["class"],
                confidence=det["confidence"],
                bbox=bbox_obj,
                geolocation=Geolocation(
                    latitude=geo.get("latitude") if geo_available else None,
                    longitude=geo.get("longitude") if geo_available else None,
                    status=geo.get("status", "unavailable") if geo_available else "unavailable"
                ),
                risk_level=det.get("risk_level", "medium"),
                risk_score=det.get("risk_score", 0.5),
                passed_filter=det.get("passed_filter", True),
                rejection_reason=det.get("rejection_reason"),
                mask_points=det.get("mask_points"),
            )
        )

    filtered_models: list[Detection] = [d for d in raw_models if d.passed_filter]

    # Acoustic shadow zones (experimental heuristic)
    raw_shadows = inference.shadow_zones(image)
    shadow_zones = [ShadowZone(**sz) for sz in raw_shadows]

    run_id = "run_" + secrets.token_hex(6)
    rdir = run_dir(run_id)

    # Save original image
    raw_dest = rdir / filename
    raw_dest.write_bytes(contents)

    # Draw & save green bounding box annotated image
    annotated_img = inference.draw_annotations(image, [d.model_dump(by_alias=True) for d in filtered_models])
    annotated_filename = f"{Path(filename).stem}_annotated.jpg"
    annotated_dest = rdir / annotated_filename
    cv2.imwrite(str(annotated_dest), annotated_img)

    result = RunResult(
        id=run_id,
        filename=filename,
        model=str(settings.model_path.name),
        inference_mode=inference_mode,
        image_width=int(width),
        image_height=int(height),
        metadata_attached=parsed_meta is not None,
        conf_threshold=conf_threshold,
        raw_detections=raw_models,
        filtered_detections=filtered_models,
        detections=filtered_models,
        shadow_zones=shadow_zones,
        geolocation_available=geo_available,
        geolocation_note=geo_note,
        annotated_image_url=f"/api/v1/runs/{run_id}/image/annotated",
        json_report_url=f"/api/v1/runs/{run_id}/report.json",
        csv_report_url=f"/api/v1/runs/{run_id}/report.csv",
    )

    payload = result.model_dump(by_alias=True)
    write_json(run_id, payload)
    write_csv(run_id, payload)
    return result


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


@router.get("/info", response_model=SystemInfo)
def system_info(request: Request) -> SystemInfo:
    """Returns system capabilities and model information."""
    inference = getattr(request.app.state, "inference", None)
    loaded = bool(inference and getattr(inference, "loaded", False))

    classes: list[str] = ["crab_pot"]
    seg_support = False
    if inference and hasattr(inference, "names") and inference.names:
        classes = list(set(inference.names.values()))

    onnx_path = settings.model_path.parent / "best.onnx"
    onnx_available = onnx_path.is_file()

    return SystemInfo(
        version="1.0.0",
        model="YOLOv8n",
        classes=classes,
        segmentation_support=seg_support,
        onnx_available=onnx_available,
        metadata_formats=["json", "csv", "xtf"],
        max_upload_mb=settings.max_upload_mb,
        confidence_threshold=settings.default_conf_threshold,
    )


@router.post("/detect", response_model=RunResult)
def detect(
    request: Request,
    file: UploadFile = File(...),
    metadata: UploadFile | None = File(default=None),
    conf_threshold: float = Query(default=0.25, ge=0.05, le=0.95),
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

    parsed_meta = None
    if metadata is not None:
        meta_bytes = metadata.file.read()
        meta_fname = (metadata.filename or "").lower()
        try:
            if meta_fname.endswith(".xtf"):
                import tempfile, os
                from app.services.xtf_parser import parse_xtf_navigation
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xtf") as tmp:
                    tmp.write(meta_bytes)
                    tmp_path = tmp.name
                try:
                    xtf_nav = parse_xtf_navigation(tmp_path)
                    parsed_meta = xtf_nav if xtf_nav else {}
                finally:
                    os.unlink(tmp_path)
            else:
                text = meta_bytes.decode("utf-8")
                parsed_meta = parse_metadata_text(text, metadata.filename or "")
        except (UnicodeDecodeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="invalid metadata") from exc
        except Exception:
            parsed_meta = None

    inference = _get_inference(request)
    return _process_image(contents, filename, inference, parsed_meta, conf_threshold)


@router.post("/detect/batch", response_model=BatchResult)
def detect_batch(
    request: Request,
    files: list[UploadFile] = File(...),
    conf_threshold: float = Query(default=0.25, ge=0.05, le=0.95),
) -> BatchResult:
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="max 10 files per batch")

    inference = _get_inference(request)
    runs: list[RunResult] = []
    errors: list[str] = []
    failed = 0

    for upload in files:
        fname = _safe_filename(upload.filename)
        suffix = Path(fname).suffix.lower()
        try:
            if suffix not in _allowed_suffixes():
                raise ValueError(f"unsupported file type: {suffix}")
            contents = upload.file.read()
            if not contents:
                raise ValueError("empty file")
            max_bytes = settings.max_upload_mb * 1024 * 1024
            if len(contents) > max_bytes:
                raise ValueError("file too large")
            run = _process_image(contents, fname, inference, None, conf_threshold)
            runs.append(run)
        except Exception as exc:
            failed += 1
            errors.append(f"{fname}: {exc}")

    return BatchResult(
        runs=runs,
        total=len(files),
        failed=failed,
        errors=errors,
    )


@router.get("/runs", response_model=list[RunSummary])
def list_runs() -> list[RunSummary]:
    runs_dir = settings.storage_dir / "runs"
    if not runs_dir.exists():
        return []

    summaries: list[RunSummary] = []
    run_dirs = sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)

    for rd in run_dirs[:50]:
        json_path = rd / "report.json"
        if not json_path.is_file():
            continue
        try:
            import json
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            summaries.append(RunSummary(
                id=payload.get("id", rd.name),
                filename=payload.get("filename", ""),
                inference_mode=payload.get("inference_mode", "unknown"),
                detection_count=len(payload.get("filtered_detections") or payload.get("detections") or []),
            ))
        except Exception:
            continue

    return summaries


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


@router.get("/runs/{run_id}/image/annotated")
def get_run_image_annotated(run_id: str) -> FileResponse:
    payload = read_json(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="run not found")
    filename = _safe_filename(payload.get("filename"))
    annotated_filename = f"{Path(filename).stem}_annotated.jpg"
    path = run_dir(run_id, create=False) / annotated_filename
    if not path.is_file():
        # Fallback to original image if annotated image not generated
        path = run_dir(run_id, create=False) / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="image not found")
    return FileResponse(path, media_type="image/jpeg")


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
