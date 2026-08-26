import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { detect } from '../api'

function fileFormat(file: File): string {
  const ext = file.name.split('.').pop()
  if (ext && ext !== file.name) return ext.toLowerCase()
  return file.type || 'unknown'
}

function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function Upload() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [metadata, setMetadata] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onRun() {
    if (!file || busy) return
    setBusy(true)
    setError(null)
    try {
      const run = await detect(file, metadata)
      navigate(`/runs/${run.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <h2>Upload sonar image</h2>
      <label htmlFor="sonar-file">Sonar image</label>
      <input
        id="sonar-file"
        type="file"
        accept=".png,.jpg,.jpeg,.tif,.tiff"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <label htmlFor="meta-file">Metadata (optional)</label>
      <input
        id="meta-file"
        type="file"
        accept=".json,.csv"
        onChange={(e) => setMetadata(e.target.files?.[0] ?? null)}
      />

      {file ? (
        <ul className="meta-list">
          <li>
            Filename: <strong>{file.name}</strong>
          </li>
          <li>
            Format: <strong>{fileFormat(file)}</strong>
          </li>
          <li>
            Size: <strong>{fileSize(file.size)}</strong>
          </li>
          <li>
            Metadata: <strong>{metadata ? `attached (${metadata.name})` : 'not attached'}</strong>
          </li>
        </ul>
      ) : (
        <p className="muted">Select a PNG, JPEG, or TIFF sonar image to run detection.</p>
      )}

      <button type="button" onClick={onRun} disabled={!file || busy}>
        {busy ? 'Running detection…' : 'Run detection'}
      </button>
      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}
