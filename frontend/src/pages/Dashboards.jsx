import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getDashboardStats().then(setStats).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!stats) return <p>Loading...</p>;

  return (
    <div>
      <h1>Dashboard</h1>

      <div className="stat-grid">
        <div className="stat-card"><div className="stat-value">{stats.total_connections}</div><div className="stat-label">Connections</div></div>
        <div className="stat-card"><div className="stat-value">{stats.total_databases}</div><div className="stat-label">Databases</div></div>
        <div className="stat-card"><div className="stat-value">{stats.total_tables}</div><div className="stat-label">Tables</div></div>
        <div className="stat-card"><div className="stat-value">{stats.total_columns}</div><div className="stat-label">Columns</div></div>
      </div>

      <h2>Recent Ingestion Runs</h2>
      <table className="table">
        <thead>
          <tr><th>Connection</th><th>Status</th><th>Started</th><th>Finished</th></tr>
        </thead>
        <tbody>
          {stats.recent_runs.map((run) => (
            <tr key={run.id}>
              <td>{run.connection_name}</td>
              <td className={`status status-${run.status}`}>{run.status}</td>
              <td>{new Date(run.started_at).toLocaleString()}</td>
              <td>{run.finished_at ? new Date(run.finished_at).toLocaleString() : "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}