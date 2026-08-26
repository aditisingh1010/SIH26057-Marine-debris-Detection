import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.inference import InferenceService


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
        assert "inference_mode" in body
        assert body["inference_mode"] in {"real", "mock"}


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
        assert r.status_code == 200
        body = r.json()
        assert "detections" in body
        assert "inference_mode" in body
        assert body["inference_mode"] in {"real", "mock"}
        assert body["metadata_attached"] is False
        for det in body["detections"]:
            assert det["geolocation"]["status"] == "unavailable"
            assert det["geolocation"]["latitude"] is None
            assert det["geolocation"]["longitude"] is None
            assert "risk_level" in det
            assert "risk_score" in det
            assert isinstance(det["risk_score"], (int, float))
            assert 0.0 <= det["risk_score"] <= 1.0
            assert det["risk_level"] in {"low", "medium", "high", "critical"}


def test_detect_survey_position_only():
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/detect",
            files={
                "file": ("sonar.png", _png_bytes(), "image/png"),
                "metadata": (
                    "nav.json",
                    b'{"latitude": 15.0, "longitude": 73.0}',
                    "application/json",
                ),
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["metadata_attached"] is True
        if body["detections"]:
            geo = body["detections"][0]["geolocation"]
            assert geo["status"] == "survey_position_only"
            assert geo["latitude"] == 15.0
            assert geo["longitude"] == 73.0


def test_detect_computed_position():
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/detect",
            files={
                "file": ("sonar.png", _png_bytes(), "image/png"),
                "metadata": (
                    "nav.json",
                    b'{"latitude": 15.0, "longitude": 73.0, "pixel_size_m": 0.05, "heading": 90.0}',
                    "application/json",
                ),
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["metadata_attached"] is True
        if body["detections"]:
            geo = body["detections"][0]["geolocation"]
            assert geo["status"] == "computed"
            assert geo["latitude"] is not None
            assert geo["longitude"] is not None


def test_get_run_and_reports():
    with TestClient(app) as client:
        r = client.post(
            "/api/v1/detect",
            files={"file": ("sonar.png", _png_bytes(), "image/png")},
        )
        assert r.status_code == 200
        run_id = r.json()["id"]

        # Test GET /runs/{run_id}
        res_run = client.get(f"/api/v1/runs/{run_id}")
        assert res_run.status_code == 200
        assert res_run.json()["id"] == run_id

        # Test GET /runs/{run_id}/report.json
        res_json = client.get(f"/api/v1/runs/{run_id}/report.json")
        assert res_json.status_code == 200
        assert res_json.headers["content-type"].startswith("application/json")

        # Test GET /runs/{run_id}/report.csv
        res_csv = client.get(f"/api/v1/runs/{run_id}/report.csv")
        assert res_csv.status_code == 200
        assert "risk_level" in res_csv.text
        assert "risk_score" in res_csv.text

        # Test GET /runs/{run_id}/image
        res_img = client.get(f"/api/v1/runs/{run_id}/image")
        assert res_img.status_code == 200


def test_mock_inference_fallback():
    service = InferenceService("non_existent_weights.pt")
    assert service.loaded is False
    assert service.inference_mode == "mock"

    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)
    dets = service.predict(dummy_img)
    assert len(dets) >= 1
    for d in dets:
        assert "id" in d
        assert "class" in d
        assert "confidence" in d
        assert "bbox" in d
        assert "risk_level" in d
        assert "risk_score" in d


def test_missing_run_returns_404():
    with TestClient(app) as client:
        r = client.get("/api/v1/runs/run_does_not_exist")
        assert r.status_code == 404

