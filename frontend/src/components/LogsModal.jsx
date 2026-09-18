import { X } from "lucide-react";

export default function LogsModal({ open, logs, error, onClose }) {
  if (!open) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal logs-modal" onClick={(e) => e.stopPropagation()}>
        <div className="logs-modal-header">
          <h3>Airflow Task Logs</h3>
          <button className="icon-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>
        {error ? (
          <p className="error">{error}</p>
        ) : (
          <pre className="logs-pre">{logs || "Loading..."}</pre>
        )}
      </div>
    </div>
  );
}
