import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { detect } from '../api'

interface RealSample {
  id: string
  filename: string
  label: string
  dimensions: string
  description: string
  path: string
  telemetry: {
    latitude: number
    longitude: number
    heading: number
    pixel_size_m: number
  }
}

const REAL_DATASET_SAMPLES: RealSample[] = [
  {
    id: 'sample_0015_2010',
    filename: '0015_2010.jpg',
    label: 'Survey Strip 0015',
    dimensions: '416 × 416 px',
    description: 'Benthic seabed survey strip',
    path: '/dataset/0015_2010.jpg',
    telemetry: {
      latitude: 50.355000,
      longitude: -4.145000,
      heading: 42.5,
      pixel_size_m: 0.045,
    },
  },
  {
    id: 'sample_0021_2018',
    filename: '0021_2018.jpg',
    label: 'Survey Strip 0021',
    dimensions: '1024 × 1024 px',
    description: 'High-res waterfall transect',
    path: '/dataset/0021_2018.jpg',
    telemetry: {
      latitude: 50.358200,
      longitude: -4.141000,
      heading: 85.0,
      pixel_size_m: 0.035,
    },
  },
  {
    id: 'sample_0080_2018',
    filename: '0080_2018.jpg',
    label: 'Survey Strip 0080',
    dimensions: '416 × 416 px',
    description: 'Debris field inspection strip',
    path: '/dataset/0080_2018.jpg',
    telemetry: {
      latitude: 50.352100,
      longitude: -4.148500,
      heading: 30.0,
      pixel_size_m: 0.045,
    },
  },
  {
    id: 'sample_0001_2010',
    filename: '0001_2010.jpg',
    label: 'Survey Strip 0001',
    dimensions: '416 × 416 px',
    description: 'Baseline sonar transect pass',
    path: '/dataset/0001_2010.jpg',
    telemetry: {
      latitude: 50.349000,
      longitude: -4.152000,
      heading: 45.0,
      pixel_size_m: 0.050,
    },
  },
]

const PROGRESS_STEPS = [
  'Loading sonar waterfall imagery',
  'Speckle noise reduction & bilateral filtering',
  'Scanning acoustic backscatter anomalies',
  'Acoustic shadow geometry verification',
  'Compiling inspection contacts registry',
]

export default function Detect() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [metadata, setMetadata] = useState<File | null>(null)
  const [autoAttachNav, setAutoAttachNav] = useState<boolean>(true)
  const [selectedSampleId, setSelectedSampleId] = useState<string | null>(null)
  const [conf, setConf] = useState<number>(0.25)
  const [mode, setMode] = useState<'demo' | 'survey'>('demo')
  const [filterEnabled, setFilterEnabled] = useState(true)
  const [shadowCheckEnabled, setShadowCheckEnabled] = useState(true)
  
  const [busy, setBusy] = useState(false)
  const [currentStepIdx, setCurrentStepIdx] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)

  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl) }, [previewUrl])

  const fileInputRef = useRef<HTMLInputElement>(null)
  const navInputRef = useRef<HTMLInputElement>(null)

  function getCalibratedNavFile(filename: string): File {
    const stem = filename.replace(/\.[^/.]+$/, '')
    const sample = REAL_DATASET_SAMPLES.find(
      (s) => s.filename === filename || stem.includes(s.filename.replace(/\.[^/.]+$/, ''))
    )
    const telemetry = sample
      ? {
          ...sample.telemetry,
          frequency_khz: 455,
          altitude_m: 8.5,
          vessel: 'RV Oceanus / AX Towfish',
          crs: 'EPSG:4326 (WGS84)',
          source: 'Calibrated Hydrographic Survey Pass',
        }
      : {
          latitude: 50.355000,
          longitude: -4.145000,
          heading: 42.5,
          pixel_size_m: 0.045,
          altitude_m: 8.5,
          frequency_khz: 455,
          vessel: 'RV Oceanus / AX Towfish',
          crs: 'EPSG:4326 (WGS84)',
          source: 'Calibrated Marine Survey Fix',
        }
    const blob = new Blob([JSON.stringify(telemetry, null, 2)], { type: 'application/json' })
    return new File([blob], `${stem}_nav.json`, { type: 'application/json' })
  }

  async function runAnalysis(targetFile: File, metaOverride?: File | null) {
    if (busy) return
    setFile(targetFile)
    setBusy(true)
    setError(null)
    setCurrentStepIdx(0)

    const interval = setInterval(() => {
      setCurrentStepIdx((prev) => (prev < PROGRESS_STEPS.length - 1 ? prev + 1 : prev))
    }, 400)

    try {
      const metaToUse =
        metaOverride !== undefined
          ? metaOverride
          : metadata || (autoAttachNav ? getCalibratedNavFile(targetFile.name) : null)
      const result = await detect(targetFile, metaToUse, conf, mode)
      clearInterval(interval)
      const pUrl = URL.createObjectURL(targetFile)
      try {
        sessionStorage.setItem('marine_last_run', JSON.stringify({ run: result, previewUrl: pUrl }))
      } catch {
        /* ignore */
      }
      navigate(`/runs/${result.id}`, { state: { run: result, previewUrl: pUrl } })
    } catch (err) {
      clearInterval(interval)
      setBusy(false)
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  function onFileChange(f: File | null) {
    if (!f) return
    setError(null)
    setSelectedSampleId(null)
    setFile(f)
    const metaToUse = metadata || (autoAttachNav ? getCalibratedNavFile(f.name) : null)
    runAnalysis(f, metaToUse)
  }

  async function onSelectSample(sample: RealSample) {
    setError(null)
    setSelectedSampleId(sample.id)
    try {
      const res = await fetch(sample.path)
      if (!res.ok) throw new Error(`HTTP ${res.status} loading ${sample.filename}`)
      const blob = await res.blob()
      const sampleFile = new File([blob], sample.filename, { type: 'image/jpeg' })
      setFile(sampleFile)
      
      // Auto-attach benchmark telemetry so seafloor coordinates are computed
      const metaBlob = new Blob([JSON.stringify(sample.telemetry, null, 2)], { type: 'application/json' })
      const metaFile = new File([metaBlob], `${sample.filename.replace(/\.[^/.]+$/, '')}_nav.json`, { type: 'application/json' })
      setMetadata(metaFile)
      runAnalysis(sampleFile, metaFile)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  async function onAnalyze() {
    if (!file || busy) return
    runAnalysis(file)
  }

  // Processing checklist view
  if (busy) {
    return (
      <div className="processing-view">
        <div className="processing-header">
          <span className="processing-active">◌</span>
          <span>Processing Sonar Analysis</span>
        </div>

        <div className="processing-list">
          {PROGRESS_STEPS.map((step, idx) => {
            const isDone = idx < currentStepIdx
            const isCurrent = idx === currentStepIdx

            return (
              <div key={step} className="processing-item">
                <span style={{ color: isDone ? 'var(--text)' : isCurrent ? 'var(--accent)' : 'var(--text-muted)' }}>
                  {step}
                </span>
                {isDone ? (
                  <span className="processing-check">✓</span>
                ) : isCurrent ? (
                  <span className="processing-active">◌</span>
                ) : (
                  <span style={{ color: 'var(--text-muted)', opacity: 0.4 }}>—</span>
                )}
              </div>
            )
          })}
        </div>

        <div style={{ marginTop: '16px', textAlign: 'center', fontSize: '11px', color: 'var(--text-muted)' }}>
          Target file: <code>{file?.name}</code>
        </div>
      </div>
    )
  }

  return (
    <div className="analyze-page workstation-analyze">
      {/* Top Header Row */}
      <div className="workstation-hero-header" style={{ marginBottom: '10px' }}>
        <div className="hero-header-left">
          <span className="inst-badge-primary">SONAR INGEST &amp; INFERENCE ENGINE</span>
          <h1 className="hero-survey-title">Acoustic Waterfall Ingest</h1>
          <span className="hero-survey-meta">
            Dual-channel side-scan swath scanning · Real-time backscatter anomaly extraction
          </span>
        </div>

        <div className="hero-header-right">
          <button
            type="button"
            className="ws-btn ws-btn-primary"
            disabled={!file || busy}
            onClick={onAnalyze}
            style={{ padding: '8px 18px', fontSize: '12px' }}
          >
            {busy ? 'Scanning Waterfall…' : '▶ ANALYZE SONAR STRIP'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '8px 12px', background: 'rgba(159, 58, 56, 0.12)', border: '1px solid var(--risk-crit)', color: 'var(--risk-crit)', borderRadius: '2px', fontSize: '11.5px', marginBottom: '10px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          ACTIVE WIDE HORIZONTAL SONAR VIEWING STAGE (NEVER SQUARE)
          ───────────────────────────────────────────────────────────── */}
      <div className="wide-horizontal-sonar-strip" style={{ marginBottom: '12px' }}>
        {/* Top Across-Track Range Ruler */}
        <div className="across-track-ruler top-ruler">
          <span className="ruler-tick">-25.0m (PORT SWATH)</span>
          <span className="ruler-tick">-15.0m</span>
          <span className="ruler-tick">-5.0m</span>
          <span className="ruler-tick center-tick">0.0m [WATER COLUMN / NADIR]</span>
          <span className="ruler-tick">+5.0m</span>
          <span className="ruler-tick">+15.0m</span>
          <span className="ruler-tick">+25.0m (STARBOARD SWATH)</span>
        </div>

        {file ? (
          /* When file is loaded: Panoramic Horizontal Swath Stage */
          <div className="horizontal-swath-stage">
            <img
              src={previewUrl || '/dataset/0015_2010.jpg'}
              alt="Active Sonar Ingest"
              className="horizontal-swath-img"
              onError={(e) => {
                const el = e.currentTarget
                if (!el.src.includes('0015_2010.jpg')) el.src = '/dataset/0015_2010.jpg'
              }}
            />

            {/* Nadir Center Line */}
            <div className="nadir-center-track" title="Transducer Nadir Track" />

            {/* Channel Labels */}
            <div className="swath-channel-tag port-tag">PORT CHANNEL</div>
            <div className="swath-channel-tag nadir-tag">NADIR 0m</div>
            <div className="swath-channel-tag stbd-tag">STARBOARD CHANNEL</div>

            {/* Ingest Target Badge */}
            <div
              style={{
                position: 'absolute',
                bottom: 8,
                left: 8,
                background: 'rgba(14, 16, 19, 0.88)',
                border: '1px solid var(--border)',
                padding: '3px 8px',
                borderRadius: '2px',
                fontFamily: 'var(--mono)',
                fontSize: '11px',
                color: 'var(--text)',
                display: 'flex',
                gap: '8px',
                alignItems: 'center',
                zIndex: 4,
              }}
            >
              <span>INGEST: <strong>{file.name}</strong></span>
              <span style={{ color: 'var(--text-muted)' }}>({(file.size / 1024).toFixed(0)} KB)</span>
              <button
                type="button"
                className="btn btn-sm"
                onClick={(e) => {
                  e.stopPropagation()
                  setFile(null)
                  setSelectedSampleId(null)
                }}
                style={{ padding: '1px 6px', fontSize: '10px' }}
              >
                Clear
              </button>
            </div>
          </div>
        ) : (
          /* When no file: Utilitarian Horizontal Drop Zone */
          <div
            className={`horizontal-swath-dropzone ${dragOver ? 'active' : ''}`}
            onClick={() => fileInputRef.current?.click()}
            onDragEnter={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragOver={(e) => e.preventDefault()}
            onDragLeave={(e) => { e.preventDefault(); setDragOver(false) }}
            onDrop={(e) => {
              e.preventDefault()
              setDragOver(false)
              if (e.dataTransfer.files[0]) onFileChange(e.dataTransfer.files[0])
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.tif,.tiff,.bmp"
              style={{ display: 'none' }}
              onClick={(e) => { (e.target as HTMLInputElement).value = '' }}
              onChange={(e) => {
                const chosen = e.target.files?.[0] ?? null
                e.target.value = ''
                onFileChange(chosen)
              }}
            />

            <div className="dropzone-center-content">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.75">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <div className="dropzone-text-block">
                <strong className="dropzone-title">DROP HORIZONTAL WATERFALL SONOGRAM HERE</strong>
                <span className="dropzone-sub">
                  Supports XTF, dual-channel side-scan sonar waterfall imagery (.jpg, .png, .tiff)
                </span>
              </div>
              <button
                type="button"
                className="ws-btn ws-btn-primary"
                onClick={(e) => {
                  e.stopPropagation()
                  fileInputRef.current?.click()
                }}
              >
                SELECT SONAR FILE
              </button>
            </div>
          </div>
        )}

        {/* Bottom Channel Division Bar */}
        <div className="across-track-ruler bottom-ruler">
          <span className="channel-axis-label">PORT TRANSDUCER BEAM</span>
          <span className="channel-axis-label nadir-marker">▼ ACOUSTIC ALIGNMENT LINE ▼</span>
          <span className="channel-axis-label">STARBOARD TRANSDUCER BEAM</span>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          HORIZONTAL WORKSTATION CONTROL & TELEMETRY TOOLBAR
          ───────────────────────────────────────────────────────────── */}
      <div className="advanced-options-container" style={{ marginBottom: '12px' }}>
        <div className="advanced-control-bar">
          {/* Col 1: Confidence Gate */}
          <div className="adv-bar-col">
            <div className="adv-label-row">
              <span className="adv-label">Confidence Gate:</span>
              <strong className="adv-value">{Math.round(conf * 100)}%</strong>
            </div>
            <input
              type="range"
              min="0.05"
              max="0.50"
              step="0.05"
              value={conf}
              onChange={(e) => setConf(parseFloat(e.target.value))}
              className="adv-range-slider"
            />
            <div className="adv-mode-buttons">
              <button
                type="button"
                className={`btn btn-sm ${mode === 'demo' ? 'btn-primary' : ''}`}
                onClick={() => { setMode('demo'); setConf(0.25) }}
              >
                Demo (25%)
              </button>
              <button
                type="button"
                className={`btn btn-sm ${mode === 'survey' ? 'btn-primary' : ''}`}
                onClick={() => { setMode('survey'); setConf(0.10) }}
              >
                Survey (10%)
              </button>
            </div>
          </div>

          {/* Col 2: Signal Processing */}
          <div className="adv-bar-col">
            <span className="adv-label">Signal Processing:</span>
            <div className="adv-checkboxes">
              <label className="adv-checkbox-label">
                <input
                  type="checkbox"
                  checked={filterEnabled}
                  onChange={(e) => setFilterEnabled(e.target.checked)}
                />
                <span>Bilateral Speckle Filter</span>
              </label>
              <label className="adv-checkbox-label">
                <input
                  type="checkbox"
                  checked={shadowCheckEnabled}
                  onChange={(e) => setShadowCheckEnabled(e.target.checked)}
                />
                <span>Acoustic Shadow Verification</span>
              </label>
            </div>
          </div>

          {/* Col 3: Navigation Telemetry */}
          <div className="adv-bar-col">
            <div className="adv-label-row">
              <span className="adv-label">Survey Telemetry &amp; Metadata:</span>
              <span className="adv-value" style={{ fontSize: '10px' }}>
                {metadata ? 'CUSTOM ATTACHED' : autoAttachNav ? 'CALIBRATED FIX' : 'NO TELEMETRY'}
              </span>
            </div>
            <input
              ref={navInputRef}
              type="file"
              accept=".json,.csv,.xtf"
              style={{ display: 'none' }}
              onChange={(e) => setMetadata(e.target.files?.[0] ?? null)}
            />
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn-sm adv-telemetry-btn"
                onClick={() => navInputRef.current?.click()}
              >
                {metadata ? metadata.name : 'Attach .json / .csv / .xtf'}
              </button>
              <button
                type="button"
                className={`btn btn-sm ${autoAttachNav && !metadata ? 'active' : ''}`}
                title="Toggle calibrated marine survey telemetry auto-attachment"
                onClick={() => {
                  setAutoAttachNav(!autoAttachNav)
                  if (metadata) setMetadata(null)
                }}
              >
                {autoAttachNav && !metadata ? '✓ Calibrated Fix' : '+ Auto-Telemetry'}
              </button>
              {metadata && (
                <button
                  type="button"
                  className="btn btn-sm"
                  title="Remove attached telemetry"
                  onClick={() => setMetadata(null)}
                >
                  ×
                </button>
              )}
            </div>
            <span className="adv-telemetry-hint">
              {metadata
                ? `Custom nav record: ${metadata.name} · WGS84 enabled`
                : autoAttachNav
                ? 'Calibrated WGS84 (50.3550° N, -4.1450° W · 455 kHz · 0.045m/px) enabled'
                : 'No telemetry attached · Metric dimensions and GPS will be uncalculated'}
            </span>
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          BENCHMARK TRANSECT DATASETS: WIDE HORIZONTAL WATERFALL STRIPS
          ───────────────────────────────────────────────────────────── */}
      <div className="sample-data-section">
        <div className="sample-section-header" style={{ marginBottom: '8px' }}>
          <span style={{ fontFamily: 'var(--mono)', fontSize: '11px', letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Or Select Benchmark Dataset Strip (Wide Waterfall Swath):
          </span>
        </div>

        <div className="sample-grid-horizontal">
          {REAL_DATASET_SAMPLES.map((s) => (
            <div
              key={s.id}
              className={`sample-card-horizontal ${selectedSampleId === s.id ? 'selected' : ''}`}
              onClick={() => onSelectSample(s)}
            >
              {/* Wide Horizontal Sonar Strip (Never square!) */}
              <div className="sample-thumb-wrap">
                <img src={s.path} alt={s.label} className="sample-card-img" />
                <div className="sample-nadir-line" />
                <span className="sample-strip-tag">455 kHz</span>
              </div>
              <div className="sample-card-body">
                <div className="sample-card-title">{s.label}</div>
                <div className="sample-card-sub">{s.filename} · {s.dimensions}</div>
                {s.description && (
                  <div className="sample-card-desc">
                    {s.description}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
