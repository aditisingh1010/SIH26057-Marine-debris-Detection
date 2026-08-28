import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ml" / "src"))

from app.main import app

def analyze_test_images():
    test_dir = ROOT / "ml" / "data" / "processed" / "ghost_pot" / "images" / "test"
    assert test_dir.exists(), f"Test directory missing: {test_dir}"

    # Grab 20 test images to scan
    img_paths = sorted(list(test_dir.glob("*.jpg")))[:30]
    assert len(img_paths) >= 10, f"Expected at least 10 images, found {len(img_paths)}"

    client = TestClient(app)

    results = []

    for img_path in img_paths:
        img_bytes = img_path.read_bytes()

        # Test with default threshold conf=0.25 (and also record low conf detections if any)
        res = client.post(
            "/api/v1/detect",
            files={"file": (img_path.name, img_bytes, "image/jpeg")},
            params={"conf_threshold": 0.15}
        )

        if res.status_code != 200:
            continue

        data = res.json()
        run_id = data["id"]

        # Check annotated image endpoint
        img_res = client.get(f"/api/v1/runs/{run_id}/image/annotated")
        annotated_ok = (img_res.status_code == 200 and len(img_res.content) > 0)

        raw_dets = data.get("raw_detections", [])
        filtered_dets = data.get("filtered_detections", [])

        max_conf = 0.0
        best_det = None
        for d in (filtered_dets if filtered_dets else raw_dets):
            if d.get("confidence", 0) > max_conf:
                max_conf = d["confidence"]
                best_det = d

        bbox_str = "N/A"
        cls_name = "N/A"
        if best_det:
            cls_name = best_det.get("class", "crab_pot")
            b = best_det.get("bbox", {})
            x1 = b.get("x1", b.get("x", 0))
            y1 = b.get("y1", b.get("y", 0))
            x2 = b.get("x2", x1 + b.get("width", 0))
            y2 = b.get("y2", y1 + b.get("height", 0))
            bbox_str = f"[{x1}, {y1}, {x2}, {y2}] ({b.get('width', 0)}x{b.get('height', 0)} px)"

        results.append({
            "filename": img_path.name,
            "dimensions": f"{data['image_width']}x{data['image_height']}",
            "raw_count": len(raw_dets),
            "filtered_count": len(filtered_dets),
            "top_class": cls_name,
            "top_confidence": max_conf,
            "bbox": bbox_str,
            "annotated_ok": annotated_ok,
            "run_id": run_id
        })

    # Sort by top_confidence descending
    results.sort(key=lambda x: x["top_confidence"], reverse=True)

    # Select 10 representative images
    selected_10 = results[:10]

    print("\n==================================================")
    print("      SONAR AQUA 10 DEMO IMAGES EVALUATION       ")
    print("==================================================")

    for idx, item in enumerate(selected_10, start=1):
        print(f"\n[{idx}] {item['filename']}")
        print(f"    Dimensions: {item['dimensions']} px")
        print(f"    Raw Detections: {item['raw_count']} | Filtered Detections: {item['filtered_count']}")
        print(f"    Top Class: {item['top_class']} | Confidence: {item['top_confidence']*100:.2f}%")
        print(f"    BBox Coordinates: {item['bbox']}")
        print(f"    Annotated Image Generated: {item['annotated_ok']}")

    # Write summary report to scratch/demo_images_analysis.json
    scratch_dir = ROOT / ".gemini" / "antigravity-ide" / "brain"
    output_report = {
        "evaluated_total": len(results),
        "top_10": selected_10
    }

    with open("ml/data/demo_images_analysis.json", "w", encoding="utf-8") as f:
        json.dump(output_report, f, indent=2)

    print("\nSaved report to ml/data/demo_images_analysis.json")
    return selected_10

if __name__ == "__main__":
    analyze_test_images()
