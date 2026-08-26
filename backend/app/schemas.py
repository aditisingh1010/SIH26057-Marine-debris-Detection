from typing import Literal, Optional

from pydantic import BaseModel, Field


class BBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class Geolocation(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Literal["computed", "survey_position_only", "unavailable"]


class ShadowZone(BaseModel):
    """Acoustic shadow zone detected via heuristic analysis (experimental)."""
    x: int
    y: int
    width: int
    height: int
    adjacent_to_highlight: bool


class Detection(BaseModel):
    id: str
    class_name: str = Field(alias="class")
    confidence: float
    bbox: BBox
    geolocation: Geolocation
    risk_level: str = "low"
    risk_score: float = 0.0
    mask_points: Optional[list[list[float]]] = None
    """Segmentation polygon points (normalized 0–1). None for detection-only models."""

    model_config = {"populate_by_name": True}


class RunResult(BaseModel):
    id: str
    filename: str
    model: str
    inference_mode: str = "standard"
    image_width: int
    image_height: int
    metadata_attached: bool
    detections: list[Detection]
    shadow_zones: list[ShadowZone] = []


class BatchResult(BaseModel):
    runs: list[RunResult]
    total: int
    failed: int
    errors: list[str]


class RunSummary(BaseModel):
    id: str
    filename: str
    inference_mode: str
    detection_count: int


class SystemInfo(BaseModel):
    version: str
    model: str
    classes: list[str]
    segmentation_support: bool
    onnx_available: bool
    metadata_formats: list[str]
    max_upload_mb: int
    confidence_threshold: float
