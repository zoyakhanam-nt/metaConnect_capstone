# Architecture

## Overview

```
React UI → FastAPI backend → App DB (Postgres)
                ↓        ↑
             Airflow  (extraction happens HERE, then reports back)
                ↓
      get_db/get_schema/get_table/get_column → CockroachDB (source)

```

- **React UI** — talks to FastAPI only, over HTTP/JSON with a Keycloak bearer token.
- **FastAPI backend** — owns connection CRUD, encryption, Airflow DAG deployment/triggering, chart rendering, and **persistence** of ingestion results. It does not perform extraction itself.
- **App DB (Postgres)** — stores connections (encrypted credentials), the extracted metadata hierarchy, and ingestion run history.
- **Airflow** — runs the actual extraction logic against the data source, then reports the result back to the backend to persist.
- **CockroachDB** — an external system being cataloged, not part of the app's own infrastructure.

## Request flow: triggering ingestion

1. UI calls `POST /api/connections/{id}/ingest`.
2. Backend writes/refreshes a DAG file for that connection (a human-readable ID derived from the connection name plus a short suffix of its UUID — e.g. `production_postgres_a1b2c3d4e5f6`) and triggers a run via Airflow's REST API.
3. Airflow's scheduler picks up the run and executes the DAG's task, `ingest_metadata`.
4. That task (`airflow/dags/utils/run_ingestion.py`) first calls `GET /api/internal/connections/{id}/config` to get the connection's **decrypted** credentials, then `POST /api/internal/connections/{id}/start-run` to register/start an ingestion run row.
5. It then runs the real extraction itself, inside the Airflow worker: `extract_metadata()` drives `get_db → get_schema → get_table → get_column`, each connecting directly to the source via `psycopg2` and walking the full hierarchy.
6. The complete metadata tree is POSTed back in one payload to `POST /api/internal/connections/{id}/metadata`.
7. `IngestionService.handle_metadata_payload()` persists it — replacing any prior metadata for that connection in one transaction — and marks the run `success` or `failed`.
8. The UI (Services → History tab) shows the result; Airflow's task logs for that run are fetchable via `GET /api/ingestion/{run_id}/logs`, which discovers and aggregates all task instances in that DAG run.

## Where extraction logic actually lives

- `airflow/dags/utils/get_db.py` / `get_schema.py` / `get_table.py` / `get_column.py` — one function per metadata level. Each accepts either a connector object, a raw config dict, or a live DB-API connection; the live path used today passes a config dict, hitting the dict-branch `information_schema` queries directly.
- `airflow/dags/utils/extract_metadata.py` — orchestrates those four into one full tree walk, with support for resuming from partial results if some levels were already extracted.
- `airflow/dags/utils/run_ingestion.py` — the DAG task's entry point: fetches config, runs extraction, reports the result.
- `backend/app/connectors/` — a separate, class-based abstraction (`BaseConnector`, `CockroachDBConnector`) used by the `/connections/test` endpoint. It is **not** the code path the live ingestion pipeline uses.
- `backend/app/services/ingestion_service.py` — persistence and run-lifecycle only. Its own docstring states extraction is "decoupled and executed in Airflow workers."

This means the Airflow containers need a Postgres driver (`psycopg2`) installed, not just `requests` — see the dependency gap noted in `README.md`.

## Charts

All three dashboard charts (`ChartService`) are **pie charts**, not time-series/bar charts, despite one function being named `render_runs_over_time_chart` — it currently renders a status-outcome breakdown (success/failed/running proportions) rather than a trend line over the 14-day window it queries.

## Security

- **Keycloak (OIDC)** protects every user-facing endpoint — the backend validates JWTs against Keycloak's JWKS endpoint on every request (`core/security.py`).
- **Internal API key** (`X-Internal-Api-Key` header) protects the `/api/internal/...` endpoints Airflow calls — a static shared secret, since Airflow is a machine caller, not a logged-in user.
- **Encryption at rest**: `host`, `port`, and `password` on every connection are Fernet-encrypted before being written to Postgres, decrypted only in-memory when a request actually needs them (testing, or building the config Airflow fetches). The key lives in `.env`, supplied to containers at runtime via `env_file:` — never baked into the Docker image.

## Frontend structure

- **Sidebar**: Dashboard / Services / Explorer.
- **Dashboard**: aggregate stat cards + the three pie charts, nothing else.
- **Services**: one page, three tabs — Connections (CRUD, test, schedule, trigger), Recent Runs (last 10 across all connections), History (full paginated, connection- and status-filterable run log, with per-run Airflow log viewing).
- **Explorer**: select a connection, then drill Database → Schema → Table → Column via breadcrumbs, with search and pagination per level.

## Scheduling

Each connection's optional `schedule_cron` is set via a friendly frequency/time picker (`cronUtils.js` converts to/from a real 5-field cron string) or raw cron for advanced cases. When set, the generated DAG file carries that schedule directly, so **Airflow's own scheduler** — not the backend — fires future runs automatically. The "next run" time shown in the connections table is computed independently via `croniter`, purely for display.
