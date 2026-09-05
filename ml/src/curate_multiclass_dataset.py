"""
Curate Unified Multi-Class Side-Scan Sonar Dataset for YOLOv8 Training.
Extracts and balances:
  Class 0: ghost_pot (from existing Dataset/ - 140 positives)
  Class 1: shipwreck (from AI4Shipwrecks - 141 images with mask to bbox)
  Class 2: pipeline (from SubPipe - 200 high-quality annotated SSS tiles)
  Class 3: seafloor_debris (from side-scan-sonar-object-detection - 200 annotated SSS tiles)
  Background: 100 empty negative seafloor tiles for negative suppression

Outputs a clean, balanced dataset directory at ml/data/multiclass_dataset and a zip for Colab.
Zero heavy training runs locally; solely prepares the dataset package.
"""

import os
import shutil
import random
import zipfile
from pathlib import Path
import cv2
import numpy as np

random.seed(42)

ROOT = Path(__file__).resolve().parents[2]
DOWNLOADS = ROOT / "downloads"
ORIG_DATASET = ROOT / "Dataset"
OUT_DIR = ROOT / "ml" / "data" / "multiclass_dataset"
ZIP_OUT = ROOT / "ml" / "data" / "multiclass_sonar_dataset.zip"

CLASSES = {
    0: "ghost_pot",
    1: "shipwreck",
    2: "pipeline",
    3: "seafloor_debris",
}


def mask_to_yolo_bboxes(mask_path: Path):
    """Reads a binary PNG mask and extracts normalized YOLO bounding boxes."""
    mask = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED)
    if mask is None:
        return []

    h, w = mask.shape[:2]
    # Threshold mask (> 0 is foreground object)
    thresh = (mask > 0).astype(np.uint8) * 255
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bboxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 50:  # Ignore tiny speckle contours
            continue
        bx, by, bw, bh = cv2.boundingRect(cnt)

        # Convert to YOLO (cx, cy, w, h normalized)
        cx = (bx + bw / 2.0) / w
        cy = (by + bh / 2.0) / h
        norm_w = bw / float(w)
        norm_h = bh / float(h)

        # Clamp to [0, 1]
        cx = max(0.0, min(1.0, cx))
        cy = max(0.0, min(1.0, cy))
        norm_w = max(0.001, min(1.0, norm_w))
        norm_h = max(0.001, min(1.0, norm_h))

        bboxes.append((cx, cy, norm_w, norm_h))

    return bboxes


def build_unified_dataset():
    print("[*] Starting Multi-Class SSS Dataset Curation...")

    # 1. Clean output directories
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)

    for split in ["train", "val", "test"]:
        (OUT_DIR / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "labels" / split).mkdir(parents=True, exist_ok=True)

    all_samples = []  # List of dicts: {'image_path': Path, 'bboxes': [(class_id, cx, cy, w, h)], 'origin': str}

    # -------------------------------------------------------------
    # 1. GHOST POTS (Class 0) from Dataset/
    # -------------------------------------------------------------
    orig_imgs = list(ORIG_DATASET.rglob("*.jpg")) + list(ORIG_DATASET.rglob("*.png"))
    pos_pots = 0
    neg_bg = 0

    for img_p in orig_imgs:
        txt_p = img_p.with_suffix(".txt")
        if txt_p.exists():
            bboxes = []
            with open(txt_p, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        # Remap to Class 0
                        bboxes.append((0, float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])))
            if bboxes:
                all_samples.append({'image_path': img_p, 'bboxes': bboxes, 'origin': 'ghost_pot'})
                pos_pots += 1
            else:
                if neg_bg < 100:  # Keep up to 100 clean background tiles
                    all_samples.append({'image_path': img_p, 'bboxes': [], 'origin': 'background'})
                    neg_bg += 1

    print(f"  [+] Ghost Pots (Class 0): {pos_pots} labeled images, {neg_bg} background images")

    # -------------------------------------------------------------
    # 2. SHIPWRECKS (Class 1) from AI4Shipwrecks
    # -------------------------------------------------------------
    ai4_dir = DOWNLOADS / "AI4Shipwrecks"
    ai4_train_imgs = ai4_dir / "train" / "images"
    ai4_train_lbls = ai4_dir / "train" / "labels"
    shipwrecks_count = 0

    if ai4_train_imgs.exists() and ai4_train_lbls.exists():
        for mask_p in ai4_train_lbls.glob("*.png"):
            # Image counterpart could be .png, .jpg, etc.
            stem = mask_p.stem
            img_p = ai4_train_imgs / f"{stem}.png"
            if not img_p.exists():
                img_p = ai4_train_imgs / f"{stem}.jpg"
            if not img_p.exists():
                continue

            raw_boxes = mask_to_yolo_bboxes(mask_p)
            if raw_boxes:
                bboxes = [(1, cx, cy, w, h) for (cx, cy, w, h) in raw_boxes]
                all_samples.append({'image_path': img_p, 'bboxes': bboxes, 'origin': 'shipwreck'})
                shipwrecks_count += 1

    print(f"  [+] Shipwrecks (Class 1): {shipwrecks_count} images converted from segmentation masks")

    # -------------------------------------------------------------
    # 3. PIPELINES (Class 2) from SubPipeMiniSSS
    # -------------------------------------------------------------
    subpipe_dir = DOWNLOADS / "SubPipeMiniSSS" / "DATA" / "SSS_HF_images"
    subpipe_imgs_dir = subpipe_dir / "Image"
    subpipe_lbls_dir = subpipe_dir / "YOLO_Annotation"
    pipeline_count = 0

    if subpipe_lbls_dir.exists():
        lbl_files = list(subpipe_lbls_dir.glob("*.txt"))
        random.shuffle(lbl_files)

        for lbl_p in lbl_files:
            if lbl_p.name == "classes.txt":
                continue
            # Look for image
            img_p = subpipe_imgs_dir / f"{lbl_p.stem}.pbm"
            if not img_p.exists():
                img_p = subpipe_imgs_dir / f"{lbl_p.stem}.jpg"
            if not img_p.exists():
                img_p = subpipe_imgs_dir / f"{lbl_p.stem}.png"
            if not img_p.exists():
                continue

            bboxes = []
            with open(lbl_p, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        bboxes.append((2, float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])))
            if bboxes:
                all_samples.append({'image_path': img_p, 'bboxes': bboxes, 'origin': 'pipeline'})
                pipeline_count += 1
                if pipeline_count >= 200:  # Cap at 200 to prevent class domination
                    break

    print(f"  [+] Pipelines (Class 2): {pipeline_count} images curated from SubPipe")

    # -------------------------------------------------------------
    # 4. SEAFLOOR DEBRIS / CYLINDERS (Class 3) from Kaggle
    # -------------------------------------------------------------
    kaggle_dir = DOWNLOADS / "side-scan-sonar-object-detection" / "train"
    kaggle_imgs_dir = kaggle_dir / "images"
    kaggle_lbls_dir = kaggle_dir / "labels"
    debris_count = 0

    if kaggle_lbls_dir.exists():
        lbl_files = list(kaggle_lbls_dir.glob("*.txt"))
        random.shuffle(lbl_files)

        for lbl_p in lbl_files:
            img_p = kaggle_imgs_dir / f"{lbl_p.stem}.jpg"
            if not img_p.exists():
                img_p = kaggle_imgs_dir / f"{lbl_p.stem}.png"
            if not img_p.exists():
                continue

            bboxes = []
            with open(lbl_p, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        bboxes.append((3, float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])))
            if bboxes:
                all_samples.append({'image_path': img_p, 'bboxes': bboxes, 'origin': 'seafloor_debris'})
                debris_count += 1
                if debris_count >= 200:  # Cap at 200 to balance with others
                    break

    print(f"  [+] Seafloor Debris / Objects (Class 3): {debris_count} images curated from Kaggle SSS")

    # -------------------------------------------------------------
    # 5. SPLIT & WRITE (70% Train, 15% Val, 15% Test)
    # -------------------------------------------------------------
    random.shuffle(all_samples)
    n_total = len(all_samples)
    n_train = int(n_total * 0.70)
    n_val = int(n_total * 0.15)

    train_samples = all_samples[:n_train]
    val_samples = all_samples[n_train:n_train + n_val]
    test_samples = all_samples[n_train + n_val:]

    splits = [("train", train_samples), ("val", val_samples), ("test", test_samples)]

    print(f"\n[+] Writing Unified Dataset ({n_total} total images):")
    print(f"   Train: {len(train_samples)} | Val: {len(val_samples)} | Test: {len(test_samples)}")

    idx = 0
    for split_name, samples in splits:
        for item in samples:
            idx += 1
            dst_img_name = f"sonar_{idx:04d}.jpg"
            dst_lbl_name = f"sonar_{idx:04d}.txt"

            dst_img_path = OUT_DIR / "images" / split_name / dst_img_name
            dst_lbl_path = OUT_DIR / "labels" / split_name / dst_lbl_name

            # Read & write image as standard JPG
            src_img = cv2.imread(str(item['image_path']))
            if src_img is None:
                continue
            cv2.imwrite(str(dst_img_path), src_img)

            # Write label file
            with open(dst_lbl_path, "w") as f:
                for (cid, cx, cy, w, h) in item['bboxes']:
                    f.write(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")

    # Write dataset.yaml
    yaml_content = f"""# Multi-Class Side-Scan Sonar Dataset
path: ./multiclass_dataset
train: images/train
val: images/val
test: images/test

names:
  0: ghost_pot
  1: shipwreck
  2: pipeline
  3: seafloor_debris
"""
    with open(OUT_DIR / "dataset.yaml", "w") as f:
        f.write(yaml_content)

    print(f"\n[+] Dataset YAML created at {OUT_DIR / 'dataset.yaml'}")

    # -------------------------------------------------------------
    # 6. PACKAGE TO ZIP FOR 1-CLICK COLAB UPLOAD
    # -------------------------------------------------------------
    print(f"[*] Compressing dataset to {ZIP_OUT.name} for fast Google Colab upload...")
    with zipfile.ZipFile(ZIP_OUT, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(OUT_DIR):
            for file in files:
                abs_path = Path(root) / file
                rel_path = abs_path.relative_to(OUT_DIR.parent)
                zipf.write(abs_path, arcname=str(rel_path))

    zip_size_mb = ZIP_OUT.stat().st_size / (1024 * 1024)
    print(f"[SUCCESS] Colab Package Ready: {ZIP_OUT} ({zip_size_mb:.2f} MB)")


if __name__ == "__main__":
    build_unified_dataset()
