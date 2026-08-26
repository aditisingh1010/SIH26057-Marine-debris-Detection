import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import MapView from './pages/MapView'
import Result from './pages/Result'
import Upload from './pages/Upload'

function App() {
  const location = useLocation()
  const runMatch = location.pathname.match(/^\/runs\/([^/]+)/)
  const runId = runMatch?.[1]

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="brand">AquaX</h1>
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

export default App
