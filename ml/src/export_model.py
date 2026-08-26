"""
Export best.pt to ONNX and TorchScript for edge/AUV deployment.
Run from repo root: python ml/src/export_model.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEIGHTS = ROOT / "best.pt"


def export_model(weights: Path, fmt: str = "all") -> None:
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics not installed. Run: pip install ultralytics")
        return

    if not weights.is_file():
        print(f"ERROR: weights not found at {weights}")
        return

    model = YOLO(str(weights))
    print(f"Loaded model: {weights} ({weights.stat().st_size / 1e6:.1f} MB)")
    print(f"Task: {model.task} | Classes: {list(model.names.values())}")

    exported: list[Path] = []

    if fmt in ("onnx", "all"):
        print("\nExporting to ONNX (for edge CPU/GPU and Jetson Nano)...")
        out = model.export(format="onnx", imgsz=416, simplify=True)
        p = Path(str(out))
        if p.is_file():
            print(f"  ONNX: {p} ({p.stat().st_size / 1e6:.1f} MB)")
            exported.append(p)
        else:
            print(f"  ONNX export: {out}")

    if fmt in ("torchscript", "all"):
        print("\nExporting to TorchScript (for PyTorch Mobile / RaspberryPi)...")
        try:
            out = model.export(format="torchscript", imgsz=416)
            p = Path(str(out))
            if p.is_file():
                print(f"  TorchScript: {p} ({p.stat().st_size / 1e6:.1f} MB)")
                exported.append(p)
            else:
                print(f"  TorchScript export: {out}")
        except Exception as exc:
            print(f"  TorchScript export failed: {exc}")

    if exported:
        print(f"\nExported {len(exported)} format(s).")
        for p in exported:
            print(f"  {p}")
    else:
        print("\nNo files confirmed exported.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export YOLOv8 model to edge formats")
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS,
                        help=f"Path to .pt weights file (default: {DEFAULT_WEIGHTS})")
    parser.add_argument("--format", choices=["onnx", "torchscript", "all"], default="all",
                        help="Export format (default: all)")
    args = parser.parse_args()
    export_model(args.weights, args.format)


if __name__ == "__main__":
    main()
