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

  const iconStyle = {
    width: 16,
    height: 16,
    flexShrink: 0,
    verticalAlign: "middle",
  };

  const DatabaseIcon = () => (
    <svg viewBox="0 0 24 24" style={iconStyle} aria-hidden="true">
      <path
        d="M4 7.5C4 5.57 7.13 4 12 4s8 1.57 8 3.5S16.87 11 12 11 4 9.43 4 7.5Zm0 4.5c0 1.93 3.13 3.5 8 3.5s8-1.57 8-3.5v5c0 1.93-3.13 3.5-8 3.5s-8-1.57-8-3.5v-5Z"
        fill="currentColor"
      />
    </svg>
  );

  const FolderIcon = () => (
    <svg viewBox="0 0 24 24" style={iconStyle} aria-hidden="true">
      <path
        d="M3 7.5A2.5 2.5 0 0 1 5.5 5H9l1.5 2H18.5A2.5 2.5 0 0 1 21 9.5v7A2.5 2.5 0 0 1 18.5 19h-13A2.5 2.5 0 0 1 3 16.5v-9Z"
        fill="currentColor"
      />
    </svg>
  );

  const TableIcon = () => (
    <svg viewBox="0 0 24 24" style={iconStyle} aria-hidden="true">
      <path
        d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v13a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 18.5v-13Zm2.5 1.5h11v3h-11V7Zm0 5h4v4h-4v-4Zm6 0h5v4h-5v-4Z"
        fill="currentColor"
      />
    </svg>
  );

  const ColumnIcon = () => (
    <svg viewBox="0 0 24 24" style={iconStyle} aria-hidden="true">
      <path
        d="M5 4.5A2.5 2.5 0 0 1 7.5 2h9A2.5 2.5 0 0 1 19 4.5v15A2.5 2.5 0 0 1 16.5 22h-9A2.5 2.5 0 0 1 5 19.5v-15Zm2.5 1.5h9v3h-9V6Zm0 5h9v3h-9v-3Zm0 5h9v3h-9v-3Z"
        fill="currentColor"
      />
    </svg>
  );

  const levelIconMap = {
    databases: DatabaseIcon,
    schemas: FolderIcon,
    tables: TableIcon,
    columns: ColumnIcon,
  };

  const LevelIcon = levelIconMap[level];
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
                    <td style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <LevelIcon />
                      <span>{row.name}</span>
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
