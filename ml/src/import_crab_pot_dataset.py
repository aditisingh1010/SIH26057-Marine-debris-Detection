"""Import PINGEcosystem/sss-crab-pot-detection-ds into the project YOLO dataset.

The Hugging Face dataset is gated, so the user must first accept its access
conditions and authenticate with Hugging Face. This script downloads the
train/valid/test splits through `datasets`, keeps only the high-confidence
`Crab-Pot` class, converts pixel-space [x, y, width, height] boxes to YOLO
normalized [class, cx, cy, w, h], and writes the result under Dataset/.

Usage from repo root:
    python ml/src/import_crab_pot_dataset.py

Optional:
    python ml/src/import_crab_pot_dataset.py --output-root Dataset/crab_pot
    python ml/src/import_crab_pot_dataset.py --repo-id PINGEcosystem/sss-crab-pot-detection-ds

Do NOT commit the downloaded images to Git. The project's .gitignore should
exclude Dataset/crab_pot/images/ if the data is kept locally.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ID = "PINGEcosystem/sss-crab-pot-detection-ds"
KEEP_CLASS = "Crab-Pot"
SPLIT_MAP = {"train": "train", "valid": "val", "test": "test"}


def _as_float(value: Any) -> float:
    return float(value)


def _get_image_size(image: Any) -> tuple[int, int]:
    if hasattr(image, "size"):
        width, height = image.size
        return int(width), int(height)
    if isinstance(image, dict) and "width" in image and "height" in image:
        return int(image["width"]), int(image["height"])
    raise ValueError("Unable to determine image dimensions from dataset image field")


def _save_image(image: Any, path: Path) -> None:
    if hasattr(image, "save"):
        image.save(path, format="JPEG")
        return
    if isinstance(image, dict) and "bytes" in image and image["bytes"] is not None:
        path.write_bytes(image["bytes"])
        return
    raise ValueError("Unsupported Hugging Face image representation")


def _convert_bbox(bbox: list[Any], width: int, height: int) -> tuple[float, float, float, float]:
    if len(bbox) != 4:
        raise ValueError(f"Expected [x, y, width, height], got {bbox}")
    x, y, bw, bh = map(_as_float, bbox)
    if width <= 0 or height <= 0:
        raise ValueError("Image dimensions must be positive")

    # Clip to image bounds before normalization.
    x1 = max(0.0, min(x, width))
    y1 = max(0.0, min(y, height))
    x2 = max(0.0, min(x + bw, width))
    y2 = max(0.0, min(y + bh, height))
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"Invalid/empty bbox after clipping: {bbox}")

    cx = ((x1 + x2) / 2.0) / width
    cy = ((y1 + y2) / 2.0) / height
    nw = (x2 - x1) / width
    nh = (y2 - y1) / height
    return cx, cy, nw, nh


def import_dataset(repo_id: str, output_root: Path) -> dict[str, int]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("Install dependencies first: pip install -U datasets pillow huggingface_hub") from exc

    output_root.mkdir(parents=True, exist_ok=True)
    counts = {"train": 0, "val": 0, "test": 0, "images": 0, "boxes": 0}

    try:
        dataset = load_dataset(repo_id)
    except Exception as exc:
        raise RuntimeError(
            "Could not load the Hugging Face dataset. It is gated: accept the dataset "
            "conditions on Hugging Face and run `hf auth login` (or set HF_TOKEN) first."
        ) from exc

    for source_split, destination_split in SPLIT_MAP.items():
        if source_split not in dataset:
            continue
        split = dataset[source_split]
        image_dir = output_root / "images" / destination_split
        label_dir = output_root / "labels" / destination_split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)

        for index, row in enumerate(split):
            image = row["image"]
            width, height = _get_image_size(image)
            file_name = Path(row.get("file_name", f"crab_pot_{index:06d}.jpg")).name
            stem = Path(file_name).stem
            image_path = image_dir / f"{stem}.jpg"
            label_path = label_dir / f"{stem}.txt"

            _save_image(image, image_path)
            counts["images"] += 1
            counts[destination_split] += 1

            objects = row.get("objects", {}) or {}
            boxes = objects.get("bbox", []) or []
            categories = objects.get("category", []) or []
            yolo_lines: list[str] = []
            for bbox, category in zip(boxes, categories):
                if str(category) != KEEP_CLASS:
                    continue
                cx, cy, bw, bh = _convert_bbox(bbox, width, height)
                yolo_lines.append(f"2 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
                counts["boxes"] += 1

            # Empty label files are valid YOLO background examples.
            label_path.write_text("\n".join(yolo_lines) + ("\n" if yolo_lines else ""), encoding="utf-8")

    (output_root / "IMPORT_REPORT.json").write_text(
        json.dumps({"repo_id": repo_id, "kept_class": KEEP_CLASS, "class_id": 2, **counts}, indent=2),
        encoding="utf-8",
    )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the gated crab-pot SSS dataset into YOLO format.")
    parser.add_argument("--repo-id", default=REPO_ID)
    parser.add_argument("--output-root", default="Dataset/crab_pot")
    args = parser.parse_args()

    counts = import_dataset(args.repo_id, Path(args.output_root))
    print(json.dumps(counts, indent=2))
    print("Imported Crab-Pot as YOLO class id 2. Maybe-Crab-Pot was intentionally excluded.")


if __name__ == "__main__":
    main()
