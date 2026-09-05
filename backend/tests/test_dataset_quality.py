from pathlib import Path

import cv2
import numpy as np

from app.services.class_names import normalize_class_name
from app.services.dataset_quality import scan_dataset


def test_normalize_class_name_is_dataset_agnostic():
    assert normalize_class_name("Ghost-Net", 3) == "ghost_net"
    assert normalize_class_name("", 4) == "class_4"
    assert normalize_class_name(None) == "object"


def test_scan_dataset_reads_arbitrary_yolo_classes(tmp_path: Path):
    image = np.full((32, 32, 3), 40, dtype=np.uint8)
    img_path = tmp_path / "tile.png"
    cv2.imwrite(str(img_path), image)
    (tmp_path / "tile.txt").write_text("7 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    empty = tmp_path / "bg.png"
    cv2.imwrite(str(empty), image)
    (tmp_path / "bg.txt").write_text("", encoding="utf-8")

    report = scan_dataset(tmp_path, names={7: "pipe"})
    assert report is not None
    assert report.total_images == 2
    assert report.labeled_images == 1
    assert report.background_images == 1
    assert report.total_annotations == 1
    assert report.class_counts == {"pipe": 1}
