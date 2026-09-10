import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { detect, getRun, getRuns, imageUrl, reportUrl } from '../api'
import type { Detection, RunResult } from '../types'
import { formatConfidence, getModelMode } from '../utils'
import { FALLBACK_DEMO } from './Result'

const SAMPLE_MARINE_TELEMETRY = {
  latitude: 50.355000,
  longitude: -4.145000,
  heading: 42.5,
  pixel_size_m: 0.045,
  survey_area: 'Plymouth Sound Marine Hydrographic Sector',
}

function getRiskColor(risk?: string) {
  switch (risk?.toLowerCase()) {
    case 'critical':
    case 'high':
      return { border: '#C84A48', fill: '#C84A48', bg: 'rgba(200, 74, 72, 0.18)' }
    case 'medium':
      return { border: '#C7A252', fill: '#C7A252', bg: 'rgba(199, 162, 82, 0.18)' }
    default:
      return { border: '#6E9C82', fill: '#6E9C82', bg: 'rgba(110, 156, 130, 0.18)' }
  }
}

function getBasemapConfig(mode: 'satellite' | 'ocean') {
  if (mode === 'ocean') {
    return {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
      attribution: 'Tiles &copy; Esri &mdash; GEBCO, NOAA, CHS, Bathymetry',
      maxNativeZoom: 13,
    }
  }
  return {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Maxar, Earthstar Geographics',
    maxNativeZoom: 17,
  }
}

export default function MapView() {
  const { id: paramId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()

  const navState = location.state as { run?: RunResult } | null
  const [run, setRun] = useState<RunResult | null>(navState?.run || null)
  const [loading, setLoading] = useState(!navState?.run)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [attachingTelemetry, setAttachingTelemetry] = useState(false)
  const [basemap, setBasemap] = useState<'satellite' | 'ocean'>('satellite')

  const mapEl = useRef<HTMLDivElement>(null)
  const mapInstance = useRef<L.Map | null>(null)
  const tileLayerRef = useRef<L.TileLayer | null>(null)
  const markersRef = useRef<{ [id: string]: L.CircleMarker }>({})

  useEffect(() => {
    if (navState?.run && (!paramId || navState.run.id === paramId)) {
      setRun(navState.run)
      setLoading(false)
      return
    }

    if (paramId) {
      setLoading(true)
      if (paramId.includes('survey') || paramId.includes('demo')) {
        setRun(FALLBACK_DEMO)
        setSelectedId(FALLBACK_DEMO.detections?.[0]?.id || null)
        setLoading(false)
        return
      }
      getRun(paramId)
        .then((data) => {
          setRun(data)
          setSelectedId(data.detections?.[0]?.id || null)
        })
        .catch((err) => {
          if (paramId.includes('survey') || paramId.includes('demo')) {
            setRun(FALLBACK_DEMO)
            setSelectedId(FALLBACK_DEMO.detections?.[0]?.id || null)
          } else {
            setError(err instanceof Error ? err.message : String(err))
          }
        })
        .finally(() => setLoading(false))
      return
    }

    // If navigated to /map directly, find latest run or latest geolocated run
    setLoading(true)
    getRuns()
      .then(async (runs) => {
        if (runs.length === 0) {
          setRun(FALLBACK_DEMO)
          setSelectedId(FALLBACK_DEMO.detections?.[0]?.id || null)
          setLoading(false)
          return
        }
        const geoRun = runs.find((r) => r.geolocation_available) || runs[0]
        const full = await getRun(geoRun.id)
        setRun(full)
        setSelectedId(full.detections?.[0]?.id || null)
      })
      .catch(() => {
        setRun(FALLBACK_DEMO)
        setSelectedId(FALLBACK_DEMO.detections?.[0]?.id || null)
      })
      .finally(() => setLoading(false))
  }, [paramId, navState])

  const detections = run?.detections || []
  const located = detections.filter(
    (d) => d.geolocation && d.geolocation.latitude != null && d.geolocation.longitude != null,
  )

  // Basemap switcher effect
  useEffect(() => {
    if (!mapInstance.current) return
    if (tileLayerRef.current) {
      mapInstance.current.removeLayer(tileLayerRef.current)
    }
    const cfg = getBasemapConfig(basemap)
    const baseLayer = L.tileLayer(cfg.url, {
      attribution: cfg.attribution,
      maxZoom: 19,
      maxNativeZoom: cfg.maxNativeZoom,
    }).addTo(mapInstance.current)
    baseLayer.bringToBack()
    tileLayerRef.current = baseLayer
  }, [basemap])

  // Initialize and update Leaflet Map
  useEffect(() => {
    if (!mapEl.current || located.length === 0) return

    if (mapInstance.current) {
      mapInstance.current.remove()
      mapInstance.current = null
    }

    const map = L.map(mapEl.current, {
      zoomControl: true,
      attributionControl: true,
    })
    mapInstance.current = map

    // Base Tiles
    const cfg = getBasemapConfig(basemap)
    const baseLayer = L.tileLayer(cfg.url, {
      attribution: cfg.attribution,
      maxZoom: 19,
      maxNativeZoom: cfg.maxNativeZoom,
    }).addTo(map)
    tileLayerRef.current = baseLayer

    const markerGroup: L.CircleMarker[] = []
    markersRef.current = {}

    located.forEach((d, idx) => {
      const lat = d.geolocation.latitude!
      const lon = d.geolocation.longitude!
      const colors = getRiskColor(d.risk_level)

      const marker = L.circleMarker([lat, lon], {
        radius: 9,
        color: colors.border,
        weight: 2,
        fillColor: colors.fill,
        fillOpacity: 0.85,
      })

      const popupHtml = `
        <div style="font-family: 'IBM Plex Sans', sans-serif; font-size: 12px; line-height: 1.4; min-width: 170px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <span style="font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #938D82;">#${idx + 1} · ${d.id}</span>
            <span style="font-size: 9px; font-weight: 600; text-transform: uppercase; padding: 1px 5px; border-radius: 2px; color: ${colors.border}; background: ${colors.bg};">
              ${(d.risk_level || 'standard').toUpperCase()}
            </span>
          </div>
          <h4 style="margin: 0 0 6px; font-family: 'Source Serif 4', Georgia, serif; font-size: 13.5px; color: #EDE8DF; text-transform: capitalize;">
            ${d.class.replace(/_/g, ' ')}
          </h4>
          <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 3px; color: #938D82;">
            <span>Confidence:</span>
            <strong style="color: #EDE8DF;">${formatConfidence(d.confidence)}</strong>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 3px; color: #938D82;">
            <span>Coordinates:</span>
            <code style="color: #DDD5C7; font-family: 'IBM Plex Mono', monospace; font-size: 10px;">${lat.toFixed(6)}°, ${lon.toFixed(6)}°</code>
          </div>
          ${d.width_m && d.height_m ? `
            <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 3px; color: #938D82;">
              <span>Dimensions:</span>
              <strong style="color: #EDE8DF;">${d.width_m}m × ${d.height_m}m</strong>
            </div>
          ` : ''}
          ${d.shadow_verified ? `
            <div style="margin-top: 4px; font-size: 10px; color: #6E9C82; font-family: 'IBM Plex Mono', monospace;">
              ✓ Acoustic Shadow Verified
            </div>
          ` : ''}
        </div>
      `

      marker.bindPopup(popupHtml, {
        className: 'custom-leaflet-popup',
      })

      marker.on('click', () => {
        setSelectedId(d.id)
      })

      marker.addTo(map)
      markerGroup.push(marker)
      markersRef.current[d.id] = marker
    })

    if (markerGroup.length > 0) {
      const group = L.featureGroup(markerGroup)
      map.fitBounds(group.getBounds(), { padding: [50, 50], maxZoom: 18 })
    }

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove()
        mapInstance.current = null
      }
    }
  }, [located.length, run?.id])

  function selectContact(d: Detection) {
    setSelectedId(d.id)
    if (!mapInstance.current || d.geolocation.latitude == null || d.geolocation.longitude == null) return
    mapInstance.current.flyTo([d.geolocation.latitude, d.geolocation.longitude], 18, { duration: 0.6 })
    const marker = markersRef.current[d.id]
    if (marker) {
      marker.openPopup()
    }
  }

  // Quick Action: Auto-attach sample marine telemetry and re-run analysis
  async function attachSampleTelemetryAndRerun() {
    if (!run || attachingTelemetry) return
    setAttachingTelemetry(true)
    setError(null)

    try {
      // Fetch sample image or run image
      const filename = run.filename || '0015_2010.jpg'
      const imageSrc = filename.startsWith('00') ? `/dataset/${filename}` : imageUrl(run.id)
      const res = await fetch(imageSrc)
      const blob = await res.blob()
      const imageFile = new File([blob], filename, { type: 'image/jpeg' })

      // Create sample marine navigation metadata file
      const navBlob = new Blob([JSON.stringify(SAMPLE_MARINE_TELEMETRY, null, 2)], { type: 'application/json' })
      const navFile = new File([navBlob], 'sample_marine_nav.json', { type: 'application/json' })

      // Call detect with metadata attached
      const result = await detect(imageFile, navFile, run.conf_threshold || 0.25, run.detection_mode || 'demo')
      setRun(result)
      setSelectedId(result.detections?.[0]?.id || null)
      navigate(`/runs/${result.id}/map`, { state: { run: result }, replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setAttachingTelemetry(false)
    }
  }

  if (loading) {
    return (
      <div className="marine-panel" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
        Loading hydrographic GIS map coordinates…
      </div>
    )
  }

  if (error) {
    return (
      <div className="panel error" style={{ padding: '16px' }}>
        <strong>GIS Map Error:</strong> {error}
      </div>
    )
  }

  if (!run) {
    return (
      <div className="marine-panel" style={{ textAlign: 'center', padding: '48px' }}>
        <h2 style={{ fontFamily: 'var(--serif)', fontSize: '18px', marginBottom: '8px' }}>No Survey Loaded</h2>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
          Analyze a side-scan waterfall sonogram with navigation telemetry to view georeferenced seabed targets.
        </p>
        <Link className="btn btn-primary" to="/analyze">
          Analyze Sonar Strip →
        </Link>
      </div>
    )
  }

  const modelInfo = getModelMode(run.inference_mode, run.model)

  // Empty State: Metadata Unavailable
  if (located.length === 0) {
    return (
      <div className="map-view-page" style={{ maxWidth: '1000px', margin: '0 auto' }}>
        <div className="result-header" style={{ marginBottom: '14px' }}>
          <div>
            <h1 className="result-filename">{run.filename}</h1>
            <p className="lede">
              {detections.length} contact{detections.length === 1 ? '' : 's'} identified · {modelInfo.fullName} · Geolocation telemetry unavailable
            </p>
          </div>

          <div className="header-actions">
            <Link className="btn btn-primary" to={`/runs/${run.id}`}>
              ← Back to Sonar Strip
            </Link>
          </div>
        </div>

        <div
          className="panel"
          style={{
            background: 'var(--panel)',
            border: '1px solid var(--border)',
            borderRadius: '2px',
            padding: '48px 24px',
            textAlign: 'center',
          }}
        >
          <div style={{ maxWidth: '480px', margin: '0 auto' }}>
            <div style={{ fontSize: '28px', opacity: 0.5, marginBottom: '12px' }}>⌖</div>
            <span
              style={{
                fontFamily: 'var(--mono)',
                fontSize: '10px',
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                color: 'var(--risk-med)',
                display: 'block',
                marginBottom: '6px',
              }}
            >
              Geospatial Telemetry Unavailable
            </span>
            <h2
              style={{
                fontFamily: 'var(--serif)',
                fontSize: '19px',
                fontWeight: 600,
                color: 'var(--text)',
                marginBottom: '10px',
              }}
            >
              Map unavailable — sonar image does not contain GPS coordinates.
            </h2>
            <p
              style={{
                fontSize: '12px',
                color: 'var(--text-muted)',
                lineHeight: '1.5',
                marginBottom: '22px',
              }}
            >
              Side-scan waterfall image <code>{run.filename}</code> has no navigation telemetry file attached.
              In compliance with strict hydrographic integrity, AquaX never fabricates coordinates.
              You can attach real survey telemetry or test immediately with our pre-calibrated North Sea marine coordinates.
            </p>

            <div style={{ display: 'flex', justifyContent: 'center', gap: '10px' }}>
              <button
                type="button"
                className="btn btn-primary"
                onClick={attachSampleTelemetryAndRerun}
                disabled={attachingTelemetry}
                style={{ padding: '8px 18px', fontSize: '12px' }}
              >
                {attachingTelemetry ? 'Calibrating Coordinates…' : '+ Attach Sample Marine GPS & Plot Map'}
              </button>
              <Link className="btn btn-secondary" to={`/runs/${run.id}`} style={{ padding: '8px 16px', fontSize: '12px' }}>
                Back to Sonar Strip
              </Link>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="map-view-page">
      {/* Top Header */}
      <div className="result-header" style={{ marginBottom: '10px' }}>
        <div>
          <h1 className="result-filename">{run.filename}</h1>
          <p className="lede">
            {located.length} georeferenced contact{located.length === 1 ? '' : 's'} · {modelInfo.fullName} · WGS84 Seabed Coordinates
            {run.geolocation_note ? ` · ${run.geolocation_note}` : ''}
          </p>
        </div>

        <div className="header-actions">
          <div className="theme-switch-group" role="group" aria-label="Basemap switcher" style={{ marginRight: '4px' }}>
            <button
              type="button"
              className={`theme-toggle-btn ${basemap === 'satellite' ? 'active' : ''}`}
              onClick={() => setBasemap('satellite')}
              title="High-resolution satellite seafloor imagery"
            >
              Satellite
            </button>
            <button
              type="button"
              className={`theme-toggle-btn ${basemap === 'ocean' ? 'active' : ''}`}
              onClick={() => setBasemap('ocean')}
              title="Hydrographic ocean bathymetry base"
            >
              Bathymetry
            </button>
          </div>
          <Link className="btn btn-primary" to={`/runs/${run.id}`}>
            ← Sonar Strip
          </Link>
          <a
            className="btn btn-secondary"
            href={reportUrl(run.id, 'geojson')}
            download={`aquax_${run.id}_map.geojson`}
          >
            Export GeoJSON
          </a>
          <a
            className="btn btn-secondary"
            href={reportUrl(run.id, 'csv')}
            download={`aquax_${run.id}_contacts.csv`}
          >
            CSV
          </a>
        </div>
      </div>

      {/* Map Layout: Left Canvas + Right Contact Sheet */}
      <div className="map-layout-grid" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.4fr) 320px', gap: '12px' }}>
        {/* Left: Leaflet Seafloor Map Canvas */}
        <div
          className="map-canvas-wrapper"
          style={{
            background: '#07080A',
            border: '1px solid var(--border)',
            borderRadius: '2px',
            height: 'calc(100vh - 120px)',
            minHeight: '460px',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <div ref={mapEl} style={{ width: '100%', height: '100%', background: '#07080A' }} />

          {/* Coordinate HUD in corner */}
          <div
            style={{
              position: 'absolute',
              bottom: '10px',
              left: '10px',
              zIndex: 1000,
              background: 'rgba(14, 16, 19, 0.90)',
              border: '1px solid var(--border)',
              borderRadius: '2px',
              padding: '3px 8px',
              fontFamily: 'var(--mono)',
              fontSize: '10px',
              color: 'var(--text-muted)',
              pointerEvents: 'none',
            }}
          >
            CARTO DARK MATTER · WGS84 EPSG:4326 · <strong>{located.length} TARGETS PLOTTED</strong>
          </div>
        </div>

        {/* Right: Geolocated Contacts Sidebar */}
        <aside
          className="contact-sheet"
          style={{
            background: 'var(--panel)',
            border: '1px solid var(--border)',
            borderRadius: '2px',
            height: 'calc(100vh - 120px)',
            overflowY: 'auto',
            padding: '12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
          }}
        >
          <header className="title-block" style={{ paddingBottom: '6px', borderBottom: '1px solid var(--border)' }}>
            <div className="tb-kicker" style={{ fontSize: '10px', fontFamily: 'var(--mono)', color: 'var(--text-muted)' }}>
              HYDROGRAPHIC CONTACTS · {located.length}
            </div>
            <div className="tb-line" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text)', marginTop: '2px' }}>
              Seabed Debris GPS Registry
            </div>
          </header>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '4px' }}>
            {located.map((d, idx) => {
              const isSelected = d.id === selectedId
              const colors = getRiskColor(d.risk_level)

              return (
                <div
                  key={d.id}
                  onClick={() => selectContact(d)}
                  style={{
                    background: isSelected ? 'var(--panel-2)' : 'transparent',
                    border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                    borderRadius: '2px',
                    padding: '8px 10px',
                    cursor: 'pointer',
                    transition: 'all 0.12s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontFamily: 'var(--mono)', fontSize: '11px', fontWeight: 600, color: 'var(--accent)' }}>
                        {idx + 1}
                      </span>
                      <strong style={{ fontSize: '12.5px', textTransform: 'capitalize', color: 'var(--text)' }}>
                        {d.class.replace(/_/g, ' ')}
                      </strong>
                    </div>
                    <span
                      style={{
                        fontSize: '9px',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        padding: '1px 5px',
                        borderRadius: '2px',
                        color: colors.border,
                        background: colors.bg,
                      }}
                    >
                      {d.risk_level || 'standard'}
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10.5px', color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
                    <span>Conf: <strong style={{ color: 'var(--text)' }}>{formatConfidence(d.confidence)}</strong></span>
                    {d.width_m && d.height_m && (
                      <span>{d.width_m}m × {d.height_m}m</span>
                    )}
                  </div>

                  <div
                    style={{
                      marginTop: '4px',
                      padding: '3px 6px',
                      background: 'var(--surface-sonar)',
                      border: '1px solid var(--border)',
                      borderRadius: '2px',
                      fontFamily: 'var(--mono)',
                      fontSize: '10px',
                      color: 'var(--accent)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                    }}
                  >
                    <span>⌖</span>
                    <span>{d.geolocation.latitude?.toFixed(6)}° N, {d.geolocation.longitude?.toFixed(6)}° E</span>
                  </div>
                </div>
              )
            })}
          </div>
        </aside>
      </div>
    </div>
  )
}

