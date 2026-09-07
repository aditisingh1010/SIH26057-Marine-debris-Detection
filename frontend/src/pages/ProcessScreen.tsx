import { useEffect, useState } from 'react'

const STEPS = ['Preprocessing', 'Detection', 'Filtering', 'Report']

export default function ProcessScreen({ image, name }: { image?: string | null; name?: string | null }) {
  const [i, setI] = useState(0)
  useEffect(() => {
    const t = window.setInterval(() => setI((n) => Math.min(n + 1, STEPS.length - 1)), 900)
    return () => window.clearInterval(t)
  }, [])

  return (
    <div className="process-screen">
      <div className="process-stage">
        {image ? <img src={image} alt="" /> : null}
        <div className="process-scan" />
      </div>
      <div className="process-caption">
        <p className="process-mark">{STEPS[i]}</p>
        <p className="muted">{name || 'Sonar strip'}</p>
      </div>
    </div>
  )
}
