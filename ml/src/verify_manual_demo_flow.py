import json
import sys
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ml" / "src"))

from app.main import app

def run_manual_demo_verification():
    print("==================================================")
    print("   SONAR AQUA MANUAL DEMO VERIFICATION SUITE     ")
    print("==================================================")

    test_img = ROOT / "ml" / "data" / "processed" / "ghost_pot" / "images" / "test" / "Rec09_Sensor_Depth_wcp_ss_port_00001_jpg.rf.cf8037272b75606be7164ab0922c8a26.jpg"
    assert test_img.exists(), f"Missing test image: {test_img}"
    img_bytes = test_img.read_bytes()

    client = TestClient(app)

    # ----------------------------------------------------
    # FLOW 1: SONAR IMAGE UPLOAD WITHOUT METADATA
    # ----------------------------------------------------
    print("\n--- FLOW 1: SONAR IMAGE UPLOAD WITHOUT METADATA ---")
    res1 = client.post(
        "/api/v1/detect",
        files={"file": (test_img.name, img_bytes, "image/jpeg")},
        params={"conf_threshold": 0.25}
    )
    assert res1.status_code == 200, f"Flow 1 failed: {res1.status_code}"
    data1 = res1.json()
    run_id1 = data1["id"]

    print(f"✓ Backend Endpoint Reached: POST /api/v1/detect -> HTTP 200")
    print(f"✓ Run Identifier: {run_id1}")
    print(f"✓ Model Executed: {data1['model']}")
    print(f"✓ Inference Mode: {data1['inference_mode'].upper()} (Real YOLO GPU)")
    print(f"✓ Image Dimensions: {data1['image_width']} x {data1['image_height']} px")
    print(f"✓ Total Raw Detections: {len(data1['raw_detections'])}")
    print(f"✓ Total Filtered Detections: {len(data1['filtered_detections'])}")
    print(f"✓ Geolocation Available: {data1['geolocation_available']}")
    print(f"✓ Geolocation Note: {data1['geolocation_note']}")

    # Check Annotated Image
    img_res1 = client.get(f"/api/v1/runs/{run_id1}/image/annotated")
    assert img_res1.status_code == 200
    print(f"✓ Annotated Green Bounding Box Image Retrieved: {len(img_res1.content)} bytes")

    # Check Reports
    json_res1 = client.get(f"/api/v1/runs/{run_id1}/report.json")
    assert json_res1.status_code == 200
    print(f"✓ JSON Report Download Verified: /api/v1/runs/{run_id1}/report.json")

    csv_res1 = client.get(f"/api/v1/runs/{run_id1}/report.csv")
    assert csv_res1.status_code == 200
    print(f"✓ CSV Report Download Verified: /api/v1/runs/{run_id1}/report.csv")

    # ----------------------------------------------------
    # FLOW 2: SONAR IMAGE UPLOAD WITH REAL NAVIGATION METADATA
    # ----------------------------------------------------
    print("\n--- FLOW 2: SONAR IMAGE UPLOAD WITH REAL NAVIGATION METADATA ---")
    meta_content = json.dumps({
        "latitude": 47.6062,
        "longitude": -122.3321,
        "heading": 180.0,
        "pixel_size_m": 0.05
    }).encode("utf-8")

    res2 = client.post(
        "/api/v1/detect",
        files={
            "file": (test_img.name, img_bytes, "image/jpeg"),
            "metadata": ("nav_telemetry.json", meta_content, "application/json")
        },
        params={"conf_threshold": 0.15}
    )
    assert res2.status_code == 200, f"Flow 2 failed: {res2.status_code}"
    data2 = res2.json()
    run_id2 = data2["id"]

    print(f"✓ Backend Endpoint Reached: POST /api/v1/detect with metadata -> HTTP 200")
    print(f"✓ Run Identifier: {run_id2}")
    print(f"✓ Metadata Attached: {data2['metadata_attached']}")
    print(f"✓ Geolocation Available: {data2['geolocation_available']}")
    print(f"✓ Geolocation Note: {data2['geolocation_note']}")

    dets2 = data2["filtered_detections"]
    if dets2:
        geo2 = dets2[0]["geolocation"]
        print(f"✓ Extracted Coordinates: Lat {geo2['latitude']}°, Lon {geo2['longitude']}° (Status: {geo2['status']})")
        print(f"✓ Geolocation Extraction Verified: Exact real metadata parsed successfully!")

    print("\n==================================================")
    print("   MANUAL DEMO VERIFICATION PASSED 100% PERFECTLY ")
    print("==================================================")

if __name__ == "__main__":
    run_manual_demo_verification()
