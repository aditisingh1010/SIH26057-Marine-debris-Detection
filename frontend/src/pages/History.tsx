import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getRuns } from '../api'
import type { RunSummary } from '../types'

function formatWhen(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString()
}

export default function History() {
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    getRuns()
      .then(setRuns)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="history-page-shell">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '16px', fontWeight: 700, textTransform: 'uppercase' }}>
            Survey Operations History
          </h1>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--mono)', marginTop: '2px' }}>
            Historical side-scan sonar runs and contact registry
          </p>
        </div>

        <Link className="btn btn-primary" to="/analyze">
          New Analysis
        </Link>
      </div>

      {loading && (
        <div className="marine-panel" style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
          Loading survey archives…
        </div>
      )}

      {!loading && runs.length === 0 && (
        <div className="marine-panel" style={{ textAlign: 'center', padding: '48px 24px' }}>
          <h3 style={{ fontSize: '14px', marginBottom: '8px' }}>No Survey Runs Recorded</h3>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Upload or select a sonar waterfall image on the Analyze page to record a survey run.
          </p>
          <Link className="btn btn-primary" to="/analyze">
            Analyze Sonar Image
          </Link>
        </div>
      )}

      {!loading && runs.length > 0 && (
        <table className="sonar-table">
          <thead>
            <tr>
              <th>Date & Time</th>
              <th>Sonar File</th>
              <th>Survey ID</th>
              <th>Detections</th>
              <th>Navigation</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr
                key={run.id}
                onClick={() => navigate(`/runs/${run.id}`)}
              >
                <td style={{ color: 'var(--text-muted)', fontFamily: 'var(--mono)', fontSize: '11px' }}>
                  {formatWhen(run.created_at)}
                </td>
                <td style={{ fontWeight: 600, color: 'var(--text)' }}>
                  {run.filename}
                </td>
                <td style={{ fontFamily: 'var(--mono)', fontSize: '11px', color: 'var(--accent)' }}>
                  {run.id}
                </td>
                <td style={{ fontFamily: 'var(--mono)', fontWeight: 700 }}>
                  {run.detection_count}
                </td>
                <td>
                  {run.geolocation_available ? (
                    <span style={{ color: '#22C55E', fontSize: '11px', fontFamily: 'var(--mono)' }}>
                      Geolocated
                    </span>
                  ) : (
                    <span style={{ color: 'var(--text-muted)', fontSize: '11px', fontStyle: 'italic' }}>
                      No GPS
                    </span>
                  )}
                </td>
                <td>
                  <span style={{ fontSize: '10px', padding: '2px 6px', background: 'var(--panel-2)', border: '1px solid var(--border)', borderRadius: '3px' }}>
                    Complete
                  </span>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: '6px' }} onClick={(e) => e.stopPropagation()}>
                    <Link className="btn btn-sm" to={`/runs/${run.id}`}>
                      View
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
