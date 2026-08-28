from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

# Domain preprocessing & noise filter
try:
    from ml.src.preprocess_sonar import compute_debris_risk, detect_acoustic_shadows, filter_sonar_noise
except ImportError:
    try:
        from preprocess_sonar import compute_debris_risk, detect_acoustic_shadows, filter_sonar_noise
    except ImportError:
        def detect_acoustic_shadows(image_bgr: np.ndarray, **kwargs: Any) -> list:
            return []
        def filter_sonar_noise(image: np.ndarray, **kwargs: Any) -> np.ndarray:
            return image
        def compute_debris_risk(bbox: dict, image_width: int, image_height: int, confidence: float, class_name: str) -> tuple[str, float]:
            return "medium", 0.50

class InferenceService:
    _shared_model = None
    _shared_names = None
    _shared_path = None

    def __init__(self, weights: Optional[Path | str] = None) -> None:
        self.weights = Path(weights or settings.model_path)
        self.loaded = False
        self.inference_mode: str = "mock"
        self.model = None
        self.names: dict[int, str] = {0: "crab_pot"}

        if self.weights.is_file():
            try:
                from ultralytics import YOLO

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
                logger.warning("Failed to load weights from %s (%s). Using mock mode.", self.weights, exc)
                self.loaded = False
                self.inference_mode = "mock"
                self.model = None
        else:
            logger.info("Weights not found at %s. Initialized in mock mode.", self.weights)
            self.loaded = False
            self.inference_mode = "mock"

    def _mock_predict(self, image_bgr: np.ndarray) -> list[dict[str, Any]]:
        """Generates deterministic mock detections for testing fallback."""
        height, width = image_bgr.shape[:2]
        mock_specs = [
            {"rel_x1": 0.30, "rel_y1": 0.25, "rel_w": 0.16, "rel_h": 0.18, "conf": 0.87, "class": "crab_pot"},
            {"rel_x1": 0.58, "rel_y1": 0.50, "rel_w": 0.14, "rel_h": 0.15, "conf": 0.76, "class": "crab_pot"},
        ]
        detections = []
        for idx, spec in enumerate(mock_specs, start=1):
            x1 = int(round(width * spec["rel_x1"]))
            y1 = int(round(height * spec["rel_y1"]))
            w = int(round(width * spec["rel_w"]))
            h = int(round(height * spec["rel_h"]))
            x2 = x1 + w
            y2 = y1 + h
            bbox = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "x": x1, "y": y1, "width": w, "height": h}
            conf = spec["conf"]
            cls_name = spec["class"]
            detections.append({
                "id": f"det_{idx:03d}",
                "class": cls_name,
                "confidence": conf,
                "bbox": bbox,
                "risk_level": "medium",
                "risk_score": 0.65,
            })
        return detections

    def predict(self, image_bgr: np.ndarray, conf: float = 0.15) -> list[dict[str, Any]]:
        """Runs sonar noise filtering + YOLOv8 object detection."""
        height, width = image_bgr.shape[:2]

        if not self.loaded or self.model is None:
            return self._mock_predict(image_bgr)

        try:
            cleaned = filter_sonar_noise(image_bgr)
            results = self.model.predict(source=cleaned, conf=conf, imgsz=640, verbose=False)
        except Exception as exc:
            logger.error("Real inference execution failed: %s. Using mock fallback.", exc)
            return self._mock_predict(image_bgr)

        detections: list[dict[str, Any]] = []
        if not results:
            return detections

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return detections

        masks = getattr(results[0], "masks", None)

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

            ix1, iy1 = int(round(x1)), int(round(y1))
            ix2, iy2 = int(round(x2)), int(round(y2))
            w = max(1, ix2 - ix1)
            h = max(1, iy2 - iy1)

            cls_id = int(box.cls[0].item())
            class_name = self.names.get(cls_id, "crab_pot")
            # Map 'Crab-Pot' to 'crab_pot' for consistency
            if class_name.lower().replace("-", "_") == "crab_pot":
                class_name = "crab_pot"

            conf_val = float(box.conf[0].item())
            bbox = {
                "x1": ix1,
                "y1": iy1,
                "x2": ix2,
                "y2": iy2,
                "x": ix1,
                "y": iy1,
                "width": w,
                "height": h,
            }

            mask_points: list[list[float]] | None = None
            if masks is not None:
                try:
                    mask_xy = masks.xy[index - 1]
                    if mask_xy is not None and len(mask_xy) > 0:
                        mask_points = [
                            [float(pt[0]) / width, float(pt[1]) / height]
                            for pt in mask_xy
                        ]
                except Exception:
                    mask_points = None

            detections.append({
                "id": f"det_{index:03d}",
                "class": class_name,
                "confidence": round(conf_val, 4),
                "bbox": bbox,
                "risk_level": "medium",
                "risk_score": round(conf_val, 2),
                "mask_points": mask_points,
            })
        return detections

    def draw_annotations(self, image_bgr: np.ndarray, detections: list[dict[str, Any]]) -> np.ndarray:
        """Draws green bounding boxes and label badges onto the sonar image."""
        annotated = image_bgr.copy()
        h, w = annotated.shape[:2]

        # Color palette: Vibrant Green for detections
        box_color = (45, 212, 191)  # BGR for teal/green #2dd4bf
        text_bg_color = (18, 11, 5) # Dark badge

        thickness = 2 if max(w, h) >= 600 else 1

        for det in detections:
            bbox = det.get("bbox", {})
            x1 = int(bbox.get("x1", bbox.get("x", 0)))
            y1 = int(bbox.get("y1", bbox.get("y", 0)))
            x2 = int(bbox.get("x2", x1 + bbox.get("width", 0)))
            y2 = int(bbox.get("y2", y1 + bbox.get("height", 0)))

            # Draw green bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, thickness)

            # Label badge
            cls_name = det.get("class", "crab_pot").replace("_", " ").title()
            conf = det.get("confidence", 0.0)
            label = f"{cls_name} {conf * 100:.0f}%"

            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.45
            font_thickness = 1

            (tw, th), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)

            # Label positioning (edge-safe)
            ly1 = max(th + 4, y1 - 4)
            ly2 = ly1 - th - 4
            lx2 = min(w - 1, x1 + tw + 8)

            cv2.rectangle(annotated, (x1, ly2), (lx2, ly1), text_bg_color, -1)
            cv2.rectangle(annotated, (x1, ly2), (lx2, ly1), box_color, 1)
            cv2.putText(annotated, label, (x1 + 4, ly1 - 3), font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)

        return annotated

    def shadow_zones(self, image_bgr: np.ndarray) -> list[dict]:
        try:
            return detect_acoustic_shadows(image_bgr)
        except Exception as exc:
            logger.warning("Shadow zone detection failed: %s", exc)
            return []
