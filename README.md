# SIH26057 — DeepSea SSS Sonar Workstation
### Autonomous Marine Debris Detection & Acoustic Telemetry Profiler
**Smart India Hackathon 2026 | Problem Statement: SIH26057**

---

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch YOLOv8](https://img.shields.io/badge/ML%20Engine-YOLOv8-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://ultralytics.com)
[![React TypeScript](https://img.shields.io/badge/Frontend-React%20%7C%20TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Build-Vite%205-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev/)
[![OpenCV](https://img.shields.io/badge/Vision-OpenCV%20%26%20NumPy-5C3EE8?style=flat-square&logo=opencv&logoColor=white)](https://opencv.org)
[![Acoustic Tests](https://img.shields.io/badge/Test%20Suite-39%20Passed-2EA44F?style=flat-square)](#automated-verification--test-suite)
[![Workstation UI](https://img.shields.io/badge/Interface-Hydrographic%20Dark%20%2F%20Light-1E222A?style=flat-square)](#workstation-architecture--design)

---

## Executive Overview

**DeepSea SSS Sonar Workstation** is an edge-deployable, hydrographic-grade marine survey system engineered for autonomous identification, acoustic shadow profiling, and geodetic positioning of anthropogenic marine debris from **Side-Scan Sonar (SSS)** waterfall scans.

Engineered to operate in high-reverberation, low-contrast benthic environments, the system replaces manual sonar waterfall inspection with an automated 4-phase hydroacoustic intelligence pipeline.

---

## How It Works

```
   +-------------------------------------------------------------------------------+
   |                      RAW SSS WATERFALL SONAR SCAN                             |
   |              Acoustic Backscatter Matrix + Survey Telemetry                   |
   +-------------------------------------------------------------------------------+
                                          |
                                          v
   +-------------------------------------------------------------------------------+
   | PHASE 1: CONSERVATIVE ACOUSTIC SIGNAL CONDITIONING                            |
   |   * Bilateral Speckle Reduction (Multiplicative noise attenuation)            |
   |   * Lateral Swath Gain Equalization (Outer beam falloff compensation)         |
   |   * Nadir Line Artifact Isolation & Water Column Masking                      |
   +-------------------------------------------------------------------------------+
                                          |
                                          v
   +-------------------------------------------------------------------------------+
   | PHASE 2: YOLOv8 ACOUSTIC ANOMALY INFERENCE & SUB-SWATH TILING                 |
   |   * Sliding-window sub-swath patch slicing with 20% spatial overlap           |
   |   * High-contrast acoustic highlight target classification                    |
   |   * Non-Maximum Suppression (NMS) with acoustic aspect-ratio weighting        |
   +-------------------------------------------------------------------------------+
                                          |
                                          v
   +-------------------------------------------------------------------------------+
   | PHASE 3: HYDROACOUSTIC SHADOW PROFILING & HEIGHT ESTIMATION                   |
   |   * Down-range acoustic shadow identification adjacent to bright highlights   |
   |   * Target vertical relief estimation via triangular ray-path geometry:       |
   |          Target Height: h_t = (Towfish Altitude * Shadow Length) /            |
   |                               (Slant Range + Shadow Length)                   |
   +-------------------------------------------------------------------------------+
                                          |
                                          v
   +-------------------------------------------------------------------------------+
   | PHASE 4: GEODETIC WGS84 POSITIONING & TELEMETRY COMPILATION                   |
   |   * Across-track slant-to-ground range projection                             |
   |   * Heading-vector rigid-body coordinate rotation                             |
   |   * Ellipsoidal geodetic offset: [Latitude, Longitude] WGS84                   |
   +-------------------------------------------------------------------------------+
                                          |
                                          v
   +-------------------------------------------------------------------------------+
   | HYDROGRAPHIC SURVEY AUDIT & CONTACT REGISTRY                                  |
   |   * Interactive Sonar Waterfall Workspace with dynamic sensitivity controls   |
   |   * Calibrated Sensor & Mission Telemetry Logging (Towfish, Swath, Altitude)  |
   |   * Deterministic export package: GeoJSON contacts, CSV registry, audit logs  |
   +-------------------------------------------------------------------------------+
```

---

### Phase 1: Conservative Acoustic Signal Conditioning
Side-scan sonar imagery differs fundamentally from optical imagery: it represents acoustic backscatter reflectivity across time (range) and towfish movement (along-track).
- **Multiplicative Speckle Suppression:** Uses edge-preserving bilateral filtering that attenuates high-frequency acoustic speckle while safeguarding micro-relief boundaries between hard debris and soft seabed substrates.
- **Swath Normalization:** Corrects for radial acoustic propagation loss and lateral beam spread attenuation without introducing synthetic artificial gradients.
- **Nadir / Altitude Awareness:** Protects against false alarms caused by the first bottom acoustic return and towfish water-column reflections.

### Phase 2: Neural Acoustic Object Detection
- **Model Architecture:** Custom fine-tuned Ultralytics YOLOv8 network optimized for single-channel acoustic backscatter signatures.
- **Sub-Swath Tiled Inference:** High-resolution sonar waterfalls (e.g., 2000x8000 pixels) are dynamically sliced into overlapping tiles (`tiled_inference.py`). This prevents downsampling degradation and guarantees that small debris (tires, lost gear, drums) remain sharp and detectable.
- **Dynamic Confidence Gating:** Hydrographers can modulate threshold sensitivity from `0.10` to `0.95` in real time without re-running preprocessing.

### Phase 3: Acoustic Shadow Physics & Relief Profiling
Unlike optical cameras, side-scan sonar relies on acoustic shadows (regions occluded from acoustic sound pings) to verify elevation above the seabed:

$$\text{Target Relief: } h_t = \frac{H_a \cdot L_s}{R_s + L_s}$$

*Where:*
- $h_t$: Estimated vertical relief / height of target above the seabed (meters).
- $H_a$: Towfish altitude above seafloor (meters).
- $L_s$: Acoustic shadow length measured along the acoustic beam (meters).
- $R_s$: Slant range from sonar transducer to target highlight (meters).

The system pairs acoustic highlight returns with contiguous down-range shadow pockets to validate targets and eliminate 2D bottom texture false positives.

### Phase 4: Deterministic Geodetic Telemetry Projection
The system strictly rejects fabricated or hallucinated coordinates:
- When real survey telemetry (`latitude`, `longitude`, `heading`, `pixel_size_m`, `towfish_altitude`) is supplied via JSON, CSV, or raw binary XTF headers, the engine executes a rigid-body coordinate rotation to project target pixel coordinates $[X, Y]$ into physical seabed offsets:

$$\Delta \text{East} = (r_{\text{across}} \cdot \cos\theta) + (d_{\text{along}} \cdot \sin\theta)$$

$$\Delta \text{North} = (-r_{\text{across}} \cdot \sin\theta) + (d_{\text{along}} \cdot \cos\theta)$$

- These physical meter offsets are converted to true WGS84 coordinates on the reference ellipsoid.
- If no survey telemetry is provided, coordinates are reported as **UNLINKED / NO GEOLOCATION** to preserve hydrographic data integrity.

---

## Target Classification Taxonomy

| Class ID | Target Category | Acoustic Signature | Shadow Characteristic | Typical Risk Level |
|:---|:---|:---|:---|:---|
| `marine-debris` | General Anthropogenic Debris | Sharp high-impedance specular highlight | Sharp, detached down-range acoustic shadow | Medium |
| `tire` | Rubber Tires & Vehicle Debris | Symmetrical toroidal / circular outline | Distinct crescent shadow pocket | Low |
| `drum` | Oil / Chemical Drums | High-amplitude cylindrical reflector | Rectangular sharp-boundary shadow | High (Ecological) |
| `ghost-net` | Abandoned Fishing Gear / Nets | Diffuse, tangled, non-uniform backscatter | Mottled, elongated trailing shadow | Critical (Entanglement) |
| `pipe` | Subsea Pipelines & Tubulars | Continuous linear high-reflectivity trace | Parallel continuous acoustic shadow line | High (Navigational) |
| `wreck` | Sunken Vessels & Airframes | Complex multi-point structural reflection | Extensive multi-faceted acoustic shadow | Navigational Hazard |

---

## Workstation Architecture & Design

Built with a dedicated hydrographic workstation aesthetic inspired by modern marine survey consoles:
- **Hydrographic Charcoal Theme:** Default near-black/charcoal surfaces (`#0a0b0e`), warm typography (`#f0f2f5`), subtle architectural borders (`#1a1d26`), and restrained signal indicators (`#c29b38`).
- **High-Visibility Lab Mode:** 1-click toggle for bright offshore deck or laboratory environments with high-contrast text and crisp border separation.
- **Horizontal Waterfall Viewer:** Preserves native wide acoustic sonar swathes without aggressive square cropping or artificial distortion.
- **Hydrographic Telemetry Panel:** Direct real-time sensor audit display:
  - Latitude, Longitude, Heading, Slant Range, Towfish Altitude, Swath Width, and Sound Velocity.
  - Formatted Target Contact Registry with precise geographic coordinates and risk tier indicators.
- **Export Formats:** One-click generation of structured survey datasets:
  - **GeoJSON Feature Collection:** Standard GIS/QGIS interoperability with bounded acoustic coordinates.
  - **CSV Target Registry:** Tabular survey logs formatted for hydrographic report generation.
  - **JSON Audit Stream:** Complete programmatic output containing bounding boxes, confidence tiers, and shadow geometries.

---

## Quick Start (Run in 2 Commands)

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- Git

### 1. Launch FastAPI Backend
```bash
# From repository root
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Interactive OpenAPI Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Launch Hydrographic Frontend
```bash
# In a second terminal
cd frontend
npm install
npm run dev
```
- **Sonar Workstation Web App:** [http://localhost:5173](http://localhost:5173)

### One-Click Launchers (Windows)
For convenience during offshore field trials or hackathon evaluations:
```powershell
# Native PowerShell
.\run_side_by_side.ps1

# Or Windows Batch
run_side_by_side.bat
```

---

## Telemetry & Navigation Ingestion Specifications

The workstation accepts survey navigation metadata alongside sonar imagery in three formats:

#### 1. JSON Telemetry Record (`telemetry.json`)
```json
{
  "latitude": 15.421850,
  "longitude": 73.784210,
  "heading": 42.5,
  "pixel_size_m": 0.05,
  "altitude_m": 12.4,
  "survey_name": "Goa Coastal Sonar Transect 04",
  "vessel_name": "RV Sagar Sampada",
  "sound_speed_mps": 1500.0
}
```

#### 2. CSV Navigational Track (`navigation.csv`)
```csv
latitude,longitude,heading,pixel_size_m,altitude_m,survey_name
15.421850,73.784210,42.5,0.05,12.4,"Goa Coastal Survey"
```

#### 3. XTF Binary Stream (`survey.xtf`)
Direct ingestion of **eXtended Triton Format (.xtf)** hydrographic sonar ping packets. Navigation and attitude packets (Packet Type 0 & Type 1) are parsed directly to extract real-time ping lat/lon, heading, towfish altitude, and slant-range parameters.

---

## Machine Learning Pipeline & Tooling

```bash
# 1. Audit dataset distribution, label balances, and bounding box ratios
python ml/src/data_audit.py --dataset-root Dataset

# 2. Build train/val/test splits with conservative bilateral sonar preprocessing
python ml/src/build_splits.py --dataset-root Dataset --output-dir ml/data/splits/processed --yaml ml/data/splits/dataset.yaml --preprocess

# 3. Train YOLOv8 with acoustic backscatter augmentations
python ml/src/train_sih.py

# 4. Evaluate detector on test split with Precision-Recall metrics
python ml/src/evaluate_detector.py --weights best.pt --data ml/data/splits/dataset.yaml --split test

# 5. Export for edge deployment on autonomous underwater vehicles (AUV / USV)
python ml/src/export_model.py --format onnx --weights best.pt
# Produces: best.onnx (FP32/FP16) & best.torchscript
```

---

## Automated Verification & Test Suite

The system includes a rigorous test suite validating API contracts, inference pipelines, telemetry parsers, and coordinate transformations:

```bash
# Execute backend test suite
python -m pytest backend/tests/ -v
```
```
============================= test session starts =============================
platform win32 -- Python 3.11.x, pytest-8.x.x
rootdir: C:\...\SIH26057-Marine-debris-Detection
collected 39 items

backend/tests/test_api.py ................................... [ 89%]
backend/tests/test_filtering.py ....                          [100%]
============================== 39 passed in 4.82s ==============================
```

```bash
# Verify frontend production build
cd frontend
npm run build
```

---

## Project Repository Structure

```
SIH26057-Marine-debris-Detection/
├── backend/                        # FastAPI Hydrographic Backend
│   ├── app/
│   │   ├── api/routes.py           # REST endpoints (/detect, /runs, /metadata, /export)
│   │   ├── services/
│   │   │   ├── inference.py        # YOLOv8 engine & sub-swath sliding window
│   │   │   ├── filtering.py        # Bilateral speckle filter & artifact cleaner
│   │   │   └── navigation.py       # Geodetic coordinate transforms & XTF parser
│   │   ├── schemas.py              # Pydantic hydrographic data contracts
│   │   └── main.py                 # FastAPI application factory & CORS configuration
│   └── tests/                      # Automated test suite (39 tests)
├── frontend/                       # React + TypeScript Workstation
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx       # Mission overview & quick access
│   │   │   ├── Detect.tsx          # Real-time sonar scan & telemetry upload
│   │   │   ├── Result.tsx          # Waterfall viewer & Telemetry / Contact panel
│   │   │   ├── Batch.tsx           # Multi-swath batch processing queue
│   │   │   └── History.tsx         # Historical survey audit log
│   │   ├── components/             # Reusable UI controls, telemetry cards & buttons
│   │   └── api.ts                  # Axios client for backend API
│   └── package.json
├── ml/                             # Machine Learning & Sonar Signal Processing
│   ├── src/
│   │   ├── tiled_inference.py      # High-res sub-swath window slicing
│   │   ├── train_sih.py            # YOLOv8 acoustic training loop
│   │   ├── evaluate_detector.py    # Metric calculation & confusion matrix
│   │   └── export_model.py         # ONNX / TorchScript edge export
│   └── data/                       # Split definitions & annotations
├── best.pt                         # Trained YOLOv8 acoustic weights
└── README.md                       # Comprehensive workstation documentation
```

---

## License & Acknowledgments

- Developed for the **Smart India Hackathon 2026** (Problem Statement SIH26057).
- Built for hydrographic researchers, coastal survey teams, and autonomous underwater vehicle (AUV) operations.
- References: IHO S-44 Standards for Hydrographic Surveys & NOAA Marine Debris Acoustic Characterization Guidelines.
