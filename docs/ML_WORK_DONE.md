# ML Work Completed

> **Author:** Medha (ML Lead)
> **Project:** SIH26057 — Marine Debris & Anomaly Detection
> **Last Updated:** 2026-08-26

---

## 1. Dataset Audit

- Audited the Side-Scan Sonar datasets from the 2010 and 2018 surveys.
- Total dataset: **909 images**
  - 2010: **345 images**
  - 2018: **564 images**
- Identified **140 labeled images** (with YOLO-format `.txt` annotation files containing bounding-box coordinates).
- Identified **769 background/unlabeled images** (empty or no corresponding label file).
- Two object classes defined: `debris_0` (class 0) and `debris_1` (class 1).
- Verified YOLO annotation formatting: `class_id x_center y_center width height` (normalized coordinates).
- Original `Dataset/` directory remains untouched throughout all work.

**Script:** `ml/src/data_audit.py`

---

## 2. Dataset Preparation

Prepared the dataset for YOLOv8 object detection training:

- Stratified train/validation/test splitting (default ratio: 67% / 17% / 16%).
- Stratification ensures both labeled and background images are distributed across splits.
- YOLO-compatible directory structure generated:
  ```
  images/
      train/  val/  test/
  labels/
      train/  val/  test/
  ```
- Corresponding YOLO label `.txt` files are copied alongside their images.
- Dataset YAML configuration file generated for Ultralytics training.

**Script:** `ml/src/build_splits.py`

---

## 3. Sonar Preprocessing

Implemented conservative preprocessing specifically designed for Side-Scan Sonar imagery. The goal was to reduce sensor noise without destroying fine acoustic features critical for detection.

### 3a. Conservative Bilateral Filtering

Applied an edge-preserving bilateral filter with intentionally mild parameters:

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Diameter | `5` | Small kernel to avoid over-smoothing |
| Sigma color | `25.0` | Intensity difference threshold for edge preservation |
| Sigma space | `25.0` | Spatial distance threshold |

This reduces high-frequency sonar speckle noise while preserving object boundaries, acoustic shadow edges, and seabed texture.

### 3b. Lateral Artifact Attenuation

Implemented smooth attenuation of persistent vertical acquisition line artifacts that appear along the extreme left and right margins of side-scan sonar images.

- Uses a smooth **cubic fade ramp** applied to the outer margins.
- Margin fraction: `0.035` (3.5% of image width on each side).
- Attenuates the systematic outer-swath line artifacts without affecting the central imaging area.

The preprocessing is intentionally conservative — it prioritizes preserving useful sonar features over aggressive noise removal.

**Script:** `ml/src/preprocess_sonar.py`

---

## 4. Preprocessing Verification

Tested the preprocessing pipeline on sample images to confirm:

- Images are processed successfully without errors.
- Image dimensions are preserved (no resizing or cropping).
- YOLO annotation files are preserved alongside their images during split building.
- Fine edges and acoustic shadow boundaries remain intact after filtering.
- Original `Dataset/` files are never modified (read-only access).

The preprocessing module is standalone and reusable — it can be imported by other scripts or called from the command line.

---

## 5. Raw vs Filtered A/B Experiment

A controlled 5-epoch experiment was conducted to compare detection performance on:

- **Raw** (unprocessed) sonar images
- **Filtered** (bilateral-filtered) sonar images

Both models used identical training conditions:

| Parameter | Value |
|-----------|-------|
| Architecture | YOLOv8n |
| Epochs | 5 |
| Image size | 416 × 416 |
| Batch size | 16 |
| Seed | 42 |
| Device | CPU |

### A/B Results (5-epoch experiment)

| Metric | Raw Baseline | Filtered |
|--------|-------------|----------|
| mAP@50 | 0.0 | 0.0 |
| mAP@50-95 | 0.0 | 0.0 |
| Precision | 0.0 | 0.0 |
| Recall | 0.0 | 0.0 |
| True Positives | 0 | 0 |
| False Positives | 0 | 0 |
| False Negatives | 22 | 22 |
| Training time | ~149 s | ~158 s |
| Inference time | ~58 ms/img | ~77 ms/img |

At 5 epochs, both models produced zero detections on the test split. The experiment was too short for either model to converge, which motivated the longer 50-epoch final training run.

**Results file:** `ml/data/exp_data/ab_experiment_results.json`
**Raw baseline config:** `ml/data/exp_runs/raw_baseline/args.yaml`
**Filtered model config:** `ml/data/exp_runs/filtered_model/args.yaml`

> **Note:** This was a short controlled experiment to compare raw vs filtered data. It is separate from the final 50-epoch model training.

---

## 6. YOLOv8 Training

### Training Script

Implemented a YOLOv8 training wrapper with configurable hyperparameters: dataset path, epochs, image size, batch size, device, seed, and experiment naming.

**Script:** `ml/src/train_detector.py`

### Final Model Training

The final YOLOv8n model was trained with the following configuration:

| Parameter | Value |
|-----------|-------|
| Architecture | YOLOv8n (nano) |
| Base weights | `yolov8n.pt` (COCO-pretrained) |
| Dataset | Filtered (preprocessed) sonar images |
| Epochs | **50** |
| Image size | 416 × 416 |
| Batch size | 16 |
| Seed | 42 |
| Optimizer | Auto (AdamW) |
| Augmentation | Mosaic, flip, random augment, erasing |

The trained checkpoint (`best.pt`, 5.9 MB) is saved in the project root and included in the Git repository.

**Trained model:** `best.pt` (project root)
**Training config:** Saved in the local YOLO training run directory (`runs/detect/train/args.yaml`)

---

## 7. Model Evaluation

Implemented a model evaluation script that reports:

- Precision, Recall
- mAP@50, mAP@50-95
- Per-class metrics
- True Positives, False Positives, False Negatives
- Inference speed (ms/image)
- Optional JSON export of results

The evaluation script was used to assess both the A/B experiment models and the final 50-epoch model.

**Script:** `ml/src/evaluate_detector.py`

---

## 8. Combined Pipeline: Preprocessing → Detection → Visualization

Created a single end-to-end pipeline that chains all ML steps:

```
Raw Sonar Image
      ↓
Conservative Preprocessing (bilateral filter + lateral attenuation)
      ↓
YOLOv8 Inference (best.pt, conf=0.25, imgsz=416)
      ↓
Green Bounding Box Drawing + Class/Confidence Label
      ↓
Saved Annotated Image
```

### Visual output details

- **Box:** Thin green rectangle (1 px for ≤600 px images, 2 px for larger).
- **Padding:** 5% breathing margin around detected objects.
- **Label:** Compact badge showing `class_name confidence_score`.
- **Edge safety:** Labels are automatically repositioned to avoid clipping off image borders.
- **Quality:** Output saved as JPEG at 95% quality.

The pipeline preserves the original subfolder structure (`2010/`, `2018/`) in the output directory.

**Script:** `ml/src/predict_visualize.py`

---

## 9. Full 909-Image Processing

The combined pipeline was executed on the complete dataset:

| Metric | Result |
|--------|--------|
| Total images processed | **909 / 909** |
| 2010 images | 345 |
| 2018 images | 564 |
| Processing failures | **0** |
| Processing time | ~199 seconds (~0.22 s/image) |

All output images (cleaned + annotated with green bounding boxes) are saved to:

```
ml/data/cleaned_predictions/all_909/
├── 2010/   (345 images)
└── 2018/   (564 images)
```

This folder is generated at runtime and is listed in `.gitignore` (not tracked in Git). Any team member can regenerate it by running the pipeline.

---

## 10. Repository Cleanup & Git Configuration

### Cleanup performed

Removed duplicate/temporary output folders that were created during development and testing:

- `ml/data/cleaned_predictions/2010/` (duplicate of subset)
- `ml/data/cleaned_predictions/2018/` (duplicate of subset)
- `ml/data/cleaned_predictions/reproducibility_test/` (3-image test run)

Only the final consolidated output (`ml/data/cleaned_predictions/all_909/`) was retained.

### .gitignore configuration

Updated `.gitignore` to exclude generated and large files from version control:

| Rule | What it excludes |
|------|-----------------|
| `.venv/`, `__pycache__/`, `*.pyc` | Python environment & bytecode |
| `.env` | Environment secrets |
| `ml/data/raw/`, `ml/data/processed/` | Intermediate data |
| `.ipynb_checkpoints/` | Jupyter artifacts |
| `ml/data/exp_data/`, `ml/data/exp_runs/` | Experiment artifacts |
| `ml/data/cleaned_predictions/` | Generated pipeline output (909 images) |
| `ml/data/splits/` | Generated train/val/test splits |
| `runs/` | YOLO training run logs |
| `*.log`, `Thumbs.db`, `.DS_Store` | Logs & OS cache files |

The trained `best.pt` model (5.9 MB) is **included** in the repository so team members receive it on pull.

---

## 11. Current Status

### ✅ Completed

| Component | Status |
|-----------|--------|
| Dataset audit & validation | Done |
| Dataset splitting (train/val/test) | Done |
| Conservative sonar preprocessing | Done |
| Lateral artifact attenuation | Done |
| Raw vs Filtered A/B experiment (5 epochs) | Done |
| YOLOv8n final training (50 epochs) | Done |
| Model evaluation script | Done |
| Combined pipeline (clean → detect → visualize) | Done |
| Full 909-image batch processing | Done |
| Repository cleanup & .gitignore | Done |
| Trained model (`best.pt`) pushed to repo | Done |

### ⬚ Not Yet Implemented

| Component | Status |
|-----------|--------|
| FastAPI backend integration | Not started |
| React frontend & analytics dashboard | Not started |
| Geolocation mapping | Not started |
| Risk / priority scoring | Not started |
| End-to-end deployment | Not started |
| Confidence-based false positive filtering | Not started |

---

## 12. File Reference

All ML source code is located in `ml/src/`:

| File | Purpose |
|------|---------|
| `data_audit.py` | Scans `Dataset/`, counts labeled vs background images, validates YOLO labels |
| `build_splits.py` | Generates stratified train/val/test splits in YOLO-compatible format |
| `preprocess_sonar.py` | Conservative bilateral filtering + lateral artifact attenuation |
| `train_detector.py` | YOLOv8 training wrapper with configurable hyperparameters |
| `evaluate_detector.py` | Model evaluation: precision, recall, mAP, per-class metrics |
| `predict_visualize.py` | Combined pipeline: preprocess → detect → draw green boxes → save |

### Key data files

| File | Purpose |
|------|---------|
| `best.pt` | Trained YOLOv8n model checkpoint (50 epochs, 5.9 MB) |
| `ml/data/exp_data/filtered_data.yaml` | YOLO dataset config for filtered data |
| `ml/data/exp_data/raw_data.yaml` | YOLO dataset config for raw data |
| `ml/data/exp_data/ab_experiment_results.json` | A/B experiment metrics (5-epoch run) |
| `ml/data/exp_runs/filtered_model/args.yaml` | Training args for filtered A/B model |
| `ml/data/exp_runs/raw_baseline/args.yaml` | Training args for raw A/B model |

---

## 13. How to Reproduce

After cloning the repository, place the `Dataset/` folder in the project root, then:

```bash
# Install dependencies
pip install ultralytics opencv-python numpy matplotlib pyyaml

# Run the full pipeline (generates 909 cleaned + annotated images)
python ml/src/predict_visualize.py --weights best.pt --input Dataset --output ml/data/cleaned_predictions/all_909 --conf 0.25 --imgsz 416
```

Output will appear in `ml/data/cleaned_predictions/all_909/` with `2010/` and `2018/` subfolders.

