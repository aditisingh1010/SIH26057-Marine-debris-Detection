from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

# Attempt to load domain preprocessing and risk calculation utilities
try:
    from ml.src.preprocess_sonar import compute_debris_risk, filter_sonar_noise
except ImportError:
    try:
        from preprocess_sonar import compute_debris_risk, filter_sonar_noise
    except ImportError:
        def filter_sonar_noise(image: np.ndarray, **kwargs: Any) -> np.ndarray:
            return image

        def compute_debris_risk(
            bbox: dict,
            image_width: int,
            image_height: int,
            confidence: float,
            class_name: str,
        ) -> tuple[str, float]:
            width = float(bbox.get("width", 0.0))
            height = float(bbox.get("height", 0.0))
            total_area = float(image_width * image_height)
            rel_area = (width * height) / total_area if total_area > 0 else 0.0
            size_score = min(1.0, (rel_area ** 0.5) * 3.5)
            conf = min(1.0, max(0.0, float(confidence)))
            raw_risk = (0.45 * conf) + (0.35 * 0.70) + (0.20 * size_score)
            score = round(float(np.clip(raw_risk, 0.0, 1.0)), 2)
            level = "high" if score >= 0.70 else ("medium" if score >= 0.40 else "low")
            return level, score


def _safe_compute_risk(
    bbox: dict,
    width: int,
    height: int,
    conf: float,
    class_name: str,
) -> tuple[str, float]:
    """Safely invokes compute_debris_risk handling flexible return formats and fallbacks."""
    try:
        res = compute_debris_risk(
            bbox=bbox,
            image_width=width,
            image_height=height,
            confidence=conf,
            class_name=class_name,
        )
        if isinstance(res, tuple) and len(res) == 2:
            a, b = res
            if isinstance(a, str) and isinstance(b, (int, float)):
                return a, float(b)
            if isinstance(a, (int, float)) and isinstance(b, str):
                return b, float(a)
    except Exception as exc:
        logger.warning("Error invoking compute_debris_risk (%s); using fallback.", exc)

    # Deterministic fallback calculation
    w = float(bbox.get("width", 0.0))
    h = float(bbox.get("height", 0.0))
    total_area = float(width * height)
    rel_area = (w * h) / total_area if total_area > 0 else 0.0
    size_score = min(1.0, (rel_area ** 0.5) * 3.5)
    score = round(float(np.clip(0.45 * conf + 0.35 * 0.70 + 0.20 * size_score, 0.0, 1.0)), 2)
    level = "high" if score >= 0.70 else ("medium" if score >= 0.40 else "low")
    return level, score


class InferenceService:
    _shared_model = None
    _shared_names = None
    _shared_path = None

    def __init__(self, weights: Optional[Path | str] = None) -> None:
        self.weights = Path(weights or settings.model_path)
        self.loaded = False
        self.inference_mode: str = "mock"
        self.model = None
        self.names: dict[int, str] = {0: "debris_0", 1: "debris_1"}

        if self.weights.is_file():
            try:
                from ultralytics import YOLO  # lazy import inside try-catch

                path = str(self.weights.resolve())
                if (
                    InferenceService._shared_model is None
                    or InferenceService._shared_path != path
                ):
                    InferenceService._shared_model = YOLO(path)
                    InferenceService._shared_names = dict(
                        InferenceService._shared_model.names
                    )
                    InferenceService._shared_path = path

                self.model = InferenceService._shared_model
                self.names = InferenceService._shared_names
                self.loaded = True
                self.inference_mode = "real"
                logger.info("Loaded real YOLOv8 weights from %s", path)
            except Exception as exc:
                logger.warning(
                    "Failed to load weights from %s (%s). Falling back to mock mode.",
                    self.weights,
                    exc,
                )
                self.loaded = False
                self.inference_mode = "mock"
                self.model = None
        else:
            logger.info(
                "Model weights not found at %s. Initialized in mock inference mode.",
                self.weights,
            )
            self.loaded = False
            self.inference_mode = "mock"

    def _mock_predict(self, image_bgr: np.ndarray) -> list[dict[str, Any]]:
        """Generates deterministic mock detections on sonar image frame."""
        height, width = image_bgr.shape[:2]
        mock_specs = [
            {
                "rel_x": 0.35,
                "rel_y": 0.30,
                "rel_w": 0.15,
                "rel_h": 0.18,
                "conf": 0.88,
                "class": "debris_0",
            },
            {
                "rel_x": 0.60,
                "rel_y": 0.52,
                "rel_w": 0.12,
                "rel_h": 0.14,
                "conf": 0.74,
                "class": "debris_1",
            },
        ]
        detections = []
        for idx, spec in enumerate(mock_specs, start=1):
            x = max(0, min(width - 10, int(round(width * spec["rel_x"]))))
            y = max(0, min(height - 10, int(round(height * spec["rel_y"]))))
            w = max(10, min(width - x, int(round(width * spec["rel_w"]))))
            h = max(10, min(height - y, int(round(height * spec["rel_h"]))))
            bbox = {"x": x, "y": y, "width": w, "height": h}
            conf = spec["conf"]
            cls_name = spec["class"]
            risk_level, risk_score = _safe_compute_risk(
                bbox=bbox,
                width=width,
                height=height,
                conf=conf,
                class_name=cls_name,
            )
            detections.append(
                {
                    "id": f"det_{idx:03d}",
                    "class": cls_name,
                    "confidence": conf,
                    "bbox": bbox,
                    "risk_level": risk_level,
                    "risk_score": risk_score,
                }
            )
        return detections

    def predict(self, image_bgr: np.ndarray) -> list[dict[str, Any]]:
        """
        Runs object detection inference on a BGR image.
        If real weights are loaded, runs sonar noise filtering + YOLOv8 detection.
        Otherwise, runs deterministic mock detection.
        """
        height, width = image_bgr.shape[:2]

        if not self.loaded or self.model is None:
            return self._mock_predict(image_bgr)

        try:
            cleaned = filter_sonar_noise(image_bgr)
            results = self.model.predict(
                source=cleaned, conf=0.25, imgsz=416, verbose=False
            )
        except Exception as exc:
            logger.error("Real inference execution failed: %s. Falling back to mock.", exc)
            return self._mock_predict(image_bgr)

        detections: list[dict[str, Any]] = []
        if not results:
            return detections

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return detections

        for index, box in enumerate(boxes, start=1):
            xyxy = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = (float(v) for v in xyxy)
            x1 = max(0.0, min(float(width), x1))
            y1 = max(0.0, min(float(height), y1))
            x2 = max(0.0, min(float(width), x2))
            y2 = max(0.0, min(float(height), y2))
            if x2 < x1:
                x1, x2 = x2, x1
            if y2 < y1:
                y1, y2 = y2, y1
            x = int(round(x1))
            y = int(round(y1))
            box_w = int(round(x2 - x1))
            box_h = int(round(y2 - y1))
            box_w = max(0, min(width - x, box_w))
            box_h = max(0, min(height - y, box_h))
            cls_id = int(box.cls[0].item())
            class_name = self.names.get(cls_id, f"debris_{cls_id}")
            conf = float(box.conf[0].item())
            bbox = {"x": x, "y": y, "width": box_w, "height": box_h}
            risk_level, risk_score = _safe_compute_risk(
                bbox=bbox,
                width=width,
                height=height,
                conf=conf,
                class_name=class_name,
            )
            detections.append(
                {
                    "id": f"det_{index:03d}",
                    "class": class_name,
                    "confidence": round(conf, 4),
                    "bbox": bbox,
                    "risk_level": risk_level,
                    "risk_score": risk_score,
                }
            )
        return detections
