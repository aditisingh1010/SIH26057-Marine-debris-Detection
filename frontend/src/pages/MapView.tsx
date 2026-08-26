import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import * as L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { getRun } from '../api'
import type { Detection, RunResult } from '../types'
import {
  formatConfidence,
  formatGeoStatus,
  getModelMode,
  getRiskLevel,
} from '../utils'

function locatedDetections(run: RunResult): Detection[] {
  return run.detections.filter(
    (d) => d.geolocation.latitude != null && d.geolocation.longitude != null,
  )
}

export default function MapView() {
  const { id } = useParams()
  const mapEl = useRef<HTMLDivElement>(null)
  const mapInstance = useRef<L.Map | null>(null)
  const [run, setRun] = useState<RunResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setRun(null)
    setError(null)
    getRun(id)
      .then((data) => {
        if (!cancelled) {
          setRun(data)
          const valid = locatedDetections(data)
          if (valid.length > 0) {
            setSelectedId(valid[0].id)
          }
        }
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
    if (!run || located.length === 0 || !mapEl.current) return

    // Clean up any existing map instance
    if (mapInstance.current) {
      mapInstance.current.remove()
      mapInstance.current = null
    }

    const map = L.map(mapEl.current, {
      zoomControl: true,
      attributionControl: true,
    })
    mapInstance.current = map

    // High quality dark seafloor map tiles
    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
      {
        attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap',
        maxZoom: 19,
      },
    ).addTo(map)

    const markers: L.CircleMarker[] = []

    located.forEach((d) => {
      const lat = d.geolocation.latitude
      const lon = d.geolocation.longitude
      if (lat == null || lon == null) return

      const risk = getRiskLevel(d)
      let markerColor = '#2dd4bf'
      let fillColor = '#14b8a6'

      if (risk === 'High') {
        markerColor = '#f43f5e'
        fillColor = '#e11d48'
      } else if (risk === 'Medium') {
        markerColor = '#f59e0b'
        fillColor = '#d97706'
      }

      const marker = L.circleMarker([lat, lon], {
        radius: 10,
        color: markerColor,
        weight: 3,
        fillColor: fillColor,
        fillOpacity: 0.85,
      })

      const popupHtml = `
        <div class="map-popup-card">
          <div class="map-popup-header">
            <span class="map-popup-id">${d.id}</span>
            <span class="risk-badge risk-${risk.toLowerCase()}">${risk} Risk</span>
          </div>
          <h4 class="map-popup-title">${d.class.replace(/_/g, ' ')}</h4>
          <div class="map-popup-row">
            <span>Confidence:</span>
            <strong>${formatConfidence(d.confidence)}</strong>
          </div>
          <div class="map-popup-row">
            <span>Coordinates:</span>
            <code class="map-popup-coords">${lat.toFixed(6)}°, ${lon.toFixed(6)}°</code>
          </div>
          <div class="map-popup-row">
            <span>Status:</span>
            <span class="geo-badge geo-${d.geolocation.status}">${formatGeoStatus(d.geolocation.status)}</span>
          </div>
        </div>
      `

      marker.bindPopup(popupHtml, { className: 'custom-leaflet-popup' })
      marker.on('click', () => setSelectedId(d.id))
      marker.addTo(map)
      markers.push(marker)
    })

    if (markers.length > 0) {
      const group = L.featureGroup(markers)
      map.fitBounds(group.getBounds(), { padding: [50, 50], maxZoom: 16 })
    }

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove()
        mapInstance.current = null
      }
    }
  }, [run])

  if (!id) return <p className="error">Missing run id</p>
  if (error) return <div className="panel error"><strong>Error:</strong> {error}</div>
  if (!run) {
    return (
      <div className="panel loading-state">
        <div className="step-spinner" style={{ width: 28, height: 28 }} />
        <p className="muted">Loading geospatial coordinates…</p>
      </div>
    )
  }

  const modelInfo = getModelMode(run.model)

  if (located.length === 0) {
    return (
      <section className="panel empty-map">
        <div className="empty-map-content">
          <div className="empty-map-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#8aa8a3" strokeWidth="1.6">
              <path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 12 8 12s8-6.75 8-12a8 8 0 0 0-8-8z" />
              <circle cx="12" cy="10" r="3" />
              <line x1="4" y1="4" x2="20" y2="20" stroke="#f43f5e" strokeWidth="2" />
            </svg>
          </div>
          <p className="kicker">Honest Geospatial Status</p>
          <h2>Navigation Telemetry Unavailable</h2>
          <p className="muted" style={{ maxWidth: '32rem', margin: '0 auto 24px' }}>
            No GPS or survey heading metadata was supplied with <code>{run.filename}</code>.
            In compliance with strict data integrity standards, AquaX will never fabricate or hallucinate seafloor coordinates.
          </p>
          <div className="actions" style={{ justifyContent: 'center' }}>
            <Link className="btn btn-primary" to={`/runs/${run.id}`}>
              Back to Detection Waterfall
            </Link>
            <Link className="btn btn-secondary" to="/">
              Upload New Survey with Metadata
            </Link>
          </div>
        </div>
      </section>
    )
  }

  return (
    <div className="map-view-page">
      <div className="result-header">
        <div>
          <div className="header-meta-row">
            <span className="kicker">GIS Spatial Analysis</span>
            <span className={`mode-badge ${modelInfo.isMock ? 'mode-badge-mock' : 'mode-badge-real'}`}>
              <span className="mode-dot" />
              {modelInfo.badgeLabel}
            </span>
          </div>
          <h1 className="result-filename">{run.filename}</h1>
          <p className="lede">
            Plotted {located.length} georeferenced anomaly position{located.length === 1 ? '' : 's'} derived from authentic survey metadata.
          </p>
        </div>

        <div className="header-actions">
          <Link className="btn btn-secondary" to={`/runs/${run.id}`}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            Back to Result
          </Link>
        </div>
      </div>

      <div className="grid-2 map-layout-grid">
        <div className="panel map-wrap">
          <div ref={mapEl} className="map-canvas" />
        </div>

        <aside className="panel map-sidebar">
          <div className="anomaly-header">
            <h2 style={{ margin: 0, fontSize: '1.15rem' }}>Geolocated Targets</h2>
            <span className="anomaly-count-pill text-teal">{located.length} mapped</span>
          </div>

          <div className="detections-list">
            {located.map((d) => {
              const risk = getRiskLevel(d)
              const isSelected = d.id === selectedId

              return (
                <article
                  key={d.id}
                  className={`detection-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => setSelectedId(d.id)}
                >
                  <div className="detection-card-top">
                    <div className="detection-title-group">
                      <span className="detection-id-tag">{d.id}</span>
                      <h3 className="detection-name">{d.class.replace(/_/g, ' ')}</h3>
                    </div>
                    <span className={`risk-badge risk-${risk.toLowerCase()}`}>
                      {risk}
                    </span>
                  </div>

                  <div className="detection-metrics">
                    <div className="metric-item">
                      <span className="metric-label">Confidence:</span>
                      <strong>{formatConfidence(d.confidence)}</strong>
                    </div>
                    <div className="metric-item">
                      <span className="metric-label">Status:</span>
                      <span className={`geo-badge geo-${d.geolocation.status}`}>
                        {formatGeoStatus(d.geolocation.status)}
                      </span>
                    </div>
                  </div>

                  <div className="geo-coordinates mono-text" style={{ marginTop: 8 }}>
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                      <circle cx="12" cy="10" r="3" />
                    </svg>
                    <span>
                      {d.geolocation.latitude?.toFixed(6)}°, {d.geolocation.longitude?.toFixed(6)}°
                    </span>
                  </div>
                </article>
              )
            })}
          </div>
        </aside>
      </div>
    </div>
  )
}
