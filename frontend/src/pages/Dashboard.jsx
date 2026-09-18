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
  const [charts, setCharts] = useState({});
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    const chartNames = [
      ["status", "connection-status"],
      ["runs", "ingestion-runs"],
      ["metadata", "metadata-counts"],
    ];

    Promise.all([
      api.getDashboardStats(),
      ...chartNames.map(async ([key, name]) => [
        key,
        await api.getDashboardChart(name),
      ]),
    ])
      .then(([dashboardStats, ...chartResults]) => {
        if (!active) return;
        setStats(dashboardStats);
        setCharts(Object.fromEntries(chartResults));
      })
      .catch((err) => {
        if (active) setError(err.message);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(
    () => () =>
      Object.values(charts).forEach((url) => URL.revokeObjectURL(url)),
    [charts],
  );

  return (
    <div>
      <h1>Dashboard</h1>
      {error && <p className="error">{error}</p>}
      <div className="stat-grid">
        <div className="card stat-card">
          <span className="stat-label">Connections</span>
          <strong className="stat-value">{stats.total_connections}</strong>
        </div>
        <div className="card stat-card">
          <span className="stat-label">Databases</span>
          <strong className="stat-value">{stats.total_databases}</strong>
        </div>
        <div className="card stat-card">
          <span className="stat-label">Tables</span>
          <strong className="stat-value">{stats.total_tables}</strong>
        </div>
        <div className="card stat-card">
          <span className="stat-label">Columns</span>
          <strong className="stat-value">{stats.total_columns}</strong>
        </div>
      </div>
      <div className="chart-grid">
        {[
          ["status", "Connections by Status"],
          ["runs", "Ingestion Run Status"],
          ["metadata", "Metadata Distribution"],
        ].map(([key, title]) => (
          <div className="card" key={key}>
            <h2>{title}</h2>
            {charts[key] ? (
              <img className="chart-img" src={charts[key]} alt={title} />
            ) : (
              <p className="field-hint">Loading chart...</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
