import { useEffect, useState } from "react";
import { api } from "../api.js";
import Pagination from "../components/Pagination.jsx";

const LIMIT = 10;
const LEVELS = ["databases", "schemas", "tables", "columns"];

export default function MetadataExplorer() {
  const [connections, setConnections] = useState([]);
  const [connectionId, setConnectionId] = useState("");

  const [level, setLevel] = useState("databases");
  const [breadcrumb, setBreadcrumb] = useState([]); // [{id, name}] per level entered

  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.listConnections({ limit: 100 }).then((p) => setConnections(p.items));
  }, []);

  useEffect(() => {
    if (!connectionId) return;
    setBreadcrumb([]);
    setLevel("databases");
    setSkip(0);
    setSearch("");
  }, [connectionId]);

  useEffect(() => {
    if (!connectionId) return;
    loadLevel();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connectionId, level, skip, search, breadcrumb]);

  const loadLevel = async () => {
    const params = { skip, limit: LIMIT };
    if (search) params.search = search;

    let page;
    if (level === "databases")
      page = await api.listDatabases(connectionId, params);
    else if (level === "schemas")
      page = await api.listSchemas(breadcrumb[0].id, params);
    else if (level === "tables")
      page = await api.listTables(breadcrumb[1].id, params);
    else page = await api.listColumns(breadcrumb[2].id, params);

    setRows(page.items);
    setTotal(page.total);
  };

  const drillInto = (item) => {
    if (level === "columns") return;
    setBreadcrumb((b) => [...b, { id: item.id, name: item.name }]);
    setLevel(LEVELS[LEVELS.indexOf(level) + 1]);
    setSkip(0);
    setSearch("");
  };

  const goToBreadcrumb = (index) => {
    // index -1 = the connection root, 0..2 = a level already drilled into
    setBreadcrumb((b) => b.slice(0, index + 1));
    setLevel(LEVELS[index + 1]);
    setSkip(0);
    setSearch("");
  };

  const levelLabel = {
    databases: "Databases",
    schemas: "Schemas",
    tables: "Tables",
    columns: "Columns",
  }[level];
  const icon = { databases: "🗄", schemas: "📁", tables: "📋", columns: "▫" }[
    level
  ];
  const connName = connections.find(
    (c) => c.id === connectionId,
  )?.connection_name;

  return (
    <div>
      <h1>Metadata Explorer</h1>

      <select
        className="filter-select"
        value={connectionId}
        onChange={(e) => setConnectionId(e.target.value)}
      >
        <option value="">Select a connection</option>
        {connections.map((c) => (
          <option key={c.id} value={c.id}>
            {c.connection_name}
          </option>
        ))}
      </select>

      {connectionId && (
        <>
          <div className="breadcrumb">
            <span className="crumb" onClick={() => goToBreadcrumb(-1)}>
              {connName}
            </span>
            {breadcrumb.map((b, i) => (
              <span key={b.id}>
                {" \u203A "}
                <span className="crumb" onClick={() => goToBreadcrumb(i)}>
                  {b.name}
                </span>
              </span>
            ))}
          </div>

          <div className="toolbar">
            <input
              className="search-box"
              placeholder={`Search ${levelLabel.toLowerCase()}...`}
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setSkip(0);
              }}
            />
          </div>

          <div className="card">
            <table className="table">
              <thead>
                <tr>
                  <th>
                    {level === "columns" ? "Column" : levelLabel.slice(0, -1)}
                  </th>
                  {level === "columns" ? (
                    <>
                      <th>Type</th>
                      <th>Nullable</th>
                      <th>Key</th>
                    </>
                  ) : (
                    <th></th>
                  )}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={row.id}
                    className={level !== "columns" ? "clickable-row" : ""}
                    onClick={() => drillInto(row)}
                  >
                    <td>
                      {icon} {row.name}
                    </td>
                    {level === "columns" ? (
                      <>
                        <td>
                          <code>{row.data_type}</code>
                        </td>
                        <td>{row.is_nullable ? "Yes" : "No"}</td>
                        <td>
                          {row.is_primary_key && (
                            <span className="pk-badge">PK</span>
                          )}
                        </td>
                      </>
                    ) : (
                      <td className="drill-arrow">›</td>
                    )}
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td
                      colSpan={level === "columns" ? 4 : 2}
                      className="empty-row"
                    >
                      No {levelLabel.toLowerCase()} found
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
        </>
      )}
    </div>
  );
}
