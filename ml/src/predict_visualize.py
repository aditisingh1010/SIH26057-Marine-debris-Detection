"""
End-to-End Sonar Preprocessing + YOLO Detection & Visualization Pipeline
File: ml/src/predict_visualize.py

Pipeline Flow:
    RAW SONAR IMAGE
      --> Conservative Noise Filtering & Lateral Line Attenuation (filter_sonar_noise)
      --> YOLOv8 Detection (best.pt)
      --> Cleaned Sonar Image with Refined Green Bounding Boxes + Compact Labels
      --> Saved to Dedicated Output Folder

Requirements:
    - Leaves original Dataset/ 100% untouched.
    - Preserves fine object edges and acoustic shadows.
    - Visual formatting: Thin green bounding box, spacious margin padding,
      compact readable label with anti-clipping edge guards.

Usage:
    # Run on a single image:
    python ml/src/predict_visualize.py --input Dataset/2010/0256_2010.jpg --output ml/data/cleaned_predictions/single

    # Run on all 909 images across Dataset/2010 and Dataset/2018:
    python ml/src/predict_visualize.py --input Dataset --output ml/data/cleaned_predictions
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from ultralytics import YOLO

# Import conservative preprocessing module
try:
    from ml.src.preprocess_sonar import filter_sonar_noise
except ImportError:
    from preprocess_sonar import filter_sonar_noise  # Fallback for direct execution

# ---------------------------------------------------------------------------
# Default paths and hyperparameters
DEFAULT_WEIGHTS = "best.pt"
FALLBACK_CANDIDATES = [
    "best.pt",
    r"ml/data/exp_runs/sonar_detector/weights/best.pt",
    r"ml/data/exp_runs/filtered_model/weights/best.pt",
]
DEFAULT_INPUT = "Dataset"
DEFAULT_OUTPUT = "ml/data/cleaned_predictions"
DEFAULT_CONF = 0.25
DEFAULT_IMGSZ = 416

# Visual Styling: Vibrant Green in BGR
BOX_COLOR = (0, 240, 0)        # Crisp, vibrant green
TEXT_BG_COLOR = (0, 140, 0)    # Soft dark green badge background
TEXT_COLOR = (255, 255, 255)   # Crisp white text

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def resolve_model_path(weights_path: str) -> Path:
    """Find and validate the model weights file."""
    p = Path(weights_path)
    if p.is_file():
        return p.resolve()
    for candidate in FALLBACK_CANDIDATES:
        cand_path = Path(candidate)
        if cand_path.is_file():
            print(f"[pipeline] Specified weights not found. Using fallback: {cand_path.resolve()}")
            return cand_path.resolve()
    raise FileNotFoundError(f"Model weights file not found: {weights_path}")


def draw_green_detections(
    image: np.ndarray,
    boxes,
    names: dict,
    pad_ratio: float = 0.05,
) -> np.ndarray:
    """
    Draw clean, thin green bounding boxes with comfortable object spacing
    and compact, edge-safe confidence badges.
    """
    annotated = image.copy()
    h, w = annotated.shape[:2]

    for box in boxes:
        # Extract raw coordinates
        xyxy = box.xyxy[0].cpu().numpy().astype(float)
        raw_x1, raw_y1, raw_x2, raw_y2 = xyxy
        bw = raw_x2 - raw_x1
        bh = raw_y2 - raw_y1

        # 1. Comfortable breathing margin around object (prevents cramped look)
        pad_x = max(2, int(round(bw * pad_ratio)))
        pad_y = max(2, int(round(bh * pad_ratio)))

        x1 = max(0, int(round(raw_x1 - pad_x)))
        y1 = max(0, int(round(raw_y1 - pad_y)))
        x2 = min(w - 1, int(round(raw_x2 + pad_x)))
        y2 = min(h - 1, int(round(raw_y2 + pad_y)))

        cls_id = int(box.cls[0].item())
        conf = float(box.conf[0].item())
        cls_name = names.get(cls_id, f"debris_{cls_id}")

        label = f"{cls_name} {conf:.2f}"

        # 2. Refined, thin box line (1px for 416-512, 2px for 1024+)
        thickness = 1 if min(w, h) <= 600 else 2
        cv2.rectangle(annotated, (x1, y1), (x2, y2), BOX_COLOR, thickness)

        # 3. Compact, readable label styling
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.38 if min(w, h) <= 600 else 0.50
        font_thick = 1

        (tw, th), baseline = cv2.getTextSize(label, font, font_scale, font_thick)
        badge_w = tw + 6
        badge_h = th + baseline + 4

        # 4. Anti-clipping Edge Guards:
        # Prevent label running off left or right border
        badge_x1 = max(0, min(x1, w - badge_w - 1))
        badge_x2 = badge_x1 + badge_w

        # If box is too close to top edge, render label inside the box
        if y1 - badge_h < 0:
            badge_y1 = y1
            badge_y2 = y1 + badge_h
            text_y = badge_y1 + th + 2
        else:
            badge_y1 = y1 - badge_h
            badge_y2 = y1
            text_y = badge_y2 - baseline - 2

        text_x = badge_x1 + 3

        # Draw compact badge background + crisp text
        cv2.rectangle(annotated, (badge_x1, badge_y1), (badge_x2, badge_y2), TEXT_BG_COLOR, -1)
        cv2.putText(
            annotated,
            label,
            (text_x, text_y),
            font,
            font_scale,
            TEXT_COLOR,
            font_thick,
            cv2.LINE_AA,
        )

    return annotated


def process_single_image(
    model: YOLO,
    img_path: Path,
    output_dir: Path,
    conf: float = DEFAULT_CONF,
    imgsz: int = DEFAULT_IMGSZ,
    apply_preprocess: bool = True,
    relative_root: Optional[Path] = None,
) -> Path:
    """
    Executes full pipeline on a single image:
    RAW Image -> Conservative Preprocessing -> YOLO Inference -> Refined Green Box
    """
    raw_img = cv2.imread(str(img_path))
    if raw_img is None:
        raise ValueError(f"Failed to read image: {img_path}")

    # Conservative Sonar Preprocessing (Noise Filtering + Lateral Line Attenuation)
    if apply_preprocess:
        cleaned_img = filter_sonar_noise(
            image=raw_img,
            diameter=5,
            sigma_color=25.0,
            sigma_space=25.0,
            suppress_side_artifacts=True,
            margin_fraction=0.035,
        )
    else:
        cleaned_img = raw_img

    # YOLO Detection Inference
    results = model.predict(source=cleaned_img, conf=conf, imgsz=imgsz, verbose=False)
    boxes = results[0].boxes

    # Draw Refined Green Bounding Boxes onto the CLEANED image
    annotated_output = draw_green_detections(cleaned_img, boxes, model.names)

    # Determine destination path preserving subfolder structure
    if relative_root and img_path.is_relative_to(relative_root):
        rel_sub = img_path.relative_to(relative_root)
        dest_path = output_dir / rel_sub
    else:
        dest_path = output_dir / img_path.name

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest_path), annotated_output, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

    return dest_path


def run_combined_pipeline(
    weights: str,
    input_path: str,
    output_path: str,
    conf: float = DEFAULT_CONF,
    imgsz: int = DEFAULT_IMGSZ,
    no_preprocess: bool = False,
) -> None:
    """Batch processes images through the combined pipeline."""
    model_file = resolve_model_path(weights)
    print(f"\n[pipeline] Loading trained model: {model_file}")
    model = YOLO(str(model_file))

    inp = Path(input_path).resolve()
    out = Path(output_path).resolve()

    if not inp.exists():
        raise FileNotFoundError(f"Input path does not exist: {inp}")

    if inp.is_file():
        target_files = [inp]
        rel_root = None
    else:
        target_files = sorted(
            [p for p in inp.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS]
        )
        rel_root = inp

    total = len(target_files)
    if total == 0:
        print(f"[pipeline] No image files found under: {inp}")
        return

    apply_preprocess = not no_preprocess
    print(f"[pipeline] Processing {total} images...")
    print(f"[pipeline] Preprocessing enabled : {apply_preprocess} (Conservative bilateral + lateral attenuation)")
    print(f"[pipeline] Confidence threshold  : {conf}")
    print(f"[pipeline] Target output folder  : {out}\n")

    for idx, fpath in enumerate(target_files, start=1):
        process_single_image(
            model=model,
            img_path=fpath,
            output_dir=out,
            conf=conf,
            imgsz=imgsz,
            apply_preprocess=apply_preprocess,
            relative_root=rel_root,
        )
        if idx % 100 == 0 or idx == total:
            print(f"  Progress: {idx}/{total} images processed ({idx/total*100:.1f}%)")

    print(f"\n[pipeline] Pipeline finished successfully! All cleaned + boxed images saved to:")
    print(f"  {out}\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Combined Sonar Preprocessing + YOLO Green Box Detection Pipeline."
    )
    parser.add_argument(
        "--weights", "-w",
        type=str,
        default=DEFAULT_WEIGHTS,
        help=f"Path to trained YOLO weights checkpoint (default: {DEFAULT_WEIGHTS})",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        default=DEFAULT_INPUT,
        help=f"Input image file or directory (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=DEFAULT_OUTPUT,
        help=f"Output directory for cleaned + boxed images (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--conf", "-c",
        type=float,
        default=DEFAULT_CONF,
        help=f"Detection confidence threshold (default: {DEFAULT_CONF})",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=DEFAULT_IMGSZ,
        help=f"Inference image size (default: {DEFAULT_IMGSZ})",
    )
    parser.add_argument(
        "--no-preprocess",
        action="store_true",
        help="Disable conservative preprocessing filter (uses raw image directly)",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        run_combined_pipeline(
            weights=args.weights,
            input_path=args.input,
            output_path=args.output,
            conf=args.conf,
            imgsz=args.imgsz,
            no_preprocess=args.no_preprocess,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
