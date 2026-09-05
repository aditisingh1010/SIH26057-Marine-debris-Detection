import { useState } from 'react'
import { Link } from 'react-router-dom'
import { detectBatch } from '../api'
import type { BatchResult } from '../types'

export default function Batch() {
  const [files, setFiles] = useState<File[]>([])
  const [mode, setMode] = useState<'demo' | 'survey'>('survey')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<BatchResult | null>(null)

  async function onRun() {
    if (!files.length || busy) return
    setBusy(true)
    setError(null)
    try {
      const conf = mode === 'demo' ? 0.25 : 0.10
      const data = await detectBatch(files.slice(0, 10), conf, mode)
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="hero">
        <p className="kicker">Line survey</p>
        <h1>Batch a sonar strip, then triage the briefing.</h1>
        <p className="lede">
          Up to 10 waterfall images in one pass. Each file gets its own run, overlay, and JSON/CSV report.
          No coordinates unless you attach nav metadata on single-image upload.
        </p>
      </div>

      <section className="panel">
        <input
          type="file"
          multiple
          accept=".png,.jpg,.jpeg,.tif,.tiff,.bmp"
          onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
        />
        <p className="muted" style={{ marginTop: 8 }}>
          {files.length ? `${files.length} file(s) selected` : 'Select several sonar images'}
        </p>
        <div className="mode-picker-grid" style={{ marginTop: 12, maxWidth: 420 }}>
          <button
            type="button"
            className={`mode-card ${mode === 'demo' ? 'mode-card-active' : ''}`}
            onClick={() => setMode('demo')}
          >
            <strong>Demo</strong>
            <span>Fewer boxes for a clean strip overview.</span>
          </button>
          <button
            type="button"
            className={`mode-card ${mode === 'survey' ? 'mode-card-active' : ''}`}
            onClick={() => setMode('survey')}
          >
            <strong>Survey</strong>
            <span>Keep weaker candidates for operator review.</span>
          </button>
        </div>
        <div className="submit-section" style={{ marginTop: 16 }}>
          <button type="button" className="btn btn-primary" onClick={onRun} disabled={!files.length || busy}>
            {busy ? 'Running batch…' : 'Run batch detection'}
          </button>
        </div>
        {error ? <div className="error"><strong>Batch error:</strong> {error}</div> : null}
      </section>

      {result ? (
        <section className="panel" style={{ marginTop: 16 }}>
          <h2>Batch result</h2>
          <p className="muted">
            {result.total} files · {result.failed} failed
          </p>
          {result.errors.length > 0 ? (
            <ul className="quality-list">
              {result.errors.map((item) => <li key={item}>{item}</li>)}
            </ul>
          ) : null}
          <table className="history-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Kept</th>
                <th>Review queue</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {result.runs.map((run) => (
                <tr key={run.id} className="history-row">
                  <td>
                    <span className="history-filename">{run.filename}</span>
                    <span className="history-id">{run.id}</span>
                  </td>
                  <td>{run.operator_briefing?.kept ?? run.detections.length}</td>
                  <td>{run.operator_briefing?.review_queue_count ?? 0}</td>
                  <td>
                    <Link className="btn btn-secondary" to={`/runs/${run.id}`}>Open</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </div>
  )
}
