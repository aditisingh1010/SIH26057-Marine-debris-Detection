from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.modes import DEMO_CONF_THRESHOLD, SURVEY_CONF_THRESHOLD


def _box_xywh(bbox: Dict[str, Any]) -> tuple[float, float, float, float]:
    x = float(bbox.get("x", bbox.get("x1", 0)))
    y = float(bbox.get("y", bbox.get("y1", 0)))
    w = float(bbox.get("width", 0))
    h = float(bbox.get("height", 0))
    if w <= 0 and "x2" in bbox:
        w = max(0.0, float(bbox["x2"]) - x)
    if h <= 0 and "y2" in bbox:
        h = max(0.0, float(bbox["y2"]) - y)
    return x, y, w, h


def _overlap_fraction(bbox: Dict[str, Any], zone: Dict[str, Any]) -> float:
    x, y, w, h = _box_xywh(bbox)
    if w <= 0 or h <= 0:
        return 0.0
    zx = float(zone.get("x", 0))
    zy = float(zone.get("y", 0))
    zw = float(zone.get("width", 0))
    zh = float(zone.get("height", 0))
    ix1 = max(x, zx)
    iy1 = max(y, zy)
    ix2 = min(x + w, zx + zw)
    iy2 = min(y + h, zy + zh)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    return (iw * ih) / (w * h)


def _shadow_overlap_and_dimensions(
    bbox: Dict[str, Any],
    shadow_zones: List[Dict[str, Any]],
    pixel_size_m: Optional[float] = None,
    towfish_altitude_m: float = 5.0,
    nadir_x: float = 208.0,
) -> tuple[bool, Optional[float], Optional[float]]:
    """
    Computes acoustic shadow overlap and calculates physical object height:
    Object Height = (Altitude * Shadow Length) / (Slant Range + Shadow Length)
    """
    x, y, w, h = _box_xywh(bbox)
    if w <= 0 or h <= 0:
        return False, None, None

    overlapping_zone = None
    for zone in shadow_zones:
        if _overlap_fraction(bbox, zone) >= 0.20:
            overlapping_zone = zone
            break

    if not overlapping_zone:
        return False, None, None

    # Calculate shadow length across horizontal swath
    px_size = pixel_size_m if pixel_size_m and pixel_size_m > 0 else 0.05
    shadow_px = float(overlapping_zone.get("width", 15))
    shadow_length_m = round(shadow_px * px_size, 3)

    # Slant range distance from nadir center
    center_x = x + w / 2.0
    slant_range_px = max(10.0, abs(center_x - nadir_x))
    slant_range_m = slant_range_px * px_size

    # Physical sonar shadow height equation
    # Height = (H * Ls) / (R + Ls)
    h_debris = (towfish_altitude_m * shadow_length_m) / max(0.1, (slant_range_m + shadow_length_m))
    estimated_height_m = round(max(0.05, min(10.0, h_debris)), 3)

    return True, shadow_length_m, estimated_height_m


def _shadow_overlap(bbox: Dict[str, Any], shadow_zones: List[Dict[str, Any]]) -> bool:
    return any(_overlap_fraction(bbox, zone) >= 0.20 for zone in shadow_zones)


def _review_priority(conf: float, risk_level: str, in_shadow: bool) -> str:
    risk = str(risk_level or "low").lower()
    if in_shadow and conf < 0.55:
        return "review"
    if risk in {"high", "critical"} and conf >= DEMO_CONF_THRESHOLD:
        return "immediate"
    if conf < DEMO_CONF_THRESHOLD:
        return "review"
    return "standard"


def filter_detections(
    raw_detections: List[Dict[str, Any]],
    image_width: int,
    image_height: int,
    conf_threshold: float = 0.25,
    min_area: float = 25.0,
    max_area_ratio: float = 0.90,
    min_aspect_ratio: float = 0.05,
    max_aspect_ratio: float = 20.0,
    shadow_zones: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Transparent sonar post-filter.

    Size/aspect/confidence can reject a box. Acoustic-shadow overlap does not
    auto-delete — it flags the box for human review. That is the operator-triage
    layer, not a silent drop.
    """
    zones = shadow_zones or []
    total_image_area = float(image_width * image_height)
    max_area = total_image_area * max_area_ratio if total_image_area > 0 else float("inf")

    processed_raw: List[Dict[str, Any]] = []
    filtered_detections: List[Dict[str, Any]] = []

    for det in raw_detections:
        bbox = det.get("bbox", {})
        w, h = _box_xywh(bbox)[2], _box_xywh(bbox)[3]
        box_area = w * h
        conf = float(det.get("confidence", 0.0))
        aspect_ratio = (w / h) if h > 0 else 1.0
        in_shadow, shadow_len_m, est_height_m = _shadow_overlap_and_dimensions(
            bbox=bbox,
            shadow_zones=zones,
            nadir_x=float(image_width / 2.0),
        )
        geometry_ok = (
            box_area >= min_area
            and box_area <= max_area
            and min_aspect_ratio <= aspect_ratio <= max_aspect_ratio
        )

        # Per-class physical sensitivity thresholds (derived from AUV acoustic recommendations)
        cls_name = str(det.get("class", "")).lower()
        effective_min_conf = conf_threshold
        if cls_name == "seafloor_debris":
            # If candidate has verified acoustic shadow or we are in survey mode (conf_threshold <= 0.15)
            has_acoustic_shadow = bool(det.get("shadow_verified", False) or in_shadow)
            if conf_threshold <= 0.15:
                effective_min_conf = conf_threshold
            else:
                effective_min_conf = max(conf_threshold, 0.25 if has_acoustic_shadow else 0.40)
        elif cls_name == "shipwreck":
            # Shipwrecks are large macro objects; allow lower initial detection to be caught
            effective_min_conf = min(conf_threshold, 0.20)

        rejection_reason = None
        if conf < effective_min_conf:
            rejection_reason = f"Confidence {conf:.2f} below effective threshold {effective_min_conf:.2f} for {cls_name}"
        elif box_area < min_area:
            rejection_reason = f"Area {box_area:.0f}px² below min threshold {min_area:.0f}px²"
        elif box_area > max_area:
            rejection_reason = f"Area {box_area:.0f}px² exceeds max threshold {max_area:.0f}px²"
        elif aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
            rejection_reason = (
                f"Aspect ratio {aspect_ratio:.2f} out of range "
                f"[{min_aspect_ratio}, {max_aspect_ratio}]"
            )

        det_copy = dict(det)
        det_copy["passed_filter"] = rejection_reason is None
        det_copy["rejection_reason"] = rejection_reason
        det_copy["acoustic_shadow_overlap"] = in_shadow
        det_copy["shadow_length_m"] = shadow_len_m
        det_copy["estimated_height_m"] = est_height_m
        det_copy["would_pass_demo"] = bool(geometry_ok and conf >= DEMO_CONF_THRESHOLD)
        det_copy["would_pass_survey"] = bool(geometry_ok and conf >= SURVEY_CONF_THRESHOLD)
        det_copy["review_priority"] = _review_priority(
            conf, str(det.get("risk_level", "low")), in_shadow
        )

        processed_raw.append(det_copy)
        if rejection_reason is None:
            filtered_detections.append(det_copy)

    briefing = build_operator_briefing(processed_raw, filtered_detections)
    return {
        "raw_detections": processed_raw,
        "filtered_detections": filtered_detections,
        "total_raw": len(processed_raw),
        "total_filtered": len(filtered_detections),
        "noise_reduced_count": len(processed_raw) - len(filtered_detections),
        "operator_briefing": briefing,
    }


def build_operator_briefing(
    processed_raw: List[Dict[str, Any]],
    filtered_detections: List[Dict[str, Any]],
) -> Dict[str, Any]:
    review_queue = [
        det
        for det in filtered_detections
        if det.get("review_priority") == "review" or det.get("acoustic_shadow_overlap")
    ]
    immediate = [det for det in filtered_detections if det.get("review_priority") == "immediate"]
    demo_kept = sum(1 for det in processed_raw if det.get("would_pass_demo"))
    survey_kept = sum(1 for det in processed_raw if det.get("would_pass_survey"))
    return {
        "kept": len(filtered_detections),
        "suppressed": len(processed_raw) - len(filtered_detections),
        "demo_kept": demo_kept,
        "survey_kept": survey_kept,
        "extra_survey_candidates": max(0, survey_kept - demo_kept),
        "immediate_count": len(immediate),
        "review_queue_count": len(review_queue),
        "shadow_overlap_count": sum(
            1 for det in filtered_detections if det.get("acoustic_shadow_overlap")
        ),
    }
