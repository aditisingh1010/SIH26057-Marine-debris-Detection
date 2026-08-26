"""
Dataset Split Builder -- ml/src/build_splits.py

Reads the raw Dataset/ directory (with per-year survey sub-folders), applies
a stratified train/val/test split, preprocesses images via preprocess_sonar.py,
and writes a YOLO-compatible folder layout together with a dataset YAML config.

Output structure:
    <output-dir>/
        images/
            train/  val/  test/
        labels/
            train/  val/  test/
    <yaml-path>  (YOLO dataset config)

Usage (from project root):
    python ml/src/build_splits.py
    python ml/src/build_splits.py --dataset-root Dataset --output-dir ml/data/splits/processed --yaml ml/data/splits/dataset.yaml
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml  # PyYAML -- installed with ultralytics

# ---------------------------------------------------------------------------
IMAGE_EXTENSIONS: frozenset = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"})
CLASS_NAMES: Dict[int, str] = {0: "debris_0", 1: "debris_1"}

DEFAULT_TRAIN_RATIO = 0.67
DEFAULT_VAL_RATIO   = 0.17
# test = remainder (~0.16)


# ---------------------------------------------------------------------------
def _collect_samples(dataset_root: Path) -> List[Tuple[Path, Optional[Path], bool]]:
    """Return (image_path, label_path_or_None, has_annotation) for every image."""
    samples: List[Tuple[Path, Optional[Path], bool]] = []

    survey_dirs = sorted(d for d in dataset_root.iterdir() if d.is_dir())
    for sdir in survey_dirs:
        images = sorted(p for p in sdir.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)
        label_map = {p.stem: p for p in sdir.glob("*.txt")}
        for img in images:
            lbl = label_map.get(img.stem)
            has_ann = False
            if lbl is not None and lbl.stat().st_size > 0:
                has_ann = True
            samples.append((img, lbl, has_ann))

    return samples


def _stratified_split(
    samples: List[Tuple[Path, Optional[Path], bool]],
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> Tuple[
    List[Tuple[Path, Optional[Path]]],
    List[Tuple[Path, Optional[Path]]],
    List[Tuple[Path, Optional[Path]]],
]:
    """Split samples into train/val/test, preserving labeled/background ratio."""
    rng = random.Random(seed)

    labeled   = [(img, lbl) for img, lbl, has_ann in samples if has_ann]
    background= [(img, lbl) for img, lbl, has_ann in samples if not has_ann]

    def _split_group(items, tr, vr):
        items = list(items)
        rng.shuffle(items)
        n = len(items)
        n_train = int(n * tr)
        n_val   = int(n * vr)
        return items[:n_train], items[n_train:n_train + n_val], items[n_train + n_val:]

    l_train, l_val, l_test = _split_group(labeled,    train_ratio, val_ratio)
    b_train, b_val, b_test = _split_group(background, train_ratio, val_ratio)

    train = l_train + b_train
    val   = l_val   + b_val
    test  = l_test  + b_test

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)

    return train, val, test


def _copy_split(
    split_samples: List[Tuple[Path, Optional[Path]]],
    split_name: str,
    output_dir: Path,
    preprocess: bool,
    diameter: int,
    sigma_color: float,
    sigma_space: float,
) -> None:
    """Copy (and optionally preprocess) images + labels into the split directory."""
    img_dst = output_dir / "images" / split_name
    lbl_dst = output_dir / "labels" / split_name
    img_dst.mkdir(parents=True, exist_ok=True)
    lbl_dst.mkdir(parents=True, exist_ok=True)

    if preprocess:
        # Import here to avoid hard dependency when preprocess=False
        from ml.src.preprocess_sonar import preprocess_sonar_image  # noqa: PLC0415

    for img_path, lbl_path in split_samples:
        if preprocess:
            preprocess_sonar_image(
                input_image_path=img_path,
                output_dir=img_dst,
                copy_label=False,
                diameter=diameter,
                sigma_color=sigma_color,
                sigma_space=sigma_space,
            )
        else:
            shutil.copy2(str(img_path), str(img_dst / img_path.name))

        if lbl_path is not None and lbl_path.exists():
            shutil.copy2(str(lbl_path), str(lbl_dst / lbl_path.name))
        else:
            # Write empty label file for background images (required by YOLO)
            (lbl_dst / (img_path.stem + ".txt")).write_text("", encoding="utf-8")


def _write_yaml(output_dir: Path, yaml_path: Path) -> None:
    """Write a YOLO-compatible dataset YAML config."""
    config = {
        "path": str(output_dir.resolve()),
        "train": "images/train",
        "val":   "images/val",
        "test":  "images/test",
        "names": {k: v for k, v in CLASS_NAMES.items()},
    }
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False), encoding="utf-8")


def build_splits(
    dataset_root: Path,
    output_dir: Path,
    yaml_path: Path,
    train_ratio: float = DEFAULT_TRAIN_RATIO,
    val_ratio: float = DEFAULT_VAL_RATIO,
    seed: int = 42,
    preprocess: bool = False,
    diameter: int = 5,
    sigma_color: float = 25.0,
    sigma_space: float = 25.0,
) -> Dict:
    """
    Main entry point: collect, split, copy, and write YAML.

    Args:
        dataset_root: Root folder containing per-year survey sub-directories.
        output_dir:   Destination for YOLO-format images/labels split folders.
        yaml_path:    Path to write the YOLO dataset YAML config file.
        train_ratio:  Fraction of data for training (default 0.67).
        val_ratio:    Fraction of data for validation (default 0.17).
        seed:         Random seed for reproducibility.
        preprocess:   Whether to apply sonar noise filtering before copying.
        diameter:     Bilateral filter diameter (used if preprocess=True).
        sigma_color:  Bilateral filter sigma_color (used if preprocess=True).
        sigma_space:  Bilateral filter sigma_space (used if preprocess=True).

    Returns:
        Dict with split counts summary.
    """
    samples = _collect_samples(dataset_root)
    if not samples:
        raise ValueError(f"No images found under: {dataset_root}")

    train, val, test = _stratified_split(samples, train_ratio, val_ratio, seed)

    for split_name, split_data in (("train", train), ("val", val), ("test", test)):
        _copy_split(
            split_samples=split_data,
            split_name=split_name,
            output_dir=output_dir,
            preprocess=preprocess,
            diameter=diameter,
            sigma_color=sigma_color,
            sigma_space=sigma_space,
        )

    _write_yaml(output_dir, yaml_path)

    return {
        "total_samples": len(samples),
        "train": len(train),
        "val":   len(val),
        "test":  len(test),
        "output_dir": str(output_dir.resolve()),
        "yaml_path":  str(yaml_path.resolve()),
        "seed": seed,
        "preprocess": preprocess,
    }


# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build YOLO-format train/val/test splits from the raw Dataset/."
    )
    parser.add_argument("--dataset-root", "-d", type=str, default="Dataset",
                        help="Raw dataset root with per-year sub-dirs (default: Dataset).")
    parser.add_argument("--output-dir", "-o", type=str, default="ml/data/splits/processed",
                        help="Destination directory for the YOLO split layout.")
    parser.add_argument("--yaml", "-y", type=str, default="ml/data/splits/dataset.yaml",
                        help="Path to write the YOLO dataset YAML config.")
    parser.add_argument("--train-ratio", type=float, default=DEFAULT_TRAIN_RATIO)
    parser.add_argument("--val-ratio",   type=float, default=DEFAULT_VAL_RATIO)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--preprocess", action="store_true",
                        help="Apply sonar bilateral-filter preprocessing before copying.")
    parser.add_argument("--diameter",    type=int,   default=5)
    parser.add_argument("--sigma-color", type=float, default=25.0)
    parser.add_argument("--sigma-space", type=float, default=25.0)
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    output_dir   = Path(args.output_dir)
    yaml_path    = Path(args.yaml)

    print(f"\n[build_splits] Dataset root : {dataset_root.resolve()}")
    print(f"[build_splits] Output dir   : {output_dir.resolve()}")
    print(f"[build_splits] YAML path    : {yaml_path.resolve()}")
    print(f"[build_splits] Ratios       : train={args.train_ratio:.2f}  val={args.val_ratio:.2f}  "
          f"test={1 - args.train_ratio - args.val_ratio:.2f}")
    print(f"[build_splits] Seed         : {args.seed}")
    print(f"[build_splits] Preprocess   : {args.preprocess}\n")

    try:
        result = build_splits(
            dataset_root=dataset_root,
            output_dir=output_dir,
            yaml_path=yaml_path,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
            seed=args.seed,
            preprocess=args.preprocess,
            diameter=args.diameter,
            sigma_color=args.sigma_color,
            sigma_space=args.sigma_space,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print("=" * 56)
    print("  SPLIT SUMMARY")
    print("=" * 56)
    print(f"  Total samples : {result['total_samples']}")
    print(f"  Train         : {result['train']}")
    print(f"  Val           : {result['val']}")
    print(f"  Test          : {result['test']}")
    print(f"  Output dir    : {result['output_dir']}")
    print(f"  YAML          : {result['yaml_path']}")
    print("=" * 56 + "\n")


if __name__ == "__main__":
    main()
