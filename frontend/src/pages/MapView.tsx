import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import * as L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { getRun } from '../api'
import type { Detection, RunResult } from '../types'

function locatedDetections(run: RunResult): Detection[] {
  return run.detections.filter(
    (d) => d.geolocation.latitude != null && d.geolocation.longitude != null,
  )
}

export default function MapView() {
  const { id } = useParams()
  const mapEl = useRef<HTMLDivElement>(null)
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

  const located = run ? locatedDetections(run) : []

  useEffect(() => {
    const points = run ? locatedDetections(run) : []
    if (!run || points.length === 0 || !mapEl.current) return

    const map = L.map(mapEl.current, { zoomControl: true })
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)

    const markers = points
      .map((d) => {
        const lat = d.geolocation.latitude
        const lon = d.geolocation.longitude
        if (lat == null || lon == null) return null
        const marker = L.circleMarker([lat, lon], {
          radius: 9,
          color: '#2dd4bf',
          weight: 2,
          fillColor: '#14b8a6',
          fillOpacity: 0.9,
        })
        marker.bindPopup(
          `<strong>${d.class}</strong><br/>${(d.confidence * 100).toFixed(1)}%<br/>${d.geolocation.status}`,
        )
        marker.addTo(map)
        return marker
      })
      .filter((m): m is L.CircleMarker => m != null)

    if (markers.length > 0) {
      map.fitBounds(L.featureGroup(markers).getBounds(), { padding: [36, 36], maxZoom: 14 })
    }

    return () => {
      map.remove()
    }
  }, [run])

  if (!id) return <p className="error">Missing run id</p>
  if (error) return <p className="error">{error}</p>
  if (!run) return <p className="muted">Loading map…</p>

  if (located.length === 0) {
    return (
      <section className="panel empty-map">
        <div>
          <p className="kicker">Geospatial</p>
          <h2>Location unavailable for this survey.</h2>
          <p className="muted">
            Attach JSON or CSV navigation metadata with latitude and longitude on
            upload. AquaX will not invent map pins.
          </p>
          <Link className="btn secondary" to={`/runs/${run.id}`}>
            Back to result
          </Link>
        </div>
      </section>
    )
  }

  return (
    <div>
      <p className="kicker">Geospatial</p>
      <h1 style={{ marginTop: 0 }}>{run.filename}</h1>
      <p className="lede">
        {located.length} detection{located.length === 1 ? '' : 's'} with coordinates.
        Status comes from the uploaded metadata, not from a guessed position.
      </p>
      <div className="panel map-wrap">
        <div ref={mapEl} className="map-canvas" />
      </div>
    </div>
  )
}
