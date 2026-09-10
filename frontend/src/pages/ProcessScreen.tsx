import { useEffect, useState } from 'react'

const STAGES = [
  { step: '01/06', label: 'Ingesting side-scan sonar swath sonogram...' },
  { step: '02/06', label: 'Applying bilateral speckle filtering & nadir blanking...' },
  { step: '03/06', label: 'Running tiled YOLOv8 acoustic inference...' },
  { step: '04/06', label: 'Verifying acoustic shadow geometry & estimating 3D height...' },
  { step: '05/06', label: 'Computing towfish navigation & honest georeferencing...' },
  { step: '06/06', label: 'Compiling hydrographic contact registry & risk triage...' },
]

export default function ProcessScreen({
  image,
  name,
}: {
  image?: string | null
  name?: string | null
}) {
  const [stageIdx, setStageIdx] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setStageIdx((prev) => (prev < STAGES.length - 1 ? prev + 1 : prev))
    }, 450)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="process-screen">
      <div className="process-stage">
        {image ? (
          <img src={image} alt="Processing sonar strip" />
        ) : (
          <div className="process-placeholder">
            <span className="mono text-cyan" style={{ fontSize: '13px', letterSpacing: '0.1em' }}>
              ACOUSTIC SIGNAL INGESTION
            </span>
          </div>
        )}
        <div className="process-scan" />
        <div className="process-grid-overlay" />
      </div>

      <div className="process-caption">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="badge badge-cyan mono">{STAGES[stageIdx].step}</span>
            <span className="process-mark mono">{STAGES[stageIdx].label}</span>
          </div>
          <p className="mono text-dim" style={{ fontSize: '11px', marginTop: '4px' }}>
            Target: <span className="text-muted">{name || 'SSS Waterfall Strip'}</span> · Towfish Altitude: 12.5m · Range: 75m
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div className="ws-dot online" />
          <span className="mono text-cyan" style={{ fontSize: '11px' }}>
            Medha Acoustic Engine Active
          </span>
        </div>
      </div>
    </div>
  )
}
