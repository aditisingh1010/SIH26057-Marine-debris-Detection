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
  const [showSuppressed, setShowSuppressed] = useState(false)

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
  const rawDetections = run.raw_detections ?? detections
  const suppressed = rawDetections.filter((d) => d.passed_filter === false)
  const filterStats = run.filter_stats ?? {
    total_raw: rawDetections.length,
    total_filtered: detections.length,
    noise_reduced_count: suppressed.length,
  }
  const locatedCount = detections.filter(
    (d) => d.geolocation.latitude != null && d.geolocation.longitude != null,
  ).length

  const modelInfo = getModelMode(run.inference_mode, run.model)
  const selectedDet = [...detections, ...suppressed].find((d) => d.id === selected)
  const modeLabel = (run.detection_mode ?? 'demo').toUpperCase()
  const thresholdPct = ((run.conf_threshold ?? 0.25) * 100).toFixed(0)

  return (
    <div className="result-page">
      <div className="result-header">
        <div>
          <div className="header-meta-row">
            <span className="kicker">Detection Result</span>
            <span className={`mode-badge ${modelInfo.isMock ? 'mode-badge-mock' : 'mode-badge-real'}`}>
              <span className="mode-dot" />
              {modelInfo.badgeLabel}
            </span>
            <span className="mode-badge mode-badge-op">
              {modeLabel} · {thresholdPct}% conf
            </span>
          </div>
          <h1 className="result-filename">{run.filename}</h1>
          <p className="lede">
            {run.image_width} × {run.image_height} px.{' '}
            Navigation:{' '}
            <strong className={locatedCount > 0 ? 'text-teal' : 'text-amber'}>
              {run.geolocation_note || (run.metadata_attached ? 'Metadata attached' : 'No metadata — geolocation unavailable')}
            </strong>
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
          {locatedCount > 0 ? (
          <Link className="btn btn-primary" to={`/runs/${run.id}/map`}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" />
              <line x1="8" y1="2" x2="8" y2="18" />
              <line x1="16" y1="6" x2="16" y2="22" />
            </svg>
            GIS Map View
          </Link>
          ) : (
            <Link className="btn btn-secondary" to={`/runs/${run.id}/map`}>
              Map unavailable
            </Link>
          )}
        </div>
      </div>

      <div className="result-layout">
        {/* Sonar Stage Section */}
        <section className="panel sonar-shell">
          <div className="sonar-toolbar">
            <div className="sonar-toolbar-group">
              <span className="toolbar-label">SIZE:</span>
              <strong className="mono-text">{run.image_width} × {run.image_height} px</strong>
            </div>
            <div className="sonar-toolbar-group">
              <span className="toolbar-label">KEPT:</span>
              <strong className="mono-text">{filterStats.total_filtered}</strong>
            </div>
            <div className="sonar-toolbar-group">
              <span className="toolbar-label">SUPPRESSED:</span>
              <strong className="mono-text">{filterStats.noise_reduced_count}</strong>
            </div>
            {selectedDet && (
              <div className="sonar-toolbar-group selected-highlight">
                <span className="toolbar-label">SELECTED:</span>
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
              preserveAspectRatio="xMidYMid meet"
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
              {showSuppressed && suppressed.map((d) => {
                const active = d.id === selected
                const strokeWidth = Math.max(2, Math.round(Math.min(run.image_width, run.image_height) / 180))
                return (
                  <g key={`sup-${d.id}`} className="bbox-group suppressed" onClick={() => setSelected(d.id)}>
                    <rect
                      x={d.bbox.x}
                      y={d.bbox.y}
                      width={d.bbox.width}
                      height={d.bbox.height}
                      fill={active ? 'rgba(148, 163, 184, 0.18)' : 'rgba(148, 163, 184, 0.06)'}
                      stroke="#94a3b8"
                      strokeWidth={strokeWidth}
                      strokeDasharray="6 4"
                    />
                  </g>
                )
              })}
              {/* Acoustic Shadow Zones (heuristic) */}
              {(run.shadow_zones ?? []).map((sz, i) => (
                <rect
                  key={`shadow-${i}`}
                  x={sz.x}
                  y={sz.y}
                  width={sz.width}
                  height={sz.height}
                  fill="rgba(99, 102, 241, 0.08)"
                  stroke="rgba(129, 140, 248, 0.5)"
                  strokeWidth={1.5}
                  strokeDasharray="4 3"
                  className="shadow-zone-rect"
                />
              ))}
            </svg>
          </div>

          <div className="result-legends">
            {filterStats.noise_reduced_count > 0 && (
              <label className="shadow-legend filter-toggle">
                <input
                  type="checkbox"
                  checked={showSuppressed}
                  onChange={(e) => setShowSuppressed(e.target.checked)}
                />
                Show suppressed candidates ({filterStats.noise_reduced_count}) — dashed boxes
              </label>
            )}
            {(run.shadow_zones ?? []).length > 0 && (
              <div className="shadow-legend">
                <span className="shadow-legend-swatch" />
                <span>Acoustic shadow candidate zones ({run.shadow_zones.length}) — experimental heuristic</span>
              </div>
            )}
          </div>
        </section>

        {/* Details & Cards Sidebar */}
        <aside className="panel result-sidebar">
          <div className="stat-row">
            <div className="stat">
              <span>Kept</span>
              <strong>{filterStats.total_filtered}</strong>
            </div>
            <div className="stat">
              <span>Suppressed</span>
              <strong className={filterStats.noise_reduced_count > 0 ? 'text-amber' : 'text-muted'}>
                {filterStats.noise_reduced_count}
              </strong>
            </div>
            <div className="stat">
              <span>Geolocated</span>
              <strong className={locatedCount > 0 ? 'text-teal' : 'text-muted'}>{locatedCount}</strong>
            </div>
          </div>

          <p className="filter-note">
            {modeLabel} mode at {thresholdPct}% confidence. Raw YOLO boxes: {filterStats.total_raw}.
            Geometry/confidence can drop a box. Acoustic-shadow overlap is review-only — it is never a silent delete.
          </p>

          {run.operator_briefing ? (
            <div className="briefing-card">
              <h2 style={{ margin: '0 0 8px', fontSize: '1.05rem' }}>Operator briefing</h2>
              <div className="stat-row">
                <div className="stat">
                  <span>Immediate</span>
                  <strong>{run.operator_briefing.immediate_count}</strong>
                </div>
                <div className="stat">
                  <span>Review queue</span>
                  <strong className={run.operator_briefing.review_queue_count > 0 ? 'text-amber' : ''}>
                    {run.operator_briefing.review_queue_count}
                  </strong>
                </div>
              </div>
              <p className="muted" style={{ fontSize: '0.78rem', margin: 0 }}>
                Demo would keep {run.operator_briefing.demo_kept}. Survey would keep {run.operator_briefing.survey_kept}
                {run.operator_briefing.extra_survey_candidates > 0
                  ? ` (${run.operator_briefing.extra_survey_candidates} extra for review).`
                  : '.'}
                {run.operator_briefing.shadow_overlap_count > 0
                  ? ` ${run.operator_briefing.shadow_overlap_count} kept box(es) overlap a shadow zone.`
                  : ''}
              </p>
            </div>
          ) : null}

          <div className="anomaly-header">
            <h2 style={{ margin: 0, fontSize: '1.15rem' }}>Detections</h2>
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
                <h3>No detections</h3>
                <p className="muted">
                  Nothing passed the {modeLabel.toLowerCase()} filter at {thresholdPct}% confidence
                  {suppressed.length > 0 ? ` (${suppressed.length} raw boxes were suppressed).` : '.'}
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
                    {d.review_priority === 'review' || d.acoustic_shadow_overlap ? (
                      <p className="muted" style={{ margin: '4px 0 0', fontSize: '0.75rem' }}>
                        Review queue{d.acoustic_shadow_overlap ? ' · shadow overlap' : ''}
                      </p>
                    ) : null}

                    <div className="detection-metrics">
                      <div className="metric-item">
                        <span className="metric-label">Confidence:</span>
                        <strong className="metric-value">{formatConfidence(d.confidence)}</strong>
                      </div>
                      <div className="metric-item">
                        <span className="metric-label">Risk score:</span>
                        <span className="metric-value mono-text">{d.risk_score.toFixed(2)}</span>
                      </div>
                      <div className="metric-item">
                        <span className="metric-label">BBox (px):</span>
                        <span className="metric-value mono-text">
                          {d.bbox.width} × {d.bbox.height} (at {d.bbox.x}, {d.bbox.y})
                        </span>
                      </div>
                      {d.width_m != null && d.height_m != null ? (
                        <div className="metric-item">
                          <span className="metric-label">Size (m):</span>
                          <span className="metric-value mono-text">
                            {d.width_m.toFixed(2)} × {d.height_m.toFixed(2)}
                          </span>
                        </div>
                      ) : null}
                      {d.estimated_height_m != null ? (
                        <div className="metric-item" style={{ gridColumn: 'span 2', background: 'rgba(99, 102, 241, 0.08)', padding: '4px 6px', borderRadius: '4px', border: '1px solid rgba(129, 140, 248, 0.25)' }}>
                          <span className="metric-label" style={{ color: '#a5b4fc' }}>Acoustic Shadow Height:</span>
                          <strong className="metric-value text-teal" style={{ marginLeft: '6px' }}>
                            ~{d.estimated_height_m} m
                          </strong>
                          {d.shadow_length_m != null && (
                            <span className="muted" style={{ fontSize: '0.72rem', marginLeft: '6px' }}>
                              (Shadow: {d.shadow_length_m}m)
                            </span>
                          )}
                        </div>
                      ) : null}
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
            {showSuppressed && suppressed.length > 0 ? (
              <>
                <h2 className="suppressed-heading">Suppressed candidates</h2>
                {suppressed.map((d) => (
                  <article
                    key={d.id}
                    className={`detection-card detection-card-suppressed ${d.id === selected ? 'selected' : ''}`}
                    onClick={() => setSelected(d.id)}
                  >
                    <div className="detection-card-top">
                      <div className="detection-title-group">
                        <span className="detection-id-tag">{d.id}</span>
                        <h3 className="detection-name">{d.class.replace(/_/g, ' ')}</h3>
                      </div>
                      <span className="risk-badge risk-low">Filtered</span>
                    </div>
                    <div className="detection-metrics">
                      <div className="metric-item">
                        <span className="metric-label">Confidence:</span>
                        <strong className="metric-value">{formatConfidence(d.confidence)}</strong>
                      </div>
                      <div className="metric-item">
                        <span className="metric-label">Reason:</span>
                        <span className="metric-value">{d.rejection_reason || 'Did not pass filter'}</span>
                      </div>
                    </div>
                  </article>
                ))}
              </>
            ) : null}
          </div>
        </aside>
      </div>
    </div>
  )
}
