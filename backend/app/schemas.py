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


class Detection(BaseModel):
    id: str
    class_name: str = Field(alias="class")
    confidence: float
    bbox: BBox
    geolocation: Geolocation
    risk_level: str = "low"
    risk_score: float = 0.0

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
