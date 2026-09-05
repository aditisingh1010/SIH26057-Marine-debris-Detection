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

## Quick Start (Run in 2 Commands)

### 1. Start Backend
```bash
# Works on Windows, macOS, and Linux
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Docs & Interactive Swagger: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health`

### 2. Start Frontend
```bash
cd frontend
npm install
npm run dev
```
- Web Dashboard: `http://localhost:5173`

---

## Running Tests
```bash
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
