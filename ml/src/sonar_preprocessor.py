import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any

class SonarPreprocessor:
    """
    Modular preprocessor for Side-Scan Sonar (SSS) imagery.
    Handles:
    - Auto-cropping window title/header bars
    - Detecting and masking central nadir (water-column blind zone)
    - Dual-channel split (Port / Starboard)
    - Optional conservative despeckle & mild CLAHE
    """

    def __init__(
        self,
        enable_header_crop: bool = True,
        enable_nadir_mask: bool = True,
        clahe_clip_limit: float = 2.0,
        enable_clahe: bool = False,
    ):
        self.enable_header_crop = enable_header_crop
        self.enable_nadir_mask = enable_nadir_mask
        self.clahe_clip_limit = clahe_clip_limit
        self.enable_clahe = enable_clahe

    def crop_software_header(self, image: np.ndarray) -> Tuple[np.ndarray, int]:
        """
        Detects and removes window title bars, UI playback menus, or black borders at the top.
        Returns: (cropped_image, crop_top_offset)
        """
        h, w = image.shape[:2]
        if not self.enable_header_crop or h < 200:
            return image, 0

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        search_height = min(int(h * 0.15), 120)
        top_region = gray[:search_height, :]

        row_means = np.mean(top_region, axis=1)
        row_diffs = np.abs(np.diff(row_means))

        crop_y = 0
        if len(row_diffs) > 0:
            peaks = np.where(row_diffs > 15)[0]
            if len(peaks) > 0:
                candidate_y = int(peaks[-1]) + 2
                if 15 <= candidate_y <= search_height:
                    crop_y = candidate_y

        if crop_y > 0:
            return image[crop_y:, :], crop_y

        return image, 0

    def detect_nadir(self, image: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Detects the central vertical dark water column (nadir zone).
        Returns: (nadir_left_x, nadir_right_x) or None if not detected.
        """
        h, w = image.shape[:2]
        if w < 100:
            return None

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        center_start = int(w * 0.35)
        center_end = int(w * 0.65)
        center_strip = gray[:, center_start:center_end]

        col_means = np.mean(center_strip, axis=0)
        smoothed = cv2.GaussianBlur(col_means.reshape(1, -1), (1, 15), 0)[0]

        min_idx = np.argmin(smoothed)
        min_val = smoothed[min_idx]

        outer_strip = np.hstack([gray[:, :int(w * 0.25)], gray[:, int(w * 0.75):]])
        outer_mean = np.mean(outer_strip)

        if min_val < outer_mean * 0.65:
            center_x = center_start + min_idx
            threshold = min_val + (outer_mean - min_val) * 0.4

            left_x = center_x
            while left_x > center_start and smoothed[left_x - center_start] < threshold:
                left_x -= 1

            right_x = center_x
            while right_x < center_end - 1 and smoothed[right_x - center_start] < threshold:
                right_x += 1

            nadir_w = right_x - left_x
            if 6 <= nadir_w <= int(w * 0.25):
                return (left_x, right_x)

        return None

    def mask_nadir(self, image: np.ndarray, nadir_bounds: Tuple[int, int]) -> np.ndarray:
        """
        Masks the nadir region with pure black to prevent YOLO false triggers.
        """
        out = image.copy()
        left_x, right_x = nadir_bounds
        out[:, left_x:right_x] = 0
        return out

    def preprocess(self, image: np.ndarray) -> Dict[str, Any]:
        cropped_img, crop_y = self.crop_software_header(image)
        nadir_bounds = self.detect_nadir(cropped_img) if self.enable_nadir_mask else None

        processed = cropped_img.copy()
        if nadir_bounds and self.enable_nadir_mask:
            processed = self.mask_nadir(processed, nadir_bounds)

        if self.enable_clahe:
            if len(processed.shape) == 3:
                lab = cv2.cvtColor(processed, cv2.COLOR_BGR2LAB)
                clahe = cv2.createCLAHE(clipLimit=self.clahe_clip_limit, tileGridSize=(8, 8))
                lab[:, :, 0] = clahe.apply(lab[:, :, 0])
                processed = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            else:
                clahe = cv2.createCLAHE(clipLimit=self.clahe_clip_limit, tileGridSize=(8, 8))
                processed = clahe.apply(processed)

        return {
            "image": processed,
            "crop_offset_y": crop_y,
            "nadir_bounds": nadir_bounds,
            "original_shape": image.shape,
        }
