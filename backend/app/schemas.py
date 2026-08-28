from typing import Literal, Optional, List
from pydantic import BaseModel, Field

class BBox(BaseModel):
    x: int
    y: int
    width: int
    height: int
    x1: int
    y1: int
    x2: int
    y2: int

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
    passed_filter: bool = True
    rejection_reason: Optional[str] = None
    mask_points: Optional[List[List[float]]] = None

    model_config = {"populate_by_name": True}

class RunResult(BaseModel):
    id: str
    filename: str
    model: str
    inference_mode: str = "real"
    image_width: int
    image_height: int
    metadata_attached: bool
    conf_threshold: float = 0.25
    raw_detections: List[Detection] = []
    filtered_detections: List[Detection] = []
    detections: List[Detection]
    shadow_zones: List[ShadowZone] = []
    geolocation_available: bool = False
    geolocation_note: str = "Geolocation unavailable: sonar metadata not provided."
    annotated_image_url: Optional[str] = None
    json_report_url: Optional[str] = None
    csv_report_url: Optional[str] = None

class BatchResult(BaseModel):
    runs: List[RunResult]
    total: int
    failed: int
    errors: List[str]

class RunSummary(BaseModel):
    id: str
    filename: str
    inference_mode: str
    detection_count: int

class SystemInfo(BaseModel):
    version: str
    model: str
    classes: List[str]
    segmentation_support: bool
    onnx_available: bool
    metadata_formats: List[str]
    max_upload_mb: int
    confidence_threshold: float
