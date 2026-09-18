import { getToken, logout } from "./auth.js";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function request(path, options = {}) {
  const token = getToken();

  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  });

  if (res.status === 401) {
    logout();
    throw new Error("Session expired, please log in again");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }

  if (res.status === 204) return null;
  return res.json();
}

async function requestChart(path) {
  const token = getToken();
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (res.status === 401) {
    logout();
    throw new Error("Session expired, please log in again");
  }

  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return URL.createObjectURL(await res.blob());
}

export const api = {
  getDashboardStats: () => request("/dashboard/stats"),
  getDashboardChart: (name) => requestChart(`/dashboard/charts/${name}.png`),

  listConnections: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/connections${qs ? `?${qs}` : ""}`);
  },
  createConnection: (data) =>
    request("/connections", { method: "POST", body: JSON.stringify(data) }),
  deleteConnection: (id) => request(`/connections/${id}`, { method: "DELETE" }),
  testConnection: (id) =>
    request(`/connections/${id}/test`, { method: "POST" }),
  ingestConnection: (id) =>
    request(`/connections/${id}/ingest`, { method: "POST" }),
  getIngestionRun: (runId) => request(`/ingestion/${runId}`),
  updateSchedule: (id, cron) =>
    request(`/connections/${id}/schedule`, {
      method: "PUT",
      body: JSON.stringify({ schedule_cron: cron }),
    }),
  getConnectionRuns: (id, params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return request(`/connections/${id}/runs${qs ? `?${qs}` : ""}`);
  },
  updateConnection: (id, data) =>
    request(`/connections/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  getRunLogs: (runId) => request(`/ingestion/${runId}/logs`),

  listDatabases: (connectionId, params = {}) => {
    const qs = new URLSearchParams({
      connection_id: connectionId,
      ...params,
    }).toString();
    return request(`/metadata/databases?${qs}`);
  },
  listSchemas: (databaseId, params = {}) => {
    const qs = new URLSearchParams({
      database_id: databaseId,
      ...params,
    }).toString();
    return request(`/metadata/schemas?${qs}`);
  },
  listTables: (schemaId, params = {}) => {
    const qs = new URLSearchParams({
      schema_id: schemaId,
      ...params,
    }).toString();
    return request(`/metadata/tables?${qs}`);
  },
  listColumns: (tableId, params = {}) => {
    const qs = new URLSearchParams({ table_id: tableId, ...params }).toString();
    return request(`/metadata/columns?${qs}`);
  },
};
