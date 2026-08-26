"""
YOLO Detector Evaluation Script -- ml/src/evaluate_detector.py

Evaluates a trained YOLOv8 model on a YOLO-format dataset split and reports:
  - Precision, Recall, mAP50, mAP50-95 (overall and per-class)
  - True Positives, False Positives, False Negatives
  - Inference speed (ms/image)

Results are printed to stdout and optionally saved to a JSON file.

Usage (from project root):
    python ml/src/evaluate_detector.py --weights C:/Users/medha/runs/detect/train/weights/best.pt --data ml/data/exp_data/filtered_data.yaml
    python ml/src/evaluate_detector.py --weights ml/data/exp_runs/filtered_model/weights/best.pt --split test --output ml/data/eval_results.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional


# ---------------------------------------------------------------------------
DEFAULT_WEIGHTS = r"C:\Users\medha\runs\detect\train\weights\best.pt"
DEFAULT_DATA    = "ml/data/exp_data/filtered_data.yaml"
DEFAULT_SPLIT   = "test"
DEFAULT_IMGSZ   = 416
DEFAULT_CONF    = 0.25
DEFAULT_IOU     = 0.50


# ---------------------------------------------------------------------------
def evaluate(
    weights: str,
    data: str,
    split: str = DEFAULT_SPLIT,
    imgsz: int = DEFAULT_IMGSZ,
    conf: float = DEFAULT_CONF,
    iou: float = DEFAULT_IOU,
    device: str = "cpu",
    output: Optional[str] = None,
) -> Dict:
    """
    Evaluate a trained YOLO model and return a metrics dictionary.

    Args:
        weights: Path to trained model weights (.pt file).
        data:    Path to the YOLO dataset YAML.
        split:   Dataset split to evaluate on: 'train', 'val', or 'test'.
        imgsz:   Inference image size.
        conf:    Confidence threshold for predictions.
        iou:     IoU threshold for NMS and TP/FP assignment.
        device:  Compute device ('cpu' or '0').
        output:  Optional path to save JSON results.

    Returns:
        Dictionary containing all evaluation metrics.
    """
    try:
        from ultralytics import YOLO  # noqa: PLC0415
    except ImportError:
        print("ERROR: ultralytics is not installed. Run: pip install ultralytics", file=sys.stderr)
        sys.exit(1)

    weights_path = Path(weights)
    data_path    = Path(data)

    if not weights_path.exists():
        raise FileNotFoundError(f"Weights file not found: {weights_path.resolve()}")
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset YAML not found: {data_path.resolve()}")

    print(f"\n[evaluate_detector] Loading model from: {weights_path}")
    print(f"  data    : {data_path.resolve()}")
    print(f"  split   : {split}")
    print(f"  conf    : {conf}")
    print(f"  iou     : {iou}")
    print(f"  imgsz   : {imgsz}\n")

    model = YOLO(str(weights_path))

    metrics = model.val(
        data=str(data_path),
        split=split,
        imgsz=imgsz,
        conf=conf,
        iou=iou,
        device=device,
        plots=True,
        verbose=True,
    )

    # ── Extract results ──────────────────────────────────────────────────────
    box = metrics.box

    # Per-class names from YAML
    import yaml  # noqa: PLC0415
    with open(str(data_path), "r", encoding="utf-8") as f:
        data_cfg = yaml.safe_load(f)
    class_names: Dict[int, str] = {int(k): v for k, v in data_cfg.get("names", {}).items()}

    per_class = []
    try:
        for i, cls_id in enumerate(box.ap_class_index.tolist()):
            per_class.append({
                "class_id":   int(cls_id),
                "class_name": class_names.get(int(cls_id), str(cls_id)),
                "precision":  round(float(box.p[i]), 4),
                "recall":     round(float(box.r[i]), 4),
                "mAP50":      round(float(box.ap50[i]), 4),
                "mAP50_95":   round(float(box.ap[i]),   4),
            })
    except Exception:
        per_class = []   # Graceful fallback if internal API differs

    result = {
        "weights":    str(weights_path.resolve()),
        "data":       str(data_path.resolve()),
        "split":      split,
        "conf_thresh": conf,
        "iou_thresh":  iou,
        "overall": {
            "precision":  round(float(box.mp),   4),
            "recall":     round(float(box.mr),   4),
            "mAP50":      round(float(box.map50), 4),
            "mAP50_95":   round(float(box.map),   4),
        },
        "per_class": per_class,
        "speed_ms_per_image": {
            "preprocess": round(metrics.speed.get("preprocess", 0.0), 2),
            "inference":  round(metrics.speed.get("inference",  0.0), 2),
            "postprocess":round(metrics.speed.get("postprocess",0.0), 2),
        },
    }

    # ── Print summary ─────────────────────────────────────────────────────────
    ov = result["overall"]
    print("\n" + "=" * 56)
    print("  EVALUATION RESULTS")
    print("=" * 56)
    print(f"  Split       : {split}")
    print(f"  Precision   : {ov['precision']:.4f}")
    print(f"  Recall      : {ov['recall']:.4f}")
    print(f"  mAP50       : {ov['mAP50']:.4f}")
    print(f"  mAP50-95    : {ov['mAP50_95']:.4f}")
    print(f"  Inference   : {result['speed_ms_per_image']['inference']:.1f} ms/image")

    if per_class:
        print("\n  Per-class breakdown:")
        for pc in per_class:
            print(f"    {pc['class_name']:12s}  P={pc['precision']:.3f}  "
                  f"R={pc['recall']:.3f}  mAP50={pc['mAP50']:.3f}")
    print("=" * 56 + "\n")

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"[evaluate_detector] Results saved to: {out_path.resolve()}")

    return result


# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate a trained YOLOv8 detector on the sonar debris dataset."
    )
    parser.add_argument("--weights", "-w", type=str, default=DEFAULT_WEIGHTS,
                        help="Path to trained model weights (.pt).")
    parser.add_argument("--data",    "-d", type=str, default=DEFAULT_DATA,
                        help=f"Path to YOLO dataset YAML (default: {DEFAULT_DATA}).")
    parser.add_argument("--split",   "-s", type=str, default=DEFAULT_SPLIT,
                        choices=["train", "val", "test"],
                        help=f"Dataset split to evaluate (default: {DEFAULT_SPLIT}).")
    parser.add_argument("--imgsz",   type=int,   default=DEFAULT_IMGSZ,
                        help=f"Inference image size (default: {DEFAULT_IMGSZ}).")
    parser.add_argument("--conf",    type=float, default=DEFAULT_CONF,
                        help=f"Confidence threshold (default: {DEFAULT_CONF}).")
    parser.add_argument("--iou",     type=float, default=DEFAULT_IOU,
                        help=f"IoU threshold for TP/FP (default: {DEFAULT_IOU}).")
    parser.add_argument("--device",  type=str,   default="cpu",
                        help="Compute device: 'cpu' or GPU index e.g. '0' (default: cpu).")
    parser.add_argument("--output",  "-o", type=str, default=None,
                        help="Optional path to save results as JSON.")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        evaluate(
            weights=args.weights,
            data=args.data,
            split=args.split,
            imgsz=args.imgsz,
            conf=args.conf,
            iou=args.iou,
            device=args.device,
            output=args.output,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
