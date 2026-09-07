import cv2
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from ultralytics import YOLO

class SSSSlicedInference:
    """
    SAHI-style sliding-window inference tailored for SSS sonograms.
    Preserves 1:1 pixel resolution of targets, avoiding squeezed/warped 640x640 resize.
    Combines tiled predictions with coarse full-view pass via class-aware box fusion
    and cross-class containment resolution (e.g. shipwrecks vs internal debris fragments).
    """

    def __init__(
        self,
        tile_size: int = 640,
        overlap_ratio: float = 0.25,
        iou_threshold: float = 0.50,
        proximity_merge_px: int = 40,
    ):
        self.tile_size = tile_size
        self.overlap_ratio = overlap_ratio
        self.iou_threshold = iou_threshold
        self.proximity_merge_px = proximity_merge_px

    def slice_image(self, image: np.ndarray) -> List[Dict[str, Any]]:
        h, w = image.shape[:2]
        step = int(self.tile_size * (1.0 - self.overlap_ratio))
        tiles = []

        y_points = list(range(0, max(1, h - self.tile_size + 1), step))
        if len(y_points) == 0 or y_points[-1] + self.tile_size < h:
            y_points.append(max(0, h - self.tile_size))

        x_points = list(range(0, max(1, w - self.tile_size + 1), step))
        if len(x_points) == 0 or x_points[-1] + self.tile_size < w:
            x_points.append(max(0, w - self.tile_size))

        for y in set(y_points):
            for x in set(x_points):
                x1, y1 = x, y
                x2 = min(w, x + self.tile_size)
                y2 = min(h, y + self.tile_size)
                tile = image[y1:y2, x1:x2]
                tiles.append({
                    "tile": tile,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2
                })

        return tiles

    @staticmethod
    def calculate_iou(boxA: List[float], boxB: List[float]) -> float:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

        iou = interArea / float(boxAArea + boxBArea - interArea + 1e-6)
        return iou

    @staticmethod
    def calculate_intersection_over_min(boxA: List[float], boxB: List[float]) -> float:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        minArea = min(boxAArea, boxBArea)
        if minArea <= 0:
            return 0.0
        return interArea / minArea

    @staticmethod
    def _box_area(box: List[float]) -> float:
        return max(0.0, float(box[2]) - float(box[0])) * max(0.0, float(box[3]) - float(box[1]))

    def merge_class_detections(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """NMS per class. Never union boxes — unioning tiles turns a wreck into a whole-swath rectangle."""
        if not detections:
            return []

        by_class: Dict[str, List[Dict[str, Any]]] = {}
        for d in detections:
            by_class.setdefault(d["label"], []).append(d)

        merged_by_class = []

        for label, items in by_class.items():
            items = sorted(items, key=lambda x: x["confidence"], reverse=True)
            kept: List[Dict[str, Any]] = []

            for item in items:
                replaced = False
                drop_item = False
                for idx, existing in enumerate(kept):
                    iou = self.calculate_iou(item["box"], existing["box"])
                    iomin = self.calculate_intersection_over_min(item["box"], existing["box"])
                    if iou <= self.iou_threshold and iomin < 0.45:
                        continue

                    area_item = self._box_area(item["box"])
                    area_ex = self._box_area(existing["box"])
                    if area_item <= 0 or area_ex <= 0:
                        drop_item = True
                        break

                    smaller = item if area_item <= area_ex else existing
                    larger = existing if smaller is item else item
                    nested = self.calculate_intersection_over_min(smaller["box"], larger["box"]) >= 0.45
                    # Prefer the tight box on the object over a tile-sized parent.
                    if nested and smaller["confidence"] >= 0.45 * float(larger["confidence"]):
                        kept[idx] = smaller
                        replaced = True
                    drop_item = True
                    break

                if replaced or drop_item:
                    continue
                kept.append(item)

            for det in kept:
                box = det["box"]
                merged_by_class.append({
                    "label": label,
                    "confidence": round(float(det["confidence"]), 3),
                    "box": [round(float(box[0]), 1), round(float(box[1]), 1), round(float(box[2]), 1), round(float(box[3]), 1)],
                    "merged_count": int(det.get("merged_count", 1)),
                })

        # -------------------------------------------------------------
        # Cross-Class Conflict Resolution:
        # If a large shipwreck contains or heavily overlaps smaller debris boxes,
        # suppress the redundant debris box so the shipwreck remains whole and uncluttered!
        # -------------------------------------------------------------
        shipwrecks = [d for d in merged_by_class if d["label"] == "shipwreck"]
        final_clean = []

        for d in merged_by_class:
            if d["label"] == "seafloor_debris":
                # Check if this debris box is contained inside or overlapping with a shipwreck
                covered_by_wreck = False
                for sw in shipwrecks:
                    overlap_ratio = self.calculate_intersection_over_min(d["box"], sw["box"])
                    # If 40% or more of this debris box overlaps a detected shipwreck, it belongs to the wreck!
                    if overlap_ratio >= 0.40:
                        covered_by_wreck = True
                        break
                if not covered_by_wreck:
                    final_clean.append(d)
            else:
                final_clean.append(d)

        return final_clean

    def predict(
        self,
        model: YOLO,
        image: np.ndarray,
        conf_threshold: float = 0.35,
        enable_coarse_pass: bool = True
    ) -> List[Dict[str, Any]]:
        all_raw_detections: List[Dict[str, Any]] = []

        if enable_coarse_pass:
            coarse_res = model(image, conf=conf_threshold, verbose=False)[0]
            for box, conf, cls_id in zip(coarse_res.boxes.xyxy.cpu().numpy(),
                                         coarse_res.boxes.conf.cpu().numpy(),
                                         coarse_res.boxes.cls.cpu().numpy()):
                lbl = model.names[int(cls_id)]
                all_raw_detections.append({
                    "label": lbl,
                    "confidence": float(conf),
                    "box": [float(box[0]), float(box[1]), float(box[2]), float(box[3])]
                })

        tiles = self.slice_image(image)
        for t in tiles:
            res = model(t["tile"], conf=conf_threshold, verbose=False)[0]
            for box, conf, cls_id in zip(res.boxes.xyxy.cpu().numpy(),
                                         res.boxes.conf.cpu().numpy(),
                                         res.boxes.cls.cpu().numpy()):
                lbl = model.names[int(cls_id)]
                gx1 = box[0] + t["x1"]
                gy1 = box[1] + t["y1"]
                gx2 = box[2] + t["x1"]
                gy2 = box[3] + t["y1"]

                all_raw_detections.append({
                    "label": lbl,
                    "confidence": float(conf),
                    "box": [float(gx1), float(gy1), float(gx2), float(gy2)]
                })

        final_merged = self.merge_class_detections(all_raw_detections)
        return final_merged
