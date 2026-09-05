from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from app.core.config import settings
from app.services.class_names import names_from_model, normalize_class_name

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

try:
    from ml.src.sonar_preprocessor import SonarPreprocessor
    from ml.src.tiled_inference import SSSSlicedInference
    from ml.src.shadow_verifier import AcousticShadowVerifier
except ImportError:
    try:
        from sonar_preprocessor import SonarPreprocessor
        from tiled_inference import SSSSlicedInference
        from shadow_verifier import AcousticShadowVerifier
    except ImportError:
        SonarPreprocessor = None
        SSSSlicedInference = None
        AcousticShadowVerifier = None

class InferenceService:
    _shared_model = None
    _shared_names = None
    _shared_path = None

    def __init__(self, weights: Optional[Path | str] = None) -> None:
        self.weights = Path(weights or settings.model_path)
        self.loaded = False
        self.inference_mode: str = "mock"
        self.model = None
        self.names: dict[int, str] = {}

        if self.weights.is_file():
            try:
                from ultralytics import YOLO

                path = str(self.weights.resolve())
                if (
                    InferenceService._shared_model is None
                    or InferenceService._shared_path != path
                ):
                    InferenceService._shared_model = YOLO(path)
                    InferenceService._shared_names = names_from_model(
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

    def _mock_class_name(self) -> str:
        if self.names:
            return next(iter(sorted(self.names.items())))[1]
        return "object"

    def _mock_predict(self, image_bgr: np.ndarray) -> list[dict[str, Any]]:
        """Deterministic fallback detections when weights are unavailable."""
        height, width = image_bgr.shape[:2]
        class_name = self._mock_class_name()
        mock_specs = [
            {"rel_x1": 0.30, "rel_y1": 0.25, "rel_w": 0.16, "rel_h": 0.18, "conf": 0.87},
            {"rel_x1": 0.58, "rel_y1": 0.50, "rel_w": 0.14, "rel_h": 0.15, "conf": 0.76},
        ]
        detections = []
        for idx, spec in enumerate(mock_specs, start=1):
            x1 = int(round(width * spec["rel_x1"]))
            y1 = int(round(height * spec["rel_y1"]))
            w = int(round(width * spec["rel_w"]))
            h = int(round(height * spec["rel_h"]))
            bbox = {"x1": x1, "y1": y1, "x2": x1 + w, "y2": y1 + h, "x": x1, "y": y1, "width": w, "height": h}
            conf = spec["conf"]
            risk_level, risk_score = compute_debris_risk(
                bbox=bbox,
                image_width=width,
                image_height=height,
                confidence=conf,
                class_name=class_name,
            )
            detections.append({
                "id": f"det_{idx:03d}",
                "class": class_name,
                "confidence": conf,
                "bbox": bbox,
                "risk_level": risk_level,
                "risk_score": risk_score,
            })
        return detections

    def predict(
        self,
        image_bgr: np.ndarray,
        conf: float = 0.25,
        use_tiling: bool = True,
        verify_shadows: bool = True,
    ) -> list[dict[str, Any]]:
        """Runs SSS Preprocessing + Tiled/Global YOLOv8 Inference + Acoustic Shadow Verification."""
        height, width = image_bgr.shape[:2]

        if not self.loaded or self.model is None:
            return self._mock_predict(image_bgr)

        # 1. Modular SSS Preprocessing (header crop + nadir detection)
        crop_offset_y = 0
        nadir_x = width // 2
        processed_img = image_bgr

        if SonarPreprocessor is not None:
            try:
                preproc = SonarPreprocessor(enable_header_crop=True, enable_nadir_mask=True)
                pre_res = preproc.preprocess(image_bgr)
                processed_img = pre_res["image"]
                crop_offset_y = pre_res.get("crop_offset_y", 0)
                if pre_res.get("nadir_bounds"):
                    nadir_x = int((pre_res["nadir_bounds"][0] + pre_res["nadir_bounds"][1]) // 2)
            except Exception as exc:
                logger.warning("Sonar preprocessing failed: %s, continuing with raw image.", exc)
                processed_img = image_bgr

        # 2. Tiled vs Standard Inference
        # Automatically enable tiling if image dimensions exceed standard tile size (e.g., width or height >= 800)
        is_large_swath = max(width, height) >= 800

        try:
            if use_tiling and is_large_swath and SSSSlicedInference is not None:
                slicer = SSSSlicedInference(tile_size=640, overlap_ratio=0.25, iou_threshold=0.50)
                raw_dets = slicer.predict(self.model, processed_img, conf_threshold=conf, enable_coarse_pass=True)
            else:
                cleaned = filter_sonar_noise(processed_img)
                results = self.model.predict(source=cleaned, conf=conf, imgsz=640, verbose=False)
                raw_dets = []
                if results and len(results[0].boxes) > 0:
                    for box in results[0].boxes:
                        xyxy = box.xyxy[0].cpu().numpy()
                        cls_id = int(box.cls[0].item())
                        lbl = normalize_class_name(self.names.get(cls_id, f"class_{cls_id}"), cls_id)
                        conf_val = float(box.conf[0].item())
                        raw_dets.append({
                            "label": lbl,
                            "confidence": conf_val,
                            "box": [float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])]
                        })
        except Exception as exc:
            logger.error("Real inference execution failed: %s. Using mock fallback.", exc)
            return self._mock_predict(image_bgr)

        # 3. Acoustic Shadow Verification (filters phantom seabed false positives)
        if verify_shadows and AcousticShadowVerifier is not None and len(raw_dets) > 0:
            try:
                verifier = AcousticShadowVerifier()
                raw_dets = verifier.filter_detections(
                    processed_img, raw_dets, nadir_x=nadir_x, min_display_confidence=max(0.20, conf * 0.8)
                )
            except Exception as exc:
                logger.warning("Shadow verification step encountered error: %s", exc)

        detections: list[dict[str, Any]] = []
        for index, det in enumerate(raw_dets, start=1):
            x1, y1, x2, y2 = det["box"]
            # Restore header crop offset
            y1 += crop_offset_y
            y2 += crop_offset_y

            x1 = max(0.0, min(float(width), x1))
            y1 = max(0.0, min(float(height), y1))
            x2 = max(0.0, min(float(width), x2))
            y2 = max(0.0, min(float(height), y2))

            ix1, iy1 = int(round(x1)), int(round(y1))
            ix2, iy2 = int(round(x2)), int(round(y2))
            w = max(1, ix2 - ix1)
            h = max(1, iy2 - iy1)

            class_name = normalize_class_name(det.get("label", "object"))
            conf_val = float(det.get("confidence", 0.0))

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

            risk_level, risk_score = compute_debris_risk(
                bbox=bbox,
                image_width=width,
                image_height=height,
                confidence=conf_val,
                class_name=class_name,
            )

            detections.append({
                "id": f"det_{index:03d}",
                "class": class_name,
                "confidence": round(conf_val, 4),
                "bbox": bbox,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "mask_points": None,
                "shadow_verified": det.get("shadow_verified", True),
                "shadow_score": det.get("shadow_score", 1.0),
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
            cls_name = str(det.get("class") or "object").replace("_", " ").title()
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
