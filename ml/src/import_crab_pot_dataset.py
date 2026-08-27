"""Import the gated PINGEcosystem crab-pot SSS dataset into Dataset/crab_pot/.

Accept the Hugging Face dataset conditions and authenticate first:
    pip install -U datasets pillow huggingface_hub
    hf auth login
    python ml/src/import_crab_pot_dataset.py

Only high-confidence `Crab-Pot` annotations are retained and mapped to YOLO
class 2. `Maybe-Crab-Pot` annotations are intentionally excluded. The output
is kept in the flat per-survey layout expected by build_splits.py.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ID = "PINGEcosystem/sss-crab-pot-detection-ds"
KEEP_CLASS = "Crab-Pot"


def _get_image_size(image: Any) -> tuple[int, int]:
    if hasattr(image, "size"):
        width, height = image.size
        return int(width), int(height)
    if isinstance(image, dict) and "width" in image and "height" in image:
        return int(image["width"]), int(image["height"])
    raise ValueError("Unable to determine image dimensions")


def _save_image(image: Any, path: Path) -> None:
    if hasattr(image, "save"):
        image.save(path, format="JPEG")
    elif isinstance(image, dict) and image.get("bytes") is not None:
        path.write_bytes(image["bytes"])
    else:
        raise ValueError("Unsupported Hugging Face image representation")


def _convert_bbox(bbox: list[Any], width: int, height: int) -> tuple[float, float, float, float]:
    if len(bbox) != 4:
        raise ValueError(f"Expected [x, y, width, height], got {bbox}")
    x, y, bw, bh = map(float, bbox)
    x1 = max(0.0, min(x, width)); y1 = max(0.0, min(y, height))
    x2 = max(0.0, min(x + bw, width)); y2 = max(0.0, min(y + bh, height))
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"Invalid bbox after clipping: {bbox}")
    return ((x1 + x2) / 2 / width, (y1 + y2) / 2 / height,
            (x2 - x1) / width, (y2 - y1) / height)


def import_dataset(repo_id: str, output_root: Path) -> dict[str, int]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("Install dependencies: pip install -U datasets pillow huggingface_hub") from exc

    output_root.mkdir(parents=True, exist_ok=True)
    counts = {"train": 0, "valid": 0, "test": 0, "images": 0, "boxes": 0, "maybe_pot_boxes_skipped": 0}
    try:
        dataset = load_dataset(repo_id)
    except Exception as exc:
        raise RuntimeError(
            "Dataset access failed. Accept the Hugging Face gated-dataset conditions, "
            "then run `hf auth login` or set HF_TOKEN."
        ) from exc

    for split_name in ("train", "valid", "test"):
        if split_name not in dataset:
            continue
        for index, row in enumerate(dataset[split_name]):
            image = row["image"]
            width, height = _get_image_size(image)
            raw_name = str(row.get("file_name", f"crab_pot_{split_name}_{index:06d}.jpg"))
            stem = Path(raw_name).stem
            image_path = output_root / f"{stem}.jpg"
            label_path = output_root / f"{stem}.txt"
            if image_path.exists():
                image_path = output_root / f"{stem}_{split_name}_{index:06d}.jpg"
                label_path = output_root / f"{stem}_{split_name}_{index:06d}.txt"

            _save_image(image, image_path)
            counts["images"] += 1; counts[split_name] += 1
            objects = row.get("objects", {}) or {}
            boxes = objects.get("bbox", []) or []
            categories = objects.get("category", []) or []
            lines: list[str] = []
            for bbox, category in zip(boxes, categories):
                if str(category) != KEEP_CLASS:
                    counts["maybe_pot_boxes_skipped"] += 1
                    continue
                cx, cy, bw, bh = _convert_bbox(bbox, width, height)
                lines.append(f"2 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
                counts["boxes"] += 1
            label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    report = {"repo_id": repo_id, "kept_class": KEEP_CLASS, "class_id": 2, **counts}
    (output_root / "IMPORT_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import gated crab-pot SSS data into YOLO format.")
    parser.add_argument("--repo-id", default=REPO_ID)
    parser.add_argument("--output-root", default="Dataset/crab_pot")
    args = parser.parse_args()
    counts = import_dataset(args.repo_id, Path(args.output_root))
    print(json.dumps(counts, indent=2))
    print("Crab-Pot -> YOLO class 2; Maybe-Crab-Pot annotations excluded.")


if __name__ == "__main__":
    main()
