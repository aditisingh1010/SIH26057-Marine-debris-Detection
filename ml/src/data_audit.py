"""
Dataset Audit Module -- ml/src/data_audit.py

Scans Dataset/ and reports image/label counts, background images, class counts,
and YOLO label-format anomalies.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

IMAGE_EXTENSIONS: frozenset = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"})
KNOWN_CLASS_IDS: Tuple[int, ...] = (0, 1, 2)
CLASS_NAMES: Dict[int, str] = {0: "debris_0", 1: "debris_1", 2: "crab_pot"}


def _parse_yolo_label(label_path: Path) -> Tuple[List[Tuple[int, float, float, float, float]], List[str]]:
    annotations: List[Tuple[int, float, float, float, float]] = []
    errors: List[str] = []
    text = label_path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return annotations, errors
    for line_no, raw in enumerate(text.splitlines(), start=1):
        parts = raw.strip().split()
        if len(parts) != 5:
            errors.append(f"{label_path.name}:{line_no} -- expected 5 fields, got {len(parts)}")
            continue
        try:
            cls = int(parts[0]); cx, cy, bw, bh = map(float, parts[1:])
        except ValueError:
            errors.append(f"{label_path.name}:{line_no} -- non-numeric field(s)")
            continue
        if cls not in KNOWN_CLASS_IDS:
            errors.append(f"{label_path.name}:{line_no} -- unknown class id {cls}")
        for val, name in ((cx, "cx"), (cy, "cy"), (bw, "bw"), (bh, "bh")):
            if not (0.0 <= val <= 1.0):
                errors.append(f"{label_path.name}:{line_no} -- {name}={val:.4f} out of [0, 1]")
        annotations.append((cls, cx, cy, bw, bh))
    return annotations, errors


def audit_directory(survey_dir: Path) -> Dict:
    image_files = sorted(p for p in survey_dir.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)
    label_files = {p.stem: p for p in survey_dir.glob("*.txt")}
    total_images = len(image_files); labeled_images = 0; background_images = 0; total_annotations = 0
    class_counts: Dict[int, int] = {cid: 0 for cid in KNOWN_CLASS_IDS}
    format_errors: List[str] = []; images_without_label: List[str] = []
    for img in image_files:
        lbl_path: Optional[Path] = label_files.get(img.stem)
        if lbl_path is None:
            images_without_label.append(img.name); background_images += 1; continue
        annotations, errors = _parse_yolo_label(lbl_path); format_errors.extend(errors)
        if annotations:
            labeled_images += 1; total_annotations += len(annotations)
            for cls, *_ in annotations:
                if cls in class_counts: class_counts[cls] += 1
        else:
            background_images += 1
    return {
        "survey": survey_dir.name, "total_images": total_images, "labeled_images": labeled_images,
        "background_images": background_images, "total_annotations": total_annotations,
        "class_counts": {CLASS_NAMES[k]: v for k, v in class_counts.items()},
        "format_error_count": len(format_errors), "format_errors": format_errors[:20],
        "images_without_label_file": images_without_label,
    }


def audit_dataset(dataset_root: Path) -> Dict:
    if not dataset_root.is_dir(): raise FileNotFoundError(f"Dataset root not found: {dataset_root}")
    survey_dirs = sorted(d for d in dataset_root.iterdir() if d.is_dir())
    if not survey_dirs: raise ValueError(f"No sub-directories found under: {dataset_root}")
    per_survey: List[Dict] = []; grand = {"total_images": 0, "labeled_images": 0, "background_images": 0, "total_annotations": 0, "total_format_errors": 0}
    grand_class_counts: Dict[str, int] = {v: 0 for v in CLASS_NAMES.values()}
    for sdir in survey_dirs:
        report = audit_directory(sdir); per_survey.append(report)
        for key in grand: grand[key] += report["format_error_count"] if key == "total_format_errors" else report[key]
        for cls_name, count in report["class_counts"].items(): grand_class_counts[cls_name] += count
    return {"dataset_root": str(dataset_root.resolve()), "surveys_found": [d.name for d in survey_dirs], "summary": {**grand, "class_counts": grand_class_counts}, "per_survey": per_survey}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the raw sonar dataset.")
    parser.add_argument("--dataset-root", "-d", default="Dataset")
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()
    try:
        report = audit_dataset(Path(args.dataset_root))
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); sys.exit(1)
    s = report["summary"]
    print("=" * 56); print("  DATASET AUDIT SUMMARY"); print("=" * 56)
    print(f"  Surveys found    : {report['surveys_found']}")
    print(f"  Total images     : {s['total_images']}")
    print(f"  Labeled images   : {s['labeled_images']}")
    print(f"  Background tiles : {s['background_images']}")
    print(f"  Total annotations: {s['total_annotations']}")
    for cls_name, cnt in s["class_counts"].items(): print(f"    {cls_name:12s}: {cnt}")
    print(f"  Format errors    : {s['total_format_errors']}"); print("=" * 56)
    if args.output:
        out_path = Path(args.output); out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[data_audit] Report saved to: {out_path.resolve()}")


if __name__ == "__main__":
    main()
