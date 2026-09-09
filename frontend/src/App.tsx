import { lazy, Suspense, useEffect, useState } from 'react'
import { Navigate, NavLink, Route, Routes, useLocation, useParams } from 'react-router-dom'
import { health } from './api'
import Detect from './pages/Detect'
import ErrorBoundary from './ErrorBoundary.tsx'
import './App.css'

const History = lazy(() => import('./pages/History'))
const MapView = lazy(() => import('./pages/MapView'))
const Result = lazy(() => import('./pages/Result'))
const DetectionList = lazy(() => import('./pages/DetectionList'))
const Batch = lazy(() => import('./pages/Batch'))

function RunToMap() {
  const { id } = useParams()
  return <Navigate to={`/map?run=${id}`} replace />
}

/** Kept so a stale HMR bundle that still references this name cannot crash the app. */
function RunToDetect() {
  return <Result />
}

type Theme = 'light' | 'dark'

function readTheme(): Theme {
  try {
    const saved = localStorage.getItem('aquax-theme') ?? localStorage.getItem('sonar-aqua-theme')
    if (saved === 'dark' || saved === 'light') return saved
  } catch {
    /* ignore */
  }
  return 'light'
}

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute('data-theme', theme)
  try {
    localStorage.setItem('aquax-theme', theme)
  } catch {
    /* ignore */
  }
}

export default function App() {
  const { pathname } = useLocation()
  const [theme, setTheme] = useState<Theme>(() => readTheme())
  const [modelOk, setModelOk] = useState<boolean | null>(null)
  const [modelName, setModelName] = useState<string | null>(null)
  const [inferenceMode, setInferenceMode] = useState<string>('real')

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

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
            <span className="brand-name">AquaX</span>
            <span className="brand-sub">Marine debris detection</span>
          </span>
        </NavLink>
        <nav className="nav">
          <NavLink to="/" end>Detect</NavLink>
          <NavLink to="/runs" className={pathname === '/runs' ? 'active' : ''}>Runs</NavLink>
          <NavLink to="/map">Map</NavLink>
        </nav>
        <div className="topbar-end">
          <button
            type="button"
            className="theme-toggle"
            onClick={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
            aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          >
            {theme === 'light' ? 'Dark' : 'Light'}
          </button>
          <span className={`health ${modelOk ? (isMock ? 'mock' : 'ok') : modelOk === false ? 'bad' : ''}`}>
            {modelOk === null
              ? 'APIâ€¦'
              : modelOk
              ? `${modelName || 'model'} Â· ${isMock ? 'mock' : 'real'}`
              : 'offline'}
          </span>
        </div>
      </header>
      <main className="main">
        <ErrorBoundary>
          <Suspense fallback={<p className="muted">Loadingâ€¦</p>}>
            <Routes>
              <Route path="/" element={<Detect />} />
              <Route path="/runs" element={<History />} />
              <Route path="/map" element={<MapView />} />
              <Route path="/batch" element={<Batch />} />
              <Route path="/history" element={<Navigate to="/runs" replace />} />
              <Route path="/runs/:id/map" element={<RunToMap />} />
              <Route path="/runs/:id/list" element={<DetectionList />} />
              <Route path="/runs/:id" element={<RunToDetect />} />
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </main>
    </div>
  )
}
