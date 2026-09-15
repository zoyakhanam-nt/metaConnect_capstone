import { useEffect, useState } from "react";
import { api } from "../api.js";

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
  else if (form.connection_name.length > 255) errors.connection_name = "Max 255 characters";

  if (!form.host.trim()) errors.host = "Required";

  if (!form.port) errors.port = "Required";
  else if (form.port < 1 || form.port > 65535) errors.port = "Must be between 1 and 65535";

  if (!form.username.trim()) errors.username = "Required";

  if (!form.database.trim()) errors.database = "Required";

  return errors;
}

export default function Connections() {
  const [connections, setConnections] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = () =>
    api
      .listConnections(search ? { search } : {})
      .then((page) => {
        setConnections(page.items);
        setTotal(page.total);
      })
      .catch((e) => setMessage(e.message));

  useEffect(() => { load(); }, [search]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: name === "port" ? Number(value) : value }));
    setErrors((errs) => ({ ...errs, [name]: undefined }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const validationErrors = validate(form);
    setErrors(validationErrors);
    if (Object.keys(validationErrors).length > 0) return;

    setMessage(null);
    try {
      await api.createConnection(form);
      setForm(emptyForm);
      load();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const handleTest = async (id) => {
    setBusyId(id);
    try {
      const result = await api.testConnection(id);
      setMessage(result.success ? "Connection successful" : result.message);
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusyId(null);
      load();
    }
  };

  const handleIngest = async (id) => {
    setBusyId(id);
    try {
      await api.ingestConnection(id);
      setMessage("Ingestion triggered — check Dashboard for status");
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this connection?")) return;
    await api.deleteConnection(id);
    load();
  };

  return (
    <div>
      <h1>Connections</h1>
      {message && <p className="message">{message}</p>}

      <form className="form" onSubmit={handleSubmit} noValidate>
        <div className="field">
          <input name="connection_name" placeholder="Connection name" value={form.connection_name} onChange={handleChange} />
          {errors.connection_name && <span className="field-error">{errors.connection_name}</span>}
        </div>
        <div className="field">
          <input name="host" placeholder="Host" value={form.host} onChange={handleChange} />
          {errors.host && <span className="field-error">{errors.host}</span>}
        </div>
        <div className="field">
          <input name="port" type="number" placeholder="Port" value={form.port} onChange={handleChange} />
          {errors.port && <span className="field-error">{errors.port}</span>}
        </div>
        <div className="field">
          <input name="database" placeholder="Database" value={form.database} onChange={handleChange} />
          {errors.database && <span className="field-error">{errors.database}</span>}
        </div>
        <div className="field">
          <input name="username" placeholder="Username" value={form.username} onChange={handleChange} />
          {errors.username && <span className="field-error">{errors.username}</span>}
        </div>
        <div className="field">
          <input name="password" type="password" placeholder="Password" value={form.password} onChange={handleChange} />
        </div>
        <button type="submit">Add Connection</button>
      </form>

      <input
        className="search-box"
        placeholder="Search connections..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      <table className="table">
        <thead><tr><th>Name</th><th>Host</th><th>Database</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
          {connections.map((c) => (
            <tr key={c.id}>
              <td>{c.connection_name}</td>
              <td>{c.host}:{c.port}</td>
              <td>{c.database}</td>
              <td className={`status status-${c.status}`}>{c.status}</td>
              <td>
                <button disabled={busyId === c.id} onClick={() => handleTest(c.id)}>Test</button>
                <button disabled={busyId === c.id} onClick={() => handleIngest(c.id)}>Run Ingestion</button>
                <button onClick={() => handleDelete(c.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="total-count">{total} total connection(s)</p>
    </div>
  );
}