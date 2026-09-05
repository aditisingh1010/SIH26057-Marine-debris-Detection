import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { detect, getQuality } from '../api'
import type { ModelQuality } from '../types'

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
  'Running detection...',
  'Filtering false positives...',
  'Computing geolocation...',
  'Building report...',
]

const MODE_PRESETS = {
  demo: {
    id: 'demo' as const,
    title: 'Demo',
    conf: 0.25,
    blurb: 'Higher precision. Best for live judging — fewer false boxes.',
  },
  survey: {
    id: 'survey' as const,
    title: 'Survey',
    conf: 0.10,
    blurb: 'Higher recall. Keeps weaker candidates so operators can review them.',
  },
  custom: {
    id: 'custom' as const,
    title: 'Custom',
    conf: 0.15,
    blurb: 'Set the confidence cutoff yourself.',
  },
}

export default function Upload() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [metadata, setMetadata] = useState<File | null>(null)
  const [quality, setQuality] = useState<ModelQuality | null>(null)
  const [detectionMode, setDetectionMode] = useState<'demo' | 'survey' | 'custom'>('demo')
  const [confThreshold, setConfThreshold] = useState<number>(MODE_PRESETS.demo.conf)
  const [busy, setBusy] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)

  useEffect(() => {
    let cancelled = false
    getQuality()
      .then((data) => {
        if (!cancelled) setQuality(data)
      })
      .catch(() => {
        if (!cancelled) setQuality(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

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

  async function loadSampleImage(path: string, filename: string) {
    try {
      setError(null)
      const res = await fetch(path)
      const blob = await res.blob()
      const sampleFile = new File([blob], filename, { type: 'image/jpeg' })
      setFile(sampleFile)
    } catch (err) {
      setError(`Failed to load sample image: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  async function onRun() {
    if (!file || busy) return
    setBusy(true)
    setError(null)
    try {
      const run = await detect(file, metadata, confThreshold, detectionMode)
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
          Detect first, then brief a cleanup operator: keep/suppress counts, shadow-overlap review flags,
          and Demo vs Survey candidate counts. Coordinates appear only when navigation metadata is attached.
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
                <div style={{ textAlign: 'center', marginTop: '0.75rem' }}>
                  <p className="muted empty-file-text" style={{ marginBottom: '0.5rem' }}>
                    No sonar imagery selected yet.
                  </p>
                  <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      className="btn-subtle"
                      style={{ fontSize: '0.82rem', padding: '0.35rem 0.75rem', cursor: 'pointer' }}
                      onClick={() => loadSampleImage('/samples/sample_pipeline.jpg', 'pipeline_auv_sonar.jpg')}
                    >
                      🛢️ Subsea Pipeline (REMARO)
                    </button>
                    <button
                      type="button"
                      className="btn-subtle"
                      style={{ fontSize: '0.82rem', padding: '0.35rem 0.75rem', cursor: 'pointer' }}
                      onClick={() => loadSampleImage('/samples/sample_ghost_pot.jpg', 'ghost_pot_survey.jpg')}
                    >
                      🎣 Ghost Net Pot
                    </button>
                    <button
                      type="button"
                      className="btn-subtle"
                      style={{ fontSize: '0.82rem', padding: '0.35rem 0.75rem', cursor: 'pointer' }}
                      onClick={() => loadSampleImage('/samples/sample_shipwreck.jpg', 'shipwreck_auv_sonar.jpg')}
                    >
                      🚢 Shipwreck
                    </button>
                    <button
                      type="button"
                      className="btn-subtle"
                      style={{ fontSize: '0.82rem', padding: '0.35rem 0.75rem', cursor: 'pointer' }}
                      onClick={() => loadSampleImage('/samples/sample_debris.jpg', 'seafloor_debris.jpg')}
                    >
                      🪨 Seafloor Debris
                    </button>
                    <button
                      type="button"
                      className="btn-subtle"
                      style={{ fontSize: '0.82rem', padding: '0.35rem 0.75rem', cursor: 'pointer' }}
                      onClick={() => loadSampleImage('/samples/sample_human.jpg', 'human_sar_sonar.jpg')}
                    >
                      🧑 Human (SAR Target)
                    </button>
                  </div>
                </div>
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

              <div className="mode-picker" role="radiogroup" aria-label="Detection operating mode">
                <div className="mode-picker-header">
                  <span className="metadata-label" style={{ margin: 0 }}>
                    Operating mode
                  </span>
                  <span className="mono-text text-teal">
                    {(confThreshold * 100).toFixed(0)}% confidence
                  </span>
                </div>
                <div className="mode-picker-grid">
                  {(Object.values(MODE_PRESETS)).map((preset) => (
                    <button
                      key={preset.id}
                      type="button"
                      className={`mode-card ${detectionMode === preset.id ? 'mode-card-active' : ''}`}
                      onClick={() => {
                        setDetectionMode(preset.id)
                        setConfThreshold(preset.conf)
                      }}
                    >
                      <strong>{preset.title}</strong>
                      <span>{preset.blurb}</span>
                    </button>
                  ))}
                </div>
              </div>

              {detectionMode === 'custom' ? (
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
                  <span>Custom</span>
                  <span>50% (Strict)</span>
                </div>
              </div>
              ) : (
                <p className="muted mode-hint">
                  {detectionMode === 'demo'
                    ? 'Demo locks the cutoff at 25% so overlays stay conservative for presentation.'
                    : 'Survey locks the cutoff at 10% so more debris-like shapes survive filtering.'}
                </p>
              )}

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
                  Run Detection
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
              <strong>Operator briefing:</strong> Shadow overlap is flagged for human review, not auto-deleted. Survey mode lists extra candidates Demo would hide.
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

      {quality ? (
        <section className="panel quality-panel" aria-label="Dataset and model quality">
          <div className="quality-header">
            <div>
              <p className="kicker">Model Evidence</p>
              <h2>Dataset & Accuracy Snapshot</h2>
            </div>
            <span className="quality-chip">
              {quality.quality_available ? 'Evaluated' : 'Live facts'} · {quality.task.toUpperCase()}
            </span>
          </div>

          <div className="quality-grid">
            <div className="quality-card quality-card-primary">
              <span>mAP50</span>
              <strong>
                {quality.quality_available
                  ? `${(quality.pr_sweep_metrics.mAP50 * 100).toFixed(1)}%`
                  : 'n/a'}
              </strong>
              <small>{quality.evaluation_split}</small>
            </div>
            <div className="quality-card">
              <span>Precision</span>
              <strong>
                {quality.quality_available
                  ? `${(quality.primary_metrics.precision * 100).toFixed(1)}%`
                  : 'n/a'}
              </strong>
              <small>
                {quality.quality_available
                  ? `at ${(quality.primary_metrics.confidence_threshold * 100).toFixed(0)}% confidence`
                  : 'no snapshot for this checkpoint'}
              </small>
            </div>
            <div className="quality-card">
              <span>Recall</span>
              <strong>
                {quality.quality_available
                  ? `${(quality.primary_metrics.recall * 100).toFixed(1)}%`
                  : 'n/a'}
              </strong>
              <small>{quality.metrics_source === 'snapshot' ? 'from validation snapshot' : 'evaluate after training'}</small>
            </div>
            <div className="quality-card">
              <span>CPU Speed</span>
              <strong>
                {quality.quality_available
                  ? `${quality.primary_metrics.inference_ms_cpu.toFixed(1)} ms`
                  : 'n/a'}
              </strong>
              <small>per image validation run</small>
            </div>
          </div>

          <div className="quality-detail-grid">
            <div className="quality-detail">
              <h3>Dataset</h3>
              <div className="quality-stat-row">
                <span>Total images</span>
                <strong>{quality.dataset.total_images}</strong>
              </div>
              <div className="quality-stat-row">
                <span>Labeled images</span>
                <strong>{quality.dataset.labeled_images}</strong>
              </div>
              <div className="quality-stat-row">
                <span>Annotations</span>
                <strong>{quality.dataset.total_annotations}</strong>
              </div>
              <div className="quality-stat-row">
                <span>Label issues</span>
                <strong className={quality.dataset.label_issues > 0 ? 'text-amber' : 'text-teal'}>
                  {quality.dataset.label_issues}
                </strong>
              </div>
            </div>

            <div className="quality-detail">
              <h3>Scope</h3>
              <div className="class-pill-row">
                {quality.classes.length > 0 ? (
                  quality.classes.map((cls) => (
                    <span className="class-pill" key={cls}>{cls}</span>
                  ))
                ) : (
                  <span className="muted">No class names until a model is loaded.</span>
                )}
              </div>
              <p className="quality-note">{quality.dataset.summary}</p>
              <p className="quality-note">
                ONNX export:{' '}
                <strong className={quality.onnx_available ? 'text-teal' : 'text-amber'}>
                  {quality.onnx_available ? 'available' : 'not found'}
                </strong>
              </p>
            </div>

            <div className="quality-detail">
              <h3>Next Improvements</h3>
              <ul className="quality-list">
                {quality.next_improvements.slice(0, 3).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  )
}
