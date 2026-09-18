import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "../api.js";
import Pagination from "../components/Pagination.jsx";
import LogsModal from "../components/LogsModal.jsx";

const LIMIT = 10;

export default function ConnectionRuns() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [runs, setRuns] = useState([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [logsState, setLogsState] = useState({
    open: false,
    logs: null,
    error: null,
  });

  useEffect(() => {
    api.getConnectionRuns(id, { skip, limit: LIMIT }).then((page) => {
      setRuns(page.items);
      setTotal(page.total);
    });
  }, [id, skip]);

  const viewLogs = async (runId) => {
    setLogsState({ open: true, logs: null, error: null });
    try {
      const result = await api.getRunLogs(runId);
      setLogsState({ open: true, logs: result.logs, error: null });
    } catch (err) {
      setLogsState({ open: true, logs: null, error: err.message });
    }
  };

  return (
    <div>
      <button className="back-link" onClick={() => navigate("/connections")}>
        ← Back to Connections
      </button>
      <h1>Ingestion Run History</h1>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Started</th>
              <th>Finished</th>
              <th>Error</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id}>
                <td>
                  <span className={`badge badge-${r.status}`}>{r.status}</span>
                </td>
                <td>{new Date(r.started_at).toLocaleString()}</td>
                <td>
                  {r.finished_at
                    ? new Date(r.finished_at).toLocaleString()
                    : "-"}
                </td>
                <td className="error-cell">{r.error_message || "-"}</td>
                <td>
                  {r.dag_id && (
                    <button
                      className="icon-btn"
                      title="View Airflow logs"
                      onClick={() => viewLogs(r.id)}
                    >
                      ▤
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={5} className="empty-row">
                  No runs yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <Pagination
        skip={skip}
        limit={LIMIT}
        total={total}
        onPageChange={setSkip}
      />

      <LogsModal
        open={logsState.open}
        logs={logsState.logs}
        error={logsState.error}
        onClose={() => setLogsState({ open: false, logs: null, error: null })}
      />
    </div>
  );
}
