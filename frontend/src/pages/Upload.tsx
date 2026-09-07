import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { detect } from '../api'

const MODE_PRESETS = {
  demo: { id: 'demo' as const, title: 'Demo', conf: 0.25 },
  survey: { id: 'survey' as const, title: 'Survey', conf: 0.10 },
  custom: { id: 'custom' as const, title: 'Custom', conf: 0.15 },
}

const SAMPLES = [
  { path: '/samples/sample_shipwreck.jpg', name: 'shipwreck.jpg', label: 'Wreck' },
  { path: '/samples/sample_ghost_pot.jpg', name: 'ghost_pot.jpg', label: 'Pot' },
  { path: '/samples/sample_pipeline.jpg', name: 'pipeline.jpg', label: 'Pipe' },
]

export default function Upload() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [metadata, setMetadata] = useState<File | null>(null)
  const [detectionMode, setDetectionMode] = useState<'demo' | 'survey' | 'custom'>('demo')
  const [confThreshold, setConfThreshold] = useState<number>(MODE_PRESETS.demo.conf)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)

  useEffect(() => {
    /* keep file input in sync visually only */
  }, [file])

  async function loadSampleImage(path: string, filename: string) {
    try {
      setError(null)
      const res = await fetch(path)
      if (!res.ok) throw new Error(`Could not load ${filename}`)
      const blob = await res.blob()
      setFile(new File([blob], filename, { type: blob.type || 'image/jpeg' }))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  async function onRun() {
    if (!file || busy) return
    setBusy(true)
    setError(null)
    try {
      const run = await detect(file, metadata, confThreshold, detectionMode)
      navigate(`/runs/${run.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  function prevent(e: React.DragEvent) {
    e.preventDefault()
    e.stopPropagation()
  }

  return (
    <div className="sheet">
      <h1 className="sheet-title">Detect debris on a sonar strip</h1>
      <p className="sheet-lede">
        Drop an image, pick Demo or Survey, run. Map pins appear only if you attach navigation data.
      </p>

      {busy ? (
        <p className="sheet-busy">
          <span className="step-spinner" />
          Working…
        </p>
      ) : (
        <>
          <label
            className={`drop ${dragOver ? 'drop-active' : ''}`}
            onDragEnter={(e) => { prevent(e); setDragOver(true) }}
            onDragLeave={(e) => { prevent(e); setDragOver(false) }}
            onDragOver={prevent}
            onDrop={(e) => {
              prevent(e)
              setDragOver(false)
              if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0])
            }}
          >
            <input
              type="file"
              accept=".png,.jpg,.jpeg,.tif,.tiff,.bmp"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <strong>{file ? file.name : 'Drop a sonar image here'}</strong>
            <span className="muted">{file ? 'Click to replace' : 'PNG, JPEG, or TIFF'}</span>
          </label>

          <p className="sample-row">
            Try
            {SAMPLES.map((s, i) => (
              <span key={s.path}>
                {i > 0 ? ', ' : ' '}
                <button type="button" className="text-link" onClick={() => loadSampleImage(s.path, s.name)}>
                  {s.label}
                </button>
              </span>
            ))}
            .
          </p>

          <div className="sheet-row">
            <div className="seg" role="radiogroup" aria-label="Mode">
              {(Object.values(MODE_PRESETS)).map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  className={detectionMode === preset.id ? 'seg-on' : ''}
                  onClick={() => {
                    setDetectionMode(preset.id)
                    setConfThreshold(preset.conf)
                  }}
                >
                  {preset.title}
                </button>
              ))}
            </div>
            <span className="muted">{Math.round(confThreshold * 100)}%</span>
          </div>

          {detectionMode === 'custom' ? (
            <input
              type="range"
              min="0.05"
              max="0.50"
              step="0.05"
              value={confThreshold}
              onChange={(e) => setConfThreshold(parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--text)' }}
            />
          ) : null}

          <label className="nav-attach">
            Navigation file (optional)
            <input
              type="file"
              accept=".json,.csv,.xtf"
              onChange={(e) => setMetadata(e.target.files?.[0] ?? null)}
            />
            <span className="muted">{metadata ? metadata.name : 'None — location will be unavailable'}</span>
          </label>

          <button type="button" className="btn btn-primary run-btn" onClick={onRun} disabled={!file}>
            Detect
          </button>

          {error ? <div className="error">{error}</div> : null}
        </>
      )}
    </div>
  )
}
