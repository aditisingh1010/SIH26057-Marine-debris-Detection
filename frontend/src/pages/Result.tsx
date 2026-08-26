import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getRun, imageUrl, reportUrl } from '../api'
import type { RunResult } from '../types'

export default function Result() {
  const { id } = useParams()
  const [run, setRun] = useState<RunResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setRun(null)
    setError(null)
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
  }, [id])

  if (!id) return <p className="error">Missing run id</p>
  if (error) return <p className="error">{error}</p>
  if (!run) return <p className="muted">Loading run…</p>

  const detections = run.detections

  return (
    <div className="result-layout">
      <section>
        <div
          className="sonar-stage"
          style={{ aspectRatio: `${run.image_width} / ${run.image_height}` }}
        >
          <img src={imageUrl(run.id)} alt={run.filename} />
          <svg
            viewBox={`0 0 ${run.image_width} ${run.image_height}`}
            preserveAspectRatio="xMidYMid meet"
          >
            {detections.map((d) => (
              <rect
                key={d.id}
                x={d.bbox.x}
                y={d.bbox.y}
                width={d.bbox.width}
                height={d.bbox.height}
                fill="none"
                stroke="#2dd4bf"
                strokeWidth={Math.max(2, Math.round(Math.min(run.image_width, run.image_height) / 120))}
              />
            ))}
          </svg>
        </div>
        <div className="actions">
          <a className="btn" href={reportUrl(run.id, 'json')}>
            Download JSON
          </a>
          <a className="btn" href={reportUrl(run.id, 'csv')}>
            Download CSV
          </a>
          <Link className="btn" to={`/runs/${run.id}/map`}>
            Map
          </Link>
          <Link className="btn" to="/">
            Back to upload
          </Link>
        </div>
      </section>
      <aside className="panel">
        <h2>Detections</h2>
        {detections.length === 0 ? (
          <p>No detections above threshold</p>
        ) : (
          detections.map((d) => (
            <article key={d.id} className="detection-card">
              <h3>{d.class}</h3>
              <p>Confidence: {(d.confidence * 100).toFixed(1)}%</p>
              <p>
                BBox: x {d.bbox.x} y {d.bbox.y} w {d.bbox.width} h {d.bbox.height}
              </p>
              <p>Geolocation: {d.geolocation.status}</p>
              {d.geolocation.latitude != null && d.geolocation.longitude != null ? (
                <p>
                  Lat {d.geolocation.latitude} Lon {d.geolocation.longitude}
                </p>
              ) : null}
            </article>
          ))
        )}
      </aside>
    </div>
  )
}
