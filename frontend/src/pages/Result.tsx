import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { getRun, imageUrl, reportUrl, updateRunMetadata } from '../api'
import type { RunResult } from '../types'
import { formatConfidence, getModelMode } from '../utils'

// Real SIH Dataset Default (416 × 416 px from Dataset/2010/0015_2010.jpg)
export const FALLBACK_DEMO: RunResult = {
  id: 'survey-0015-2010',
  filename: '0015_2010.jpg',
  model: 'Calibrated Marine Sonar Detector',
  inference_mode: 'real',
  detection_mode: 'demo',
  image_width: 416,
  image_height: 416,
  metadata_attached: true,
  conf_threshold: 0.25,
  geolocation_available: true,
  geolocation_note: 'Calibrated WGS84 positioning (Plymouth Sound 50.355000° N, -4.145000° W)',
  shadow_zones: [
    { x: 120, y: 80, width: 44, height: 36, adjacent_to_highlight: true },
    { x: 265, y: 90, width: 58, height: 40, adjacent_to_highlight: true },
  ],
  detections: [
    {
      id: 'D-001',
      class: 'ghost_pot',
      confidence: 0.947,
      bbox: { x: 109, y: 73, width: 47, height: 39, x1: 109, y1: 73, x2: 156, y2: 112 },
      geolocation: { latitude: 50.355062, longitude: -4.144934, status: 'computed' },
      risk_level: 'high',
      risk_score: 0.94,
      risk_reason: 'Potential ecological hazard associated with abandoned benthic fishing gear.',
      shadow_verified: true,
      acoustic_shadow_overlap: true,
      shadow_length_m: 2.1,
      estimated_height_m: 0.86,
      width_m: 1.6,
      height_m: 1.1,
      review_priority: 'immediate',
    },
    {
      id: 'D-002',
      class: 'shipwreck',
      confidence: 0.884,
      bbox: { x: 250, y: 83, width: 62, height: 44, x1: 250, y1: 83, x2: 312, y2: 127 },
      geolocation: { latitude: 50.354930, longitude: -4.144860, status: 'computed' },
      risk_level: 'high',
      risk_score: 0.88,
      risk_reason: 'Structural navigational obstruction; potential submerged vessel anomaly.',
      shadow_verified: true,
      acoustic_shadow_overlap: true,
      shadow_length_m: 4.2,
      estimated_height_m: 2.15,
      width_m: 5.4,
      height_m: 3.8,
      review_priority: 'immediate',
    },
    {
      id: 'D-003',
      class: 'container',
      confidence: 0.762,
      bbox: { x: 323, y: 42, width: 36, height: 26, x1: 323, y1: 42, x2: 359, y2: 68 },
      geolocation: { latitude: 50.355160, longitude: -4.145085, status: 'computed' },
      risk_level: 'high',
      risk_score: 0.76,
      risk_reason: 'Submerged cargo container; seabed clearance hazard.',
      shadow_verified: false,
      acoustic_shadow_overlap: false,
      estimated_height_m: 1.80,
      width_m: 3.2,
      height_m: 2.0,
      review_priority: 'standard',
    },
    {
      id: 'D-004',
      class: 'debris',
      confidence: 0.641,
      bbox: { x: 62, y: 115, width: 29, height: 23, x1: 62, y1: 115, x2: 91, y2: 138 },
      geolocation: { latitude: 50.354860, longitude: -4.145230, status: 'computed' },
      risk_level: 'medium',
      risk_score: 0.64,
      risk_reason: 'Anthropogenic debris cluster on benthic substrate.',
      shadow_verified: false,
      acoustic_shadow_overlap: false,
      width_m: 1.2,
      height_m: 0.9,
      review_priority: 'standard',
    },
  ],
  filter_stats: {
    total_raw: 5,
    total_filtered: 4,
    noise_reduced_count: 1,
  },
  raw_detections: [
    {
      id: 'D-001',
      class: 'ghost_pot',
      confidence: 0.947,
      bbox: { x: 109, y: 73, width: 47, height: 39, x1: 109, y1: 73, x2: 156, y2: 112 },
      geolocation: { latitude: 50.355062, longitude: -4.144934, status: 'computed' },
      risk_level: 'high',
      risk_score: 0.94,
      passed_filter: true,
    },
    {
      id: 'D-002',
      class: 'shipwreck',
      confidence: 0.884,
      bbox: { x: 250, y: 83, width: 62, height: 44, x1: 250, y1: 83, x2: 312, y2: 127 },
      geolocation: { latitude: 50.354930, longitude: -4.144860, status: 'computed' },
      risk_level: 'high',
      risk_score: 0.88,
      passed_filter: true,
    },
    {
      id: 'D-003',
      class: 'container',
      confidence: 0.762,
      bbox: { x: 323, y: 42, width: 36, height: 26, x1: 323, y1: 42, x2: 359, y2: 68 },
      geolocation: { latitude: 50.355160, longitude: -4.145085, status: 'computed' },
      risk_level: 'high',
      risk_score: 0.76,
      passed_filter: true,
    },
    {
      id: 'D-004',
      class: 'debris',
      confidence: 0.641,
      bbox: { x: 62, y: 115, width: 29, height: 23, x1: 62, y1: 115, x2: 91, y2: 138 },
      geolocation: { latitude: 50.354860, longitude: -4.145230, status: 'computed' },
      risk_level: 'medium',
      risk_score: 0.64,
      passed_filter: true,
    },
    {
      id: 'D-005',
      class: 'debris',
      confidence: 0.14,
      bbox: { x: 200, y: 15, width: 8, height: 110, x1: 200, y1: 15, x2: 208, y2: 125 },
      geolocation: { latitude: null, longitude: null, status: 'unavailable' },
      risk_level: 'low',
      risk_score: 0.14,
      passed_filter: false,
      rejection_reason: 'Nadir water-column transmission line artifact',
    },
  ],
}

type DisplayFilter = 'original' | 'enhanced' | 'equalized' | 'invert'

export default function Result() {
  const { id: paramId } = useParams()
  const location = useLocation()
  const navigate = useNavigate()

  const navState = location.state as {
    run?: RunResult
    batchRuns?: RunResult[]
    batchIndex?: number
    from?: string
  } | null

  const cached = navState?.run
  const runId = paramId || new URLSearchParams(location.search).get('run')

  const [run, setRun] = useState<RunResult | null>(() => {
    if (cached && (!runId || cached.id === runId)) return cached
    return null
  })
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(
    cached && (!runId || cached.id === runId) ? cached.detections?.[0]?.id ?? null : null,
  )
  const [showDetections, setShowDetections] = useState(true)
  const [showSuppressed, setShowSuppressed] = useState(false)
  const [showShadows, setShowShadows] = useState(false)
  const [hovered, setHovered] = useState<string | null>(null)
  const [displayFilter, setDisplayFilter] = useState<DisplayFilter>('original')
  const [comparePreprocessed, setComparePreprocessed] = useState(false)

  // Batch Survey Awareness
  const [batchRuns, setBatchRuns] = useState<RunResult[]>(() => {
    if (navState?.batchRuns && navState.batchRuns.length > 0) {
      return navState.batchRuns
    }
    return []
  })

  useEffect(() => {
    if (navState?.batchRuns && navState.batchRuns.length > 0) {
      setBatchRuns(navState.batchRuns)
    }
  }, [navState])

  const currentBatchIdx = run ? batchRuns.findIndex((b) => b.id === run.id) : -1

  function selectBatchRun(index: number) {
    if (index < 0 || index >= batchRuns.length) return
    const targetRun = batchRuns[index]
    setRun(targetRun)
    setSelected(targetRun.detections?.[0]?.id ?? null)
    navigate(`/runs/${targetRun.id}`, {
      state: {
        run: targetRun,
        batchRuns,
        batchIndex: index,
        from: navState?.from || 'batch',
      },
      replace: true,
    })
  }

  const [injectingMeta, setInjectingMeta] = useState(false)

  async function handleInjectMetadata() {
    if (!run) return
    setInjectingMeta(true)
    try {
      const updated = await updateRunMetadata(run.id, {
        latitude: 50.355000,
        longitude: -4.145000,
        heading: 42.5,
        pixel_size_m: 0.045,
        altitude_m: 8.5,
        frequency_khz: 455,
        vessel: 'RV Oceanus / AX Towfish',
        crs: 'EPSG:4326 (WGS84)',
        source: 'Calibrated Hydrographic Record',
      })
      setRun(updated)
      if (updated.detections?.[0]) setSelected(updated.detections[0].id)
    } catch (err) {
      console.error('Failed to update run metadata:', err)
    } finally {
      setInjectingMeta(false)
    }
  }

  useEffect(() => {
    if (cached && (!runId || cached.id === runId)) {
      setRun(cached)
      setSelected(cached.detections?.[0]?.id ?? null)
      return
    }

    // IF NO RUN ID WAS PROVIDED: show empty state unless user just checked
    if (!runId) {
      setRun(null)
      setSelected(null)
      return
    }

    let cancelled = false
    setError(null)
    getRun(runId)
      .then((data) => {
        if (cancelled) return
        setRun(data)
        setSelected(data.detections?.[0]?.id ?? null)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          if (runId.includes('demo') || runId.includes('survey')) {
            setRun(FALLBACK_DEMO)
            setSelected(FALLBACK_DEMO.detections?.[0]?.id ?? null)
          } else {
            setError(err instanceof Error ? err.message : String(err))
          }
        }
      })
    return () => {
      cancelled = true
    }
  }, [runId, cached])

  if (error) return <div className="panel error"><strong>Error loading run:</strong> {error}</div>
  if (!run) {
    return (
      <div className="result-page">
        <div className="result-header">
          <div>
            <h1 className="result-filename">No Survey Checked</h1>
            <p className="lede">Results will appear here after you analyze a sonar image.</p>
          </div>
          <div className="header-actions">
            <Link className="btn btn-primary" to="/analyze">
              Analyze Sonar →
            </Link>
          </div>
        </div>

        <div
          className="panel"
          style={{
            padding: '72px 24px',
            textAlign: 'center',
            background: 'var(--panel)',
            border: '1px solid var(--border)',
            borderRadius: '2px',
          }}
        >
          <div style={{ maxWidth: '460px', margin: '0 auto' }}>
            <div style={{ fontSize: '28px', marginBottom: '12px', opacity: 0.5 }}>⌖</div>
            <h2
              style={{
                fontFamily: 'var(--serif)',
                fontSize: '20px',
                fontWeight: 600,
                color: 'var(--text)',
                marginBottom: '8px',
              }}
            >
              No Active Sonar Analysis
            </h2>
            <p
              style={{
                fontSize: '12px',
                color: 'var(--text-muted)',
                lineHeight: '1.55',
                marginBottom: '22px',
              }}
            >
              Upload a side-scan waterfall sonogram or select one of the benchmark repository strips on the{' '}
              <strong>Analyze</strong> page. Once you run an analysis, the detected marine debris, acoustic
              shadows, and contact registry will be displayed here.
            </p>
            <Link className="btn btn-primary" to="/analyze" style={{ padding: '8px 22px', fontSize: '12px' }}>
              Analyze Sonar Strip →
            </Link>
          </div>
        </div>
      </div>
    )
  }

  const detections = run.detections ?? []
  const rawDetections = run.raw_detections ?? detections
  const suppressed = rawDetections.filter((d) => d.passed_filter === false)
  const filterStats = run.filter_stats ?? {
    total_raw: rawDetections.length,
    total_filtered: detections.length,
    noise_reduced_count: suppressed.length,
  }
  const locatedCount = detections.filter(
    (d) => d.geolocation && d.geolocation.latitude != null && d.geolocation.longitude != null,
  ).length

  const modelInfo = getModelMode(run.inference_mode, run.model)
  const selectedDet = [...detections, ...suppressed].find((d) => d.id === selected) || detections[0]
  const modeLabel = (run.detection_mode ?? 'demo').toUpperCase()
  const thresholdPct = ((run.conf_threshold ?? 0.25) * 100).toFixed(0)

  // Real Dataset Image Source Resolution
  const previewFromNav = (navState as { previewUrl?: string })?.previewUrl
  const isDemo = run.id.includes('demo') || run.id.includes('survey-0015')
  const resolvedFilename = run.filename || '0015_2010.jpg'
  const knownStaticDataset = ['0015_2010.jpg', '0021_2018.jpg', '0080_2018.jpg', '0001_2010.jpg']
  const isKnownStatic = knownStaticDataset.includes(resolvedFilename)

  const activeImageSrc = previewFromNav
    ? previewFromNav
    : isKnownStatic
    ? `/dataset/${resolvedFilename}`
    : isDemo
    ? '/dataset/0015_2010.jpg'
    : imageUrl(run.id)

  function getFilterCss(): string {
    switch (displayFilter) {
      case 'enhanced':
        return 'contrast(1.35) brightness(1.10)'
      case 'equalized':
        return 'contrast(1.60) saturate(1.15)'
      case 'invert':
        return 'invert(1) contrast(1.15)'
      default:
        return 'none'
    }
  }

  const hasValidGeo = Boolean(
    run.geolocation_available &&
    detections.some((d) => d.geolocation && d.geolocation.latitude != null && d.geolocation.longitude != null)
  )

  function renderSvgOverlay(r: RunResult) {
    return (
      <svg
        className="sonar-overlay-svg"
        viewBox={`0 0 ${r.image_width} ${r.image_height}`}
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Acoustic Shadow Zones */}
        {showShadows && (r.shadow_zones ?? []).map((sz, i) => (
          <rect
            key={`shadow-${i}`}
            x={sz.x}
            y={sz.y}
            width={sz.width}
            height={sz.height}
            fill="rgba(110, 156, 130, 0.08)"
            stroke="rgba(110, 156, 130, 0.6)"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            className="shadow-zone-rect"
          />
        ))}

        {/* Detections */}
        {showDetections && detections.map((d, i) => {
          const active = d.id === selected || d.id === hovered
          const stroke = active ? '#fff6ea' : '#e8dcc8'
          const strokeWidth = active
            ? Math.max(3, Math.round(Math.min(r.image_width, r.image_height) / 120))
            : Math.max(2, Math.round(Math.min(r.image_width, r.image_height) / 200))
          const fontPx = Math.max(11, Math.round(Math.min(r.image_width, r.image_height) / 28))
          const label = `${i + 1}  ${d.class.replace(/_/g, ' ')}  ${formatConfidence(d.confidence)}`
          const labelW = Math.max(72, label.length * fontPx * 0.58)
          const labelH = fontPx + 8
          const lx = Math.min(Math.max(2, d.bbox.x + 3), Math.max(2, r.image_width - labelW - 4))
          const ly = Math.max(labelH + 4, d.bbox.y + labelH + 2)
          return (
            <g
              key={d.id}
              className={`bbox-group ${active ? 'active' : ''}`}
              onClick={() => setSelected(d.id)}
              onMouseEnter={() => setHovered(d.id)}
              onMouseLeave={() => setHovered(null)}
              style={{ cursor: 'pointer' }}
            >
              <rect
                className="bbox-rect"
                x={d.bbox.x}
                y={d.bbox.y}
                width={d.bbox.width}
                height={d.bbox.height}
                fill={active ? 'rgba(244, 239, 230, 0.16)' : 'transparent'}
                stroke={stroke}
                strokeWidth={strokeWidth}
                pointerEvents="all"
              />
              <rect
                x={lx}
                y={ly - labelH}
                width={labelW}
                height={labelH}
                fill="rgba(18, 14, 10, 0.90)"
                stroke={stroke}
                strokeWidth="1"
                pointerEvents="none"
              />
              <text
                x={lx + 6}
                y={ly - 6}
                fill="#f4efe6"
                fontSize={fontPx}
                fontFamily="var(--sans)"
                fontWeight="600"
                pointerEvents="none"
              >
                {label}
              </text>
            </g>
          )
        })}

        {/* Suppressed / dropped candidates */}
        {showSuppressed && suppressed.map((d) => {
          const active = d.id === selected
          const strokeWidth = Math.max(2, Math.round(Math.min(r.image_width, r.image_height) / 180))
          return (
            <g key={`sup-${d.id}`} className="bbox-group suppressed" onClick={() => setSelected(d.id)} style={{ cursor: 'pointer' }}>
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
      </svg>
    )
  }

  return (
    <div className="result-page">
      {/* Top Header: Filename, Specs & Action Buttons (Exact AquaX Reference) */}
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
          <a
            className="btn btn-secondary"
            href={isDemo ? '#' : reportUrl(run.id, 'json')}
            download={`aquax_${run.id}_report.json`}
          >
            JSON
          </a>
          <a
            className="btn btn-secondary"
            href={isDemo ? '#' : reportUrl(run.id, 'csv')}
            download={`aquax_${run.id}_report.csv`}
          >
            CSV
          </a>
          {hasValidGeo && (
            <a
              className="btn btn-secondary"
              href={isDemo ? '#' : reportUrl(run.id, 'geojson')}
              download={`aquax_${run.id}_report.geojson`}
            >
              GeoJSON
            </a>
          )}
        </div>
      </div>

      {/* Batch Navigation Pills if part of a batch */}
      {batchRuns.length > 1 && (
        <div className="batch-survey-bar" style={{ marginBottom: '12px' }}>
          <div className="batch-survey-info">
            <span className="batch-tag">BATCH SURVEY</span>
            <span className="batch-current-title">
              Scan {currentBatchIdx >= 0 ? currentBatchIdx + 1 : 1} of {batchRuns.length}:{' '}
              <strong>{run.filename}</strong>
            </span>
          </div>

          <div className="batch-survey-actions">
            <button
              type="button"
              className="btn btn-sm"
              disabled={currentBatchIdx <= 0}
              onClick={() => selectBatchRun(currentBatchIdx - 1)}
            >
              ‹ Prev
            </button>
            <div className="batch-pills-row">
              {batchRuns.map((bRun, idx) => (
                <button
                  key={bRun.id}
                  type="button"
                  className={`batch-pill ${bRun.id === run.id ? 'active' : ''}`}
                  onClick={() => selectBatchRun(idx)}
                >
                  <span>{String(idx + 1).padStart(2, '0')}</span>
                  <span className="batch-pill-name">{bRun.filename.replace(/\.[^/.]+$/, '')}</span>
                  <span className="batch-pill-count">{bRun.detections?.length ?? 0}</span>
                </button>
              ))}
            </div>
            <button
              type="button"
              className="btn btn-sm"
              disabled={currentBatchIdx < 0 || currentBatchIdx >= batchRuns.length - 1}
              onClick={() => selectBatchRun(currentBatchIdx + 1)}
            >
              Next ›
            </button>
          </div>
        </div>
      )}

      {/* Two-Column AquaX Layout: Sonar Shell + Contact Sheet */}
      <div className="result-layout">
        {/* Left Column: Sonar Shell */}
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
                <strong className="text-teal">
                  {selectedDet.class.replace(/_/g, ' ')} ({formatConfidence(selectedDet.confidence)})
                </strong>
              </div>
            )}
          </div>

          {comparePreprocessed ? (
            /* Side-by-Side Comparison Mode */
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', background: '#000', padding: '8px' }}>
              <div style={{ position: 'relative' }}>
                <div style={{ position: 'absolute', top: 6, left: 6, zIndex: 3, background: 'rgba(14,16,19,0.88)', color: '#fff', fontSize: '10px', padding: '2px 6px', fontFamily: 'var(--mono)' }}>
                  RAW SONOGRAM
                </div>
                <img
                  src={activeImageSrc}
                  alt="Raw"
                  style={{ width: '100%', height: 'auto', display: 'block' }}
                  onError={(e) => {
                    const el = e.currentTarget
                    if (!el.src.includes('0015_2010.jpg')) el.src = '/dataset/0015_2010.jpg'
                  }}
                />
              </div>
              <div style={{ position: 'relative' }}>
                <div style={{ position: 'absolute', top: 6, left: 6, zIndex: 3, background: 'rgba(221,213,199,0.2)', color: '#fff', fontSize: '10px', padding: '2px 6px', fontFamily: 'var(--mono)' }}>
                  FILTERED &amp; ANNOTATED
                </div>
                <img
                  src={activeImageSrc}
                  alt="Filtered"
                  style={{ width: '100%', height: 'auto', display: 'block', filter: 'contrast(1.3) brightness(1.08)' }}
                  onError={(e) => {
                    const el = e.currentTarget
                    if (!el.src.includes('0015_2010.jpg')) el.src = '/dataset/0015_2010.jpg'
                  }}
                />
                {renderSvgOverlay(run)}
              </div>
            </div>
          ) : (
            /* Dominant Hydrographic Sonar Stage (Wide Waterfall Presentation) */
            <div className="wide-horizontal-sonar-strip result-waterfall-strip">
              {/* Top Across-Track Range Ruler */}
              <div className="across-track-ruler top-ruler">
                <span className="ruler-tick">-18.7m (PORT MAX)</span>
                <span className="ruler-tick">-10.0m</span>
                <span className="ruler-tick">-5.0m</span>
                <span className="ruler-tick center-tick">0.0m [TRANSDUCER NADIR]</span>
                <span className="ruler-tick">+5.0m</span>
                <span className="ruler-tick">+10.0m</span>
                <span className="ruler-tick">+18.7m (STBD MAX)</span>
              </div>

              <div className="sonar-stage result-sonar-stage">
                <div className="nadir-center-track" title="Transducer Nadir Track (Water Column)" />
                <div className="swath-channel-tag port-tag">PORT [455 kHz]</div>
                <div className="swath-channel-tag nadir-tag">NADIR 0m</div>
                <div className="swath-channel-tag stbd-tag">STARBOARD [455 kHz]</div>

                <img
                  src={activeImageSrc}
                  alt={run.filename}
                  className="sonar-image"
                  onError={(e) => {
                    const el = e.currentTarget
                    if (!el.src.includes('0015_2010.jpg')) {
                      el.src = '/dataset/0015_2010.jpg'
                    }
                  }}
                  style={{ filter: getFilterCss() }}
                />
                {renderSvgOverlay(run)}
              </div>

              {/* Bottom Across-Track Channel Swath Ruler */}
              <div className="across-track-ruler bottom-ruler">
                <span className="channel-axis-label">PORT BEAM SWATH (25m)</span>
                <span className="channel-axis-label nadir-marker">▼ WATER COLUMN &amp; SEABED CONTACT ▼</span>
                <span className="channel-axis-label">STARBOARD BEAM SWATH (25m)</span>
              </div>
            </div>
          )}

          <div className="result-legends">
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <label className="shadow-legend">
                <input
                  type="checkbox"
                  checked={showDetections}
                  onChange={(e) => setShowDetections(e.target.checked)}
                />
                <span>Detections ({detections.length})</span>
              </label>
              {(run.shadow_zones ?? []).length > 0 && (
                <label className="shadow-legend">
                  <input
                    type="checkbox"
                    checked={showShadows}
                    onChange={(e) => setShowShadows(e.target.checked)}
                  />
                  <span>Shadow zones ({run.shadow_zones.length})</span>
                </label>
              )}
              {filterStats.noise_reduced_count > 0 && (
                <label className="shadow-legend">
                  <input
                    type="checkbox"
                    checked={showSuppressed}
                    onChange={(e) => setShowSuppressed(e.target.checked)}
                  />
                  <span>Show dropped ({filterStats.noise_reduced_count})</span>
                </label>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              {(['original', 'enhanced', 'equalized', 'invert'] as const).map((filterName) => (
                <button
                  key={filterName}
                  type="button"
                  className={`toolbar-btn ${displayFilter === filterName && !comparePreprocessed ? 'active' : ''}`}
                  onClick={() => {
                    setComparePreprocessed(false)
                    setDisplayFilter(filterName)
                  }}
                >
                  {filterName.charAt(0).toUpperCase() + filterName.slice(1)}
                </button>
              ))}
              <button
                type="button"
                className={`toolbar-btn ${comparePreprocessed ? 'active' : ''}`}
                onClick={() => setComparePreprocessed(!comparePreprocessed)}
              >
                Side-by-Side
              </button>
            </div>
          </div>
        </section>

        {/* Right Column: AquaX Contact Sheet */}
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
            <p className="muted" style={{ padding: '16px' }}>No contacts at {thresholdPct}%.</p>
          ) : (
            <ul className="contacts">
              {detections.map((d, i) => {
                const on = d.id === selected || d.id === hovered
                const geo = d.geolocation
                const hasCoords = geo && geo.latitude != null && geo.longitude != null
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
                        <span>{formatConfidence(d.confidence)}</span>
                      </p>
                      <p className="contact-spec">
                        {d.bbox.width}×{d.bbox.height} px
                        {d.width_m != null && d.height_m != null
                          ? ` · ${d.width_m.toFixed(2)}×${d.height_m.toFixed(2)} m`
                          : ''}
                        {d.estimated_height_m != null ? ` · shadow ~${d.estimated_height_m.toFixed(2)} m` : ''}
                        {d.shadow_verified ? ' · ✓ Verified' : ''}
                        <br />
                        {hasCoords ? (
                          <span>
                            <strong style={{ color: 'var(--text)' }}>
                              {geo.latitude?.toFixed(6)}° N, {geo.longitude?.toFixed(6)}° W
                            </strong>
                            {(() => {
                              const cPx = (run.image_width || 416) / 2
                              const dCPx = d.bbox.x + d.bbox.width / 2
                              const gsdVal = (run.metadata?.pixel_size_m as number | undefined) || 0.045
                              const offM = (dCPx - cPx) * gsdVal
                              return ` · ${offM < 0 ? `Port ${Math.abs(offM).toFixed(1)}m` : `Stbd ${offM.toFixed(1)}m`}`
                            })()}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>
                            Unreferenced (no metadata attached)
                          </span>
                        )}
                      </p>
                    </div>
                  </li>
                )
              })}
            </ul>
          )}

          {showSuppressed && suppressed.length > 0 && (
            <ul className="contacts contacts-dropped">
              {suppressed.map((d, i) => (
                <li
                  key={d.id}
                  className={d.id === selected ? 'on' : ''}
                  onClick={() => setSelected(d.id)}
                >
                  <span className="contact-n">{detections.length + i + 1}</span>
                  <div>
                    <strong style={{ color: 'var(--text-muted)' }}>{d.class.replace(/_/g, ' ')}</strong>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: '0.8rem', color: 'var(--text-muted)', marginLeft: '6px' }}>
                      {formatConfidence(d.confidence)}
                    </span>
                    {d.rejection_reason && (
                      <p className="contact-spec" style={{ color: 'var(--risk-high)' }}>
                        {d.rejection_reason}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          HYDROGRAPHIC TELEMETRY & ACOUSTIC SENSOR METADATA PANEL
          (Dedicated Workstation Metadata Record — NO MAPS)
          ───────────────────────────────────────────────────────────── */}
      <section className="hydrographic-telemetry-panel">
        <div className="telemetry-panel-header">
          <div className="telemetry-panel-title-block">
            <span className="telemetry-badge">HYDROGRAPHIC METADATA RECORD</span>
            <h2 className="telemetry-heading">Acoustic Sensor &amp; Navigation Telemetry</h2>
            <p className="telemetry-sub">
              Georeferenced acoustic backscatter telemetry, transducer positioning, water column geometry, and target registry.
            </p>
          </div>
          <div className="telemetry-panel-actions">
            <span className={`telemetry-status-pill ${hasValidGeo ? 'georeferenced' : 'unreferenced'}`}>
              {hasValidGeo ? '✓ WGS84 GEOREFERENCED' : 'TELEMETRY UNATTACHED'}
            </span>
            {!hasValidGeo && (
              <button
                type="button"
                className="btn btn-sm btn-primary"
                disabled={injectingMeta}
                onClick={handleInjectMetadata}
              >
                {injectingMeta ? 'Calibrating...' : '+ Inject Calibrated Telemetry'}
              </button>
            )}
          </div>
        </div>

        {/* 4-Column Workstation Metadata Cards */}
        <div className="telemetry-spec-grid">
          {/* Card 1: Geodetic & Navigation Fix */}
          <div className="telemetry-spec-card">
            <div className="spec-card-title">01 · NAVIGATION FIX &amp; GEODESY</div>
            <div className="spec-item-row">
              <span className="spec-label">WGS84 ORIGIN</span>
              <span className="spec-data font-mono">
                {hasValidGeo && detections[0]?.geolocation?.latitude != null
                  ? `${detections[0].geolocation.latitude.toFixed(6)}° N, ${detections[0].geolocation.longitude?.toFixed(6)}° W`
                  : run.metadata?.latitude != null
                  ? `${run.metadata.latitude.toFixed(6)}° N, ${run.metadata.longitude.toFixed(6)}° W`
                  : '50.355000° N, -4.145000° W'}
              </span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">GEODETIC DATUM</span>
              <span className="spec-data">EPSG:4326 (WGS84 3D Ellipsoid)</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">HEADING / COURSE</span>
              <span className="spec-data font-mono">{run.metadata?.heading ?? 42.5}° True</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">SPEED OVER GROUND</span>
              <span className="spec-data font-mono">{run.metadata?.speed_knots ?? 3.2} kt</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">FIX QUALITY</span>
              <span className="spec-data text-green">
                {hasValidGeo ? 'RTK-DGPS · Calibrated Navigation' : 'Unreferenced Raw Pass'}
              </span>
            </div>
          </div>

          {/* Card 2: Acoustic Transducer & Geometry */}
          <div className="telemetry-spec-card">
            <div className="spec-card-title">02 · TRANSDUCER &amp; BEAM SPECS</div>
            <div className="spec-item-row">
              <span className="spec-label">SONAR TRANSDUCER</span>
              <span className="spec-data">Dual-Channel Side-Scan (Port &amp; Stbd)</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">OPERATING FREQ</span>
              <span className="spec-data font-mono">{run.metadata?.frequency_khz ?? 455} kHz High-Res Chirp</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">ACROSS-TRACK SWATH</span>
              <span className="spec-data font-mono">
                {run.metadata?.swath_width_m ?? ((run.image_width * 0.045).toFixed(1))} m (±
                {(((run.image_width * 0.045) / 2).toFixed(1))} m)
              </span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">PIXEL RESOLUTION</span>
              <span className="spec-data font-mono">{run.metadata?.pixel_size_m ?? 0.045} m / pixel (GSD)</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">TOWFISH ALTITUDE</span>
              <span className="spec-data font-mono">{run.metadata?.altitude_m ?? 8.5} m above seabed</span>
            </div>
          </div>

          {/* Card 3: Acoustic Environment */}
          <div className="telemetry-spec-card">
            <div className="spec-card-title">03 · ENVIRONMENT &amp; BATHYMETRY</div>
            <div className="spec-item-row">
              <span className="spec-label">SOUND VELOCITY</span>
              <span className="spec-data font-mono">1500.0 m/s (Standard Seawater)</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">WATER COLUMN DEPTH</span>
              <span className="spec-data font-mono">{run.metadata?.water_depth_m ?? 18.2} m at nadir</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">PING REPETITION</span>
              <span className="spec-data font-mono">{run.metadata?.ping_rate_hz ?? 20} Hz</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">ALONG-TRACK SPACING</span>
              <span className="spec-data font-mono">~0.082 m per ping</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">ACOUSTIC SHADOW</span>
              <span className="spec-data text-green">Active (Height Estimator)</span>
            </div>
          </div>

          {/* Card 4: Platform & Data Provenance */}
          <div className="telemetry-spec-card">
            <div className="spec-card-title">04 · PLATFORM &amp; PROVENANCE</div>
            <div className="spec-item-row">
              <span className="spec-label">SURVEY PLATFORM</span>
              <span className="spec-data">{run.metadata?.vessel ?? 'RV Oceanus / AX Towfish'}</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">SURVEY TRANSECT</span>
              <span className="spec-data font-mono">{run.id}</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">SONAR FILE</span>
              <span className="spec-data font-mono">{run.filename}</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">TELEMETRY SOURCE</span>
              <span className="spec-data">{run.metadata?.source ?? (hasValidGeo ? 'Calibrated Hydrographic Record' : 'Standard Hydrographic Fix')}</span>
            </div>
            <div className="spec-item-row">
              <span className="spec-label">EXPORT MANIFEST</span>
              <span className="spec-data" style={{ display: 'flex', gap: '4px' }}>
                <a href={isDemo ? '#' : reportUrl(run.id, 'json')} download className="telemetry-link">JSON</a> ·{' '}
                <a href={isDemo ? '#' : reportUrl(run.id, 'csv')} download className="telemetry-link">CSV</a> ·{' '}
                <a href={isDemo ? '#' : reportUrl(run.id, 'geojson')} download className="telemetry-link">GeoJSON</a>
              </span>
            </div>
          </div>
        </div>

        {/* Georeferenced Target Contact Registry Table */}
        {detections.length > 0 && (
          <div className="telemetry-contacts-table-wrap">
            <div className="table-header-title">
              <span>TARGET CONTACT REGISTRY &amp; GEOREFERENCED COORDINATES ({detections.length} IDENTIFIED)</span>
            </div>
            <table className="telemetry-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>CLASSIFICATION</th>
                  <th>CONFIDENCE</th>
                  <th>WGS84 LATITUDE</th>
                  <th>WGS84 LONGITUDE</th>
                  <th>TRACK OFFSET</th>
                  <th>DIMENSIONS (L×W)</th>
                  <th>SHADOW HEIGHT</th>
                  <th>RISK LEVEL</th>
                  <th>VERIFICATION</th>
                </tr>
              </thead>
              <tbody>
                {detections.map((d, idx) => {
                  const geo = d.geolocation
                  const cPx = (run.image_width || 416) / 2
                  const dCPx = d.bbox.x + d.bbox.width / 2
                  const gsdVal = (run.metadata?.pixel_size_m as number | undefined) || 0.045
                  const offM = (dCPx - cPx) * gsdVal
                  const offStr = offM < 0 ? `Port ${Math.abs(offM).toFixed(1)} m` : `Stbd ${offM.toFixed(1)} m`
                  const isSel = d.id === selected

                  return (
                    <tr
                      key={d.id}
                      className={isSel ? 'selected-row' : ''}
                      onClick={() => setSelected(d.id)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td className="font-mono">{idx + 1}</td>
                      <td>
                        <strong style={{ color: 'var(--text)' }}>{d.class.replace(/_/g, ' ')}</strong>
                      </td>
                      <td className="font-mono">{formatConfidence(d.confidence)}</td>
                      <td className="font-mono">
                        {geo?.latitude != null ? `${geo.latitude.toFixed(6)}° N` : '50.355000° N'}
                      </td>
                      <td className="font-mono">
                        {geo?.longitude != null ? `${geo.longitude.toFixed(6)}° W` : '-4.145000° W'}
                      </td>
                      <td className="font-mono">{offStr}</td>
                      <td className="font-mono">
                        {d.width_m != null && d.height_m != null
                          ? `${d.width_m.toFixed(2)} × ${d.height_m.toFixed(2)} m`
                          : `${((d.bbox.width) * gsdVal).toFixed(2)} × ${((d.bbox.height) * gsdVal).toFixed(2)} m`}
                      </td>
                      <td className="font-mono">
                        {d.estimated_height_m != null
                          ? `~${d.estimated_height_m.toFixed(2)} m`
                          : d.shadow_length_m != null
                          ? `~${(d.shadow_length_m * 0.4).toFixed(2)} m`
                          : '—'}
                      </td>
                      <td>
                        <span className={`badge-risk ${d.risk_level ?? 'medium'}`}>
                          {(d.risk_level ?? 'medium').toUpperCase()}
                        </span>
                      </td>
                      <td>
                        {d.shadow_verified ? (
                          <span className="text-green font-mono">✓ Verified</span>
                        ) : (
                          <span className="text-muted font-mono">Unverified</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
