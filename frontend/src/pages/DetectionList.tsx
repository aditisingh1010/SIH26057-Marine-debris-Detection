import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { getRun, reportUrl } from '../api'
import type { Detection, RunResult } from '../types'
import { formatConfidence, formatGeoStatus, getRiskBadgeClass, getRiskLevel } from '../utils'

export default function DetectionList() {
  const { id } = useParams()
  const location = useLocation()
  const cached = (location.state as { run?: RunResult } | null)?.run
  const [run, setRun] = useState<RunResult | null>(cached && cached.id === id ? cached : null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id || (cached && cached.id === id)) return
    let cancelled = false
    getRun(id)
      .then((data) => {
        if (!cancelled) setRun(data)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
    return () => {
      cancelled = true
    }
  }, [id, cached])

  if (error) return <div className="error">{error}</div>
  if (!run) return <p className="muted">Loading list…</p>

  const detections = run.detections ?? []
  const raw = run.raw_detections ?? detections
  const dropped = raw.filter((d) => d.passed_filter === false)
  const located = detections.filter((d) => d.geolocation.latitude != null && d.geolocation.longitude != null).length
  const briefing = run.operator_briefing
  const stats = run.filter_stats
  const mode = (run.detection_mode ?? 'demo').toLowerCase()
  const pct = ((run.conf_threshold ?? 0.25) * 100).toFixed(0)

  return (
    <div className="list-page">
      <p className="sheet-lede">
        <Link to={`/runs/${run.id}`}>Output</Link>
        {' · '}
        <a href={reportUrl(run.id, 'json')}>JSON</a>
        {' · '}
        <a href={reportUrl(run.id, 'csv')}>CSV</a>
      </p>
      <h1 className="sheet-title">{run.filename}</h1>
      <p className="lede">
        {mode} at {pct}% · {run.image_width}×{run.image_height}px · {run.inference_mode}
      </p>

      <div className="stat-row">
        <div className="stat">
          <span>Kept</span>
          <strong>{stats?.total_filtered ?? detections.length}</strong>
        </div>
        <div className="stat">
          <span>Dropped</span>
          <strong>{stats?.noise_reduced_count ?? dropped.length}</strong>
        </div>
        <div className="stat">
          <span>Raw YOLO</span>
          <strong>{stats?.total_raw ?? raw.length}</strong>
        </div>
        <div className="stat">
          <span>Geolocated</span>
          <strong>{located}</strong>
        </div>
      </div>

      <p className="filter-note">
        {run.geolocation_note || 'Geolocation unavailable unless nav metadata was attached.'}
        {briefing
          ? ` Demo would keep ${briefing.demo_kept}. Survey would keep ${briefing.survey_kept}.`
          : ''}
        {briefing?.shadow_overlap_count
          ? ` ${briefing.shadow_overlap_count} box(es) overlap a shadow zone (review, not auto-deleted).`
          : ''}
      </p>

      <h2>Kept detections</h2>
      {detections.length === 0 ? (
        <p className="muted">Nothing passed the {mode} filter at {pct}%.</p>
      ) : (
        detections.map((d) => <DetectionCard key={d.id} d={d} />)
      )}

      {dropped.length > 0 ? (
        <>
          <h2>Dropped</h2>
          {dropped.map((d) => <DetectionCard key={d.id} d={d} dropped />)}
        </>
      ) : null}
    </div>
  )
}

export function DetectionCard({ d, dropped }: { d: Detection; dropped?: boolean }) {
  const risk = getRiskLevel(d)
  const hasCoords = d.geolocation.latitude != null && d.geolocation.longitude != null
  return (
    <article className={`detection-card ${dropped ? 'detection-card-suppressed' : ''}`}>
      <div className="detection-card-top">
        <div className="detection-title-group">
          <span className="detection-id-tag">{d.id}</span>
          <h3 className="detection-name">{d.class.replace(/_/g, ' ')}</h3>
        </div>
        <span className={dropped ? 'risk-badge risk-low' : getRiskBadgeClass(risk)}>
          {dropped ? 'Filtered' : `${risk} risk`}
        </span>
      </div>
      {d.review_priority === 'review' || d.acoustic_shadow_overlap ? (
        <p className="muted">
          Review{d.acoustic_shadow_overlap ? ' · shadow overlap' : ''}
        </p>
      ) : null}
      <div className="detection-metrics">
        <div className="metric-item">
          <span className="metric-label">Confidence</span>
          <strong>{formatConfidence(d.confidence)}</strong>
        </div>
        <div className="metric-item">
          <span className="metric-label">Risk score</span>
          <span>{d.risk_score?.toFixed(2)}</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Box (px)</span>
          <span>
            {d.bbox.width} × {d.bbox.height} at {d.bbox.x}, {d.bbox.y}
          </span>
        </div>
        {d.width_m != null && d.height_m != null ? (
          <div className="metric-item">
            <span className="metric-label">Size (m)</span>
            <span>
              {d.width_m.toFixed(2)} × {d.height_m.toFixed(2)}
            </span>
          </div>
        ) : null}
        {d.estimated_height_m != null ? (
          <div className="metric-item">
            <span className="metric-label">Shadow height</span>
            <span>~{d.estimated_height_m} m</span>
          </div>
        ) : null}
        {dropped && d.rejection_reason ? (
          <div className="metric-item">
            <span className="metric-label">Reason</span>
            <span>{d.rejection_reason}</span>
          </div>
        ) : null}
      </div>
      <p className="muted">
        Geo: {formatGeoStatus(d.geolocation.status)}
        {hasCoords
          ? ` · ${d.geolocation.latitude?.toFixed(6)}, ${d.geolocation.longitude?.toFixed(6)}`
          : ' · no coordinates'}
      </p>
    </article>
  )
}
