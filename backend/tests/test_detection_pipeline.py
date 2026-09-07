from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import numpy as np
import cv2
import json

from app.main import app
from app.services.filtering import filter_detections

client = TestClient(app)

@pytest.fixture
def sample_sonar_image_bytes():
    """Generates a valid 640x640 synthetic sonar image for testing."""
    img = np.full((640, 640, 3), 40, dtype=np.uint8)
    # Draw a simulated bright object with shadow
    cv2.rectangle(img, (200, 200), (280, 280), (220, 220, 220), -1)
    cv2.rectangle(img, (280, 200), (360, 280), (10, 10, 10), -1)
    is_success, buffer = cv2.imencode(".jpg", img)
    assert is_success
    return buffer.tobytes()

def test_1_image_upload(sample_sonar_image_bytes):
    """Test 1: Image upload functionality."""
    response = client.post(
        "/api/v1/detect",
        files={"file": ("sonar_test.jpg", sample_sonar_image_bytes, "image/jpeg")},
        params={"conf_threshold": 0.25}
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["filename"] == "sonar_test.jpg"
    assert data["image_width"] == 640
    assert data["image_height"] == 640

def test_2_inference_endpoint(sample_sonar_image_bytes):
    """Test 2: Inference endpoint returning structured detection dict."""
    response = client.post(
        "/api/v1/detect",
        files={"file": ("sonar_test.jpg", sample_sonar_image_bytes, "image/jpeg")},
        params={"conf_threshold": 0.25}
    )
    assert response.status_code == 200
    data = response.json()
    assert "inference_mode" in data
    assert "raw_detections" in data
    assert "filtered_detections" in data
    assert "detections" in data

def test_3_confidence_and_noise_filtering():
    """Test 3: Post-processing noise and confidence filtering."""
    raw = [
        {"id": "det_001", "class": "object", "confidence": 0.85, "bbox": {"x": 100, "y": 100, "width": 50, "height": 50}},
        {"id": "det_002", "class": "object", "confidence": 0.15, "bbox": {"x": 200, "y": 200, "width": 50, "height": 50}}, # Low conf
        {"id": "det_003", "class": "object", "confidence": 0.90, "bbox": {"x": 0, "y": 0, "width": 640, "height": 640}}, # Full image artifact
    ]

    res = filter_detections(
        raw_detections=raw,
        image_width=640,
        image_height=640,
        conf_threshold=0.25,
        min_area=25.0,
        max_area_ratio=0.90
    )

    assert res["total_raw"] == 3
    assert res["total_filtered"] == 1
    assert res["filtered_detections"][0]["id"] == "det_001"
    assert res["noise_reduced_count"] == 2


def test_default_filter_rejects_channel_sized_box():
    """A box covering ~half the waterfall must not be kept as the wreck."""
    raw = [
        {
            "id": "det_tight",
            "class": "shipwreck",
            "confidence": 0.70,
            "bbox": {"x": 480, "y": 90, "width": 90, "height": 70},
        },
        {
            "id": "det_giant",
            "class": "shipwreck",
            "confidence": 0.86,
            "bbox": {"x": 400, "y": 8, "width": 390, "height": 320},
        },
    ]
    res = filter_detections(raw, 800, 336, conf_threshold=0.25)
    kept_ids = [d["id"] for d in res["filtered_detections"]]
    assert "det_giant" not in kept_ids
    assert "det_tight" in kept_ids


def test_tile_merge_keeps_tight_wreck_not_union():
    from tiled_inference import SSSSlicedInference

    slicer = SSSSlicedInference()
    merged = slicer.merge_class_detections(
        [
            {
                "label": "shipwreck",
                "confidence": 0.86,
                "box": [400.0, 8.0, 790.0, 328.0],
            },
            {
                "label": "shipwreck",
                "confidence": 0.70,
                "box": [500.0, 110.0, 610.0, 190.0],
            },
        ]
    )
    assert len(merged) == 1
    box = merged[0]["box"]
    assert box[2] - box[0] < 200
    assert box[3] - box[1] < 120

def test_operating_modes_resolve_thresholds():
    from app.services.modes import (
        DEMO_CONF_THRESHOLD,
        RAW_INFERENCE_CONF,
        SURVEY_CONF_THRESHOLD,
        raw_yolo_conf,
        resolve_operating_mode,
    )

    assert RAW_INFERENCE_CONF <= SURVEY_CONF_THRESHOLD
    assert SURVEY_CONF_THRESHOLD < DEMO_CONF_THRESHOLD
    assert raw_yolo_conf("demo", 0.25) == 0.20
    assert raw_yolo_conf("survey", 0.10) == RAW_INFERENCE_CONF
    assert raw_yolo_conf("custom", 0.40) == 0.30
    assert resolve_operating_mode("demo", 0.99) == ("demo", 0.25)
    assert resolve_operating_mode("survey", 0.99) == ("survey", 0.10)
    assert resolve_operating_mode("custom", 0.40) == ("custom", 0.40)
    assert resolve_operating_mode(None, 0.25) == ("demo", 0.25)
    assert resolve_operating_mode(None, 0.10) == ("survey", 0.10)
    assert resolve_operating_mode(None, 0.40) == ("custom", 0.40)


def test_survey_filter_keeps_mid_confidence_demo_drops():
    """Boxes between 10% and 25% must be keepable by Survey after YOLO proposes them."""
    raw = [
        {
            "id": "det_mid",
            "class": "crab_pot",
            "confidence": 0.15,
            "bbox": {"x": 40, "y": 40, "width": 30, "height": 30},
        }
    ]
    demo = filter_detections(raw, 640, 640, conf_threshold=0.25)
    survey = filter_detections(raw, 640, 640, conf_threshold=0.10)
    assert demo["total_filtered"] == 0
    assert survey["total_filtered"] == 1
    assert survey["filtered_detections"][0]["id"] == "det_mid"


def test_detect_demo_and_survey_modes_persist(sample_sonar_image_bytes):
    demo = client.post(
        "/api/v1/detect",
        files={"file": ("sonar_test.jpg", sample_sonar_image_bytes, "image/jpeg")},
        params={"mode": "demo"},
    )
    assert demo.status_code == 200
    demo_body = demo.json()
    assert demo_body["detection_mode"] == "demo"
    assert demo_body["conf_threshold"] == 0.25
    assert "filter_stats" in demo_body
    assert demo_body["filter_stats"]["total_raw"] >= demo_body["filter_stats"]["total_filtered"]

    survey = client.post(
        "/api/v1/detect",
        files={"file": ("sonar_test.jpg", sample_sonar_image_bytes, "image/jpeg")},
        params={"mode": "survey"},
    )
    assert survey.status_code == 200
    survey_body = survey.json()
    assert survey_body["detection_mode"] == "survey"
    assert survey_body["conf_threshold"] == 0.10


def test_detect_rejects_unknown_mode(sample_sonar_image_bytes):
    response = client.post(
        "/api/v1/detect",
        files={"file": ("sonar_test.jpg", sample_sonar_image_bytes, "image/jpeg")},
        params={"mode": "turbo"},
    )
    assert response.status_code == 400
    assert "mode must be" in response.json()["detail"]


def test_4_report_generation(sample_sonar_image_bytes):
    """Test 4: JSON and CSV report downloads."""
    # Run detection
    post_res = client.post(
        "/api/v1/detect",
        files={"file": ("sonar_test.jpg", sample_sonar_image_bytes, "image/jpeg")},
        params={"conf_threshold": 0.25}
    )
    assert post_res.status_code == 200
    run_id = post_res.json()["id"]

    # Test JSON download
    json_res = client.get(f"/api/v1/runs/{run_id}/report.json")
    assert json_res.status_code == 200
    report_data = json_res.json()
    assert report_data["id"] == run_id
    assert "filtered_detections" in report_data

    # Test CSV download
    csv_res = client.get(f"/api/v1/runs/{run_id}/report.csv")
    assert csv_res.status_code == 200
    csv_text = csv_res.text
    assert "detection_id" in csv_text
    assert "image_name" in csv_text
    assert "bbox_x1" in csv_text

def test_5_invalid_image_handling():
    """Test 5: Error handling for unreadable or invalid image upload."""
    corrupt_bytes = b"NOT_AN_IMAGE_FILE_DATA"
    response = client.post(
        "/api/v1/detect",
        files={"file": ("bad_image.jpg", corrupt_bytes, "image/jpeg")}
    )
    assert response.status_code == 400
    assert "unreadable or invalid image" in response.json()["detail"]
