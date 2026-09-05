"""
Sonar Image Preprocessing and Noise-Filtering Module.

Applies conservative, edge-preserving noise reduction tailored for side-scan
and forward-looking sonar imagery. Preserves object highlight edges and
acoustic shadow boundaries while smoothing high-frequency speckle noise.
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
    Conservatively attenuate persistent vertical acquisition-line artifacts.

    Side-scan sonar strips often contain bright/dark line bias near the outer
    swath margins. This adjusts only those margins with a smooth ramp and leaves
    the central image content untouched.
    """
    if image is None or image.size == 0:
        raise ValueError("Input image is empty or invalid.")

    height, width = image.shape[:2]
    margin = max(6, int(round(width * margin_fraction)))
    if margin <= 0 or 2 * margin >= width:
        return image.copy()

    out = image.astype(np.float32, copy=True)
    channel_views = [out[:, :, idx] for idx in range(out.shape[2])] if out.ndim == 3 else [out]

    for channel in channel_views:
        left_means = np.mean(channel[:, : margin + 1], axis=0)
        left_ref = left_means[margin]
        for x in range(margin):
            t = (margin - x) / margin
            alpha = t * t * (3.0 - 2.0 * t)
            channel[:, x] -= (left_means[x] - left_ref) * alpha

        right_means = np.mean(channel[:, width - margin - 1 :], axis=0)
        right_ref = right_means[0]
        for idx, x in enumerate(range(width - margin, width)):
            t = (idx + 1) / margin
            alpha = t * t * (3.0 - 2.0 * t)
            channel[:, x] -= (right_means[idx + 1] - right_ref) * alpha

    return np.clip(out, 0, 255).astype(image.dtype, copy=False)


def filter_sonar_noise(
    image: np.ndarray,
    diameter: int = 5,
    sigma_color: float = 25.0,
    sigma_space: float = 25.0,
    suppress_side_artifacts: bool = True,
    margin_fraction: float = 0.035,
) -> np.ndarray:
    """
    Applies conservative bilateral filtering to reduce sonar speckle noise.

    Bilateral filtering smooths uniform seafloor acoustic speckle noise while
    strictly preserving steep intensity gradients at debris highlight edges
    and acoustic shadows.

    Args:
        image: Input sonar image array (grayscale or BGR/RGB, uint8).
        diameter: Diameter of pixel neighborhood used during filtering.
        sigma_color: Filter sigma in the color/intensity space. Smaller values
            keep intensity boundaries sharper.
        sigma_space: Filter sigma in coordinate space.
        suppress_side_artifacts: Whether to attenuate lateral acquisition lines.
        margin_fraction: Fraction of image width treated as each outer margin.

    Returns:
        Denoised sonar image array with identical shape and dtype.
    """
    if image is None or image.size == 0:
        raise ValueError("Input image is empty or invalid.")

    processed = (
        attenuate_lateral_artifacts(image, margin_fraction=margin_fraction)
        if suppress_side_artifacts
        else image
    )
    filtered = cv2.bilateralFilter(
        src=processed,
        d=diameter,
        sigmaColor=sigma_color,
        sigmaSpace=sigma_space,
    )
    return filtered


CLASS_HAZARD_WEIGHTS: dict[str, float] = {
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
    "ghost_net": 0.80,
    "fishing_gear": 0.80,
    "metal": 0.75,
    "marine_debris": 0.75,
    "seabed_object": 0.70,
    "debris": 0.70,
}


def detect_acoustic_shadows(
    image_bgr: np.ndarray,
    highlight_thresh: int = 175,
    shadow_thresh: int = 65,
    min_area: int = 200,
    max_zones: int = 10,
) -> list[dict]:
    """
    Detect candidate acoustic-shadow zones next to bright highlight returns.

    This is an explanatory heuristic for the dashboard and false-positive review,
    not a replacement for model detections.
    """
    if image_bgr is None or image_bgr.size == 0:
        return []

    try:
        gray = (
            cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            if image_bgr.ndim == 3
            else image_bgr.copy()
        )
        _, highlight_mask = cv2.threshold(gray, highlight_thresh, 255, cv2.THRESH_BINARY)
        _, shadow_mask = cv2.threshold(gray, shadow_thresh, 255, cv2.THRESH_BINARY_INV)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        adjacent_region = cv2.dilate(highlight_mask, kernel, iterations=2)
        adjacent_shadows = cv2.bitwise_and(shadow_mask, adjacent_region)

        contours, _ = cv2.findContours(
            adjacent_shadows, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        zones: list[dict] = []
        for contour in contours:
            x, y, width, height = cv2.boundingRect(contour)
            area = width * height
            if area < min_area:
                continue
            zones.append(
                {
                    "x": int(x),
                    "y": int(y),
                    "width": int(width),
                    "height": int(height),
                    "adjacent_to_highlight": True,
                }
            )

        zones.sort(key=lambda item: item["width"] * item["height"], reverse=True)
        return zones[:max_zones]
    except Exception:
        return []


def compute_debris_risk(
    bbox: dict,
    image_width: int,
    image_height: int,
    confidence: float,
    class_name: str,
) -> tuple[str, float]:
    """
    Compute a transparent prototype risk score from confidence, class, and size.
    """
    width = float(bbox.get("width", bbox.get("w", 0.0)))
    height = float(bbox.get("height", bbox.get("h", 0.0)))
    if width <= 0.0 and "x1" in bbox and "x2" in bbox:
        width = max(0.0, float(bbox["x2"]) - float(bbox["x1"]))
    if height <= 0.0 and "y1" in bbox and "y2" in bbox:
        height = max(0.0, float(bbox["y2"]) - float(bbox["y1"]))

    image_area = float(image_width * image_height)
    relative_area = max(0.0, width * height / image_area) if image_area > 0 else 0.0
    size_score = min(1.0, (relative_area ** 0.5) * 3.5)

    class_key = str(class_name).lower().replace("-", "_").strip()
    class_weight = CLASS_HAZARD_WEIGHTS.get(class_key)
    if class_weight is None:
        class_weight = next(
            (weight for key, weight in CLASS_HAZARD_WEIGHTS.items() if key in class_key),
            0.70,
        )

    conf = min(1.0, max(0.0, float(confidence)))
    risk_score = round(float(np.clip((0.45 * conf) + (0.35 * class_weight) + (0.20 * size_score), 0.0, 1.0)), 2)
    if risk_score >= 0.70:
        return "high", risk_score
    if risk_score >= 0.40:
        return "medium", risk_score
    return "low", risk_score


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
        label_path: Optional explicit path to the YOLO .txt label file. If None,
            the function checks for a .txt file matching the image stem in the
            same input directory.
        copy_label: Whether to copy the corresponding YOLO label to output_dir.
        diameter: Neighborhood diameter for bilateral filtering.
        sigma_color: Color/intensity sigma for bilateral filtering.
        sigma_space: Coordinate space sigma for bilateral filtering.
        suppress_side_artifacts: Whether to attenuate lateral acquisition lines.
        margin_fraction: Fraction of image width treated as each outer margin.

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

    # Apply conservative noise reduction
    processed_image = filter_sonar_noise(
        image=image,
        diameter=diameter,
        sigma_color=sigma_color,
        sigma_space=sigma_space,
        suppress_side_artifacts=suppress_side_artifacts,
        margin_fraction=margin_fraction,
    )

    # Save processed image under output directory
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
        suppress_side_artifacts: Whether to attenuate lateral acquisition lines.
        margin_fraction: Fraction of image width treated as each outer margin.

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
