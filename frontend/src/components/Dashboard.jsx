import { useEffect, useState } from "react";
import { api } from "../api.js";
import AuthImage from "../components/AuthImage.jsx";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getDashboardStats()
      .then(setStats)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!stats) return <p>Loading...</p>;

  return (
    <div>
      <h1>Dashboard</h1>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.total_connections}</div>
          <div className="stat-label">Connections</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.total_databases}</div>
          <div className="stat-label">Databases</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.total_tables}</div>
          <div className="stat-label">Tables</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.total_columns}</div>
          <div className="stat-label">Columns</div>
        </div>
      </div>

      <div className="chart-grid">
        <AuthImage
          path="/dashboard/charts/connection-status.png"
          alt="Connections by status"
        />
        <AuthImage
          path="/dashboard/charts/metadata-counts.png"
          alt="Metadata volume"
        />
        <AuthImage
          path="/dashboard/charts/ingestion-runs.png"
          alt="Ingestion runs over time"
        />
      </div>
    </div>
  );
}
