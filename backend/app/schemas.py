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
    width_m: Optional[float] = None
    height_m: Optional[float] = None
    estimated_height_m: Optional[float] = None
    shadow_length_m: Optional[float] = None
    acoustic_shadow_overlap: bool = False
    would_pass_demo: bool = False
    would_pass_survey: bool = False
    review_priority: str = "standard"

    model_config = {"populate_by_name": True}

class FilterStats(BaseModel):
    total_raw: int = 0
    total_filtered: int = 0
    noise_reduced_count: int = 0


class OperatorBriefing(BaseModel):
    kept: int = 0
    suppressed: int = 0
    demo_kept: int = 0
    survey_kept: int = 0
    extra_survey_candidates: int = 0
    immediate_count: int = 0
    review_queue_count: int = 0
    shadow_overlap_count: int = 0


class RunResult(BaseModel):
    id: str
    filename: str
    model: str
    inference_mode: str = "real"
    detection_mode: str = "demo"
    image_width: int
    image_height: int
    metadata_attached: bool
    conf_threshold: float = 0.25
    raw_detections: List[Detection] = []
    filtered_detections: List[Detection] = []
    detections: List[Detection]
    filter_stats: FilterStats = Field(default_factory=FilterStats)
    operator_briefing: OperatorBriefing = Field(default_factory=OperatorBriefing)
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
    detection_mode: str = "demo"
    geolocation_available: bool = False
    created_at: Optional[str] = None

class SystemInfo(BaseModel):
    version: str
    model: str
    classes: List[str]
    segmentation_support: bool
    onnx_available: bool
    metadata_formats: List[str]
    max_upload_mb: int
    confidence_threshold: float

class DatasetQuality(BaseModel):
    total_images: int
    labeled_images: int
    background_images: int
    total_annotations: int
    class_counts: dict[str, int]
    image_sizes: List[str]
    label_issues: int
    summary: str

class EvaluationMetricSet(BaseModel):
    precision: float
    recall: float
    mAP50: float
    mAP50_95: float
    inference_ms_cpu: float
    confidence_threshold: float
    test_images: int
    test_annotations: int

class ModelQuality(BaseModel):
    model_name: str
    task: str
    classes: List[str]
    segmentation_support: bool
    onnx_available: bool
    evaluation_split: str
    quality_available: bool = False
    metrics_source: str = "none"
    primary_metrics: EvaluationMetricSet
    pr_sweep_metrics: EvaluationMetricSet
    dataset: DatasetQuality
    limitations: List[str]
    next_improvements: List[str]
