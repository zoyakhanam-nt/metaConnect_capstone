import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Play,
  TestTube2,
  Trash2,
  History,
  Plus,
  X,
  Pencil,
} from "lucide-react";
import { api } from "../api.js";
import Pagination from "../components/Pagination.jsx";
import ConfirmDialog from "../components/ConfirmDialog.jsx";
import Toast from "../components/Toast.jsx";
import { buildCron, parseCron, WEEKDAYS } from "../cronUtils.js";

const emptyForm = {
  connection_name: "",
  connection_type: "cockroachdb",
  host: "",
  port: 26257,
  username: "root",
  password: "",
  database: "",
};

function validate(form) {
  const errors = {};
  if (!form.connection_name.trim()) errors.connection_name = "Required";
  else if (form.connection_name.length > 255)
    errors.connection_name = "Max 255 characters";
  if (!form.host.trim()) errors.host = "Required";
  if (!form.port) errors.port = "Required";
  else if (form.port < 1 || form.port > 65535)
    errors.port = "Must be between 1 and 65535";
  if (!form.username.trim()) errors.username = "Required";
  if (!form.database.trim()) errors.database = "Required";
  return errors;
}

const LIMIT = 8;

export default function Connections() {
  const navigate = useNavigate();
  const [connections, setConnections] = useState([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null); // null = add mode, id = edit mode
  const [activeTab, setActiveTab] = useState("details");
  const [form, setForm] = useState(emptyForm);
  const [ownerInfo, setOwnerInfo] = useState(null); // {owner_name, owner_email} shown read-only in edit mode
  const [schedule, setSchedule] = useState({
    frequency: "manual",
    time: "00:00",
    weekday: 0,
  });
  const [customCron, setCustomCron] = useState("");
  const [errors, setErrors] = useState({});
  const [toast, setToast] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);

  const load = () => {
    const params = { skip, limit: LIMIT };
    if (search) params.search = search;
    if (statusFilter) params.status = statusFilter;
    api
      .listConnections(params)
      .then((page) => {
        setConnections(page.items);
        setTotal(page.total);
      })
      .catch((e) => setToast({ type: "error", message: e.message }));
  };

  useEffect(() => {
    load();
  }, [skip, search, statusFilter]);
  useEffect(() => {
    setSkip(0);
  }, [search, statusFilter]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: name === "port" ? Number(value) : value }));
    setErrors((errs) => ({ ...errs, [name]: undefined }));
    setTestResult(null);
  };

  const openAddForm = () => {
    setEditingId(null);
    setForm(emptyForm);
    setOwnerInfo(null);
    setSchedule({ frequency: "manual", time: "00:00", weekday: 0 });
    setCustomCron("");
    setTestResult(null);
    setActiveTab("details");
    setShowForm(true);
  };

  const openEditForm = (c) => {
    setEditingId(c.id);
    setForm({
      connection_name: c.connection_name,
      connection_type: c.connection_type,
      host: c.host,
      port: c.port,
      username: c.username,
      password: "", // left blank = keep existing password
      database: c.database,
    });
    setOwnerInfo({ owner_name: c.owner_name, owner_email: c.owner_email });
    const parsed = parseCron(c.schedule_cron);
    if (parsed.frequency === "custom") {
      setSchedule({ frequency: "custom", time: "00:00", weekday: 0 });
      setCustomCron(parsed.raw || "");
    } else {
      setSchedule(parsed);
      setCustomCron("");
    }
    setTestResult(null);
    setActiveTab("details");
    setShowForm(true);
  };

  const closeForm = () => setShowForm(false);

  const resolvedCron =
    schedule.frequency === "custom" ? customCron : buildCron(schedule);

  const handleTestInForm = async () => {
    const validationErrors = validate(form);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) {
      setActiveTab("details");
      return;
    }
    setTesting(true);
    setTestResult(null);
    try {
      const result = await api.testConnection(form);
      setTestResult(result);
    } catch (err) {
      setTestResult({ success: false, message: err.message });
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validationErrors = validate(form);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) {
      setActiveTab("details");
      return;
    }
    try {
      if (editingId) {
        const payload = { ...form, schedule_cron: resolvedCron || null };
        if (!payload.password) delete payload.password; // don't overwrite with blank
        await api.updateConnection(editingId, payload);
        setToast({ type: "success", message: "Connection updated" });
      } else {
        await api.createConnection({
          ...form,
          schedule_cron: resolvedCron || null,
        });
        setToast({ type: "success", message: "Connection created" });
      }
      setShowForm(false);
      load();
    } catch (err) {
      setToast({ type: "error", message: err.message });
    }
  };

  const handleTest = async (id) => {
    setBusyId(id);
    try {
      const result = await api.testConnection(id); // fallback path unused; kept for clarity
      setToast({
        type: result.success ? "success" : "error",
        message: result.message,
      });
    } catch (err) {
      setToast({ type: "error", message: err.message });
    } finally {
      setBusyId(null);
      load();
    }
  };

  const handleTestExisting = async (id) => {
    setBusyId(id);
    try {
      const result = await fetch(
        `${import.meta.env.VITE_API_URL || "http://localhost:8000/api"}/connections/${id}/test`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${localStorage.getItem("metaconnect_token")}`,
          },
        },
      ).then((r) => r.json());
      setToast({
        type: result.success ? "success" : "error",
        message: result.message,
      });
    } catch (err) {
      setToast({ type: "error", message: err.message });
    } finally {
      setBusyId(null);
      load();
    }
  };

  const handleIngest = async (id) => {
    setBusyId(id);
    try {
      await api.ingestConnection(id);
      setToast({
        type: "success",
        message: "Ingestion triggered — check Dashboard for status",
      });
    } catch (err) {
      setToast({ type: "error", message: err.message });
    } finally {
      setBusyId(null);
    }
  };

  const confirmDelete = async () => {
    await api.deleteConnection(deleteTarget.id);
    setDeleteTarget(null);
    setToast({ type: "success", message: "Connection deleted" });
    load();
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Connections</h1>
          <p className="page-subtitle">
            Manage CockroachDB connections and ingestion schedules
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={showForm ? closeForm : openAddForm}
        >
          {showForm ? (
            <>
              <X size={16} /> Cancel
            </>
          ) : (
            <>
              <Plus size={16} /> Add Connection
            </>
          )}
        </button>
      </div>

      {showForm && (
        <div className="card form-card">
          <div className="tabs">
            <button
              type="button"
              className={activeTab === "details" ? "tab active" : "tab"}
              onClick={() => setActiveTab("details")}
            >
              1. Connection Details
            </button>
            {editingId && (
              <button
                type="button"
                className={activeTab === "owner" ? "tab active" : "tab"}
                onClick={() => setActiveTab("owner")}
              >
                2. Owner
              </button>
            )}
            <button
              type="button"
              className={activeTab === "schedule" ? "tab active" : "tab"}
              onClick={() => setActiveTab("schedule")}
            >
              {editingId ? "3." : "2."} Ingestion Schedule
            </button>
          </div>

          <form onSubmit={handleSubmit} noValidate>
            {activeTab === "details" && (
              <>
                <div className="form-grid">
                  <div className="field">
                    <label>Connection Name *</label>
                    <input
                      name="connection_name"
                      value={form.connection_name}
                      onChange={handleChange}
                    />
                    {errors.connection_name && (
                      <span className="field-error">
                        {errors.connection_name}
                      </span>
                    )}
                  </div>
                  <div className="field">
                    <label>Host *</label>
                    <input
                      name="host"
                      value={form.host}
                      onChange={handleChange}
                    />
                    {errors.host && (
                      <span className="field-error">{errors.host}</span>
                    )}
                  </div>
                  <div className="field">
                    <label>Port *</label>
                    <input
                      name="port"
                      type="number"
                      value={form.port}
                      onChange={handleChange}
                    />
                    {errors.port && (
                      <span className="field-error">{errors.port}</span>
                    )}
                  </div>
                  <div className="field">
                    <label>Database Name *</label>
                    <input
                      name="database"
                      value={form.database}
                      onChange={handleChange}
                    />
                    {errors.database && (
                      <span className="field-error">{errors.database}</span>
                    )}
                  </div>
                  <div className="field">
                    <label>Username *</label>
                    <input
                      name="username"
                      value={form.username}
                      onChange={handleChange}
                    />
                    {errors.username && (
                      <span className="field-error">{errors.username}</span>
                    )}
                  </div>
                  <div className="field">
                    <label>
                      Password
                      {editingId && (
                        <span className="field-hint">
                          {" "}
                          (leave blank to keep current)
                        </span>
                      )}
                    </label>
                    <input
                      name="password"
                      type="password"
                      value={form.password}
                      onChange={handleChange}
                    />
                  </div>
                </div>

                <div className="test-row">
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={handleTestInForm}
                    disabled={testing}
                  >
                    <TestTube2 size={15} />{" "}
                    {testing ? "Testing..." : "Test Connection"}
                  </button>
                  {testResult && (
                    <span
                      className={testResult.success ? "test-ok" : "test-fail"}
                    >
                      {testResult.message}
                    </span>
                  )}
                </div>
              </>
            )}

            {activeTab === "owner" && editingId && (
              <div className="form-grid">
                <div className="field">
                  <label>Owner Name</label>
                  <input value={ownerInfo?.owner_name || ""} disabled />
                  <span className="field-hint">
                    Owner is set to the connection's creator and can't be
                    changed here
                  </span>
                </div>
                <div className="field">
                  <label>Owner Email</label>
                  <input value={ownerInfo?.owner_email || ""} disabled />
                </div>
              </div>
            )}

            {activeTab === "schedule" && (
              <div className="form-grid">
                <div className="field field-wide">
                  <label>Frequency</label>
                  <select
                    value={schedule.frequency}
                    onChange={(e) =>
                      setSchedule((s) => ({ ...s, frequency: e.target.value }))
                    }
                  >
                    <option value="manual">Manual only</option>
                    <option value="hourly">Every hour</option>
                    <option value="daily">Every day</option>
                    <option value="weekly">Every week</option>
                    <option value="custom">Custom (advanced)</option>
                  </select>
                </div>

                {(schedule.frequency === "daily" ||
                  schedule.frequency === "weekly") && (
                  <div className="field">
                    <label>Time</label>
                    <input
                      type="time"
                      value={schedule.time}
                      onChange={(e) =>
                        setSchedule((s) => ({ ...s, time: e.target.value }))
                      }
                    />
                  </div>
                )}
                {schedule.frequency === "hourly" && (
                  <div className="field">
                    <label>Minute past the hour</label>
                    <input
                      type="number"
                      min={0}
                      max={59}
                      value={Number(schedule.time.split(":")[1] || 0)}
                      onChange={(e) =>
                        setSchedule((s) => ({
                          ...s,
                          time: `00:${e.target.value}`,
                        }))
                      }
                    />
                  </div>
                )}
                {schedule.frequency === "weekly" && (
                  <div className="field">
                    <label>Day of week</label>
                    <select
                      value={schedule.weekday}
                      onChange={(e) =>
                        setSchedule((s) => ({
                          ...s,
                          weekday: Number(e.target.value),
                        }))
                      }
                    >
                      {WEEKDAYS.map((d, i) => (
                        <option key={d} value={i}>
                          {d}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                {schedule.frequency === "custom" && (
                  <div className="field field-wide">
                    <label>Custom Cron Expression</label>
                    <input
                      placeholder="0 */6 * * *"
                      value={customCron}
                      onChange={(e) => setCustomCron(e.target.value)}
                    />
                    <span className="field-hint">
                      5 fields: minute hour day month weekday
                    </span>
                  </div>
                )}
                {schedule.frequency !== "manual" && (
                  <div className="field-wide field-hint">
                    Resulting cron: <code>{resolvedCron}</code>
                  </div>
                )}
              </div>
            )}

            <button className="btn-primary" type="submit">
              {editingId ? "Save Changes" : "Create Connection"}
            </button>
          </form>
        </div>
      )}

      <div className="toolbar">
        <input
          className="search-box"
          placeholder="Search connections..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="filter-select"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All statuses</option>
          <option value="untested">Untested</option>
          <option value="connected">Connected</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Owner</th>
              <th>Host</th>
              <th>Schedule</th>
              <th>Next Run</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {connections.map((c) => {
              const parsed = parseCron(c.schedule_cron);
              const scheduleLabel = c.schedule_cron
                ? parsed.frequency === "custom"
                  ? c.schedule_cron
                  : `${parsed.frequency}${parsed.time ? " @ " + parsed.time : ""}`
                : "Manual";
              return (
                <tr key={c.id}>
                  <td>{c.connection_name}</td>
                  <td>{c.owner_name || <span className="muted">—</span>}</td>
                  <td>
                    {c.host}:{c.port}
                  </td>
                  <td>
                    {c.schedule_cron ? (
                      scheduleLabel
                    ) : (
                      <span className="muted">Manual</span>
                    )}
                  </td>
                  <td>
                    {c.next_run_at ? (
                      new Date(c.next_run_at).toLocaleString()
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td>
                    <span className={`badge badge-${c.status}`}>
                      {c.status}
                    </span>
                  </td>
                  <td className="actions-cell">
                    <button
                      title="Test connection"
                      disabled={busyId === c.id}
                      onClick={() => handleTestExisting(c.id)}
                    >
                      <TestTube2 size={15} />
                    </button>
                    <button
                      title="Run ingestion now"
                      disabled={busyId === c.id}
                      onClick={() => handleIngest(c.id)}
                    >
                      <Play size={15} />
                    </button>
                    <button
                      title="View run history"
                      onClick={() => navigate(`/connections/${c.id}/runs`)}
                    >
                      <History size={15} />
                    </button>
                    <button title="Edit" onClick={() => openEditForm(c)}>
                      <Pencil size={15} />
                    </button>
                    <button
                      title="Delete"
                      className="btn-danger"
                      onClick={() => setDeleteTarget(c)}
                    >
                      <Trash2 size={15} />
                    </button>
                  </td>
                </tr>
              );
            })}
            {connections.length === 0 && (
              <tr>
                <td colSpan={7} className="empty-row">
                  No connections found
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

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete connection?"
        message={
          deleteTarget
            ? `This will permanently delete "${deleteTarget.connection_name}" and all its ingested metadata.`
            : ""
        }
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />

      <Toast
        message={toast?.message}
        type={toast?.type}
        onDismiss={() => setToast(null)}
      />
    </div>
  );
}
