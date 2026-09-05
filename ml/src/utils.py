from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml


@dataclass
class DatasetSample:
    image_path: Path
    label_path: Path
    year: str
    is_positive: bool
    classes: list[int]


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def dump_json(path: Path, data: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_yolo_label_classes(label_path: Path) -> list[int]:
    if not label_path.exists() or label_path.stat().st_size == 0:
        return []

    classes: list[int] = []
    with label_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                classes.append(int(float(parts[0])))
            except ValueError:
                continue
    return classes


def discover_dataset(data_root: Path) -> list[DatasetSample]:
    samples: list[DatasetSample] = []
    years = [p for p in data_root.iterdir() if p.is_dir()]

    for year_dir in sorted(years):
        year = year_dir.name
        for image_path in sorted(year_dir.glob("*.jpg")):
            label_path = image_path.with_suffix(".txt")
            classes = read_yolo_label_classes(label_path)
            samples.append(
                DatasetSample(
                    image_path=image_path,
                    label_path=label_path,
                    year=year,
                    is_positive=len(classes) > 0,
                    classes=classes,
                )
            )
    return samples


def ensure_exists(path: Path, what: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{what} not found: {path}")
