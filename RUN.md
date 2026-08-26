# 🌊 AquaX (SIH26057) — Run & Operation Guide

**Automated Marine Debris & Acoustic Anomaly Detection for Side-Scan Sonar (SSS)**  
*Smart India Hackathon 2026 — Problem Statement SIH26057*

This document provides step-by-step instructions to set up, run, and verify the AquaX marine debris detection platform on **Windows** (PowerShell / Command Prompt).

---

## 📋 System Prerequisites

- **Operating System:** Windows 10 / 11 (64-bit)
- **Python:** Python 3.10 or 3.11 ([python.org](https://www.python.org/downloads/))
- **Node.js:** Node.js 18.x or 20.x LTS ([nodejs.org](https://nodejs.org/))
- **Git:** Git for Windows ([gitforwindows.org](https://gitforwindows.org/))
- **Shell:** Windows PowerShell or Command Prompt

---

## 🛠️ Step 1: Environment Setup

Clone the repository and prepare both Python and Node.js dependencies.

```powershell
# Navigate to your workspace directory
cd C:\SIH\SIH26057-Marine-debris-Detection

# 1. Create a Python virtual environment
python -m venv .venv

# 2. Activate the virtual environment
# In PowerShell:
.\.venv\Scripts\Activate.ps1
# (If execution policy prevents activation, run: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)

# In Command Prompt (cmd.exe):
# .\.venv\Scripts\activate.bat

# 3. Upgrade pip and install Python dependencies
python -m pip install --upgrade pip
pip install -r ml/requirements.txt
pip install -r backend/requirements.txt

# 4. Install Frontend dependencies
cd frontend
npm install
cd ..
```

---

## 🚀 Step 2: Running Backend API Server

The backend runs on FastAPI with Uvicorn, serving the YOLOv8 marine debris inference engine and geolocation ray-tracing services.

In a PowerShell terminal (with `.venv` activated):

```powershell
# Set PYTHONPATH so backend and ML modules are discoverable
$env:PYTHONPATH = "backend;ml\src"

# Launch the FastAPI development server on port 8000
uvicorn app.main:app --reload --port 8000
```

> **Alternative command** (direct executable):
> ```powershell
> .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
> ```

### Verification:
- Open your browser to [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) to confirm API status.
- Interactive OpenAPI documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

## 💻 Step 3: Running Frontend Dev Server

The frontend is a React + TypeScript single-page application built on Vite and Leaflet GIS.

Open a second PowerShell terminal:

```powershell
cd C:\SIH\SIH26057-Marine-debris-Detection\frontend

# Start Vite development server
npm run dev
```

### Accessing the Dashboard:
- Open **[http://localhost:5173](http://localhost:5173)** in Google Chrome, Edge, or Firefox.
- The top-right badge will show **`MODEL READY`** when connected to the backend.

---

## 🔬 Step 4: End-to-End Testing Instructions

Follow this workflow to test detection, telemetry, risk assessment, and reporting:

### 4.1 Ingest a Sonar Image
1. Open the web interface at `http://localhost:5173`.
2. Drag and drop or browse for a sonar frame from the dataset:
   - `Dataset/2010/0061_2010.jpg` (Contains annotated debris)
   - `Dataset/2010/0208_2010.jpg`
   - `Dataset/2018/0021_2018.jpg`
   - `Dataset/2018/0080_2018.jpg`
   - `Dataset/2018/0442_2018.jpg`

### 4.2 (Optional) Attach Navigation Telemetry
To test georeferencing and GIS map rendering:
- Create a simple navigation metadata file (e.g. `nav.json`):
  ```json
  {
    "latitude": 15.2993,
    "longitude": 73.9114,
    "pixel_size_m": 0.05,
    "heading": 45.0
  }
  ```
- Upload `nav.json` in the **Optional JSON/CSV navigation metadata** field.
- *Note:* If metadata is omitted, AquaX will **never** invent fake coordinates. The location status will display `Unavailable (No metadata)`.

### 4.3 Run Detection & Inspect Results
1. Click **Run detection**.
2. The dashboard navigates to the result viewer (`/runs/<run_id>`):
   - **Acoustic Waterfall View:** Interactive bounding boxes overlaid on the sonar waterfall with confidence scores and risk indicators.
   - **Risk Level & Metrics:** High/Medium/Low risk classifications based on detection confidence and spatial anomaly dimensions.
   - **Telemetry:** Georeferenced coordinates (lat/lon) computed from survey heading and pixel pitch.

### 4.4 Download Survey Reports
- Click **Download JSON** for structured telemetry and detections (`report.json`).
- Click **Download CSV** for tabular export (`report.csv`) containing `id`, `class`, `confidence`, `risk_level`, `risk_score`, `x`, `y`, `width`, `height`, `latitude`, `longitude`, `geolocation_status`.

### 4.5 View GIS Map
- If navigation metadata was provided, click **GIS Map View** to view geolocated debris pins plotted on OpenStreetMap with popup telemetry.

---

## 🧪 Automated Testing

Run the full pytest suite from the repository root:

```powershell
$env:PYTHONPATH = "backend;ml\src"
pytest backend/tests -v
```

All tests for API endpoints, schemas, CORS, georeferencing, and fallback inference will execute and validate type safety and data integrity.
