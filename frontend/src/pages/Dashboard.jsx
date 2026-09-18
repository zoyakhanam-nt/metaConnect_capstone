import { useEffect, useState } from "react";
import { api } from "../api.js";

const emptyStats = {
  total_connections: 0,
  total_databases: 0,
  total_tables: 0,
  total_columns: 0,
};

export default function Dashboard() {
  const [stats, setStats] = useState(emptyStats);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getDashboardStats()
      .then(setStats)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div>
      <h1>Dashboard</h1>
      {error && <p className="error">{error}</p>}
      <div className="stats-grid">
        <div className="card stat-card">
          <span className="stat-label">Connections</span>
          <strong>{stats.total_connections}</strong>
        </div>
        <div className="card stat-card">
          <span className="stat-label">Databases</span>
          <strong>{stats.total_databases}</strong>
        </div>
        <div className="card stat-card">
          <span className="stat-label">Tables</span>
          <strong>{stats.total_tables}</strong>
        </div>
        <div className="card stat-card">
          <span className="stat-label">Columns</span>
          <strong>{stats.total_columns}</strong>
        </div>
      </div>
    </div>
  );
}
