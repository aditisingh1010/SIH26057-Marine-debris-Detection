# Ghost Pot Dataset Inspection & Domain-Shift Analysis

> **Dataset:** `PINGEcosystem/sss-crab-pot-detection-ds`
> **Location:** `ml/data/raw/ghost_pot/`
> **Date of Audit:** 2026-08-28
> **Status:** Complete & Validated (Read-Only Audit — No Training Performed)

---

## 1. Dataset Completeness & Disk Footprint

- **Status:** Complete local download present.
- **Directory Path:** `ml/data/raw/ghost_pot/`
- **Total Files in Directory:** **13,363 files** (includes dataset images, metadata JSONL files, `.cache` artifacts, `.gitattributes`, and `.gitignore`).
- **Disk Usage:** **536.09 MB** (~0.524 GB).
- **Git Status:** Strictly untracked and excluded via `.gitignore`.

---

## 2. File & Split Breakdown

The Ghost Pot dataset is structured into standard `train`, `valid`, and `test` splits:

| Split | Image Count | JSONL Files | Annotation Records | Image Files Corrupt | Missing Images |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **train** | 5,721 | 1 (`metadata.jsonl`) | 5,721 | 0 | 0 |
| **valid** | 555 | 1 (`metadata.jsonl`) | 555 | 0 | 0 |
| **test** | 398 | 1 (`metadata.jsonl`) | 398 | 0 | 0 |
| **Total** | **6,674** | **3** | **6,674** | **0** | **0** |

- **Verification:** 100% of the 6,674 image files on disk match their corresponding JSONL records. Zero orphaned files and zero missing records.

---

## 3. Image Properties & Decoding Verification

- **Decoding Status:** All 6,674 images were decoded successfully using Pillow & OpenCV.
- **Corrupt Files:** **0** (0 byte files: 0, broken headers: 0).
- **Dimensions:**
  - **train:** 640 × 640 px (100%)
  - **valid:** 640 × 640 px (100%)
  - **test:** 640 × 640 px (100%)
  - **Unique Shapes across dataset:** `[640, 640]`
- **Formats & Color Mode:** `JPEG / RGB` (3 channels) across 100% of images.

---

## 4. Annotations & Bounding-Box Validation

- **Annotation Format:** JSONL format with `file_name` and `objects` (`bbox`, `category`, `area`).
- **Bounding Box Coordinate Format:** `[x_min, y_min, width, height]` in absolute pixel coordinates.
- **Total Bounding Boxes:** **9,311 boxes**
  - **train:** 7,469 boxes
  - **valid:** 1,275 boxes
  - **test:** 567 boxes

### Category Distribution
- **Detected Classes in JSONL:** **`Crab-Pot`** (9,311 boxes)
- **Note on Metadata:** The Hugging Face dataset card lists `Maybe-Crab-Pot` as a potential metadata tag, but empirical parsing of all 6,674 JSONL records confirms that **100% of labeled objects belong to `Crab-Pot`**.

### Image Box Density & Background Distribution
- **Labeled Images (contains ≥1 box):** **5,127 images** (76.8%)
- **Background / Zero-Box Images:** **1,547 images** (23.2%)
  - `train` background images: 1,430
  - `valid` background images: 53
  - `test` background images: 64
- **Average Box Density on Labeled Images:** 1.82 boxes per image.

### Bounding-Box Coordinate Integrity
- **Non-Positive Size Boxes ($w \le 0$ or $h \le 0$):** **0**
- **Out-of-Bounds Boxes:** **85 boxes** (0.91% of total boxes)
  - *Cause:* Minor sub-pixel or edge boundary overlap from image tile cropping (e.g., `x = 637, w = 3.1` extending to 640.1 px). These can be safely clipped during YOLO conversion.

---

## 5. Measured Photometric & Contrast Statistics

Grayscale intensity statistics were computed across all images in each dataset:

| Dataset / Split | Mean Intensity (0–255) | Mean Contrast (Std Dev) | Baseline Brightness |
| :--- | :--- | :--- | :--- |
| **Ghost Pot (train)** | 87.53 | 35.06 | Moderate / Brighter seabed |
| **Ghost Pot (valid)** | 67.21 | 42.64 | Darker / Higher contrast |
| **Ghost Pot (test)** | 96.33 | 31.95 | Bright seabed floor |
| **Ghost Pot (Overall)** | **86.40** | **35.70** | **Medium-High gain** |
| **Existing Dataset (909 SSS)** | **46.58** | **36.02** | **Dark gain baseline** |

---

## 6. Comparison: Ghost Pot vs. Existing SSS Dataset

| Metric / Characteristic | Ghost Pot Dataset (`PINGEcosystem`) | Existing SSS Dataset (`Dataset/`) |
| :--- | :--- | :--- |
| **Total Images** | **6,674 images** | **909 images** |
| **Labeled Images** | 5,127 images (76.8%) | 140 images (15.4%) |
| **Background Images** | 1,547 images (23.2%) | 769 images (84.6%) |
| **Total Bounding Boxes** | **9,311 boxes** | **176 boxes** |
| **Image Resolution** | Uniform `640 × 640` px | Mixed `416 × 416` and `1024 × 1024` px |
| **Mean Intensity** | **86.40** (Brighter gain/texture) | **46.58** (Dark acoustic backdrop) |
| **Mean Contrast (Std Dev)** | 35.70 | 36.02 |
| **Target Classes** | `Crab-Pot` (trap cages/nets) | `debris_0`, `debris_1` (general debris) |
| **Annotation Format** | JSONL COCO `[x_min, y_min, w, h]` px | YOLO txt `[class, cx, cy, w, h]` normalized |
| **Acoustic Shadows** | Sharp, highly focused pot shadows | Variable, broad object shadows |
| **Swath Geometry** | Cropped tile swaths (port/starboard) | Full waterfall swaths with nadir gaps |

---

## 7. Domain-Shift Assessment

1. **Resolution & Aspect Ratio Shift:** Ghost Pot images are uniformly square cropped ($640 \times 640$), matching standard YOLO inputs nicely. Our existing dataset includes full sonar runs up to $1024 \times 1024$.
2. **Photometric / Gain Shift:** Ghost Pot has a significantly higher mean background pixel intensity ($86.40$ vs. $46.58$). Models trained purely on Ghost Pot may experience gain threshold mismatch when deployed directly on darker SSS acoustic backdrops without intensity normalization or adaptive gain adjustments.
3. **Class & Geometric Semantics:** Ghost Pot targets specific structured traps/cages (`Crab-Pot`) featuring regular acoustic geometry and crisp shadows. Existing labels (`debris_0`, `debris_1`) capture heterogeneous, irregular marine debris.
4. **Data Scale Advantage:** Ghost Pot increases our available sonar training data from **176 boxes to 9,487 total boxes** across both datasets (~53x increase in labeled objects!).

---

## 8. Recommended Strategy

### **Recommended Option: C (Combine Datasets with Two-Stage Pretraining / Fine-Tuning Pipeline)**

**Justification based on empirical evidence:**
1. **Transfer Learning for Feature Extraction:** Our existing dataset has only 140 labeled images (176 boxes), which limits deep feature learning. Ghost Pot provides 6,674 sonar images and 9,311 labeled objects.
2. **Two-Stage Training Plan:**
   - **Stage 1 (Pre-training / Transfer Base):** Convert Ghost Pot JSONL annotations to YOLO format (`ml/data/processed/ghost_pot/`) and train/pretrain YOLOv8 on Ghost Pot to master sonar edge detection, acoustic shadow recognition, and seabed texture filtering.
   - **Stage 2 (Fine-tuning / Multi-Class Co-Training):** Fine-tune on a combined multi-class taxonomy (`crab_pot`, `debris_0`, `debris_1`) or fine-tune directly on target SSS data with data augmentation (random gain, brightness/contrast jittering to bridge the $86.4 \to 46.58$ intensity shift).

---

## 9. Verification & Safety Summary

- **Existing `best.pt` model:** UNTOUCHED (MD5 hash / timestamp preserved).
- **Training executed:** NONE.
- **Files deleted:** NONE.
- **Git status:** Raw dataset `ml/data/raw/ghost_pot/` is strictly ignored by `.gitignore`.
