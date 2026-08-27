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
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

IMAGE_EXTENSIONS: frozenset = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"})
CLASS_NAMES: Dict[int, str] = {0: "debris_0", 1: "debris_1", 2: "crab_pot"}
DEFAULT_TRAIN_RATIO = 0.67
DEFAULT_VAL_RATIO = 0.17


def _collect_samples(dataset_root: Path) -> List[Tuple[Path, Optional[Path], bool]]:
    samples: List[Tuple[Path, Optional[Path], bool]] = []
    survey_dirs = sorted(d for d in dataset_root.iterdir() if d.is_dir())
    for sdir in survey_dirs:
        images = sorted(p for p in sdir.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)
        label_map = {p.stem: p for p in sdir.glob("*.txt")}
        for img in images:
            lbl = label_map.get(img.stem)
            has_ann = lbl is not None and lbl.stat().st_size > 0
            samples.append((img, lbl, has_ann))
    return samples


def _stratified_split(
    samples: List[Tuple[Path, Optional[Path], bool]],
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> Tuple[List[Tuple[Path, Optional[Path]]], List[Tuple[Path, Optional[Path]]], List[Tuple[Path, Optional[Path]]]]:
    rng = random.Random(seed)
    labeled = [(img, lbl) for img, lbl, has_ann in samples if has_ann]
    background = [(img, lbl) for img, lbl, has_ann in samples if not has_ann]

    def _split_group(items, tr, vr):
        items = list(items)
        rng.shuffle(items)
        n = len(items)
        n_train = int(n * tr)
        n_val = int(n * vr)
        return items[:n_train], items[n_train:n_train + n_val], items[n_train + n_val:]

    l_train, l_val, l_test = _split_group(labeled, train_ratio, val_ratio)
    b_train, b_val, b_test = _split_group(background, train_ratio, val_ratio)
    train, val, test = l_train + b_train, l_val + b_val, l_test + b_test
    rng.shuffle(train); rng.shuffle(val); rng.shuffle(test)
    return train, val, test


def _copy_split(split_samples, split_name, output_dir, preprocess, diameter, sigma_color, sigma_space):
    img_dst = output_dir / "images" / split_name
    lbl_dst = output_dir / "labels" / split_name
    img_dst.mkdir(parents=True, exist_ok=True)
    lbl_dst.mkdir(parents=True, exist_ok=True)
    if preprocess:
        try:
            from ml.src.preprocess_sonar import preprocess_sonar_image
        except ModuleNotFoundError:
            from preprocess_sonar import preprocess_sonar_image

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
            (lbl_dst / (img_path.stem + ".txt")).write_text("", encoding="utf-8")


def _write_yaml(output_dir: Path, yaml_path: Path) -> None:
    config = {
        "path": str(output_dir.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {k: v for k, v in CLASS_NAMES.items()},
    }
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False), encoding="utf-8")


def build_splits(dataset_root: Path, output_dir: Path, yaml_path: Path, train_ratio: float = DEFAULT_TRAIN_RATIO,
                 val_ratio: float = DEFAULT_VAL_RATIO, seed: int = 42, preprocess: bool = False,
                 diameter: int = 5, sigma_color: float = 25.0, sigma_space: float = 25.0) -> Dict:
    samples = _collect_samples(dataset_root)
    if not samples:
        raise ValueError(f"No images found under: {dataset_root}")
    train, val, test = _stratified_split(samples, train_ratio, val_ratio, seed)
    for split_name, split_data in (("train", train), ("val", val), ("test", test)):
        _copy_split(split_data, split_name, output_dir, preprocess, diameter, sigma_color, sigma_space)
    _write_yaml(output_dir, yaml_path)
    return {
        "total_samples": len(samples), "train": len(train), "val": len(val), "test": len(test),
        "output_dir": str(output_dir.resolve()), "yaml_path": str(yaml_path.resolve()),
        "seed": seed, "preprocess": preprocess,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build YOLO-format train/val/test splits from Dataset/.")
    parser.add_argument("--dataset-root", "-d", type=str, default="Dataset")
    parser.add_argument("--output-dir", "-o", type=str, default="ml/data/splits/processed")
    parser.add_argument("--yaml", "-y", type=str, default="ml/data/splits/dataset.yaml")
    parser.add_argument("--train-ratio", type=float, default=DEFAULT_TRAIN_RATIO)
    parser.add_argument("--val-ratio", type=float, default=DEFAULT_VAL_RATIO)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--preprocess", action="store_true")
    parser.add_argument("--diameter", type=int, default=5)
    parser.add_argument("--sigma-color", type=float, default=25.0)
    parser.add_argument("--sigma-space", type=float, default=25.0)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    result = build_splits(
        dataset_root=Path(args.dataset_root), output_dir=Path(args.output_dir), yaml_path=Path(args.yaml),
        train_ratio=args.train_ratio, val_ratio=args.val_ratio, seed=args.seed, preprocess=args.preprocess,
        diameter=args.diameter, sigma_color=args.sigma_color, sigma_space=args.sigma_space,
    )
    print("=" * 56)
    print("  SPLIT SUMMARY")
    print("=" * 56)
    for key in ("total_samples", "train", "val", "test", "output_dir", "yaml_path", "seed", "preprocess"):
        print(f"  {key:14s}: {result[key]}")
    print("  classes       : debris_0, debris_1, crab_pot")
    print("=" * 56)


if __name__ == "__main__":
    main()
