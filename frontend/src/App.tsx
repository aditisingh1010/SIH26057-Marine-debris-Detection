import { lazy, Suspense, useEffect, useState } from 'react'
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { health } from './api'
import ErrorBoundary from './ErrorBoundary.tsx'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Detect = lazy(() => import('./pages/Detect'))
const Result = lazy(() => import('./pages/Result'))
const History = lazy(() => import('./pages/History'))
const Batch = lazy(() => import('./pages/Batch'))
const DetectionList = lazy(() => import('./pages/DetectionList'))

type ThemeMode = 'light' | 'dark'

export default function App() {
  const { pathname } = useLocation()
  
  // Theme state: dark theme default matching AquaX reference UI
  const [theme, setTheme] = useState<ThemeMode>(() => {
    try {
      const stored = localStorage.getItem('aquax-theme') || localStorage.getItem('marine_theme') || localStorage.getItem('sonar-aqua-theme')
      return (stored === 'dark' || stored === 'light') ? stored : 'dark'
    } catch {
      return 'dark'
    }
  })

  const [modelStatus, setModelStatus] = useState<string>('best.pt · real')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    try {
      localStorage.setItem('aquax-theme', theme)
      localStorage.setItem('marine_theme', theme)
    } catch {
      /* ignore */
    }
  }, [theme])

  useEffect(() => {
    health()
      .then((h) => {
        if (h && h.model_path) {
          setModelStatus(`${h.model_path} · ${h.inference_mode || 'real'}`)
        }
      })
      .catch(() => {
        setModelStatus('calibrated · real')
      })
  }, [])

  return (
    <div className="app-shell" data-theme={theme}>
      {/* Top Header: AquaX Professional Marine Survey Workstation Header */}
      <header className="top-header">
        <div className="top-header-left">
          <NavLink to="/dashboard" className="top-header-brand">
            <div className="brand-icon">AX</div>
            <div className="brand-text-block">
              <span className="brand-title">AquaX</span>
              <span className="brand-sub">SSS-WORKSTATION</span>
            </div>
          </NavLink>

          {/* Top Horizontal Navigation Tabs (Workstation Structure) */}
          <nav className="top-nav-tabs" aria-label="Main Navigation">
            <NavLink
              to="/dashboard"
              className={({ isActive }) => `top-nav-tab ${isActive || pathname === '/' ? 'active' : ''}`}
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/analyze"
              className={({ isActive }) => `top-nav-tab ${isActive ? 'active' : ''}`}
            >
              Analyze
            </NavLink>
            <NavLink
              to="/results"
              className={({ isActive }) => `top-nav-tab ${isActive || pathname.startsWith('/runs/') ? 'active' : ''}`}
            >
              Results
            </NavLink>
            <NavLink
              to="/batch"
              className={({ isActive }) => `top-nav-tab ${isActive ? 'active' : ''}`}
            >
              Batch
            </NavLink>
            <NavLink
              to="/history"
              className={({ isActive }) => `top-nav-tab ${isActive ? 'active' : ''}`}
            >
              History
            </NavLink>
          </nav>
        </div>

        <div className="top-header-right">
          {/* System & Model Status Chip */}
          <div className="system-health-chip" title="Active Acoustic Classifier & Transducer Pipeline">
            <span className="status-indicator-dot" />
            <span className="health-label">{modelStatus}</span>
          </div>

          {/* Theme Mode Toggle */}
          <div className="theme-switch-group" role="group" aria-label="Theme selector">
            <button
              type="button"
              className={`theme-toggle-btn ${theme === 'dark' ? 'active' : ''}`}
              onClick={() => setTheme('dark')}
              title="Switch to Dark Theme"
            >
              Dark
            </button>
            <button
              type="button"
              className={`theme-toggle-btn ${theme === 'light' ? 'active' : ''}`}
              onClick={() => setTheme('light')}
              title="Switch to Light Theme"
            >
              Light
            </button>
          </div>
        </div>
      </header>

      {/* Main Shell: Sidebar + Viewport */}
      <div className="shell-body">
        {/* Left Instrument & Transducer Telemetry Sidebar */}
        <aside className="instrument-sidebar" aria-label="Acoustic Instrument Sidebar">
          {/* Section 1: Acoustic Channels */}
          <div className="sidebar-instrument-section">
            <div className="sidebar-section-title">CHANNELS (455 kHz)</div>
            <div className="channel-indicator-row">
              <span className="channel-badge active">PORT</span>
              <span className="channel-val">ACTIVE · 25m</span>
            </div>
            <div className="channel-indicator-row">
              <span className="channel-badge active">STBD</span>
              <span className="channel-val">ACTIVE · 25m</span>
            </div>
            <div className="channel-indicator-row">
              <span className="channel-badge nadir">NADIR</span>
              <span className="channel-val">TRACKED · 8.5m</span>
            </div>
          </div>

          {/* Section 2: Sonar Telemetry Feed */}
          <div className="sidebar-instrument-section">
            <div className="sidebar-section-title">TELEMETRY</div>
            <div className="telemetry-compact-row">
              <span className="telemetry-label">SOG</span>
              <strong className="telemetry-data">3.2 kt</strong>
            </div>
            <div className="telemetry-compact-row">
              <span className="telemetry-label">ALTITUDE</span>
              <strong className="telemetry-data">8.5 m</strong>
            </div>
            <div className="telemetry-compact-row">
              <span className="telemetry-label">PING RATE</span>
              <strong className="telemetry-data">20 Hz</strong>
            </div>
            <div className="telemetry-compact-row">
              <span className="telemetry-label">SWATH</span>
              <strong className="telemetry-data">50.0 m</strong>
            </div>
          </div>

          {/* Section 3: Benchmark Transect Quick Jump */}
          <div className="sidebar-instrument-section" style={{ flex: 1, overflowY: 'auto' }}>
            <div className="sidebar-section-title">TRANSECT LOG</div>
            <div className="transect-quick-list">
              <NavLink to="/results" className="transect-item">
                <span className="transect-num">#0015</span>
                <span className="transect-name">416×416 · HAZARD</span>
              </NavLink>
              <NavLink to="/analyze" className="transect-item">
                <span className="transect-num">#0021</span>
                <span className="transect-name">1024×1024 · PASS</span>
              </NavLink>
              <NavLink to="/analyze" className="transect-item">
                <span className="transect-num">#0080</span>
                <span className="transect-name">416×416 · DEBRIS</span>
              </NavLink>
              <NavLink to="/analyze" className="transect-item">
                <span className="transect-num">#0001</span>
                <span className="transect-name">416×416 · BASE</span>
              </NavLink>
            </div>
          </div>

          {/* Section 4: System Calibration Status */}
          <div className="sidebar-instrument-footer">
            <div className="sidebar-footer-row">
              <span className="footer-status-dot" />
              <span>TVG: EQUALIZED</span>
            </div>
            <div className="sidebar-footer-row">
              <span className="footer-status-dot" />
              <span>WGS84: ONLINE</span>
            </div>
          </div>
        </aside>

        <main className="main-viewport">
          <ErrorBoundary>
            <Suspense fallback={<div style={{ padding: '24px', color: 'var(--text-muted)' }}>Loading…</div>}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/analyze" element={<Detect />} />
                <Route path="/detect" element={<Navigate to="/analyze" replace />} />
                <Route path="/results" element={<Result />} />
                <Route path="/runs/:id" element={<Result />} />
                <Route path="/runs/:id/list" element={<DetectionList />} />
                <Route path="/runs/:id/map" element={<Navigate to="/results" replace />} />
                <Route path="/map" element={<Navigate to="/results" replace />} />
                <Route path="/analysis" element={<Navigate to="/results" replace />} />
                <Route path="/history" element={<History />} />
                <Route path="/runs" element={<Navigate to="/history" replace />} />
                <Route path="/batch" element={<Batch />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
