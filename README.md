# SIH26057 — Marine Debris Detection

AI-assisted detection of marine debris in side-scan sonar (SSS) imagery.
Smart India Hackathon 2026 — Problem Statement SIH26057.

## What it does

Runs a YOLOv8n object detector on side-scan sonar waterfall images to identify potential debris on the seafloor. Outputs bounding boxes, confidence scores, risk classification, acoustic shadow heuristic detection, and a geolocation estimate when navigation metadata is provided.

Coordinates are only shown when real survey metadata (lat, lon, heading, pixel_size_m) is attached. They are never invented.

## Key Features

- **Sonar Object Detection:** YOLOv8n detector calibrated for side-scan acoustic anomalies (marine debris & seabed objects).
- **Conservative Preprocessing:** Bilateral speckle filter + outer swath lateral line artifact attenuation.
- **Acoustic Shadow Analysis:** Heuristic detection of candidate acoustic shadow zones adjacent to acoustic highlight returns.
- **Edge / AUV Deployment:** Export script to generate ONNX (`best.onnx`) and TorchScript models for edge drone deployment.
- **Survey Navigation Ingestion:** Supports JSON, CSV, and raw XTF (eXtended Triton Format) binary navigation headers.
- **Auditing & Reporting:** Generates structured JSON, CSV survey exports, and scan history audit logs.
- **Interactive UI Dashboard:** React + Vite single-page dashboard with SVG waterfall overlays, sensitivity slider, and GIS Leaflet map.

## Stack

- **ML:** YOLOv8n (Ultralytics), trained on sonar dataset splits
- **Backend:** FastAPI + Uvicorn + OpenCV
- **Frontend:** React + TypeScript + Vite + Leaflet

## Crab-pot SSS dataset

The project can incorporate the gated `PINGEcosystem/sss-crab-pot-detection-ds` dataset as an additional high-confidence marine-object class. The source contains 6,674 side-scan sonar images with pixel-space bounding boxes and two labels: `Crab-Pot` and `Maybe-Crab-Pot`. This project intentionally keeps only `Crab-Pot` and maps it to YOLO class id `2`; ambiguous `Maybe-Crab-Pot` examples are excluded. The source dataset uses a Delaware sonar domain, so this is treated as an additional training domain rather than proof of performance on every survey system.

The dataset is gated on Hugging Face. Accept its access conditions first, then authenticate locally:

```powershell
pip install -U datasets pillow huggingface_hub
hf auth login
```

Import and convert the annotations:

```powershell
python ml/src/import_crab_pot_dataset.py
```

This writes the converted data under `Dataset/crab_pot/` and creates `Dataset/crab_pot/IMPORT_REPORT.json`. Downloaded images are ignored by Git and must not be committed.

Then audit and rebuild the combined YOLO splits:

```powershell
python ml/src/data_audit.py --dataset-root Dataset --output ml/data/audit_report.json
python ml/src/build_splits.py --dataset-root Dataset --output-dir ml/data/splits/processed --yaml ml/data/splits/dataset.yaml --preprocess
```

The resulting class map is:

```text
0 = debris_0
1 = debris_1
2 = crab_pot
```

Before a final SIH submission, evaluate both the original debris classes and the new crab-pot class separately; do not claim that crab-pot training data proves general marine-debris performance.

## Running

### Backend

```powershell
$env:PYTHONPATH = "backend;ml\src"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Check: `http://127.0.0.1:8000/health` or `http://127.0.0.1:8000/info`

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open: `http://localhost:5173`

### Tests

```powershell
$env:PYTHONPATH = "backend;ml\src"
python -m pytest backend/tests/ -v
```

## ML scripts

```bash
# Audit dataset
python ml/src/data_audit.py --dataset-root Dataset

# Build train/val/test splits with conservative sonar filtering
python ml/src/build_splits.py --dataset-root Dataset --output-dir ml/data/splits/processed --yaml ml/data/splits/dataset.yaml --preprocess

# Retrain model with sonar-optimized augmentations (150 epochs)
python ml/src/train_sih.py

# Export model for edge / AUV deployment (ONNX / TorchScript)
python ml/src/export_model.py --format all

# Run detection on all images
python ml/src/predict_visualize.py --weights best.pt --input Dataset --output ml/data/cleaned_predictions

# Evaluate model
python ml/src/evaluate_detector.py --weights best.pt --data ml/data/splits/dataset.yaml --split test
```

## Navigation metadata formats

Upload alongside the sonar image:
- **JSON:** `{"latitude": 15.0, "longitude": 73.0, "heading": 45.0, "pixel_size_m": 0.05}`
- **CSV:** Column headers `latitude,longitude,heading,pixel_size_m`
- **XTF:** Standard side-scan sonar binary survey file (`.xtf`) with embedded navigation headers

Without metadata, the map view reports "no geolocation" — coordinates are never guessed.
