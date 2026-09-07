import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getRun, imageUrl, reportUrl } from '../api'
import type { RunResult } from '../types'
import { formatConfidence, formatGeoStatus, getModelMode } from '../utils'

export default function Result() {
  const { id } = useParams()
  const location = useLocation()
  const cached = (location.state as { run?: RunResult } | null)?.run
  const [run, setRun] = useState<RunResult | null>(
    cached && cached.id === id ? cached : null,
  )
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(
    cached && cached.id === id ? cached.detections?.[0]?.id ?? null : null,
  )
  const [showSuppressed, setShowSuppressed] = useState(false)
  const [showShadows, setShowShadows] = useState(false)
  const [hovered, setHovered] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    if (cached && cached.id === id) return
    let cancelled = false
    setRun(null)
    setError(null)
    getRun(id)
      .then((data) => {
        if (cancelled) return
        setRun(data)
        setSelected(data.detections?.[0]?.id ?? null)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
    return () => {
      cancelled = true
    }
  }, [id, cached])

  if (!id) return <p className="error">Missing run identifier.</p>
  if (error) return <div className="panel error"><strong>Error loading run:</strong> {error}</div>
  if (!run) {
    return (
      <div className="panel loading-state">
        <div className="step-spinner" style={{ width: 28, height: 28 }} />
        <p className="muted">Loading result…</p>
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
          <h1 className="result-filename">{run.filename}</h1>
          <p className="lede">
            {modeLabel.toLowerCase()} · {thresholdPct}% · {run.image_width}×{run.image_height}
            {modelInfo.isMock ? ' · mock' : ''}
            {' · '}
            {locatedCount > 0 ? `${locatedCount} geolocated` : 'no location'}
          </p>
        </div>

        <div className="header-actions">
          <Link className="btn btn-primary" to={`/runs/${run.id}/list`} state={{ run }}>
            Full list
          </Link>
          <a className="btn btn-secondary" href={reportUrl(run.id, 'json')} download={`aquax_${run.id}_report.json`}>
            JSON
          </a>
          <a className="btn btn-secondary" href={reportUrl(run.id, 'csv')} download={`aquax_${run.id}_report.csv`}>
            CSV
          </a>
          <Link className="btn btn-secondary" to={locatedCount > 0 ? `/map?run=${run.id}` : '/map'}>
            Map
          </Link>
        </div>
      </div>

      <div className="result-layout">
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
              {detections.map((d, i) => {
                const active = d.id === selected || d.id === hovered
                const stroke = active ? '#fff6ea' : '#e8dcc8'
                const strokeWidth = active
                  ? Math.max(3, Math.round(Math.min(run.image_width, run.image_height) / 120))
                  : Math.max(2, Math.round(Math.min(run.image_width, run.image_height) / 200))
                const fontPx = Math.max(11, Math.round(Math.min(run.image_width, run.image_height) / 28))
                const label = `${i + 1}  ${d.class.replace(/_/g, ' ')}  ${formatConfidence(d.confidence)}`
                const labelW = Math.max(72, label.length * fontPx * 0.55)
                const labelH = fontPx + 8
                const lx = d.bbox.x + 3
                const ly = d.bbox.y + labelH + 2
                return (
                  <g
                    key={d.id}
                    className={`bbox-group ${active ? 'active' : ''}`}
                    onClick={() => setSelected(d.id)}
                    onMouseEnter={() => setHovered(d.id)}
                    onMouseLeave={() => setHovered(null)}
                  >
                    <rect
                      className="bbox-rect"
                      x={d.bbox.x}
                      y={d.bbox.y}
                      width={d.bbox.width}
                      height={d.bbox.height}
                      fill={active ? 'rgba(244,239,230,0.16)' : 'transparent'}
                      stroke={stroke}
                      strokeWidth={strokeWidth}
                      pointerEvents="all"
                    />
                    <rect
                      x={lx}
                      y={ly - labelH}
                      width={labelW}
                      height={labelH}
                      fill="rgba(18, 14, 10, 0.88)"
                      stroke={stroke}
                      strokeWidth="1"
                      pointerEvents="none"
                    />
                    <text
                      x={lx + 6}
                      y={ly - 6}
                      fill="#f4efe6"
                      fontSize={fontPx}
                      fontFamily="Georgia, serif"
                      pointerEvents="none"
                    >
                      {label}
                    </text>
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
              {showShadows && (run.shadow_zones ?? []).map((sz, i) => (
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
                Show dropped ({filterStats.noise_reduced_count})
              </label>
            )}
            {(run.shadow_zones ?? []).length > 0 && (
              <label className="shadow-legend filter-toggle">
                <input
                  type="checkbox"
                  checked={showShadows}
                  onChange={(e) => setShowShadows(e.target.checked)}
                />
                Shadow zones ({run.shadow_zones.length})
              </label>
            )}
          </div>
        </section>

        <aside className="contact-sheet">
          <header className="title-block">
            <p className="tb-kicker">
              Contact plot · {modeLabel.toLowerCase()} · {thresholdPct}% · {run.inference_mode}
            </p>
            <p className="tb-line">
              {run.image_width}×{run.image_height} · {filterStats.total_filtered} kept
              {filterStats.noise_reduced_count ? ` · ${filterStats.noise_reduced_count} dropped` : ''}
              {' · '}
              {locatedCount > 0 ? `${locatedCount} geolocated` : 'nav unavailable'}
            </p>
          </header>

          {detections.length === 0 ? (
            <p className="muted" style={{ padding: '12px 16px' }}>No contacts at {thresholdPct}%.</p>
          ) : (
            <ul className="contacts">
              {detections.map((d, i) => {
                const on = d.id === selected || d.id === hovered
                const geo = d.geolocation
                const hasCoords = geo.latitude != null && geo.longitude != null
                return (
                  <li
                    key={d.id}
                    className={on ? 'on' : ''}
                    onClick={() => setSelected(d.id)}
                    onMouseEnter={() => setHovered(d.id)}
                    onMouseLeave={() => setHovered(null)}
                  >
                    <span className="contact-n">{i + 1}</span>
                    <div>
                      <p className="contact-head">
                        {d.class.replace(/_/g, ' ')}
                        <span> {formatConfidence(d.confidence)}</span>
                      </p>
                      {on ? (
                        <p className="contact-spec">
                          {d.bbox.width}×{d.bbox.height} px
                          {d.width_m != null && d.height_m != null
                            ? ` · ${d.width_m.toFixed(2)}×${d.height_m.toFixed(2)} m`
                            : ''}
                          {d.estimated_height_m != null ? ` · shadow ~${d.estimated_height_m} m` : ''}
                          <br />
                          {formatGeoStatus(geo.status)}
                          {hasCoords ? ` · ${geo.latitude?.toFixed(6)}, ${geo.longitude?.toFixed(6)}` : ''}
                        </p>
                      ) : null}
                    </div>
                  </li>
                )
              })}
            </ul>
          )}

          {showSuppressed && suppressed.length > 0 ? (
            <ul className="contacts contacts-dropped">
              {suppressed.map((d, i) => (
                <li key={d.id} className={d.id === selected ? 'on' : ''} onClick={() => setSelected(d.id)}>
                  <span className="contact-n">{detections.length + i + 1}</span>
                  <div>
                    <strong>{d.class.replace(/_/g, ' ')}</strong>
                    <span className="contact-conf">{formatConfidence(d.confidence)}</span>
                    {d.rejection_reason ? <p className="muted">{d.rejection_reason}</p> : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </aside>
      </div>
    </div>
  )
}
