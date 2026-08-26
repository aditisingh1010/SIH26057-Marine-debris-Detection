# 🌊 SIH26057 — Marine Debris & Anomaly Detection

### AI-Powered Underwater Marine Debris Detection using Side-Scan Sonar Imagery

> Smart India Hackathon 2026 — Problem Statement SIH26057

📌 Overview

SIH26057 focuses on developing an AI-powered system for automated detection of underwater marine debris and anomalies using **Side-Scan Sonar (SSS) imagery**.

The system aims to assist marine survey and environmental monitoring teams by automatically identifying potential anthropogenic objects in sonar imagery and presenting the results through an intuitive analytical dashboard.


## 🎯 Problem

Manual analysis of side-scan sonar imagery can be time-consuming and challenging, particularly when dealing with:

- Large volumes of sonar imagery
- Speckle and acoustic noise
- Acoustic shadows
- Natural seafloor formations that resemble objects
- Difficulty identifying potential marine debris consistently

An automated and reliable detection system can help reduce manual effort and support faster identification of areas requiring further inspection.


## 💡 Our Approach

Our proposed system will follow an end-to-end pipeline:

```text
Side-Scan Sonar Imagery
          ↓
     Preprocessing
          ↓
    AI Detection /
     Segmentation
          ↓
 Confidence Scoring
          ↓
  Noise / False Positive
       Filtering
          ↓
 Object Classification
          ↓
   Geolocation & Analysis
          ↓
 Risk / Priority Assessment
          ↓
 Interactive Dashboard
```

## Run the SIH dashboard

API (from repo root). Prefer the repo-relative venv (this is what `main` already has after merge). This worktree may not contain `.venv`; if `.\.venv` is missing, use `C:\SIH\AquaX\.venv\Scripts\python.exe` instead.

```powershell
$env:PYTHONPATH = "backend;ml\src"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Web:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

Optional navigation metadata JSON example:

```json
{"latitude": 15.0, "longitude": 73.0}
```

If metadata is omitted, the map says location unavailable. Coordinates are never invented.
