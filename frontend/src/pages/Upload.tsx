import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { detect } from '../api'

function fileFormat(file: File): string {
  const ext = file.name.split('.').pop()
  if (ext && ext !== file.name) return ext.toUpperCase()
  return file.type || 'unknown'
}

function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const PROCESSING_STEPS = [
  'Ingesting acoustic raw payload & navigation headers...',
  'Applying bilateral sonar despeckling filter...',
  'Executing YOLOv8n marine debris detector (416×416)...',
  'Computing seafloor ray-traced geolocation coordinates...',
  'Assembling GIS survey report & artifact JSON/CSV...',
]

export default function Upload() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [metadata, setMetadata] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)

  useEffect(() => {
    if (!busy) {
      setStepIndex(0)
      return
    }

    const interval = setInterval(() => {
      setStepIndex((prev) => (prev + 1) % PROCESSING_STEPS.length)
    }, 1200)

    return () => clearInterval(interval)
  }, [busy])

  async function onRun() {
    if (!file || busy) return
    setBusy(true)
    setError(null)
    try {
      const run = await detect(file, metadata)
      navigate(`/runs/${run.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0])
    }
  }

  return (
    <div>
      <div className="hero">
        <p className="kicker">SIH26057 · Side-scan sonar AI Intelligence</p>
        <h1>Ingest seafloor acoustic imagery. Detect debris with deep precision.</h1>
        <p className="lede">
          AquaX executes custom-trained YOLOv8n models directly on side-scan sonar waterfall data.
          Geographic coordinates are strictly computed from authentic navigation metadata — never fabricated or hallucinated.
        </p>
      </div>

      <div className="grid-2">
        <section className="panel upload-panel">
          {busy ? (
            <div className="processing-container">
              <div className="sonar-ping-wrapper">
                <div className="sonar-ring ring-1" />
                <div className="sonar-ring ring-2" />
                <div className="sonar-ring ring-3" />
                <div className="sonar-sweep" />
                <div className="sonar-center-dot" />
              </div>

              <div className="processing-info">
                <span className="processing-tag">Processing Sonar Strip</span>
                <h3 className="processing-title">Analyzing Seafloor Anomalies</h3>
                <p className="processing-current-step">
                  <span className="step-spinner" />
                  {PROCESSING_STEPS[stepIndex]}
                </p>

                <div className="step-indicators">
                  {PROCESSING_STEPS.map((step, idx) => (
                    <div
                      key={step}
                      className={`step-dot ${idx === stepIndex ? 'active' : idx < stepIndex ? 'done' : ''}`}
                      title={step}
                    />
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              <label
                className={`drop ${dragOver ? 'drop-active' : ''}`}
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
              >
                <input
                  type="file"
                  accept=".png,.jpg,.jpeg,.tif,.tiff,.bmp"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
                <div className="drop-icon">
                  <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <strong>{file ? 'Replace sonar image' : 'Drop or select side-scan sonar image'}</strong>
                <span className="muted">Supports PNG, JPEG, TIFF, BMP sonar waterfall strips</span>
              </label>

              {file ? (
                <div className="meta-grid">
                  <div>
                    <span>Filename</span>
                    <strong className="mono-text">{file.name}</strong>
                  </div>
                  <div>
                    <span>Format</span>
                    <strong>{fileFormat(file)}</strong>
                  </div>
                  <div>
                    <span>Size</span>
                    <strong>{fileSize(file.size)}</strong>
                  </div>
                  <div>
                    <span>Navigation Metadata</span>
                    <strong className={metadata ? 'text-teal' : 'text-muted'}>
                      {metadata ? metadata.name : 'Not attached (Status: unavailable)'}
                    </strong>
                  </div>
                </div>
              ) : (
                <p className="muted empty-file-text">No sonar imagery selected yet.</p>
              )}

              <div className="metadata-section">
                <label className="metadata-label" htmlFor="meta-file">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  Optional Navigation Metadata (.json / .csv with lat, lon coordinates)
                </label>
                <input
                  id="meta-file"
                  type="file"
                  accept=".json,.csv"
                  className="metadata-input"
                  onChange={(e) => setMetadata(e.target.files?.[0] ?? null)}
                />
              </div>

              <div className="submit-section">
                <button
                  type="button"
                  className="btn btn-primary run-btn"
                  onClick={onRun}
                  disabled={!file || busy}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polygon points="5 3 19 12 5 21 5 3" />
                  </svg>
                  Run YOLOv8n Detection
                </button>
              </div>

              {error ? (
                <div className="error">
                  <strong>Detection Error:</strong> {error}
                </div>
              ) : null}
            </>
          )}
        </section>

        <aside className="panel info-panel">
          <p className="kicker">Pipeline Specifications</p>
          <h2 style={{ marginTop: 0 }}>High-Fidelity Marine Debris Analysis</h2>
          <ul className="feature-list">
            <li>
              <strong>Bilateral Acoustic Filtering:</strong> Preserves acoustic shadows while suppressing high-frequency water-column noise.
            </li>
            <li>
              <strong>Real Detector (YOLOv8n):</strong> Deep feature extraction on 416×416 spatial resolution specifically calibrated for side-scan artifacts.
            </li>
            <li>
              <strong>Ray-traced Geolocation:</strong> Translates pixel coordinates (x, y) into geodetic WGS84 coordinates when survey telemetry is provided.
            </li>
            <li>
              <strong>Complete Audit Reports:</strong> Generates immediate JSON machine-readable structures and CSV tabular datasets.
            </li>
          </ul>

          <div className="strict-notice">
            <div className="notice-icon">⚓</div>
            <div>
              <strong>Strict Data Honesty Policy</strong>
              <p>AquaX will never plot synthetic pins or guess coordinates. If no navigation metadata is supplied, geolocation is explicitly marked as unavailable.</p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
