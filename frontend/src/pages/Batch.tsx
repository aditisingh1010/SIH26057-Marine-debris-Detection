import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { detectBatch } from '../api'
import type { BatchResult, RunResult } from '../types'

const BATCH_STORAGE_KEY = 'marine_last_batch'

export default function Batch() {
  const navigate = useNavigate()
  const [files, setFiles] = useState<File[]>([])
  const [mode, setMode] = useState<'demo' | 'survey'>('survey')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Initialize result from sessionStorage to prevent loss on navigation
  const [result, setResult] = useState<BatchResult | null>(() => {
    try {
      const saved = sessionStorage.getItem(BATCH_STORAGE_KEY)
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })

  async function onRun(filesToRun?: File[]) {
    const targets = filesToRun || files
    if (!targets.length || busy) return
    setBusy(true)
    setError(null)
    try {
      const conf = mode === 'demo' ? 0.25 : 0.10
      const data = await detectBatch(targets.slice(0, 10), conf, mode)
      setResult(data)
      try {
        sessionStorage.setItem(BATCH_STORAGE_KEY, JSON.stringify(data))
      } catch {
        /* ignore storage quota */
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  async function onLoadSampleBatch() {
    setBusy(true)
    setError(null)
    try {
      const samples = [
        { path: '/dataset/0015_2010.jpg', name: '0015_2010.jpg' },
        { path: '/dataset/0021_2018.jpg', name: '0021_2018.jpg' },
        { path: '/dataset/0080_2018.jpg', name: '0080_2018.jpg' },
        { path: '/dataset/0001_2010.jpg', name: '0001_2010.jpg' },
      ]
      const loaded = await Promise.all(
        samples.map(async (s) => {
          const res = await fetch(s.path)
          if (!res.ok) throw new Error(`Could not load ${s.name}`)
          const blob = await res.blob()
          return new File([blob], s.name, { type: 'image/jpeg' })
        })
      )
      setFiles(loaded)
      onRun(loaded)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setBusy(false)
    }
  }

  function onClearBatch() {
    setResult(null)
    setFiles([])
    try {
      sessionStorage.removeItem(BATCH_STORAGE_KEY)
    } catch {
      /* ignore */
    }
  }

  function openRun(run: RunResult, idx: number) {
    if (!result) return
    navigate(`/runs/${run.id}`, {
      state: {
        run,
        batchRuns: result.runs,
        batchIndex: idx,
        from: 'batch',
      },
    })
  }

  return (
    <div className="history-page-shell">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '16px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Batch Sonar Survey
          </h1>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
            Multi-image survey line processing (up to 10 sonar strips per pass)
          </p>
        </div>

        {result && (
          <button
            type="button"
            className="btn btn-sm"
            onClick={onClearBatch}
            title="Clear stored batch survey results"
          >
            Clear Batch
          </button>
        )}
      </div>

      <section className="marine-panel">
        <div style={{ marginBottom: '12px' }}>
          <input
            type="file"
            multiple
            accept=".png,.jpg,.jpeg,.tif,.tiff,.bmp"
            onClick={(e) => { (e.target as HTMLInputElement).value = '' }}
            onChange={(e) => {
              const list = Array.from(e.target.files ?? [])
              setFiles(list)
              if (list.length) onRun(list)
            }}
            style={{ color: 'var(--text-muted)', fontSize: '12px' }}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            {files.length ? `${files.length} file(s) queued for survey line analysis` : 'Choose multiple sonar waterfall files'}
          </p>

          <button
            type="button"
            className="btn btn-sm"
            onClick={onLoadSampleBatch}
            disabled={busy}
            style={{ fontSize: '11px' }}
          >
            Load 4 Real Dataset Images
          </button>
        </div>

        <div style={{ display: 'flex', gap: '8px', marginTop: '14px' }}>
          <button
            type="button"
            className={`btn btn-sm ${mode === 'demo' ? 'btn-primary' : ''}`}
            onClick={() => setMode('demo')}
          >
            Demo (0.25 gate)
          </button>
          <button
            type="button"
            className={`btn btn-sm ${mode === 'survey' ? 'btn-primary' : ''}`}
            onClick={() => setMode('survey')}
          >
            Survey (0.10 recall)
          </button>
        </div>

        <div style={{ marginTop: '16px' }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => onRun()}
            disabled={!files.length || busy}
          >
            {busy ? 'Processing Survey Batch…' : 'Process Survey Batch →'}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: '12px', color: 'var(--risk-crit)', fontSize: '12px' }}>
            <strong>Error:</strong> {error}
          </div>
        )}
      </section>

      {result && (
        <section className="marine-panel" style={{ marginTop: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div>
              <h2 style={{ fontSize: '13px', fontWeight: 600, textTransform: 'uppercase' }}>
                Batch Analysis Results
              </h2>
              <span style={{ fontSize: '10px', color: 'var(--accent)', fontFamily: 'var(--mono)' }}>
                Click any row to inspect detections in Result viewer
              </span>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {result.total} files · {result.failed} failed
            </span>
          </div>

          <table className="sonar-table">
            <thead>
              <tr>
                <th>Sonar Strip</th>
                <th>Survey ID</th>
                <th>Contacts Kept</th>
                <th>Review Queue</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {result.runs.map((run, idx) => (
                <tr
                  key={run.id}
                  onClick={() => openRun(run, idx)}
                  style={{ cursor: 'pointer' }}
                >
                  <td style={{ fontWeight: 600 }}>{run.filename}</td>
                  <td style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--accent)' }}>
                    {run.id}
                  </td>
                  <td style={{ fontFamily: 'var(--mono)', fontWeight: 700 }}>
                    {run.operator_briefing?.kept ?? run.detections.length}
                  </td>
                  <td style={{ fontFamily: 'var(--mono)', color: 'var(--text-muted)' }}>
                    {run.operator_briefing?.review_queue_count ?? 0}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        openRun(run, idx)
                      }}
                    >
                      Open →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  )
}
