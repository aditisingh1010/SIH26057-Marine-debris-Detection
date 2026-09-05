from __future__ import annotations

from typing import Literal

DetectionMode = Literal["demo", "survey", "custom"]

DEMO_CONF_THRESHOLD = 0.25
SURVEY_CONF_THRESHOLD = 0.10

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
