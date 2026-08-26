import cv2
import numpy as np
from fastapi.testclient import TestClient
from app.main import app


def _png_bytes() -> bytes:
    image = np.full((80, 96, 3), 40, dtype=np.uint8)
    image[30:50, 40:70] = 240
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def test_health_ok():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["service"] == "aquax-api"
        assert "model_loaded" in body


def test_rejects_txt():
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/detect",
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        assert r.status_code == 400


def test_detect_without_metadata_unavailable():
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/detect",
            files={"file": ("sonar.png", _png_bytes(), "image/png")},
        )
        assert r.status_code in {200, 503}
        if r.status_code == 200:
            body = r.json()
            assert "detections" in body
            assert body["metadata_attached"] is False
            for det in body["detections"]:
                assert det["geolocation"]["status"] == "unavailable"


def test_detect_survey_position_only():
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/detect",
            files={
                "file": ("sonar.png", _png_bytes(), "image/png"),
                "metadata": ("nav.json", b'{"latitude": 15.0, "longitude": 73.0}', "application/json"),
            },
        )
        if r.status_code == 200 and r.json()["detections"]:
            geo = r.json()["detections"][0]["geolocation"]
            assert geo["status"] == "survey_position_only"
            assert geo["latitude"] == 15.0


def test_missing_run_returns_404():
    with TestClient(app) as client:
        r = client.get("/api/v1/runs/run_does_not_exist")
        assert r.status_code == 404
