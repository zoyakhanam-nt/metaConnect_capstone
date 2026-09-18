import { useEffect, useState } from "react";
import { api } from "../api.js";
import Pagination from "../components/Pagination.jsx";
import LogsModal from "../components/LogsModal.jsx";

const LIMIT = 10;

export default function HistoryTab({ connectionFilter, onClearFilter }) {
  const [connections, setConnections] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [runs, setRuns] = useState([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [logsState, setLogsState] = useState({
    open: false,
    logs: null,
    error: null,
  });

  useEffect(() => {
    api.listConnections({ limit: 100 }).then((p) => setConnections(p.items));
  }, []);

  const load = () => {
    const params = { skip, limit: LIMIT };
    if (connectionFilter) params.connection_id = connectionFilter;
    if (statusFilter) params.status = statusFilter;
    api.listAllRuns(params).then((page) => {
      setRuns(page.items);
      setTotal(page.total);
    });
  };

  useEffect(() => {
    load();
  }, [skip, connectionFilter, statusFilter]);
  useEffect(() => {
    setSkip(0);
  }, [connectionFilter, statusFilter]);

  const viewLogs = async (runId) => {
    setLogsState({ open: true, logs: null, error: null });
    try {
      const result = await api.getRunLogs(runId);
      setLogsState({ open: true, logs: result.logs, error: null });
    } catch (err) {
      setLogsState({ open: true, logs: null, error: err.message });
    }
  };

  const filteredName = connections.find(
    (c) => c.id === connectionFilter,
  )?.connection_name;

  return (
    <div>
      <div className="toolbar">
        {connectionFilter ? (
          <span className="filter-pill">
            Filtered to: <strong>{filteredName}</strong>
            <button className="pill-clear" onClick={onClearFilter}>
              ✕
            </button>
          </span>
        ) : (
          <span className="field-hint">Showing all connections</span>
        )}
        <select
          className="filter-select"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
          <option value="running">Running</option>
          <option value="pending">Pending</option>
        </select>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Connection</th>
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
                <td>{r.connection_name}</td>
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
                <td colSpan={6} className="empty-row">
                  No runs found
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
