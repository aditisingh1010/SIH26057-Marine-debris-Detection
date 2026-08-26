from pathlib import Path

from ultralytics import YOLO

from app.core.config import settings
from preprocess_sonar import filter_sonar_noise


class InferenceService:
    _shared_model = None
    _shared_names = None
    _shared_path = None

    def __init__(self, weights=None):
        self.weights = Path(weights or settings.model_path)
        self.loaded = False
        self.model = None
        self.names = {0: "debris_0", 1: "debris_1"}
        if self.weights.is_file():
            path = str(self.weights.resolve())
            if (
                InferenceService._shared_model is None
                or InferenceService._shared_path != path
            ):
                InferenceService._shared_model = YOLO(path)
                InferenceService._shared_names = dict(
                    InferenceService._shared_model.names
                )
                InferenceService._shared_path = path
            self.model = InferenceService._shared_model
            self.names = InferenceService._shared_names
            self.loaded = True

    def predict(self, image_bgr):
        if not self.loaded or self.model is None:
            raise RuntimeError("model not loaded")

        cleaned = filter_sonar_noise(image_bgr)
        results = self.model.predict(
            source=cleaned, conf=0.25, imgsz=416, verbose=False
        )
        height, width = image_bgr.shape[:2]
        detections = []
        if not results:
            return detections

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return detections

        for index, box in enumerate(boxes, start=1):
            xyxy = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = (float(v) for v in xyxy)
            x1 = max(0.0, min(float(width), x1))
            y1 = max(0.0, min(float(height), y1))
            x2 = max(0.0, min(float(width), x2))
            y2 = max(0.0, min(float(height), y2))
            if x2 < x1:
                x1, x2 = x2, x1
            if y2 < y1:
                y1, y2 = y2, y1
            x = int(round(x1))
            y = int(round(y1))
            box_w = int(round(x2 - x1))
            box_h = int(round(y2 - y1))
            box_w = max(0, min(width - x, box_w))
            box_h = max(0, min(height - y, box_h))
            cls_id = int(box.cls[0].item())
            detections.append(
                {
                    "id": f"det_{index:03d}",
                    "class": self.names.get(cls_id, f"debris_{cls_id}"),
                    "confidence": float(box.conf[0].item()),
                    "bbox": {"x": x, "y": y, "width": box_w, "height": box_h},
                }
            )
        return detections
