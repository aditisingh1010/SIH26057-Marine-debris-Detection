import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getRun, imageUrl, reportUrl } from '../api'
import type { RunResult } from '../types'

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

  if (!id) return <p className="error">Missing run id</p>
  if (error) return <p className="error">{error}</p>
  if (!run) return <p className="muted">Loading survey result…</p>

  const detections = run.detections
  const located = detections.filter(
    (d) => d.geolocation.latitude != null && d.geolocation.longitude != null,
  ).length

  return (
    <div>
      <p className="kicker">Detection viewer</p>
      <h1 style={{ marginTop: 0 }}>{run.filename}</h1>
      <p className="lede">
        Model {run.model}. Boxes are on the original sonar frame. Location status is
        honest: {run.metadata_attached ? 'metadata was attached' : 'no navigation metadata'}.
      </p>

      <div className="result-layout">
        <section className="panel sonar-shell" style={{ padding: 0 }}>
          <div className="sonar-toolbar">
            <span>{run.image_width} × {run.image_height}</span>
            <span>{detections.length} detection{detections.length === 1 ? '' : 's'}</span>
          </div>
          <div
            className="sonar-stage"
            style={{ aspectRatio: `${run.image_width} / ${run.image_height}` }}
          >
            <img src={imageUrl(run.id)} alt={run.filename} />
            <svg
              viewBox={`0 0 ${run.image_width} ${run.image_height}`}
              preserveAspectRatio="xMidYMid meet"
            >
              {detections.map((d) => {
                const active = d.id === selected
                return (
                  <rect
                    key={d.id}
                    x={d.bbox.x}
                    y={d.bbox.y}
                    width={d.bbox.width}
                    height={d.bbox.height}
                    fill={active ? 'rgba(45,212,191,0.12)' : 'none'}
                    stroke={active ? '#5eead4' : '#2dd4bf'}
                    strokeWidth={
                      active
                        ? Math.max(3, Math.round(Math.min(run.image_width, run.image_height) / 90))
                        : Math.max(2, Math.round(Math.min(run.image_width, run.image_height) / 140))
                    }
                    onClick={() => setSelected(d.id)}
                  />
                )
              })}
            </svg>
          </div>
        </section>

        <aside className="panel">
          <div className="stat-row">
            <div className="stat">
              <span>Detections</span>
              <strong>{detections.length}</strong>
            </div>
            <div className="stat">
              <span>Geolocated</span>
              <strong>{located}</strong>
            </div>
          </div>
          <h2 style={{ marginTop: 0 }}>Anomalies</h2>
          {detections.length === 0 ? (
            <p>No detections above threshold</p>
          ) : (
            detections.map((d) => (
              <article
                key={d.id}
                className={`detection-card${d.id === selected ? ' selected' : ''}`}
                onClick={() => setSelected(d.id)}
              >
                <h3>{d.class.replaceAll('_', ' ')}</h3>
                <p>Confidence {(d.confidence * 100).toFixed(1)}%</p>
                <p>
                  BBox {d.bbox.x}, {d.bbox.y} · {d.bbox.width}×{d.bbox.height} px
                </p>
                <p>Location {d.geolocation.status.replaceAll('_', ' ')}</p>
                {d.geolocation.latitude != null && d.geolocation.longitude != null ? (
                  <p>
                    {d.geolocation.latitude}, {d.geolocation.longitude}
                  </p>
                ) : null}
              </article>
            ))
          )}
          <div className="actions">
            <a className="btn" href={reportUrl(run.id, 'json')}>
              Download JSON
            </a>
            <a className="btn secondary" href={reportUrl(run.id, 'csv')}>
              Download CSV
            </a>
            <Link className="btn secondary" to={`/runs/${run.id}/map`}>
              Map
            </Link>
          </div>
        </aside>
      </div>
    </div>
  )
}
