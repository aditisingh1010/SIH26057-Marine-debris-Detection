"""
Sonar Image Preprocessing and Noise-Filtering Module.

Applies conservative, mild edge-preserving noise reduction tailored for side-scan
sonar (SSS) imagery. Preserves fine object highlight details, acoustic shadow
boundaries, and subtle seabed texture while attenuating persistent lateral sensor
acquisition line artifacts along the outer image margins.
"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

import cv2
import numpy as np


def attenuate_lateral_artifacts(
    image: np.ndarray,
    margin_fraction: float = 0.035,
) -> np.ndarray:
    """
    Conservatively attenuates persistent vertical acquisition line artifacts
    at the extreme left and right margins of side-scan sonar images.

    Applies a smooth cubic fade ramp to subtract the systematic outer-swath
    column baseline offset, preserving 2D texture and leaving the central sonar
    channel and all interior content completely untouched.

    Args:
        image: Input sonar image array (uint8).
        margin_fraction: Fraction of image width for the outer margin band (default: 0.035).

    Returns:
        Image array with side acquisition line artifacts attenuated.
    """
    if image is None or image.size == 0:
        raise ValueError("Input image is empty or invalid.")

    h, w = image.shape[:2]
    margin = max(6, int(round(w * margin_fraction)))
    if margin <= 0 or 2 * margin >= w:
        return image

    out = image.astype(np.float32)
    is_color = len(image.shape) == 3
    channels = 3 if is_color else 1

    for c in range(channels):
        ch = out[:, :, c] if is_color else out

        # Left margin attenuation
        col_means_left = np.mean(ch[:, : margin + 1], axis=0)
        ref_left = col_means_left[margin]
        for x in range(margin):
            t = (margin - x) / margin
            alpha = t * t * (3.0 - 2.0 * t)  # Smooth cubic Hermite curve
            offset = (col_means_left[x] - ref_left) * alpha
            ch[:, x] -= offset

        # Right margin attenuation
        col_means_right = np.mean(ch[:, w - margin - 1 :], axis=0)
        ref_right = col_means_right[0]
        for i, x in enumerate(range(w - margin, w)):
            t = (i + 1) / margin
            alpha = t * t * (3.0 - 2.0 * t)  # Smooth cubic Hermite curve
            offset = (col_means_right[i + 1] - ref_right) * alpha
            ch[:, x] -= offset

    return np.clip(out, 0, 255).astype(np.uint8)


def filter_sonar_noise(
    image: np.ndarray,
    diameter: int = 5,
    sigma_color: float = 25.0,
    sigma_space: float = 25.0,
    suppress_side_artifacts: bool = True,
    margin_fraction: float = 0.035,
) -> np.ndarray:
    """
    Applies conservative noise reduction and side artifact attenuation.

    Priority:
        Object visibility > Preserving sonar features > Artifact reduction > Smoothness.

    - Side Artifact Attenuation: Specifically targets the outer ~3.5% margins to
      attenuate persistent vertical acquisition line artifacts without touching
      the central sonar channel or interior seabed.
    - Mild Bilateral Filter: Uses conservative settings (d=5, sigma=25.0) to smooth
      speckle noise while strictly preserving sharp debris highlights, acoustic
      shadow boundaries, and fine seabed texture.

    Args:
        image: Input sonar image array (grayscale or BGR/RGB, uint8).
        diameter: Neighborhood diameter for bilateral filtering.
        sigma_color: Color/intensity sigma for bilateral filtering.
        sigma_space: Coordinate space sigma for bilateral filtering.
        suppress_side_artifacts: Whether to apply lateral artifact attenuation.
        margin_fraction: Fraction of width for the outer margin transition band.

    Returns:
        Processed sonar image array with identical shape and dtype.
    """
    if image is None or image.size == 0:
        raise ValueError("Input image is empty or invalid.")

    # 1. Attenuate side acquisition lines if enabled
    if suppress_side_artifacts:
        processed = attenuate_lateral_artifacts(image, margin_fraction=margin_fraction)
    else:
        processed = image

    # 2. Apply mild bilateral filter
    filtered = cv2.bilateralFilter(
        src=processed,
        d=diameter,
        sigmaColor=sigma_color,
        sigmaSpace=sigma_space,
    )
    return filtered


def preprocess_sonar_image(
    input_image_path: Union[str, Path],
    output_dir: Union[str, Path],
    label_path: Optional[Union[str, Path]] = None,
    copy_label: bool = True,
    diameter: int = 5,
    sigma_color: float = 25.0,
    sigma_space: float = 25.0,
    suppress_side_artifacts: bool = True,
    margin_fraction: float = 0.035,
) -> Tuple[Path, Optional[Path]]:
    """
    Preprocess a single sonar image and preserve its YOLO label.

    The original image is never modified or overwritten. Processed images and
    corresponding YOLO annotations are saved to the destination output directory.

    Args:
        input_image_path: Path to the input sonar image.
        output_dir: Target directory where processed image/label will be saved.
        label_path: Optional explicit path to the YOLO .txt label file.
        copy_label: Whether to copy the corresponding YOLO label to output_dir.
        diameter: Neighborhood diameter for bilateral filtering.
        sigma_color: Color/intensity sigma for bilateral filtering.
        sigma_space: Coordinate space sigma for bilateral filtering.
        suppress_side_artifacts: Whether to attenuate side acquisition lines.
        margin_fraction: Fraction of width for outer margin transition band.

    Returns:
        Tuple of (output_image_path, output_label_path).
    """
    src_img_path = Path(input_image_path).resolve()
    if not src_img_path.is_file():
        raise FileNotFoundError(f"Input image not found: {src_img_path}")

    dst_dir = Path(output_dir).resolve()
    dst_dir.mkdir(parents=True, exist_ok=True)

    # Read image without altering original
    image = cv2.imread(str(src_img_path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"Failed to read image file: {src_img_path}")

    # Apply preprocessing
    processed_image = filter_sonar_noise(
        image=image,
        diameter=diameter,
        sigma_color=sigma_color,
        sigma_space=sigma_space,
        suppress_side_artifacts=suppress_side_artifacts,
        margin_fraction=margin_fraction,
    )

    # Save processed image under output directory with high quality
    dst_img_path = dst_dir / src_img_path.name
    write_params = []
    if dst_img_path.suffix.lower() in {".jpg", ".jpeg"}:
        write_params = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
    elif dst_img_path.suffix.lower() == ".png":
        write_params = [int(cv2.IMWRITE_PNG_COMPRESSION), 3]

    success = cv2.imwrite(str(dst_img_path), processed_image, write_params)
    if not success:
        raise IOError(f"Failed to write processed image to: {dst_img_path}")

    # Resolve and copy corresponding YOLO label
    dst_lbl_path: Optional[Path] = None
    resolved_label_path: Optional[Path] = None

    if label_path is not None:
        candidate = Path(label_path).resolve()
        if candidate.is_file():
            resolved_label_path = candidate
    else:
        candidate = src_img_path.with_suffix(".txt")
        if candidate.is_file():
            resolved_label_path = candidate

    if resolved_label_path is not None and copy_label:
        dst_lbl_path = dst_dir / resolved_label_path.name
        # Copy without modifying original
        shutil.copy2(src=str(resolved_label_path), dst=str(dst_lbl_path))

    return dst_img_path, dst_lbl_path


def preprocess_sonar_batch(
    image_paths: Sequence[Union[str, Path]],
    output_dir: Union[str, Path],
    copy_labels: bool = True,
    diameter: int = 5,
    sigma_color: float = 25.0,
    sigma_space: float = 25.0,
    suppress_side_artifacts: bool = True,
    margin_fraction: float = 0.035,
) -> List[Tuple[Path, Optional[Path]]]:
    """
    Preprocess a batch of sonar images and preserve their YOLO labels.

    Args:
        image_paths: List or sequence of image file paths.
        output_dir: Destination directory for processed files.
        copy_labels: Whether to preserve/copy corresponding YOLO label files.
        diameter: Neighborhood diameter for bilateral filtering.
        sigma_color: Color/intensity sigma for bilateral filtering.
        sigma_space: Coordinate space sigma for bilateral filtering.
        suppress_side_artifacts: Whether to attenuate side acquisition lines.
        margin_fraction: Fraction of width for outer margin transition band.

    Returns:
        List of (output_image_path, output_label_path) tuples.
    """
    results: List[Tuple[Path, Optional[Path]]] = []
    for img_path in image_paths:
        res = preprocess_sonar_image(
            input_image_path=img_path,
            output_dir=output_dir,
            copy_label=copy_labels,
            diameter=diameter,
            sigma_color=sigma_color,
            sigma_space=sigma_space,
            suppress_side_artifacts=suppress_side_artifacts,
            margin_fraction=margin_fraction,
        )
        results.append(res)
    return results


# Domain-aware hazard severity weights for sonar marine debris targets
CLASS_HAZARD_WEIGHTS: dict[str, float] = {
    # Critical hazards (navigational danger, explosive, toxic, large entrapment)
    "munition": 1.00,
    "unexploded_ordnance": 1.00,
    "hazard": 0.95,
    "chemical_drum": 0.95,
    "drum": 0.90,
    "container": 0.90,
    "wreck": 0.85,
    "shipwreck": 0.85,
    "pipe": 0.85,
    "pipeline": 0.85,
    "cable": 0.80,
    "net": 0.80,
    "fishing_gear": 0.80,
    # Moderate hazards (heavy/dense debris, seabed obstacles)
    "metal": 0.75,
    "tire": 0.70,
    "tyre": 0.70,
    "concrete": 0.70,
    "debris_1": 0.75,
    "debris_0": 0.65,
    "plastic": 0.65,
    "wood": 0.60,
    "debris": 0.70,
}


def compute_debris_risk(
    bbox: dict,
    image_width: int,
    image_height: int,
    confidence: float,
    class_name: str,
) -> tuple[str, float]:
    """
    Computes domain-aware risk assessment for detected sonar debris targets.

    Combines detection confidence, relative acoustic footprint area,
    and class hazard severity weighting into a calibrated risk score and level.

    Args:
        bbox: Dictionary with bounding box dimensions containing 'width' and 'height'
              (or 'w', 'h', or 'x1','y1','x2','y2').
        image_width: Total sonar image/swath width in pixels.
        image_height: Total sonar image/swath height in pixels.
        confidence: Model prediction confidence score [0.0, 1.0].
        class_name: Predicted debris category/class label.

    Returns:
        tuple[str, float]: (risk_level, risk_score) where:
            - risk_score: float between 0.00 and 1.00 (rounded to 2 decimal places)
            - risk_level: 'high' (>= 0.70), 'medium' (>= 0.40), or 'low' (< 0.40)
    """
    # 1. Extract bounding box dimensions safely
    width = float(bbox.get("width", bbox.get("w", 0.0)))
    height = float(bbox.get("height", bbox.get("h", 0.0)))
    if width <= 0.0 and "x2" in bbox and "x1" in bbox:
        width = max(0.0, float(bbox["x2"]) - float(bbox["x1"]))
    if height <= 0.0 and "y2" in bbox and "y1" in bbox:
        height = max(0.0, float(bbox["y2"]) - float(bbox["y1"]))

    # 2. Calculate relative footprint area
    total_area = float(image_width * image_height)
    if total_area > 0:
        footprint_area = max(0.0, width * height)
        rel_area = min(1.0, max(0.0, footprint_area / total_area))
    else:
        rel_area = 0.0

    # 3. Resolve class hazard weighting
    cls_key = str(class_name).lower().strip()
    class_weight = CLASS_HAZARD_WEIGHTS.get(cls_key)
    if class_weight is None:
        # Match partial substring keys (e.g. 'submerged_pipe' -> 'pipe')
        for key, weight in CLASS_HAZARD_WEIGHTS.items():
            if key in cls_key:
                class_weight = weight
                break
        else:
            class_weight = 0.70  # Default fallback weight for unknown debris

    # 4. Compute normalized size score
    # Sonar debris occupying > 5-10% of swath represents substantial navigational hazard
    size_score = min(1.0, max(0.0, (rel_area ** 0.5) * 3.5))

    # 5. Composite risk calculation
    conf = min(1.0, max(0.0, float(confidence)))
    raw_risk = (0.45 * conf) + (0.35 * class_weight) + (0.20 * size_score)
    risk_score = round(float(np.clip(raw_risk, 0.0, 1.0)), 2)

    # 6. Categorize risk level
    if risk_score >= 0.70:
        risk_level = "high"
    elif risk_score >= 0.40:
        risk_level = "medium"
    else:
        risk_level = "low"

    return risk_level, risk_score


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sonar image noise-filtering and preprocessing module."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        required=True,
        help="Path to a single image file or directory of sonar images.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="ml/data/processed",
        help="Destination directory for processed images (default: ml/data/processed).",
    )
    parser.add_argument(
        "--limit",
        "-n",
        type=int,
        default=None,
        help="Maximum number of images to process when input is a directory.",
    )
    parser.add_argument(
        "--diameter",
        "-d",
        type=int,
        default=5,
        help="Bilateral filter neighborhood diameter (default: 5).",
    )
    parser.add_argument(
        "--sigma-color",
        type=float,
        default=25.0,
        help="Bilateral filter sigma in color/intensity space (default: 25.0).",
    )
    parser.add_argument(
        "--sigma-space",
        type=float,
        default=25.0,
        help="Bilateral filter sigma in coordinate space (default: 25.0).",
    )
    parser.add_argument(
        "--no-side-suppress",
        action="store_true",
        help="Disable suppression of lateral edge artifact lines.",
    )
    parser.add_argument(
        "--margin-fraction",
        type=float,
        default=0.035,
        help="Fraction of width for outer margin artifact suppression (default: 0.035).",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    suppress_sides = not args.no_side_suppress

    if input_path.is_file():
        img_out, lbl_out = preprocess_sonar_image(
            input_image_path=input_path,
            output_dir=output_dir,
            diameter=args.diameter,
            sigma_color=args.sigma_color,
            sigma_space=args.sigma_space,
            suppress_side_artifacts=suppress_sides,
            margin_fraction=args.margin_fraction,
        )
        print(f"Processed 1 image:")
        print(f"  Image -> {img_out}")
        if lbl_out:
            print(f"  Label -> {lbl_out}")
    else:
        # Directory mode
        candidates = sorted(
            [p for p in input_path.rglob("*") if p.suffix.lower() in image_extensions]
        )
        if args.limit is not None and args.limit > 0:
            candidates = candidates[: args.limit]

        if not candidates:
            print(f"No image files found under: {input_path}")
            return

        results = preprocess_sonar_batch(
            image_paths=candidates,
            output_dir=output_dir,
            copy_labels=True,
            diameter=args.diameter,
            sigma_color=args.sigma_color,
            sigma_space=args.sigma_space,
            suppress_side_artifacts=suppress_sides,
            margin_fraction=args.margin_fraction,
        )
        print(f"Processed {len(results)} images saved to: {output_dir}")
        for img_out, lbl_out in results[:5]:
            lbl_str = f" (label: {lbl_out.name})" if lbl_out else " (no label)"
            print(f"  - {img_out.name}{lbl_str}")
        if len(results) > 5:
            print(f"  ... and {len(results) - 5} more.")


if __name__ == "__main__":
    main()
