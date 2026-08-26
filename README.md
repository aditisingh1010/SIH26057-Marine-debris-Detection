# SIH26057 — Marine Debris Detection

AI-assisted detection of marine debris in side-scan sonar (SSS) imagery.
Smart India Hackathon 2026 — Problem Statement SIH26057.

## What it does

Runs a YOLOv8n object detector on side-scan sonar waterfall images to identify potential debris on the seafloor. Outputs bounding boxes, confidence scores, risk classification, and a geolocation estimate when navigation metadata is provided.

Coordinates are only shown when real survey metadata (lat, lon, heading, pixel_size_m) is attached. They are never invented.

## Stack

- **ML:** YOLOv8n (Ultralytics), trained on 140 labeled sonar images
- **Backend:** FastAPI + Uvicorn
- **Frontend:** React + TypeScript + Vite + Leaflet

## Running

### Backend

```powershell
# From repo root
$env:PYTHONPATH = "backend;ml\src"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Check: `http://127.0.0.1:8000/health`

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open: `http://localhost:5173`

### Tests

```powershell
python -m pytest backend/tests/ -v
```

## ML scripts

```bash
# Audit dataset
python ml/src/data_audit.py --dataset-root Dataset

# Build train/val/test splits
python ml/src/build_splits.py --dataset-root Dataset --output-dir ml/data/splits/processed --yaml ml/data/splits/dataset.yaml --preprocess

# Run detection on all images
python ml/src/predict_visualize.py --weights best.pt --input Dataset --output ml/data/cleaned_predictions

# Evaluate model
python ml/src/evaluate_detector.py --weights best.pt --data ml/data/splits/dataset.yaml --split test
```

## Optional navigation metadata

Pass a JSON file alongside the image upload:

```json
{"latitude": 15.0, "longitude": 73.0, "heading": 45.0, "pixel_size_m": 0.05}
```

Without this file, the map view shows "no geolocation" — no coordinates are guessed.
