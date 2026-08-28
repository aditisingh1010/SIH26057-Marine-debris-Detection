from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

def filter_detections(
    raw_detections: List[Dict[str, Any]],
    image_width: int,
    image_height: int,
    conf_threshold: float = 0.25,
    min_area: float = 25.0,
    max_area_ratio: float = 0.90,
    min_aspect_ratio: float = 0.05,
    max_aspect_ratio: float = 20.0,
) -> Dict[str, Any]:
    """
    Transparent post-processing module for sonar detections.
    Filters raw detections using configurable rules:
    - Confidence threshold (default 0.25)
    - Minimum bounding-box area (in pixels)
    - Maximum bounding-box area (relative to image dimensions)
    - Aspect ratio sanity check

    Returns both raw and filtered detections for side-by-side demonstration.
    """
    total_image_area = float(image_width * image_height)
    max_area = total_image_area * max_area_ratio if total_image_area > 0 else float("inf")

    processed_raw: List[Dict[str, Any]] = []
    filtered_detections: List[Dict[str, Any]] = []

    for index, det in enumerate(raw_detections, start=1):
        bbox = det.get("bbox", {})
        w = float(bbox.get("width", 0))
        h = float(bbox.get("height", 0))
        box_area = w * h
        conf = float(det.get("confidence", 0.0))

        aspect_ratio = (w / h) if h > 0 else 1.0

        # Determine rejection reason if any
        rejection_reason = None
        if conf < conf_threshold:
            rejection_reason = f"Confidence {conf:.2f} below threshold {conf_threshold:.2f}"
        elif box_area < min_area:
            rejection_reason = f"Area {box_area:.0f}px² below min threshold {min_area:.0f}px²"
        elif box_area > max_area:
            rejection_reason = f"Area {box_area:.0f}px² exceeds max threshold {max_area:.0f}px²"
        elif aspect_ratio < min_aspect_ratio or aspect_ratio > max_aspect_ratio:
            rejection_reason = f"Aspect ratio {aspect_ratio:.2f} out of range [{min_aspect_ratio}, {max_aspect_ratio}]"

        det_copy = dict(det)
        det_copy["passed_filter"] = (rejection_reason is None)
        det_copy["rejection_reason"] = rejection_reason

        processed_raw.append(det_copy)
        if rejection_reason is None:
            filtered_detections.append(det_copy)

    return {
        "raw_detections": processed_raw,
        "filtered_detections": filtered_detections,
        "total_raw": len(processed_raw),
        "total_filtered": len(filtered_detections),
        "noise_reduced_count": len(processed_raw) - len(filtered_detections)
    }
