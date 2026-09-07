import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { detect, getRun, imageUrl, reportUrl } from '../api'
import ProcessScreen from './ProcessScreen'
import type { Detection, RunResult } from '../types'
import { formatConfidence, getRiskLevel } from '../utils'

const MODES = {
  demo: { id: 'demo' as const, conf: 0.25 },
  survey: { id: 'survey' as const, conf: 0.10 },
  custom: { id: 'custom' as const, conf: 0.15 },
}

const SAMPLE = { path: '/samples/sample_shipwreck.jpg', name: 'wreck.jpg' }

export default function Detect() {
  const location = useLocation()
  const navigate = useNavigate()
  const runId = new URLSearchParams(location.search).get('run')
  const [file, setFile] = useState<File | null>(null)
  const [metadata, setMetadata] = useState<File | null>(null)
  const [mode, setMode] = useState<'demo' | 'survey' | 'custom'>('demo')
  const [conf, setConf] = useState(0.25)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [run, setRun] = useState<RunResult | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const imageInput = useRef<HTMLInputElement>(null)

  const previewUrl = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl) }, [previewUrl])

  useEffect(() => {
    if (!runId) {
      setRun(null)
      return
    }
    let cancelled = false
    getRun(runId)
      .then((data) => {
        if (cancelled) return
        setRun(data)
        setFile(null)
        setSelected(data.detections?.[0]?.id ?? null)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      })
    return () => { cancelled = true }
  }, [runId])

  async function onDetect() {
    if (!file || busy) return
    setBusy(true)
    setError(null)
    try {
      const result = await detect(file, metadata, conf, mode)
      navigate(`/runs/${result.id}`, { state: { run: result } })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  function takeFile(next: File | null) {
    setFile(next)
    setRun(null)
    navigate('/')
    setError(null)
  }

  if (busy) return <ProcessScreen image={previewUrl} name={file?.name} />

  const stageSrc = previewUrl || (run ? imageUrl(run.id) : SAMPLE.path)
  const detections = run?.detections ?? []
  const w = run?.image_width ?? 800
  const h = run?.image_height ?? 336
  const located = detections.filter((d) => d.geolocation.latitude != null && d.geolocation.longitude != null).length

  return (
    <div className="workspace">
      <section
        className={`stage ${dragOver ? 'stage-hot' : ''}`}
        onClick={() => imageInput.current?.click()}
        onDragEnter={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={(e) => { e.preventDefault(); setDragOver(false) }}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          if (e.dataTransfer.files[0]) takeFile(e.dataTransfer.files[0])
        }}
      >
        <input
          ref={imageInput}
          className="sr-only"
          type="file"
          accept=".png,.jpg,.jpeg,.tif,.tiff,.bmp"
          onChange={(e) => takeFile(e.target.files?.[0] ?? null)}
        />
        <div
          className={`stage-frame ${!run && !file ? 'stage-empty' : ''}`}
          style={run || file ? { aspectRatio: `${w} / ${h}` } : undefined}
        >
          <img src={stageSrc} alt={file?.name || run?.filename || 'sonar stage'} />
          {run ? (
            <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="xMidYMid meet" onClick={(e) => e.stopPropagation()}>
              {detections.map((d) => (
                <Box key={d.id} d={d} active={d.id === selected} onPick={() => setSelected(d.id)} />
              ))}
            </svg>
          ) : null}
          {!run && !file ? (
            <p className="stage-hint">Drop a sonar strip on the stage</p>
          ) : null}
        </div>
      </section>

      <aside className="dock">
        <p className="dock-kicker">Detect</p>
        <p className="dock-note">
          {file ? file.name : run ? run.filename : 'Click the stage to attach a strip'}
        </p>

        <div className="seg">
          {(['demo', 'survey', 'custom'] as const).map((id) => (
            <button
              key={id}
              type="button"
              className={mode === id ? 'seg-on' : ''}
              onClick={() => {
                setMode(id)
                setConf(MODES[id].conf)
              }}
            >
              {id[0].toUpperCase() + id.slice(1)}
            </button>
          ))}
        </div>
        {mode === 'custom' ? (
          <div className="ruler">
            <input
              className="ruler-input"
              type="range"
              min="0.05"
              max="0.50"
              step="0.05"
              value={conf}
              onChange={(e) => setConf(parseFloat(e.target.value))}
              aria-label="Confidence"
            />
            <div className="ruler-scale" aria-hidden="true">
              <span style={{ left: '0%' }}>5</span>
              <span style={{ left: '11%' }}>10</span>
              <span className="ruler-major" style={{ left: '44%' }}>25</span>
              <span style={{ left: '100%' }}>50</span>
            </div>
            <p className="dock-note">{Math.round(conf * 100)}%</p>
          </div>
        ) : (
          <p className="muted dock-note">{Math.round(conf * 100)}% keep</p>
        )}

        <label className="ticket">
          <input
            className="sr-only"
            type="file"
            accept=".json,.csv,.xtf"
            onChange={(e) => setMetadata(e.target.files?.[0] ?? null)}
          />
          <span className="ticket-k">Navigation</span>
          <span>{metadata ? metadata.name : 'Attach if you have lat/lon'}</span>
        </label>

        <button type="button" className="btn btn-primary run-btn" disabled={!file || busy} onClick={onDetect}>
          {busy ? 'Working…' : 'Detect'}
        </button>

        {error ? <div className="error">{error}</div> : null}

        {run ? (
          <div className="dock-result">
            <p>
              {detections.length} kept
              {located ? ` · ${located} on map` : ' · no location'}
            </p>
            <p>
              <a href={reportUrl(run.id, 'json')}>JSON</a>
              {' · '}
              <a href={reportUrl(run.id, 'csv')}>CSV</a>
              {located ? (
                <>
                  {' · '}
                  <Link to={`/map?run=${run.id}`}>Map</Link>
                </>
              ) : null}
            </p>
            <ul className="dock-list">
              {detections.map((d) => (
                <li key={d.id}>
                  <button
                    type="button"
                    className={d.id === selected ? 'text-link' : 'text-link muted'}
                    onClick={() => setSelected(d.id)}
                  >
                    {d.class.replace(/_/g, ' ')} {formatConfidence(d.confidence)}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="muted dock-note">
            Try{' '}
            <button type="button" className="text-link" onClick={() => fetch(SAMPLE.path).then((r) => r.blob()).then((b) => takeFile(new File([b], SAMPLE.name, { type: 'image/jpeg' })))}>
              wreck
            </button>
            .
          </p>
        )}
      </aside>
    </div>
  )
}

function Box({ d, active, onPick }: { d: Detection; active: boolean; onPick: () => void }) {
  const risk = getRiskLevel(d)
  const stroke = risk === 'High' ? '#b42318' : risk === 'Medium' ? '#8a5a10' : '#e8e0d4'
  return (
    <g onClick={onPick} style={{ cursor: 'pointer' }}>
      <rect
        x={d.bbox.x}
        y={d.bbox.y}
        width={d.bbox.width}
        height={d.bbox.height}
        fill={active ? 'rgba(232,224,212,0.16)' : 'rgba(232,224,212,0.05)'}
        stroke={stroke}
        strokeWidth={active ? 3 : 2}
      />
      <text x={d.bbox.x + 4} y={Math.max(14, d.bbox.y - 4)} fill={stroke} fontSize="12" fontFamily="IBM Plex Mono, monospace">
        {d.class.replace(/_/g, ' ')} {formatConfidence(d.confidence)}
      </text>
    </g>
  )
}
