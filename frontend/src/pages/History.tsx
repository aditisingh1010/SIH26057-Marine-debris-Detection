import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getRuns } from "../api";
import type { RunSummary } from "../types";
import { getModelMode } from "../utils";

export default function History() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getRuns()
      .then(setRuns)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="history-page">
      <div className="history-header">
        <div>
          <p className="kicker">Scan History</p>
          <h1 style={{ margin: 0 }}>Past runs</h1>
        </div>
        <Link className="btn btn-primary" to="/">
          New scan
        </Link>
      </div>

      {loading && (
        <div className="panel" style={{ textAlign: "center", padding: "3rem" }}>
          <p className="muted">Loading...</p>
        </div>
      )}

      {!loading && runs.length === 0 && (
        <div className="panel" style={{ textAlign: "center", padding: "4rem 2rem" }}>
          <p style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>🌊</p>
          <h3>No past runs</h3>
          <p className="muted">Upload a sonar image to get started.</p>
          <Link className="btn btn-primary" to="/" style={{ marginTop: "1rem", display: "inline-flex" }}>
            Upload image
          </Link>
        </div>
      )}

      {!loading && runs.length > 0 && (
        <section className="panel">
          <table className="history-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Mode</th>
                <th>Detections</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => {
                const mode = getModelMode(run.inference_mode);
                return (
                  <tr
                    key={run.id}
                    className="history-row"
                    onClick={() => navigate(`/runs/${run.id}`)}
                  >
                    <td>
                      <span className="history-filename">{run.filename}</span>
                      <span className="history-id">{run.id}</span>
                    </td>
                    <td>
                      <span className={`mode-badge ${mode.isMock ? "mode-badge-mock" : "mode-badge-real"}`}>
                        <span className="mode-dot" />
                        {mode.isMock ? "MOCK" : "REAL"}
                      </span>
                    </td>
                    <td>
                      <span className="detection-count-pill">{run.detection_count}</span>
                    </td>
                    <td>
                      <Link
                        className="btn btn-secondary"
                        to={`/runs/${run.id}`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        View →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
