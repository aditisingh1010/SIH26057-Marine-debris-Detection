# Machine Learning Experiment Registry

> **Project:** SIH26057 — Marine Debris & Anomaly Detection
> **Registry File:** `docs/ML_EXPERIMENTS.md`
> **Last Updated:** 2026-08-28

---

## Experiment 1: Ghost Pot Baseline (YOLOv8n Pretrained — 10-Epoch Controlled Checkpoint)

- **Date:** 2026-08-28
- **Objective:** Establish a controlled initial detection baseline on the 6,674-image Ghost Pot side-scan sonar dataset (`PINGEcosystem/sss-crab-pot-detection-ds`) using pretrained COCO weights (`yolov8n.pt`).
- **Hardware / Device:** NVIDIA GeForce RTX 2050 GPU (4 GB VRAM) with PyTorch 2.5.1 + CUDA 12.1 (AMP enabled).
- **Duration:** 1,829.16 seconds (~30.49 minutes for 10 epochs).

### Dataset & Preprocessing
- **Source Config:** `ml/data/processed/ghost_pot/data.yaml`
- **Total Images:** 6,674 images ($640 \times 640$ px, JPEG/RGB)
  - `train`: 5,721 images (4,291 labeled, 1,430 background)
  - `val`: 555 images (502 labeled, 53 background)
  - `test`: 398 images (334 labeled, 64 background)
- **Annotations:** 9,311 total bounding boxes (100% mapped to class `0` = `crab_pot`).

### Training Configuration
```yaml
model: yolov8n.pt (COCO-pretrained)
data: ml/data/processed/ghost_pot/data.yaml
epochs: 10
imgsz: 640
batch: 16
workers: 4
seed: 42
deterministic: true
device: "0" (NVIDIA GeForce RTX 2050)
checkpoint_dir: ml/data/exp_runs/ghost_pot_yolov8n_baseline/weights/
```

### Measured Quantitative Results (Epoch 10 Validation)

| Metric | Epoch 1 | Epoch 5 | Epoch 10 | Target Metric |
| :--- | :--- | :--- | :--- | :--- |
| **Precision** | 0.3310 | 0.3229 | **0.4875** (48.75%) | High precision baseline |
| **Recall** | 0.3192 | 0.2722 | **0.4180** (41.80%) | Good detection coverage |
| **mAP@50** | 0.2317 | 0.2042 | **0.3792** (37.92%) | Primary detection score |
| **mAP@50-95** | 0.0680 | 0.0614 | **0.1239** (12.39%) | Strict IoU score |
| **Train Box Loss** | 2.3153 | 2.1051 | **1.9849** | Steady convergence |
| **Train Cls Loss** | 3.6770 | 2.2122 | **2.0511** | Class loss reduction |
| **Train DFL Loss** | 1.6597 | 1.5596 | **1.4738** | Focal loss convergence |
| **Val Box Loss** | 2.6818 | 2.5945 | **2.4135** | Validation localization |
| **Val Cls Loss** | 2.4269 | 2.4291 | **1.8424** | Validation classification |
| **Val DFL Loss** | 1.2851 | 1.2134 | **1.1555** | Validation focal loss |

### Observations & Domain Insights
1. **Rapid Convergence:** The model achieved **mAP@50 = 37.92%** and **Precision = 48.75%** by Epoch 10, demonstrating strong feature transfer from YOLOv8n pretrained weights to side-scan sonar imagery.
2. **Loss Progression:** Validation classification loss decreased significantly from $2.4269$ at Epoch 1 to $1.8424$ at Epoch 10, indicating steady learning of acoustic shadow and pot framing geometry.
3. **Model Artifacts:** Checkpoint saved safely to `ml/data/exp_runs/ghost_pot_yolov8n_baseline/weights/best.pt` (24.48 MB). Root `best.pt` remained untouched.

### Scope Boundaries & Ethical Guidelines
- **No Unfounded Risk Claims:** High confidence bounding boxes indicate acoustic pattern matching for crab pot targets, NOT guaranteed structural risk level.
- **No Simulated Geolocation:** Geolocation metadata is strictly read from raw sonar header fields; no artificial coordinates are generated.
- **Class Scope:** This model is trained exclusively on `crab_pot` targets and cannot be claimed as a general marine debris detector without target class validation on additional debris types (`debris_0`, `debris_1`).
