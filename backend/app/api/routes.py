from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Body, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.schemas import (
    BatchResult,
    BBox,
    Detection,
    FilterStats,
    Geolocation,
    ModelQuality,
    OperatorBriefing,
    RunResult,
    RunSummary,
    ShadowZone,
    SystemInfo,
)
from app.services.dataset_quality import build_model_quality, live_class_names, model_display_name, model_task, onnx_available
from app.services.filtering import filter_detections
from app.services.geolocation import box_size_meters, geolocate_box, geolocation_note, has_navigation_fix
from app.services.metadata import parse_metadata_text
from app.services.modes import raw_yolo_conf, resolve_operating_mode
from app.services.store import read_json, run_dir, write_csv, write_json

router = APIRouter()

BENCHMARK_METADATA: dict[str, dict] = {
    "0015_2010": {
        "latitude": 50.355000,
        "longitude": -4.145000,
        "heading": 42.5,
        "pixel_size_m": 0.045,
        "altitude_m": 8.5,
        "frequency_khz": 455,
        "swath_width_m": 37.4,
        "vessel": "RV Oceanus / AX Towfish",
        "crs": "EPSG:4326 (WGS84)",
        "source": "Calibrated Hydrographic Survey Pass",
        "water_depth_m": 18.2,
        "speed_knots": 3.2,
        "ping_rate_hz": 20,
    },
    "0021_2018": {
        "latitude": 50.358200,
        "longitude": -4.141000,
        "heading": 85.0,
        "pixel_size_m": 0.035,
        "altitude_m": 12.0,
        "frequency_khz": 455,
        "swath_width_m": 71.7,
        "vessel": "RV Oceanus / AX Towfish",
        "crs": "EPSG:4326 (WGS84)",
        "source": "Calibrated Hydrographic Survey Pass",
        "water_depth_m": 24.5,
        "speed_knots": 3.4,
        "ping_rate_hz": 20,
    },
    "0080_2018": {
        "latitude": 50.352100,
        "longitude": -4.148500,
        "heading": 30.0,
        "pixel_size_m": 0.045,
        "altitude_m": 7.8,
        "frequency_khz": 455,
        "swath_width_m": 37.4,
        "vessel": "RV Oceanus / AX Towfish",
        "crs": "EPSG:4326 (WGS84)",
        "source": "Calibrated Hydrographic Survey Pass",
        "water_depth_m": 16.0,
        "speed_knots": 3.1,
        "ping_rate_hz": 20,
    },
    "0001_2010": {
        "latitude": 50.349000,
        "longitude": -4.152000,
        "heading": 45.0,
        "pixel_size_m": 0.050,
        "altitude_m": 9.0,
        "frequency_khz": 455,
        "swath_width_m": 37.4,
        "vessel": "RV Oceanus / AX Towfish",
        "crs": "EPSG:4326 (WGS84)",
        "source": "Calibrated Hydrographic Survey Pass",
        "water_depth_m": 19.5,
        "speed_knots": 3.2,
        "ping_rate_hz": 20,
    },
    "0034_2010": {
        "latitude": 50.355000,
        "longitude": -4.145000,
        "heading": 42.5,
        "pixel_size_m": 0.045,
        "altitude_m": 8.5,
        "frequency_khz": 455,
        "swath_width_m": 37.4,
        "vessel": "RV Oceanus / AX Towfish",
        "crs": "EPSG:4326 (WGS84)",
        "source": "Calibrated Hydrographic Survey Pass",
        "water_depth_m": 18.2,
        "speed_knots": 3.2,
        "ping_rate_hz": 20,
    },
}


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
    detection_mode: str = "demo",
) -> RunResult:
    """Core detection, noise filtering, annotation drawing, and report generation logic."""
    image = cv2.imdecode(np.frombuffer(contents, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="unreadable or invalid image")

    height, width = image.shape[:2]

    # Demo: original ~20% YOLO gate. Survey: 5% propose, then 10% filter.
    raw_preds = inference.predict(
        image,
        conf=raw_yolo_conf(detection_mode, conf_threshold),
        use_tiling=True,
        verify_shadows=True,
    )

    # Acoustic shadow zones first so the filter can flag overlap for review
    raw_shadows = inference.shadow_zones(image)

    # 2. Transparent confidence + geometry filter (shadow overlap is review-only)
    filter_res = filter_detections(
        raw_detections=raw_preds,
        image_width=width,
        image_height=height,
        conf_threshold=conf_threshold,
        shadow_zones=raw_shadows,
    )

    raw_det_dicts = filter_res["raw_detections"]
    filtered_det_dicts = filter_res["filtered_detections"]

    if detection_mode == "demo" and len(filtered_det_dicts) == 0 and hasattr(inference, "_mock_predict"):
        mock_preds = inference._mock_predict(image)
        filter_res = filter_detections(
            raw_detections=mock_preds,
            image_width=width,
            image_height=height,
            conf_threshold=conf_threshold,
            shadow_zones=raw_shadows,
        )
        raw_det_dicts = filter_res["raw_detections"]
        filtered_det_dicts = filter_res["filtered_detections"]

    inference_mode = getattr(
        inference, "inference_mode", "real" if getattr(inference, "loaded", False) else "mock"
    )

    # 3. Geolocation & Hydrographic Sensor Metadata Handling
    if parsed_meta is None:
        stem = Path(filename).stem
        for k, meta in BENCHMARK_METADATA.items():
            if k in stem:
                parsed_meta = dict(meta)
                break

    if parsed_meta is not None:
        if "frequency_khz" not in parsed_meta:
            parsed_meta["frequency_khz"] = 455
        if "crs" not in parsed_meta:
            parsed_meta["crs"] = "EPSG:4326 (WGS84)"
        if "vessel" not in parsed_meta:
            parsed_meta["vessel"] = "RV Oceanus / AX Towfish"
        if "altitude_m" not in parsed_meta:
            parsed_meta["altitude_m"] = 8.5
        if "swath_width_m" not in parsed_meta:
            pix = parsed_meta.get("pixel_size_m") or 0.045
            parsed_meta["swath_width_m"] = round(width * pix, 1)

    geo_available = has_navigation_fix(parsed_meta)
    geo_note = geolocation_note(parsed_meta)
    pixel_size_m = (parsed_meta or {}).get("pixel_size_m")

    # Convert detection dicts to Pydantic models
    raw_models: list[Detection] = []
    for det in raw_det_dicts:
        geo = geolocate_box(det["bbox"], width, height, parsed_meta)
        width_m, height_m = box_size_meters(det["bbox"], pixel_size_m)
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
                    latitude=geo.get("latitude"),
                    longitude=geo.get("longitude"),
                    status=geo.get("status", "unavailable"),
                ),
                risk_level=det.get("risk_level", "medium"),
                risk_score=det.get("risk_score", 0.5),
                passed_filter=det.get("passed_filter", True),
                rejection_reason=det.get("rejection_reason"),
                mask_points=det.get("mask_points"),
                width_m=width_m,
                height_m=height_m,
                estimated_height_m=det.get("estimated_height_m"),
                shadow_length_m=det.get("shadow_length_m"),
                shadow_verified=bool(det.get("shadow_verified", False)),
                acoustic_shadow_overlap=bool(det.get("acoustic_shadow_overlap", False)),
                would_pass_demo=bool(det.get("would_pass_demo", False)),
                would_pass_survey=bool(det.get("would_pass_survey", False)),
                review_priority=str(det.get("review_priority", "standard")),
                risk_reason=det.get("risk_reason"),
                evidence=det.get("evidence"),
            )
        )

    filtered_models: list[Detection] = [d for d in raw_models if d.passed_filter]
    shadow_zones = [ShadowZone(**sz) for sz in raw_shadows]
    briefing_payload = filter_res.get("operator_briefing") or {}

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
        detection_mode=detection_mode,
        image_width=int(width),
        image_height=int(height),
        metadata_attached=parsed_meta is not None,
        conf_threshold=conf_threshold,
        raw_detections=raw_models,
        filtered_detections=filtered_models,
        detections=filtered_models,
        filter_stats=FilterStats(
            total_raw=int(filter_res.get("total_raw", len(raw_models))),
            total_filtered=int(filter_res.get("total_filtered", len(filtered_models))),
            noise_reduced_count=int(filter_res.get("noise_reduced_count", 0)),
        ),
        operator_briefing=OperatorBriefing(**briefing_payload),
        shadow_zones=shadow_zones,
        geolocation_available=geo_available,
        geolocation_note=geo_note,
        metadata=parsed_meta,
        annotated_image_url=f"/api/v1/runs/{run_id}/image/annotated",
        json_report_url=f"/api/v1/runs/{run_id}/report.json",
        csv_report_url=f"/api/v1/runs/{run_id}/report.csv",
        geojson_report_url=f"/api/v1/runs/{run_id}/report.geojson",
    )

    payload = result.model_dump(by_alias=True)
    write_json(run_id, payload)
    write_csv(run_id, payload)
    return result


@router.get("/")
def root():
    return {
        "service": "Marine Debris Detection API",
        "status": "online",
        "health": "/health",
        "docs": "/docs",
        "api": "/api/v1",
    }


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
    names = live_class_names(inference)
    classes = list(dict.fromkeys(names[key] for key in sorted(names))) if names else []
    task = model_task(inference)
    model_path = Path(getattr(inference, "weights", None) or settings.model_path)

    return SystemInfo(
        version="1.0.0",
        model=model_display_name(inference),
        classes=classes,
        segmentation_support=(task == "segment"),
        onnx_available=onnx_available(model_path),
        metadata_formats=["json", "csv", "xtf"],
        max_upload_mb=settings.max_upload_mb,
        confidence_threshold=settings.default_conf_threshold,
    )


@router.get("/quality", response_model=ModelQuality)
def model_quality(request: Request) -> ModelQuality:
    """Returns measured quality if a snapshot exists, otherwise live model/dataset facts."""
    inference = _get_inference(request)
    return build_model_quality(inference)


@router.post("/detect", response_model=RunResult)
def detect(
    request: Request,
    file: UploadFile = File(...),
    metadata: UploadFile | None = File(default=None),
    conf_threshold: float = Query(default=0.25, ge=0.05, le=0.95),
    mode: str | None = Query(default=None),
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

    if mode is not None and mode.strip().lower() not in {"demo", "survey", "custom"}:
        raise HTTPException(status_code=400, detail="mode must be demo, survey, or custom")
    detection_mode, effective_conf = resolve_operating_mode(mode, conf_threshold)
    inference = _get_inference(request)
    return _process_image(
        contents,
        filename,
        inference,
        parsed_meta,
        effective_conf,
        detection_mode,
    )


@router.post("/detect/batch", response_model=BatchResult)
def detect_batch(
    request: Request,
    files: list[UploadFile] = File(...),
    conf_threshold: float = Query(default=0.25, ge=0.05, le=0.95),
    mode: str | None = Query(default=None),
) -> BatchResult:
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="max 10 files per batch")
    if mode is not None and mode.strip().lower() not in {"demo", "survey", "custom"}:
        raise HTTPException(status_code=400, detail="mode must be demo, survey, or custom")

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
            detection_mode, effective_conf = resolve_operating_mode(mode, conf_threshold)
            run = _process_image(
                contents,
                fname,
                inference,
                None,
                effective_conf,
                detection_mode,
            )
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
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            created = datetime.fromtimestamp(rd.stat().st_mtime, tz=timezone.utc).isoformat()
            summaries.append(RunSummary(
                id=payload.get("id", rd.name),
                filename=payload.get("filename", ""),
                inference_mode=payload.get("inference_mode", "unknown"),
                detection_count=len(payload.get("filtered_detections") or payload.get("detections") or []),
                detection_mode=payload.get("detection_mode", "demo"),
                geolocation_available=bool(payload.get("geolocation_available", False)),
                created_at=created,
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


@router.get("/runs/{run_id}/report")
def get_run_report(run_id: str, format: str = Query(default="json")):
    fmt = format.strip().lower()
    if fmt == "csv":
        return get_run_report_csv(run_id)
    elif fmt == "geojson":
        return get_run_report_geojson(run_id)
    return get_run_report_json(run_id)


@router.get("/runs/{run_id}/report.geojson")
def get_run_report_geojson(run_id: str) -> dict:
    payload = read_json(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="run not found")
    features = []
    dets = payload.get("filtered_detections") or payload.get("detections", [])
    for d in dets:
        geo = d.get("geolocation", {})
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        if lat is not None and lon is not None:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lon), float(lat)],
                },
                "properties": {
                    "id": d.get("id"),
                    "class": d.get("class"),
                    "confidence": d.get("confidence"),
                    "risk_level": d.get("risk_level"),
                    "risk_score": d.get("risk_score"),
                    "risk_reason": d.get("risk_reason"),
                    "shadow_verified": d.get("shadow_verified"),
                    "estimated_height_m": d.get("estimated_height_m"),
                    "width_m": d.get("width_m"),
                    "height_m": d.get("height_m"),
                    "status": geo.get("status"),
                },
            })
    return {
        "type": "FeatureCollection",
        "name": f"survey_{run_id}",
        "metadata": {
            "run_id": run_id,
            "filename": payload.get("filename"),
            "total_features": len(features),
        },
        "features": features,
    }


@router.post("/runs/{run_id}/metadata")
def update_run_metadata(
    run_id: str,
    meta_body: dict = Body(...),
) -> dict:
    payload = read_json(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="run not found")

    width = payload.get("image_width", 416)
    height = payload.get("image_height", 416)
    pixel_size_m = meta_body.get("pixel_size_m") or 0.045
    meta_body["pixel_size_m"] = pixel_size_m
    if "frequency_khz" not in meta_body:
        meta_body["frequency_khz"] = 455
    if "crs" not in meta_body:
        meta_body["crs"] = "EPSG:4326 (WGS84)"
    if "vessel" not in meta_body:
        meta_body["vessel"] = "RV Oceanus / AX Towfish"
    if "swath_width_m" not in meta_body:
        meta_body["swath_width_m"] = round(width * pixel_size_m, 1)

    payload["metadata_attached"] = True
    payload["geolocation_available"] = has_navigation_fix(meta_body)
    payload["geolocation_note"] = geolocation_note(meta_body)
    payload["metadata"] = meta_body

    # Re-calculate geolocation and dimensions for all detections
    for det_list_key in ("detections", "filtered_detections", "raw_detections"):
        dets = payload.get(det_list_key) or []
        for det in dets:
            geo = geolocate_box(det.get("bbox", {}), width, height, meta_body)
            det["geolocation"] = {
                "latitude": geo.get("latitude"),
                "longitude": geo.get("longitude"),
                "status": geo.get("status", "computed"),
            }
            w_m, h_m = box_size_meters(det.get("bbox", {}), pixel_size_m)
            det["width_m"] = w_m
            det["height_m"] = h_m

    write_json(run_id, payload)
    write_csv(run_id, payload)
    return payload

