import os
import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Add project roots to sys.path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ml" / "src"))

from app.main import app

def run_live_e2e_demo():
    print("=== LIVE END-TO-END DEMO TEST ===")

    test_img_path = ROOT / "ml" / "data" / "processed" / "ghost_pot" / "images" / "test" / "Rec09_Sensor_Depth_wcp_ss_port_00001_jpg.rf.cf8037272b75606be7164ab0922c8a26.jpg"
    assert test_img_path.exists(), f"Test image missing: {test_img_path}"

    img_bytes = test_img_path.read_bytes()
    print(f"Loaded real test sonar image: {test_img_path.name} ({len(img_bytes)} bytes)")

    client = TestClient(app)

    # 1. Post upload + detection request
    print("\n1. Sending POST /api/v1/detect ...")
    res = client.post(
        "/api/v1/detect",
        files={"file": (test_img_path.name, img_bytes, "image/jpeg")},
        params={"conf_threshold": 0.25}
    )

    assert res.status_code == 200, f"Failed detect request: {res.status_code} - {res.text}"
    data = res.json()
    run_id = data["id"]

    print(f"Success! Run ID: {run_id}")
    print(f"Inference Mode: {data['inference_mode']}")
    print(f"Image Dimensions: {data['image_width']} x {data['image_height']} px")
    print(f"Total Raw Detections: {len(data['raw_detections'])}")
    print(f"Total Filtered Detections: {len(data['filtered_detections'])}")
    print(f"Geolocation Available: {data['geolocation_available']}")
    print(f"Geolocation Note: {data['geolocation_note']}")

    # 2. Check Annotated Image Endpoint
    print("\n2. Fetching Annotated Image (/api/v1/runs/{id}/image/annotated) ...")
    img_res = client.get(f"/api/v1/runs/{run_id}/image/annotated")
    assert img_res.status_code == 200
    print(f"Annotated image retrieved successfully! ({len(img_res.content)} bytes)")

    # 3. Check Report Downloads
    print("\n3. Downloading JSON Report (/api/v1/runs/{id}/report.json) ...")
    json_res = client.get(f"/api/v1/runs/{run_id}/report.json")
    assert json_res.status_code == 200
    json_report = json_res.json()
    print(f"JSON report retrieved! Detections count: {len(json_report['filtered_detections'])}")

    print("\n4. Downloading CSV Report (/api/v1/runs/{id}/report.csv) ...")
    csv_res = client.get(f"/api/v1/runs/{run_id}/report.csv")
    assert csv_res.status_code == 200
    csv_lines = csv_res.text.strip().splitlines()
    print(f"CSV report retrieved! Total CSV rows: {len(csv_lines)}")
    print("CSV Header:", csv_lines[0])
    if len(csv_lines) > 1:
        print("CSV First Row:", csv_lines[1])

    print("\n=== LIVE E2E DEMO VERIFICATION PASSED PERFECTLY ===")
    return data

if __name__ == "__main__":
    run_live_e2e_demo()
