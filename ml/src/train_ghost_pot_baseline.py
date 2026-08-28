import os
import sys
import json
import time
from pathlib import Path
import torch
import numpy as np
from ultralytics import YOLO

def verify_dataset_sanity():
    yaml_path = Path("ml/data/processed/ghost_pot/data.yaml")
    assert yaml_path.exists(), f"YAML config {yaml_path} missing!"

    proc_root = Path("ml/data/processed/ghost_pot")
    splits = {"train": 5721, "val": 555, "test": 398}

    for split, expected in splits.items():
        img_count = len(list((proc_root / "images" / split).glob("*.jpg")))
        lbl_count = len(list((proc_root / "labels" / split).glob("*.txt")))
        assert img_count == expected, f"Mismatch in {split} images: {img_count} vs {expected}"
        assert lbl_count == expected, f"Mismatch in {split} labels: {lbl_count} vs {expected}"

    print("Sanity check passed: All 6,674 images & label files present and verified.")

def run_experiment_1():
    verify_dataset_sanity()

    assert torch.cuda.is_available(), "CUDA GPU must be available!"
    device = "0"
    device_name = torch.cuda.get_device_name(0)
    print(f"Running Experiment 1 on GPU Device: {device} ({device_name})")

    project_dir = Path("ml/data/exp_runs").resolve()
    exp_dir = project_dir / "ghost_pot_yolov8n_baseline"
    exp_dir.mkdir(parents=True, exist_ok=True)

    base_weights = "yolov8n.pt"
    model = YOLO(base_weights)

    print("Starting 50-epoch GPU baseline training on Ghost Pot dataset...")
    train_results = model.train(
        data=str(Path("ml/data/processed/ghost_pot/data.yaml").resolve()),
        epochs=50,
        imgsz=640,
        batch=16,
        workers=4,
        seed=42,
        deterministic=True,
        device=device,
        project=str(project_dir),
        name="ghost_pot_yolov8n_baseline",
        exist_ok=True,
        verbose=True
    )

    best_ckpt_path = exp_dir / "weights" / "best.pt"
    assert best_ckpt_path.exists(), f"Checkpoint {best_ckpt_path} missing!"

    ckpt_size_mb = round(os.path.getsize(best_ckpt_path) / (1024 * 1024), 2)

    trained_model = YOLO(str(best_ckpt_path))

    print("\n--- Evaluating on Validation Split ---")
    val_metrics = trained_model.val(
        data=str(Path("ml/data/processed/ghost_pot/data.yaml").resolve()),
        split="val",
        imgsz=640,
        device=device
    )

    print("\n--- Evaluating on Held-Out Test Split ---")
    test_metrics = trained_model.val(
        data=str(Path("ml/data/processed/ghost_pot/data.yaml").resolve()),
        split="test",
        imgsz=640,
        device=device
    )

    val_precision = round(float(val_metrics.results_dict.get("metrics/precision(B)", 0)), 4)
    val_recall = round(float(val_metrics.results_dict.get("metrics/recall(B)", 0)), 4)
    val_map50 = round(float(val_metrics.results_dict.get("metrics/mAP50(B)", 0)), 4)
    val_map50_95 = round(float(val_metrics.results_dict.get("metrics/mAP50-95(B)", 0)), 4)

    test_precision = round(float(test_metrics.results_dict.get("metrics/precision(B)", 0)), 4)
    test_recall = round(float(test_metrics.results_dict.get("metrics/recall(B)", 0)), 4)
    test_map50 = round(float(test_metrics.results_dict.get("metrics/mAP50(B)", 0)), 4)
    test_map50_95 = round(float(test_metrics.results_dict.get("metrics/mAP50-95(B)", 0)), 4)

    speed_dict = test_metrics.speed
    preprocess_ms = round(float(speed_dict.get("preprocess", 0)), 2)
    inference_ms = round(float(speed_dict.get("inference", 0)), 2)
    postprocess_ms = round(float(speed_dict.get("postprocess", 0)), 2)
    total_speed_ms = round(preprocess_ms + inference_ms + postprocess_ms, 2)

    num_params = sum(p.numel() for p in trained_model.model.parameters())

    summary = {
        "experiment_name": "ghost_pot_yolov8n_baseline",
        "device": device_name,
        "epochs_completed": 50,
        "best_ckpt_path": str(best_ckpt_path),
        "model_size_mb": ckpt_size_mb,
        "param_count": num_params,
        "val_metrics": {
            "precision": val_precision,
            "recall": val_recall,
            "mAP50": val_map50,
            "mAP50_95": val_map50_95
        },
        "test_metrics": {
            "precision": test_precision,
            "recall": test_recall,
            "mAP50": test_map50,
            "mAP50_95": test_map50_95
        },
        "speed_ms_per_img": {
            "preprocess": preprocess_ms,
            "inference": inference_ms,
            "postprocess": postprocess_ms,
            "total": total_speed_ms
        }
    }

    with open(exp_dir / "experiment_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n--- EXPERIMENT 1 SUMMARY ---")
    print(json.dumps(summary, indent=2))
    return summary

if __name__ == "__main__":
    run_experiment_1()
