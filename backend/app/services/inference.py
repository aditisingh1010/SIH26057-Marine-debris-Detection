from pathlib import Path

from app.core.config import settings


class InferenceService:
    def __init__(self, weights=None):
        self.weights = Path(weights or settings.model_path)
        self.loaded = self.weights.is_file()
        self.model = None
        self.names = {0: "debris_0", 1: "debris_1"}

    def predict(self, image_bgr):
        raise NotImplementedError
