"""
YOLO Detector Training Script -- ml/src/train_detector.py

Trains a YOLOv8 object detection model on a pre-built YOLO-format dataset.
Wraps the Ultralytics YOLO API with sensible defaults for the sonar debris
detection task and saves all artefacts under a named experiment directory.

Usage (from project root):
    python ml/src/train_detector.py --data ml/data/exp_data/filtered_data.yaml
    python ml/src/train_detector.py --data ml/data/splits/dataset.yaml --epochs 50 --name my_run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
DEFAULT_MODEL   = "yolov8n.pt"      # nano model; smallest pretrained YOLO checkpoint
DEFAULT_EPOCHS  = 50
DEFAULT_IMGSZ   = 416
DEFAULT_BATCH   = 16
DEFAULT_SEED    = 42
DEFAULT_PROJECT = "ml/data/exp_runs"
DEFAULT_NAME    = "sonar_detector"
DEFAULT_DATA    = "ml/data/exp_data/filtered_data.yaml"


# ---------------------------------------------------------------------------
def train(
    data: str,
    model: str = DEFAULT_MODEL,
    epochs: int = DEFAULT_EPOCHS,
    imgsz: int = DEFAULT_IMGSZ,
    batch: int = DEFAULT_BATCH,
    seed: int = DEFAULT_SEED,
    project: str = DEFAULT_PROJECT,
    name: str = DEFAULT_NAME,
    exist_ok: bool = True,
    device: str = "cpu",
) -> Path:
    """
    Train a YOLOv8 detection model.

    Args:
        data:     Path to the YOLO dataset YAML config.
        model:    Pretrained model checkpoint or architecture (e.g. yolov8n.pt).
        epochs:   Number of training epochs.
        imgsz:    Input image size (square).
        batch:    Batch size.
        seed:     Random seed for reproducibility.
        project:  Root directory where experiment sub-folders are saved.
        name:     Name of this experiment run.
        exist_ok: Allow overwriting an existing run directory.
        device:   Compute device (e.g. "cpu", "0" for first GPU).

    Returns:
        Path to the saved best.pt weights file.
    """
    try:
        from ultralytics import YOLO  # noqa: PLC0415
    except ImportError:
        print("ERROR: ultralytics is not installed. Run: pip install ultralytics", file=sys.stderr)
        sys.exit(1)

    data_path = Path(data)
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset YAML not found: {data_path.resolve()}")

    model_obj = YOLO(model)

    print(f"\n[train_detector] Starting training")
    print(f"  data    : {data_path.resolve()}")
    print(f"  model   : {model}")
    print(f"  epochs  : {epochs}")
    print(f"  imgsz   : {imgsz}")
    print(f"  batch   : {batch}")
    print(f"  seed    : {seed}")
    print(f"  project : {project}/{name}\n")

    results = model_obj.train(
        data=str(data_path),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        seed=seed,
        project=project,
        name=name,
        exist_ok=exist_ok,
        device=device,
        deterministic=True,
        plots=True,
        verbose=True,
    )

    save_dir = Path(results.save_dir)
    best_weights = save_dir / "weights" / "best.pt"
    print(f"\n[train_detector] Training complete.")
    print(f"  Best weights : {best_weights}")
    print(f"  Results dir  : {save_dir}\n")

    return best_weights


# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train a YOLOv8 detector on the sonar debris dataset."
    )
    parser.add_argument("--data",    type=str, default=DEFAULT_DATA,
                        help=f"Path to the YOLO dataset YAML (default: {DEFAULT_DATA}).")
    parser.add_argument("--model",   type=str, default=DEFAULT_MODEL,
                        help=f"Pretrained weights or architecture (default: {DEFAULT_MODEL}).")
    parser.add_argument("--epochs",  type=int, default=DEFAULT_EPOCHS,
                        help=f"Number of training epochs (default: {DEFAULT_EPOCHS}).")
    parser.add_argument("--imgsz",   type=int, default=DEFAULT_IMGSZ,
                        help=f"Input image size (default: {DEFAULT_IMGSZ}).")
    parser.add_argument("--batch",   type=int, default=DEFAULT_BATCH,
                        help=f"Batch size (default: {DEFAULT_BATCH}).")
    parser.add_argument("--seed",    type=int, default=DEFAULT_SEED,
                        help=f"Random seed (default: {DEFAULT_SEED}).")
    parser.add_argument("--project", type=str, default=DEFAULT_PROJECT,
                        help=f"Project directory (default: {DEFAULT_PROJECT}).")
    parser.add_argument("--name",    type=str, default=DEFAULT_NAME,
                        help=f"Experiment name (default: {DEFAULT_NAME}).")
    parser.add_argument("--device",  type=str, default="cpu",
                        help="Compute device: 'cpu' or GPU index e.g. '0' (default: cpu).")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        train(
            data=args.data,
            model=args.model,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            seed=args.seed,
            project=args.project,
            name=args.name,
            device=args.device,
        )
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
