import { useEffect, useState } from 'react'
import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { health } from './api'
import MapView from './pages/MapView'
import Result from './pages/Result'
import Upload from './pages/Upload'

export default function App() {
  const location = useLocation()
  const runId = location.pathname.match(/^\/runs\/([^/]+)/)?.[1]
  const [modelOk, setModelOk] = useState<boolean | null>(null)

  useEffect(() => {
    health()
      .then((h) => setModelOk(Boolean(h.model_loaded)))
      .catch(() => setModelOk(false))
  }, [])

  return (
    <div className="app">
      <header className="topbar">
        <NavLink to="/" className="brand" end>
          <span className="brand-mark">AX</span>
          <span>
            <span className="brand-name">AQUAX</span>
            <span className="brand-sub">Side-scan survey intelligence</span>
          </span>
        </NavLink>
        <nav className="nav">
          <NavLink to="/" end>
            Upload
          </NavLink>
          {runId ? (
            <>
              <NavLink to={`/runs/${runId}`} end>
                Result
              </NavLink>
              <NavLink to={`/runs/${runId}/map`}>Map</NavLink>
            </>
          ) : null}
        </nav>
        <span className={`health ${modelOk ? 'ok' : modelOk === false ? 'bad' : ''}`}>
          {modelOk === null ? 'API…' : modelOk ? 'MODEL READY' : 'MODEL OFFLINE'}
        </span>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/runs/:id" element={<Result />} />
          <Route path="/runs/:id/map" element={<MapView />} />
        </Routes>
      </main>
    </div>
  )
}
