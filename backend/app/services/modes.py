from __future__ import annotations

from typing import Literal

DetectionMode = Literal["demo", "survey", "custom"]

DEMO_CONF_THRESHOLD = 0.25
SURVEY_CONF_THRESHOLD = 0.10
# Only Survey uses this low YOLO floor. Demo keeps the original ~20% propose gate.
RAW_INFERENCE_CONF = 0.05
DEMO_YOLO_FLOOR = 0.20


def raw_yolo_conf(detection_mode: str, conf_threshold: float) -> float:
    """Confidence passed into YOLO.

    Demo/Custom keep the original conservative propose gate so overlays stay clean.
    Survey may propose from 5% so the 10% filter can actually keep mid boxes.
    """
    if (detection_mode or "").strip().lower() == "survey":
        return RAW_INFERENCE_CONF
    return round(max(DEMO_YOLO_FLOOR, float(conf_threshold) * 0.75), 4)


def shadow_min_display_conf(yolo_conf: float) -> float:
    """Do not re-raise Survey's YOLO floor; Demo stays at the original 20% shadow gate."""
    conf = float(yolo_conf)
    if conf >= DEMO_YOLO_FLOOR:
        return max(DEMO_YOLO_FLOOR, conf * 0.8)
    return conf

MODE_META = {
    "demo": {
        "label": "Demo",
        "goal": "higher precision",
        "description": "Fewer false positives for live judging. Some real debris may be missed.",
    },
    "survey": {
        "label": "Survey",
        "goal": "higher recall",
        "description": "Keeps weaker candidates for review. Expect more noise and shadow-like boxes.",
    },
    "custom": {
        "label": "Custom",
        "goal": "operator-chosen threshold",
        "description": "Uses the confidence slider instead of a named operating mode.",
    },
}


def resolve_operating_mode(mode: str | None, conf_threshold: float) -> tuple[str, float]:
    """Map API mode + threshold into a stored operating mode and effective confidence."""
    normalized = (mode or "").strip().lower()
    if normalized == "demo":
        return "demo", DEMO_CONF_THRESHOLD
    if normalized == "survey":
        return "survey", SURVEY_CONF_THRESHOLD
    if normalized == "custom":
        return "custom", float(conf_threshold)

    rounded = round(float(conf_threshold), 2)
    if rounded == DEMO_CONF_THRESHOLD:
        return "demo", DEMO_CONF_THRESHOLD
    if rounded == SURVEY_CONF_THRESHOLD:
        return "survey", SURVEY_CONF_THRESHOLD
    return "custom", float(conf_threshold)
