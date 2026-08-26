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
  'Loading image...',
  'Preprocessing sonar image...',
  'Running YOLOv8n detection...',
  'Computing geolocation...',
  'Building report...',
]

export default function Upload() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [metadata, setMetadata] = useState<File | null>(null)
  const [confThreshold, setConfThreshold] = useState<number>(0.15)
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
      const run = await detect(file, metadata, confThreshold)
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
        <p className="kicker">SIH26057 · Side-scan sonar detection</p>
        <h1>Upload a sonar image to detect marine debris.</h1>
        <p className="lede">
          Runs YOLOv8n on side-scan sonar imagery. Coordinates are only shown when real navigation metadata is provided — never invented.
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
                  Optional Navigation Metadata (.json / .csv / .xtf with lat, lon coordinates)
                </label>
                <input
                  id="meta-file"
                  type="file"
                  accept=".json,.csv,.xtf"
                  className="metadata-input"
                  onChange={(e) => setMetadata(e.target.files?.[0] ?? null)}
                />
              </div>

              <div className="sensitivity-section" style={{ marginTop: '16px', marginBottom: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.85rem' }}>
                  <label htmlFor="conf-slider" style={{ fontWeight: 600, color: 'var(--text-1)' }}>
                    Confidence Threshold:
                  </label>
                  <span className="mono-text" style={{ color: 'var(--teal-2)', fontWeight: 700 }}>
                    {(confThreshold * 100).toFixed(0)}%
                  </span>
                </div>
                <input
                  id="conf-slider"
                  type="range"
                  min="0.05"
                  max="0.50"
                  step="0.05"
                  value={confThreshold}
                  onChange={(e) => setConfThreshold(parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: 'var(--teal)' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--muted)', marginTop: '2px' }}>
                  <span>5% (High sensitivity)</span>
                  <span>Default (15%)</span>
                  <span>50% (Strict)</span>
                </div>
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
          <p className="kicker">Pipeline</p>
          <h2 style={{ marginTop: 0 }}>How it works</h2>
          <ul className="feature-list">
            <li>
              <strong>Preprocessing:</strong> Conservative bilateral filter to reduce sonar speckle without destroying acoustic features.
            </li>
            <li>
              <strong>Detection:</strong> YOLOv8n trained on 140 labeled sonar images. Runs at 416×416.
            </li>
            <li>
              <strong>Geolocation:</strong> Pixel coordinates mapped to WGS84 only when survey metadata (lat, lon, heading, pixel size) is attached.
            </li>
            <li>
              <strong>Reports:</strong> JSON and CSV exports for every run.
            </li>
          </ul>

          <div className="strict-notice">
            <div className="notice-icon">⚓</div>
            <div>
              <strong>No fake coordinates</strong>
              <p>If no navigation metadata is supplied, geolocation is marked unavailable. No pins are invented.</p>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
