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

Our proposed system follows an end-to-end pipeline:

```text
Side-Scan Sonar Imagery
          ↓
     Preprocessing (Conservative Bilateral Filter + Lateral Line Attenuation)
          ↓
     AI Detection (YOLOv8 Debris Detector)
          ↓
  Confidence Scoring & Edge-Guarded Bounding Box Overlay
          ↓
  Analytical Visualization & Dashboard
```

---

## 🚀 Quickstart & Usage

### 1. Setup Environment

```bash
# Clone the repository
git clone https://github.com/<org>/SIH26057-Marine-debris-Detection.git
cd SIH26057-Marine-debris-Detection

# Create virtual environment and install dependencies
python -m venv .venv
# Activate virtual environment:
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r ml/requirements.txt
```

### 2. Run Data Audit
```bash
python ml/src/data_audit.py --dataset-root Dataset
```

### 3. Build YOLO Splits
```bash
python ml/src/build_splits.py --dataset-root Dataset --output-dir ml/data/splits/processed --yaml ml/data/splits/dataset.yaml --preprocess
```

### 4. Run Combined Preprocessing + Detection Pipeline
```bash
# Process all sonar images with trained model (best.pt)
python ml/src/predict_visualize.py --weights best.pt --input Dataset --output ml/data/cleaned_predictions
```

### 5. Evaluate Model
```bash
python ml/src/evaluate_detector.py --weights best.pt --data ml/data/splits/dataset.yaml --split test
```