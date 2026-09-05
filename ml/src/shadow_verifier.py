import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

class AcousticShadowVerifier:
    """
    Physics-based Sonar Acoustic Contrast and Shadow Verifier for SSS targets.

    A genuine physical underwater 3D target MUST satisfy two core acoustic principles:
    1. Highlight Reflectance: Hard man-made objects (ship hull, crab pot, metal debris) produce
       higher backscatter and standard deviation than uniform ambient sand.
    2. Downrange Acoustic Shadow: Because high-frequency sound travels straight, protruding 3D objects
       cast a distinct acoustic shadow downrange (away from the towfish nadir).

    This module evaluates both Highlight Strength & Downrange Shadow Drop to eliminate
    phantom detections on bare sand ripples, rocks, and acoustic reverberations.
    """

    def __init__(
        self,
        shadow_intensity_ratio: float = 0.85,
        min_contrast_diff: float = 8.0,
        min_highlight_std: float = 18.0,
    ):
        self.shadow_intensity_ratio = shadow_intensity_ratio
        self.min_contrast_diff = min_contrast_diff
        self.min_highlight_std = min_highlight_std

    def verify(
        self,
        image: np.ndarray,
        detection: Dict[str, Any],
        nadir_x: Optional[int] = None
    ) -> Dict[str, Any]:
        label = detection["label"]
        conf = float(detection["confidence"])
        box = detection["box"]
        x1, y1, x2, y2 = [int(v) for v in box]

        h, w = image.shape[:2]
        if nadir_x is None:
            nadir_x = w // 2

        # 1. Pipeline objects often trench or run linear without point shadows
        if label == "pipeline":
            detection["shadow_score"] = 1.0
            detection["shadow_verified"] = True
            return detection

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Box dimensions
        box_w = max(10, x2 - x1)
        box_h = max(10, y2 - y1)
        box_center_x = (x1 + x2) // 2
        is_port_side = box_center_x < nadir_x

        # 2. Extract Highlight Target Region
        target_roi = gray[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        if target_roi.size == 0:
            return detection

        target_mean = float(np.mean(target_roi))
        target_std = float(np.std(target_roi))
        target_max = float(np.max(target_roi))

        # Ambient seabed background (samples above and below the box)
        bg_samples = []
        if y1 > 25:
            bg_samples.append(gray[max(0, y1 - 25):y1, max(0, x1):min(w, x2)])
        if y2 < h - 25:
            bg_samples.append(gray[y2:min(h, y2 + 25), max(0, x1):min(w, x2)])

        if bg_samples and any(s.size > 0 for s in bg_samples):
            ambient_bg_mean = float(np.mean(np.hstack([s.flatten() for s in bg_samples if s.size > 0])))
        else:
            ambient_bg_mean = float(np.mean(gray))

        # 3. Downrange Shadow Region
        shadow_len = max(15, int(box_w * 0.75))
        if is_port_side:
            sx1 = max(0, x1 - shadow_len)
            sx2 = x1
        else:
            sx1 = x2
            sx2 = min(w, x2 + shadow_len)

        sy1 = max(0, y1)
        sy2 = min(h, y2)

        shadow_roi = gray[sy1:sy2, sx1:sx2]

        has_shadow = False
        shadow_score = 0.0

        if shadow_roi.size > 0:
            shadow_mean = float(np.mean(shadow_roi))
            contrast_drop = ambient_bg_mean - shadow_mean
            shadow_ratio = shadow_mean / (ambient_bg_mean + 1e-5)

            # Valid shadow drops below ambient seabed background
            if shadow_ratio < self.shadow_intensity_ratio or contrast_drop >= self.min_contrast_diff:
                has_shadow = True
                shadow_score = min(1.0, max(0.2, (ambient_bg_mean - shadow_mean) / (ambient_bg_mean * 0.35 + 1e-5)))

        # Also evaluate acoustic target contrast: bare sand has very low std and matches ambient
        is_flat_sand = (target_std < self.min_highlight_std) and (abs(target_mean - ambient_bg_mean) < 18.0)
        is_pure_shadow = (
            target_mean < ambient_bg_mean * self.shadow_intensity_ratio
            and target_std < self.min_highlight_std
        )

        detection["shadow_score"] = round(float(shadow_score), 2)
        detection["shadow_verified"] = bool(has_shadow)
        detection["is_flat_sand"] = bool(is_flat_sand)

        # 4. Physical acoustic confidence weighting
        if is_pure_shadow:
            # Reject boxes placed over pure dark acoustic shadow
            detection["confidence"] = round(float(conf * 0.15), 3)

        elif label == "seafloor_debris":
            if is_flat_sand and not has_shadow:
                # Severe penalty for flat featureless seabed
                detection["confidence"] = round(float(conf * 0.25), 3)
            elif not has_shadow:
                detection["confidence"] = round(float(conf * (0.35 + 0.65 * shadow_score)), 3)
            else:
                detection["confidence"] = min(1.0, round(float(conf * 1.15), 3))

        elif label == "shipwreck":
            if has_shadow or target_std > 28.0:
                detection["confidence"] = min(1.0, round(float(conf * 1.25), 3))
            elif is_flat_sand:
                detection["confidence"] = round(float(conf * 0.30), 3)

        elif label in ["ghost_pot", "human"]:
            if is_flat_sand and not has_shadow:
                detection["confidence"] = round(float(conf * 0.30), 3)

        return detection

    def filter_detections(
        self,
        image: np.ndarray,
        detections: List[Dict[str, Any]],
        nadir_x: Optional[int] = None,
        min_display_confidence: float = 0.30
    ) -> List[Dict[str, Any]]:
        verified = []
        for det in detections:
            updated = self.verify(image, det, nadir_x)
            # Only keep detections that clear display threshold after acoustic physics check
            if updated["confidence"] >= min_display_confidence:
                verified.append(updated)
        return verified
