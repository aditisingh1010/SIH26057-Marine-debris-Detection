import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getRun, imageUrl, reportUrl } from '../api'
import type { RunResult } from '../types'
import {
  formatConfidence,
  formatGeoStatus,
  getModelMode,
  getRiskBadgeClass,
  getRiskLevel,
} from '../utils'

export default function Result() {
  const { id } = useParams()
  const [run, setRun] = useState<RunResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setRun(null)
    setError(null)
    getRun(id)
      .then((data) => {
        if (cancelled) return
        setRun(data)
        setSelected(data.detections[0]?.id ?? null)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
    return () => {
      cancelled = true
    }
  }, [id])

  if (!id) return <p className="error">Missing run identifier.</p>
  if (error) return <div className="panel error"><strong>Error loading run:</strong> {error}</div>
  if (!run) {
    return (
      <div className="panel loading-state">
        <div className="step-spinner" style={{ width: 28, height: 28 }} />
        <p className="muted">Retrieving sonar survey telemetry and anomaly matrices…</p>
      </div>
    )
  }

  const detections = run.detections
  const locatedCount = detections.filter(
    (d) => d.geolocation.latitude != null && d.geolocation.longitude != null,
  ).length

  const modelInfo = getModelMode(run.inference_mode, run.model)
  const selectedDet = detections.find((d) => d.id === selected)

  return (
    <div className="result-page">
      <div className="result-header">
        <div>
          <div className="header-meta-row">
            <span className="kicker">Sonar Analysis Result</span>
            <span className={`mode-badge ${modelInfo.isMock ? 'mode-badge-mock' : 'mode-badge-real'}`}>
              <span className="mode-dot" />
              {modelInfo.badgeLabel}
            </span>
          </div>
          <h1 className="result-filename">{run.filename}</h1>
          <p className="lede">
            Inference performed on {run.image_width} × {run.image_height} px raw acoustic waterfall.
            Navigation telemetry:{' '}
            <strong className={run.metadata_attached ? 'text-teal' : 'text-amber'}>
              {run.metadata_attached ? 'Attached & Georeferenced' : 'No navigation metadata (Honest status: unavailable)'}
            </strong>.
          </p>
        </div>

        <div className="header-actions">
          <a
            className="btn btn-secondary"
            href={reportUrl(run.id, 'json')}
            download={`aquax_${run.id}_report.json`}
            title="Download full JSON dataset"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Download JSON
          </a>
          <a
            className="btn btn-secondary"
            href={reportUrl(run.id, 'csv')}
            download={`aquax_${run.id}_report.csv`}
            title="Download CSV table"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Download CSV
          </a>
          <Link className="btn btn-primary" to={`/runs/${run.id}/map`}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
              <line x1="8" y1="2" x2="8" y2="18" />
              <line x1="16" y1="6" x2="16" y2="22" />
            </svg>
            GIS Map View
          </Link>
        </div>
      </div>

      <div className="result-layout">
        {/* Sonar Stage Section */}
        <section className="panel sonar-shell">
          <div className="sonar-toolbar">
            <div className="sonar-toolbar-group">
              <span className="toolbar-label">FRAME DIMS:</span>
              <strong className="mono-text">{run.image_width} × {run.image_height} px</strong>
            </div>
            <div className="sonar-toolbar-group">
              <span className="toolbar-label">DETECTIONS:</span>
              <strong className="mono-text">{detections.length} total</strong>
            </div>
            {selectedDet && (
              <div className="sonar-toolbar-group selected-highlight">
                <span className="toolbar-label">FOCUS:</span>
                <strong className="text-teal">{selectedDet.class.replace(/_/g, ' ')} ({formatConfidence(selectedDet.confidence)})</strong>
              </div>
            )}
          </div>

          <div
            className="sonar-stage"
            style={{ aspectRatio: `${run.image_width} / ${run.image_height}` }}
          >
            <img src={imageUrl(run.id)} alt={run.filename} className="sonar-image" />
            
            <svg
              className="sonar-overlay-svg"
              viewBox={`0 0 ${run.image_width} ${run.image_height}`}
              preserveAspectRatio="none"
            >
              <defs>
                <filter id="high-glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#f43f5e" floodOpacity="0.8" />
                </filter>
                <filter id="med-glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#f59e0b" floodOpacity="0.8" />
                </filter>
                <filter id="low-glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#2dd4bf" floodOpacity="0.8" />
                </filter>
              </defs>

              {detections.map((d) => {
                const active = d.id === selected
                const risk = getRiskLevel(d)
                
                let strokeColor = '#2dd4bf'
                let fillColor = 'rgba(45, 212, 191, 0.15)'
                let filterUrl = 'url(#low-glow)'

                if (risk === 'High') {
                  strokeColor = '#f43f5e'
                  fillColor = active ? 'rgba(244, 63, 94, 0.28)' : 'rgba(244, 63, 94, 0.12)'
                  filterUrl = 'url(#high-glow)'
                } else if (risk === 'Medium') {
                  strokeColor = '#f59e0b'
                  fillColor = active ? 'rgba(245, 158, 11, 0.28)' : 'rgba(245, 158, 11, 0.12)'
                  filterUrl = 'url(#med-glow)'
                } else {
                  fillColor = active ? 'rgba(45, 212, 191, 0.28)' : 'rgba(45, 212, 191, 0.12)'
                }

                const strokeWidth = active
                  ? Math.max(3, Math.round(Math.min(run.image_width, run.image_height) / 100))
                  : Math.max(2, Math.round(Math.min(run.image_width, run.image_height) / 180))

                const labelY = Math.max(16, d.bbox.y - 6)

                return (
                  <g key={d.id} className={`bbox-group ${active ? 'active' : ''}`} onClick={() => setSelected(d.id)}>
                    <rect
                      x={d.bbox.x}
                      y={d.bbox.y}
                      width={d.bbox.width}
                      height={d.bbox.height}
                      fill={fillColor}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                      filter={active ? filterUrl : undefined}
                      className="bbox-rect"
                    />
                    {/* Bounding box label pill */}
                    <g transform={`translate(${d.bbox.x}, ${labelY})`}>
                      <rect
                        x="0"
                        y="-14"
                        width={Math.max(60, d.class.length * 8 + 38)}
                        height="18"
                        rx="3"
                        fill="rgba(5, 11, 18, 0.88)"
                        stroke={strokeColor}
                        strokeWidth="1"
                      />
                      <text
                        x="4"
                        y="-2"
                        fill="#ffffff"
                        fontSize="11"
                        fontFamily="var(--mono)"
                        fontWeight="600"
                      >
                        {d.class.replace(/_/g, ' ')} {formatConfidence(d.confidence)}
                      </text>
                    </g>
                  </g>
                )
              })}
            </svg>
          </div>
        </section>

        {/* Details & Cards Sidebar */}
        <aside className="panel result-sidebar">
          <div className="stat-row">
            <div className="stat">
              <span>Total Anomalies</span>
              <strong>{detections.length}</strong>
            </div>
            <div className="stat">
              <span>Geolocated</span>
              <strong className={locatedCount > 0 ? 'text-teal' : 'text-muted'}>{locatedCount}</strong>
            </div>
          </div>

          <div className="anomaly-header">
            <h2 style={{ margin: 0, fontSize: '1.15rem' }}>Acoustic Targets</h2>
            <span className="anomaly-count-pill">{detections.length} found</span>
          </div>

          <div className="detections-list">
            {detections.length === 0 ? (
              <div className="empty-detections-card">
                <div className="empty-sonar-radar">
                  <div className="empty-pulse" />
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10" />
                    <circle cx="12" cy="12" r="6" />
                    <circle cx="12" cy="12" r="2" />
                    <line x1="12" y1="2" x2="12" y2="22" />
                    <line x1="2" y1="12" x2="22" y2="12" />
                  </svg>
                </div>
                <h3>No Debris Detected</h3>
                <p className="muted">
                  The acoustic confidence threshold (0.25) did not yield any significant seafloor anomalies on this waterfall section.
                </p>
              </div>
            ) : (
              detections.map((d) => {
                const isSelected = d.id === selected
                const risk = getRiskLevel(d)
                const riskClass = getRiskBadgeClass(risk)
                const hasCoords = d.geolocation.latitude != null && d.geolocation.longitude != null

                return (
                  <article
                    key={d.id}
                    className={`detection-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelected(d.id)}
                  >
                    <div className="detection-card-top">
                      <div className="detection-title-group">
                        <span className="detection-id-tag">{d.id}</span>
                        <h3 className="detection-name">{d.class.replace(/_/g, ' ')}</h3>
                      </div>
                      <span className={riskClass}>
                        {risk} Risk
                      </span>
                    </div>

                    <div className="detection-metrics">
                      <div className="metric-item">
                        <span className="metric-label">Confidence:</span>
                        <strong className="metric-value">{formatConfidence(d.confidence)}</strong>
                      </div>
                      <div className="metric-item">
                        <span className="metric-label">BBox (px):</span>
                        <span className="metric-value mono-text">
                          {d.bbox.width} × {d.bbox.height} (at {d.bbox.x}, {d.bbox.y})
                        </span>
                      </div>
                    </div>

                    <div className="detection-geo">
                      <div className="geo-header">
                        <span className="geo-label">Geolocation Status:</span>
                        <span className={`geo-badge geo-${d.geolocation.status}`}>
                          {formatGeoStatus(d.geolocation.status)}
                        </span>
                      </div>
                      {hasCoords ? (
                        <div className="geo-coordinates mono-text">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                            <circle cx="12" cy="10" r="3" />
                          </svg>
                          <span>
                            {d.geolocation.latitude?.toFixed(6)}° N, {d.geolocation.longitude?.toFixed(6)}° E
                          </span>
                        </div>
                      ) : (
                        <span className="geo-none-text">Coordinates unattached</span>
                      )}
                    </div>
                  </article>
                )
              })
            )}
          </div>
        </aside>
      </div>
    </div>
  )
}
