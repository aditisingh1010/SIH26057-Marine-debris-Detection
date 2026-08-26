import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { detect } from '../api'

function fileFormat(file: File): string {
  const ext = file.name.split('.').pop()
  if (ext && ext !== file.name) return ext.toUpperCase()
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
    <div>
      <div className="hero">
        <p className="kicker">SIH26057 · Side-scan sonar</p>
        <h1>Ingest a seafloor strip. Get boxed anomalies and a report.</h1>
        <p className="lede">
          AquaX runs your trained detector on SSS imagery — not camera photos.
          Location is written only when navigation metadata is attached. Coordinates
          are never invented.
        </p>
      </div>

      <div className="grid-2">
        <section className="panel">
          <label className="drop">
            <input
              type="file"
              accept=".png,.jpg,.jpeg,.tif,.tiff"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <strong>{file ? 'Replace sonar image' : 'Drop or choose sonar image'}</strong>
            <span className="muted">PNG, JPEG, or TIFF</span>
          </label>

          {file ? (
            <div className="meta-grid">
              <div>
                <span>Filename</span>
                <strong>{file.name}</strong>
              </div>
              <div>
                <span>Format</span>
                <strong>{fileFormat(file)}</strong>
              </div>
              <div>
                <span>Size</span>
                <strong>{fileSize(file.size)}</strong>
              </div>
              <div>
                <span>Metadata</span>
                <strong>{metadata ? metadata.name : 'Not attached'}</strong>
              </div>
            </div>
          ) : (
            <p className="muted">No file selected yet.</p>
          )}

          <label className="muted" htmlFor="meta-file">
            Optional JSON/CSV navigation metadata (lat, lon)
          </label>
          <input
            id="meta-file"
            type="file"
            accept=".json,.csv"
            onChange={(e) => setMetadata(e.target.files?.[0] ?? null)}
          />

          <div>
            <button type="button" onClick={onRun} disabled={!file || busy}>
              {busy ? 'Running detection…' : 'Run detection'}
            </button>
          </div>
          {error ? <p className="error">{error}</p> : null}
        </section>

        <aside className="panel">
          <p className="kicker">What you get</p>
          <h2 style={{ marginTop: 0 }}>Report a survey team can use</h2>
          <p className="muted">
            Bounding boxes on the sonar image, class and confidence from{' '}
            <code>best.pt</code>, JSON and CSV download. Map markers appear only
            when the metadata file contains real coordinates.
          </p>
        </aside>
      </div>
    </div>
  )
}
