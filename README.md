<div align="center">

# 🌊 Marine Debris Detection

### AI-Assisted Detection of Marine Debris in Side-Scan Sonar Imagery

**Smart India Hackathon 2026 · Problem Statement SIH26057**

[![YOLOv8](https://img.shields.io/badge/Model-YOLOv8n-00A3E0?style=flat-square)](#)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](#)
[![React](https://img.shields.io/badge/Frontend-React%20%2B%20Vite-61DAFB?style=flat-square&logo=react&logoColor=black)](#)
[![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square)](#)

*Detecting seafloor debris from acoustic returns — with honest geolocation, never guessed coordinates.*

</div>

---

## 🧭 Overview

This system runs a **YOLOv8n** object detector over side-scan sonar (SSS) waterfall images to flag potential debris on the seafloor. For every detection it returns a bounding box, confidence score, risk classification, and — where acoustic shadows suggest a raised object — a shadow-based heuristic flag.

> **Geolocation integrity:** Coordinates are only ever shown when real survey navigation metadata (`lat`, `lon`, `heading`, `pixel_size_m`) is attached to the scan. No metadata means no map pin — never an invented position.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🎯 **Sonar Object Detection** | YOLOv8n detector calibrated for acoustic anomalies — marine debris and seabed objects |
| 🧹 **Conservative Preprocessing** | Bilateral speckle filtering + outer-swath lateral line artifact attenuation |
| 🌓 **Acoustic Shadow Analysis** | Heuristic detection of candidate shadow zones adjacent to acoustic highlight returns |
| 📦 **Edge / AUV Deployment** | Export pipeline to ONNX (`best.onnx`) and TorchScript for onboard drone inference |
| 🗺️ **Navigation Ingestion** | Supports JSON, CSV, and raw XTF (eXtended Triton Format) binary nav headers |
| 📊 **Auditing & Reporting** | Structured JSON/CSV survey exports plus scan history audit logs |
| 🖥️ **Interactive Dashboard** | React + Vite SPA with SVG waterfall overlays, sensitivity slider, and Leaflet GIS map |

---

## 🏗️ Stack

```
ML         YOLOv8n (Ultralytics) — trained on sonar dataset splits
Backend    FastAPI · Uvicorn · OpenCV
Frontend   React · TypeScript · Vite · Leaflet
```

---

## 🚀 Quick Start

### 1 · Start the Backend

```bash
# Works on Windows, macOS, and Linux
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

| Resource | URL |
|---|---|
| Swagger / API Docs | `http://127.0.0.1:8000/docs` |
| Health Check | `http://127.0.0.1:8000/health` |

### 2 · Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

| Resource | URL |
|---|---|
| Web Dashboard | `http://localhost:5173` |

---

## 🧪 Running Tests

```bash
python -m pytest backend/tests/ -v
```

---

## 🔬 ML Pipeline

```bash
# 1. Audit dataset quality and class balance
python ml/src/data_audit.py --dataset-root Dataset

# 2. Build train/val/test splits with conservative sonar filtering
python ml/src/build_splits.py \
  --dataset-root Dataset \
  --output-dir ml/data/splits/processed \
  --yaml ml/data/splits/dataset.yaml \
  --preprocess

# 3. Retrain with sonar-optimized augmentations (150 epochs)
python ml/src/train_sih.py

# 4. Export for edge / AUV deployment (ONNX + TorchScript)
python ml/src/export_model.py --format all

# 5. Run detection across the full dataset
python ml/src/predict_visualize.py \
  --weights best.pt \
  --input Dataset \
  --output ml/data/cleaned_predictions

# 6. Evaluate against the held-out test split
python ml/src/evaluate_detector.py \
  --weights best.pt \
  --data ml/data/splits/dataset.yaml \
  --split test
```

---

## 🧭 Navigation Metadata Formats

Upload one of these alongside the sonar image to enable geolocation:

**JSON**
```json
{
  "latitude": 15.0,
  "longitude": 73.0,
  "heading": 45.0,
  "pixel_size_m": 0.05
}
```

**CSV**
```
latitude,longitude,heading,pixel_size_m
15.0,73.0,45.0,0.05
```

**XTF**
Standard side-scan sonar binary survey file (`.xtf`) with embedded navigation headers — parsed automatically.

> ⚠️ **No metadata uploaded?** The map view reports **"no geolocation"**. Coordinates are never guessed or interpolated.

---

<div align="center">

*Built for SIH26057 · Marine Debris Detection*

</div>
