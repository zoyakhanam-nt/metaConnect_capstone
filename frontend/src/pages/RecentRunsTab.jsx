import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function RecentRunsTab() {
  const [runs, setRuns] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getDashboardStats()
      .then((stats) => setRuns(stats.recent_runs))
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!runs) return <p>Loading...</p>;

  return (
    <div className="card">
      <table className="table">
        <thead>
          <tr>
            <th>Connection</th>
            <th>Status</th>
            <th>Started</th>
            <th>Finished</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td>{run.connection_name}</td>
              <td>
                <span className={`badge badge-${run.status}`}>
                  {run.status}
                </span>
              </td>
              <td>{new Date(run.started_at).toLocaleString()}</td>
              <td>
                {run.finished_at
                  ? new Date(run.finished_at).toLocaleString()
                  : "-"}
              </td>
            </tr>
          ))}
          {runs.length === 0 && (
            <tr>
              <td colSpan={4} className="empty-row">
                No runs yet
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
