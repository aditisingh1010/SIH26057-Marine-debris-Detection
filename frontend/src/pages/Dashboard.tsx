import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getRuns } from '../api'
import type { RunSummary } from '../types'

interface BenchmarkTransect {
  id: string
  filename: string
  label: string
  path: string
  swathWidthM: number
  rangeM: number
  contactsCount: number
  priority: 'high' | 'medium' | 'normal'
  dimensions: string
}

const BENCHMARK_TRANSECTS: BenchmarkTransect[] = [
  {
    id: 'transect_0015',
    filename: '0015_2010.jpg',
    label: 'TRANSECT #0015 — BENTHIC HAZARD PASS',
    path: '/dataset/0015_2010.jpg',
    swathWidthM: 37.4,
    rangeM: 18.7,
    contactsCount: 4,
    priority: 'high',
    dimensions: '416 × 416 px',
  },
  {
    id: 'transect_0021',
    filename: '0021_2018.jpg',
    label: 'TRANSECT #0021 — HIGH-RES WATERFALL PASS',
    path: '/dataset/0021_2018.jpg',
    swathWidthM: 71.7,
    rangeM: 35.8,
    contactsCount: 2,
    priority: 'normal',
    dimensions: '1024 × 1024 px',
  },
  {
    id: 'transect_0080',
    filename: '0080_2018.jpg',
    label: 'TRANSECT #0080 — DEBRIS FIELD ANOMALIES',
    path: '/dataset/0080_2018.jpg',
    swathWidthM: 37.4,
    rangeM: 18.7,
    contactsCount: 3,
    priority: 'medium',
    dimensions: '416 × 416 px',
  },
  {
    id: 'transect_0001',
    filename: '0001_2010.jpg',
    label: 'TRANSECT #0001 — BASELINE SEABED SCAN',
    path: '/dataset/0001_2010.jpg',
    swathWidthM: 41.6,
    rangeM: 20.8,
    contactsCount: 1,
    priority: 'normal',
    dimensions: '416 × 416 px',
  },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const [latestRun, setLatestRun] = useState<RunSummary | null>(null)

  // Workstation Instrument Controls
  const [enhanced, setEnhanced] = useState(false)
  const [equalized, setEqualized] = useState(true)
  const [showShadows, setShowShadows] = useState(true)
  const [showTargets, setShowTargets] = useState(true)
  const [zoomed, setZoomed] = useState(false)

  // Selected Transect on the Dashboard Viewer
  const [activeTransect, setActiveTransect] = useState<BenchmarkTransect>(BENCHMARK_TRANSECTS[0])

  useEffect(() => {
    getRuns()
      .then((runs) => {
        if (runs.length > 0) {
          setLatestRun(runs[0])
        }
      })
      .catch(() => {})
  }, [])

  // Calculate CSS filters based on workstation buttons
  function getStripFilter() {
    const filters: string[] = []
    if (enhanced) filters.push('contrast(1.4) brightness(1.08)')
    if (equalized) filters.push('contrast(1.15) saturate(1.1)')
    return filters.length > 0 ? filters.join(' ') : 'none'
  }

  return (
    <div className="workstation-dashboard">
      {/* ─────────────────────────────────────────────────────────────
          PRIMARY WORKSTATION INSTRUMENT: WIDE HORIZONTAL SONAR STRIP
          ───────────────────────────────────────────────────────────── */}
      <div className="workstation-instrument-container">
        {/* Top Header Row: Survey ID + Priority Badge */}
        <div className="workstation-hero-header">
          <div className="hero-header-left">
            <span className="inst-badge-primary">ACTIVE WATERFALL TRANSECT</span>
            <h1 className="hero-survey-title">
              {latestRun?.filename || activeTransect.filename}
            </h1>
            <span className="hero-survey-meta">
              Dual-channel side-scan swath · 455 kHz · {activeTransect.swathWidthM}m across-track width
            </span>
          </div>

          <div className="hero-header-right">
            <span className="badge-risk high">HIGH PRIORITY HAZARD</span>
            <span className="hero-timestamp">RECORDED 10-SEP-2026 18:00 UTC</span>
          </div>
        </div>

        {/* ── WIDE HORIZONTAL SONAR STRIP VIEWER (NEVER SQUARE) ── */}
        <div className="wide-horizontal-sonar-strip">
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

          {/* Panoramic Swath Stage */}
          <div
            className="horizontal-swath-stage"
            style={{
              transform: zoomed ? 'scale(1.15)' : 'scale(1)',
              transition: 'transform 0.25s ease',
            }}
          >
            <img
              src={activeTransect.path}
              alt="Horizontal Sonar Swath"
              className="horizontal-swath-img"
              style={{ filter: getStripFilter() }}
              onError={(e) => {
                const el = e.currentTarget
                if (!el.src.includes('0015_2010.jpg')) el.src = '/dataset/0015_2010.jpg'
              }}
            />

            {/* Nadir Center Track Line */}
            <div className="nadir-center-track" title="Transducer Nadir Track (Water Column)" />

            {/* Channel Labels Overlay */}
            <div className="swath-channel-tag port-tag">PORT [455 kHz]</div>
            <div className="swath-channel-tag nadir-tag">NADIR 0m</div>
            <div className="swath-channel-tag stbd-tag">STARBOARD [455 kHz]</div>

            {/* Technical Target Anomaly Reticles */}
            {showTargets && (
              <>
                {/* Target 1: Ghost Pot */}
                <div
                  className="sonar-reticle-box"
                  style={{ top: '18%', left: '26%', width: '11%', height: '14%' }}
                >
                  <span className="reticle-label">1 GHOST POT 94.7%</span>
                  {showShadows && <div className="reticle-shadow-vector" style={{ width: '45px' }} />}
                </div>

                {/* Target 2: Shipwreck anomaly */}
                <div
                  className="sonar-reticle-box"
                  style={{ top: '20%', left: '60%', width: '15%', height: '16%' }}
                >
                  <span className="reticle-label">2 SHIPWRECK 88.4%</span>
                  {showShadows && <div className="reticle-shadow-vector" style={{ width: '60px' }} />}
                </div>

                {/* Target 3: Container */}
                <div
                  className="sonar-reticle-box"
                  style={{ top: '10%', left: '77%', width: '9%', height: '9%' }}
                >
                  <span className="reticle-label">3 CONTAINER 76.2%</span>
                </div>

                {/* Target 4: Debris cluster */}
                <div
                  className="sonar-reticle-box"
                  style={{ top: '28%', left: '15%', width: '7%', height: '8%' }}
                >
                  <span className="reticle-label">4 DEBRIS 64.1%</span>
                </div>
              </>
            )}
          </div>

          {/* Bottom Across-Track Channel Divider Bar */}
          <div className="across-track-ruler bottom-ruler">
            <span className="channel-axis-label">PORT BEAM SWATH (25m)</span>
            <span className="channel-axis-label nadir-marker">▼ WATER COLUMN &amp; SEABED CONTACT ▼</span>
            <span className="channel-axis-label">STARBOARD BEAM SWATH (25m)</span>
          </div>
        </div>

        {/* ── COMPACT HORIZONTAL METRICS ROW ── */}
        <div className="workstation-metrics-bar">
          <div className="ws-metric-cell">
            <span className="ws-metric-label">CONTACTS</span>
            <strong className="ws-metric-val">4 IDENTIFIED</strong>
          </div>
          <div className="ws-metric-divider" />
          <div className="ws-metric-cell">
            <span className="ws-metric-label">HIGH RISK</span>
            <strong className="ws-metric-val val-priority">2 CRITICAL</strong>
          </div>
          <div className="ws-metric-divider" />
          <div className="ws-metric-cell">
            <span className="ws-metric-label">ACOUSTIC SHADOW</span>
            <strong className="ws-metric-val val-verified">✓ VERIFIED</strong>
          </div>
          <div className="ws-metric-divider" />
          <div className="ws-metric-cell">
            <span className="ws-metric-label">GEOLOCATION (WGS84)</span>
            <strong className="ws-metric-val mono-coord">50.3550° N, -4.1450° W</strong>
          </div>
          <div className="ws-metric-divider" />
          <div className="ws-metric-cell">
            <span className="ws-metric-label">SWATH COVERAGE</span>
            <strong className="ws-metric-val">{activeTransect.swathWidthM} m</strong>
          </div>
        </div>

        {/* ── WORKSTATION INSTRUMENT ACTION BAR ── */}
        <div className="workstation-action-bar">
          <button
            type="button"
            className="ws-btn ws-btn-primary"
            onClick={() => navigate('/analyze')}
            title="Open Sonar Analysis & Ingest Studio"
          >
            ▶ ANALYZE SURVEY
          </button>

          <button
            type="button"
            className={`ws-btn ${enhanced ? 'active' : ''}`}
            onClick={() => setEnhanced(!enhanced)}
            title="Toggle high-pass acoustic edge filter"
          >
            ✦ ENHANCE {enhanced ? '[ON]' : '[OFF]'}
          </button>

          <button
            type="button"
            className={`ws-btn ${equalized ? 'active' : ''}`}
            onClick={() => setEqualized(!equalized)}
            title="Toggle TVG bilateral gain equalization"
          >
            ▤ EQUALIZE {equalized ? '[ON]' : '[OFF]'}
          </button>

          <button
            type="button"
            className={`ws-btn ${showShadows ? 'active' : ''}`}
            onClick={() => setShowShadows(!showShadows)}
            title="Toggle acoustic shadow elevation vectors"
          >
            ▲ SHADOW {showShadows ? '[ON]' : '[OFF]'}
          </button>

          <button
            type="button"
            className={`ws-btn ${showTargets ? 'active' : ''}`}
            onClick={() => setShowTargets(!showTargets)}
            title="Toggle target anomaly reticles"
          >
            ⌖ TARGETS {showTargets ? '[ON]' : '[OFF]'}
          </button>

          <button
            type="button"
            className={`ws-btn ${zoomed ? 'active' : ''}`}
            onClick={() => setZoomed(!zoomed)}
            title="Toggle 1.25x across-track panoramic zoom"
          >
            ⌕ ZOOM {zoomed ? '[1.15x]' : '[1x]'}
          </button>

          <Link
            to={latestRun ? `/runs/${latestRun.id}` : '/results'}
            className="ws-btn ws-btn-accent"
            title="Open complete detection results and contact sheets"
          >
            INSPECT RESULTS →
          </Link>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          BENCHMARK HYDROGRAPHIC TRANSECTS: WIDE HORIZONTAL STRIPS
          ───────────────────────────────────────────────────────────── */}
      <section className="benchmark-transects-section">
        <div className="transects-header-row">
          <div>
            <span className="transects-section-tag">CALIBRATED SONAR ARCHIVE</span>
            <h2 className="transects-section-title">Hydrographic Survey Passes</h2>
          </div>
          <span className="transects-section-hint">
            Select any strip to load into the horizontal workstation viewer
          </span>
        </div>

        <div className="horizontal-transect-strip-list">
          {BENCHMARK_TRANSECTS.map((t) => (
            <div
              key={t.id}
              className={`horizontal-transect-strip-card ${activeTransect.id === t.id ? 'active' : ''}`}
              onClick={() => setActiveTransect(t)}
            >
              {/* Left: Panoramic Horizontal Sonar Strip (NOT square) */}
              <div className="strip-preview-stage">
                <img
                  src={t.path}
                  alt={t.label}
                  className="strip-preview-img"
                  onError={(e) => {
                    const el = e.currentTarget
                    el.src = '/dataset/0015_2010.jpg'
                  }}
                />
                <div className="strip-nadir-line" />
                <span className="strip-range-tag">PORT ◀ 0m ▶ STBD</span>
                <span className="strip-dim-tag">{t.dimensions}</span>
              </div>

              {/* Right: Telemetry & Specs */}
              <div className="strip-info-col">
                <div className="strip-info-header">
                  <span className="strip-title">{t.label}</span>
                  <span className={`badge-risk ${t.priority === 'high' ? 'high' : t.priority === 'medium' ? 'medium' : 'low'}`}>
                    {t.priority.toUpperCase()}
                  </span>
                </div>

                <div className="strip-info-specs">
                  <div className="strip-spec-item">
                    <span className="spec-lbl">FILENAME</span>
                    <strong className="spec-val mono-text">{t.filename}</strong>
                  </div>
                  <div className="strip-spec-item">
                    <span className="spec-lbl">SWATH</span>
                    <strong className="spec-val mono-text">{t.swathWidthM}m</strong>
                  </div>
                  <div className="strip-spec-item">
                    <span className="spec-lbl">RANGE</span>
                    <strong className="spec-val mono-text">±{t.rangeM}m</strong>
                  </div>
                  <div className="strip-spec-item">
                    <span className="spec-lbl">CONTACTS</span>
                    <strong className="spec-val mono-text">{t.contactsCount} targets</strong>
                  </div>
                </div>

                <div className="strip-info-actions">
                  <button
                    type="button"
                    className="btn btn-sm btn-primary"
                    onClick={(e) => {
                      e.stopPropagation()
                      navigate('/analyze')
                    }}
                  >
                    Analyze Strip →
                  </button>
                  <Link
                    to={latestRun ? `/runs/${latestRun.id}` : '/results'}
                    className="btn btn-sm btn-secondary"
                    onClick={(e) => e.stopPropagation()}
                  >
                    View Contacts
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
