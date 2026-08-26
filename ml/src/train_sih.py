"""
SIH retrain script — trains from existing best.pt with sonar-optimised settings.
Run from repo root: python ml/src/train_sih.py
"""
from pathlib import Path
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[2]
WEIGHTS = ROOT / "best.pt"
DATA    = ROOT / "ml/data/splits/dataset.yaml"
OUT_DIR = ROOT / "ml/data/exp_runs"

if not DATA.exists():
    raise FileNotFoundError(f"Dataset YAML not found: {DATA}\nRun build_splits.py first.")

model = YOLO(str(WEIGHTS))

results = model.train(
    data=str(DATA),
    epochs=150,
    imgsz=416,
    batch=8,
    device="cpu",
    seed=42,
    deterministic=True,
    # Sonar-specific augmentation — must NOT mosaic or rotate
    mosaic=0.0,      # sonar waterfalls must not be stitched together
    flipud=0.5,      # vertical flip is valid (waterfall can be inverted)
    fliplr=0.0,      # horizontal flip is invalid — mirrors port/starboard swath
    degrees=0.0,     # no rotation — sonar has fixed orientation
    translate=0.05,
    scale=0.2,
    hsv_h=0.0,       # sonar is grayscale — no hue shift
    hsv_s=0.0,
    hsv_v=0.3,       # brightness variation only
    # Detection settings
    conf=0.15,
    iou=0.5,
    patience=40,
    # Output
    project=str(OUT_DIR),
    name="sih_retrain",
    exist_ok=True,
    plots=True,
    verbose=True,
)

save_dir = Path(results.save_dir)
best_new = save_dir / "weights" / "best.pt"

print("\n=== Training complete ===")
print(f"  Best weights: {best_new}")
print(f"  mAP@50:    {results.results_dict.get('metrics/mAP50(B)', 'N/A')}")
print(f"  mAP@50-95: {results.results_dict.get('metrics/mAP50-95(B)', 'N/A')}")

# Replace root best.pt
import shutil
shutil.copy2(best_new, ROOT / "best.pt")
print(f"\n  Replaced {ROOT / 'best.pt'} with new weights.")
