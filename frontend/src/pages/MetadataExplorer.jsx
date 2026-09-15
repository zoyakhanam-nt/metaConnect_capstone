import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function MetadataExplorer() {
  const [connections, setConnections] = useState([]);
  const [selectedConnection, setSelectedConnection] = useState("");
  const [databases, setDatabases] = useState([]);
  const [schemasByDb, setSchemasByDb] = useState({});
  const [tablesBySchema, setTablesBySchema] = useState({});
  const [columnsByTable, setColumnsByTable] = useState({});
  const [expanded, setExpanded] = useState({});

  useEffect(() => {
    api.listConnections().then((page) => setConnections(page.items));
  }, []);

  useEffect(() => {
    if (!selectedConnection) return;
    setDatabases([]); setSchemasByDb({}); setTablesBySchema({}); setColumnsByTable({}); setExpanded({});
    api.listDatabases(selectedConnection).then((page) => setDatabases(page.items));
  }, [selectedConnection]);

  const toggle = (key) => setExpanded((e) => ({ ...e, [key]: !e[key] }));

  const loadSchemas = async (dbId) => {
    if (schemasByDb[dbId]) return;
    const page = await api.listSchemas(dbId);
    setSchemasByDb((s) => ({ ...s, [dbId]: page.items }));
  };
  const loadTables = async (schemaId) => {
    if (tablesBySchema[schemaId]) return;
    const page = await api.listTables(schemaId);
    setTablesBySchema((t) => ({ ...t, [schemaId]: page.items }));
  };
  const loadColumns = async (tableId) => {
    if (columnsByTable[tableId]) return;
    const page = await api.listColumns(tableId);
    setColumnsByTable((c) => ({ ...c, [tableId]: page.items }));
  };

  return (
    <div>
      <h1>Metadata Explorer</h1>

      <select value={selectedConnection} onChange={(e) => setSelectedConnection(e.target.value)}>
        <option value="">Select a connection</option>
        {connections.map((c) => <option key={c.id} value={c.id}>{c.connection_name}</option>)}
      </select>

      <ul className="tree">
        {databases.map((db) => (
          <li key={db.id}>
            <span className="tree-node" onClick={() => { toggle(`db-${db.id}`); loadSchemas(db.id); }}>
              {expanded[`db-${db.id}`] ? "▼" : "▶"} 🗄 {db.name}
            </span>
            {expanded[`db-${db.id}`] && (
              <ul>
                {(schemasByDb[db.id] || []).map((schema) => (
                  <li key={schema.id}>
                    <span className="tree-node" onClick={() => { toggle(`schema-${schema.id}`); loadTables(schema.id); }}>
                      {expanded[`schema-${schema.id}`] ? "▼" : "▶"} 📁 {schema.name}
                    </span>
                    {expanded[`schema-${schema.id}`] && (
                      <ul>
                        {(tablesBySchema[schema.id] || []).map((table) => (
                          <li key={table.id}>
                            <span className="tree-node" onClick={() => { toggle(`table-${table.id}`); loadColumns(table.id); }}>
                              {expanded[`table-${table.id}`] ? "▼" : "▶"} 📋 {table.name}
                            </span>
                            {expanded[`table-${table.id}`] && (
                              <ul>
                                {(columnsByTable[table.id] || []).map((col) => (
                                  <li key={col.id} className="column-row">
                                    {col.name} <span className="col-type">{col.data_type}</span>
                                    {col.is_primary_key && <span className="pk-badge">PK</span>}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}