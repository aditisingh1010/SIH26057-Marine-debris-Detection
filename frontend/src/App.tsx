import { useEffect, useState } from 'react'
import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { health } from './api'
import History from './pages/History'
import MapView from './pages/MapView'
import Result from './pages/Result'
import Upload from './pages/Upload'
import './App.css'

export default function App() {
  const location = useLocation()
  const runId = location.pathname.match(/^\/runs\/([^/]+)/)?.[1]
  const [modelOk, setModelOk] = useState<boolean | null>(null)
  const [modelName, setModelName] = useState<string | null>(null)
  const [inferenceMode, setInferenceMode] = useState<string>('real')

  useEffect(() => {
    health()
      .then((h) => {
        setModelOk(Boolean(h.model_loaded))
        if (h.model_path) setModelName(h.model_path)
        if (h.inference_mode) setInferenceMode(h.inference_mode)
      })
      .catch(() => setModelOk(false))
  }, [])

  const isMock = inferenceMode === 'mock'

  return (
    <div className="app">
      <header className="topbar">
        <NavLink to="/" className="brand" end>
          <span className="brand-mark">AX</span>
          <span>
            <span className="brand-name">AQUAX</span>
            <span className="brand-sub">Marine debris detection</span>
          </span>
        </NavLink>
        <nav className="nav">
          <NavLink to="/" end>Upload</NavLink>
          <NavLink to="/history">History</NavLink>
          {runId ? (
            <>
              <NavLink to={`/runs/${runId}`} end>Result</NavLink>
              <NavLink to={`/runs/${runId}/map`}>Map</NavLink>
            </>
          ) : null}
        </nav>
        <span className={`health ${modelOk ? (isMock ? 'mock' : 'ok') : modelOk === false ? 'bad' : ''}`}>
          {modelOk === null
            ? 'API…'
            : modelOk
            ? `YOLOv8n (${modelName || 'best.pt'}) | ${isMock ? 'MOCK' : 'REAL'}`
            : 'MODEL OFFLINE'}
        </span>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/history" element={<History />} />
          <Route path="/runs/:id" element={<Result />} />
          <Route path="/runs/:id/map" element={<MapView />} />
        </Routes>
      </main>
    </div>
  )
}
