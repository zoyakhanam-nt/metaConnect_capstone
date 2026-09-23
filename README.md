# MetaConnect

A metadata discovery and catalog platform. Connect to a data source, run an orchestrated ingestion pipeline via Apache Airflow, and browse the extracted metadata hierarchy — Connection → Database → Schema → Table → Column — through a searchable, paginated UI.

Built as a capstone project. Scoped end-to-end to a single connector (CockroachDB), with room designed in for more.

## Stack

| Layer                      | Technology                                                                  |
| -------------------------- | --------------------------------------------------------------------------- |
| Frontend                   | React + Vite                                                                |
| Backend API                | FastAPI                                                                     |
| App database               | PostgreSQL                                                                  |
| Migrations                 | Liquibase                                                                   |
| Orchestration & extraction | Apache Airflow (extraction itself runs inside Airflow workers, not the API) |
| Authentication             | Keycloak (OIDC)                                                             |
| Charts                     | matplotlib/seaborn, rendered server-side as PNGs                            |
| Containerization           | Docker Compose                                                              |

## Features

- Add, edit, delete, and test CockroachDB connections
- Encrypted storage of connection credentials (host, port, password) via Fernet — never stored or returned in plaintext
- Manual or cron-scheduled metadata ingestion, orchestrated by Airflow
- A friendly frequency/time picker converts to a real cron expression under the hood; raw cron is also supported for advanced cases
- Metadata Explorer — drill down Database → Schema → Table → Column with breadcrumb navigation, search, and pagination at every level
- Services page — a single tabbed view for connection management (Connections tab), a quick glance at recent activity (Recent Runs tab), and full filterable run history with Airflow log viewing (History tab)
- Dashboard with live aggregate stats and three server-rendered pie charts (connections by status, metadata volume, ingestion runs by outcome)
- Owner attribution on every connection, derived from the creating Keycloak user's token — not client-editable
- Search, status filtering, and pagination on every list endpoint
  
## Links for docker hub images
[metaconnect-frontend](https://hub.docker.com/r/zoyakhanam/metaconnect-frontend)


[metaconnect-api](https://hub.docker.com/r/zoyakhanam/metaconnect-api)

## Project structure

```

backend/app/
├── main.py                  # FastAPI app, routers, global exception handlers
├── core/                     # settings, Keycloak JWT validation + internal API key, Fernet encryption, logging, cron→next-run
├── db/                        # SQLAlchemy engine/session, declarative base + UUID/timestamp mixin
├── models/                    # Connection, DatabaseMetadata/SchemaMetadata/TableMetadata/ColumnMetadata, IngestionRun
├── schemas/                   # Pydantic request/response models, incl. validation rules
├── connectors/                 # BaseConnector + CockroachDBConnector + registry (class-based abstraction; see note below)
├── services/                   # IngestionService (persistence + run lifecycle), AirflowService (DAG deploy/trigger/logs), ChartService
└── api/v1/                     # connections, metadata, dashboard, charts, internal (Airflow-only callback endpoints)

airflow/dags/
├── generated/                  # per-connection DAG files, written at runtime — empty in git
└── utils/                       # the actual extraction pipeline: get_db, get_schema, get_table, get_column,
                                  # extract_metadata (orchestrates all four), run_ingestion (DAG task entry point)

frontend/src/
├── App.jsx                     # routing + auth gate
├── components/                  # Sidebar, Pagination, ConfirmDialog, Toast, LogsModal, AuthImage
├── pages/                       # Dashboard, Services (tab shell), ConnectionsTab, RecentRunsTab, HistoryTab, MetadataExplorer, Login
├── cronUtils.js                  # friendly schedule picker <-> cron string conversion
└── api.js                        # API client

liquibase/changelog/            # all schema migrations, in order — see DB.md
keycloak/realm-export.json      # pre-provisioned realm, client, and test user
docker-compose.yaml              # full stack definition

```

**Note on `connectors/`:** `BaseConnector`/`CockroachDBConnector`/`registry.py` are a class-based abstraction and are what the `/connections/test` endpoint uses. The actual scheduled/triggered ingestion pipeline that Airflow runs (`airflow/dags/utils/`) takes a separate, dict-based path with its own duplicated SQL rather than going through these connector classes. Worth being aware both exist if you're extending either one.

## Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- Nothing else needs to be installed locally — the frontend's `npm install` happens inside its own container

## Running locally

1. Copy the environment template and fill in real values:

   ```bash
   cp .env.example .env
   ```

   Generate an encryption key:

   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   Put that in `.env` as `ENCRYPTION_KEY`, plus a random `INTERNAL_API_KEY` and a real `AIRFLOW_PASSWORD`/`DB_PASSWORD`. Required variables (the app will fail to start without these): `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `ENCRYPTION_KEY`, `INTERNAL_API_KEY`, `KEYCLOAK_URL`, `KEYCLOAK_REALM`.

2. Start everything:

   ```bash
   docker compose up -d --build
   ```

3. Wait for `airflow-init` to finish (`docker compose ps` should show it `Exited (0)`), then check:
   - API + Swagger docs: http://localhost:8000/docs
   - Frontend: http://localhost:5173
   - Airflow UI: http://localhost:8080 (`admin` / your `AIRFLOW_PASSWORD`)
   - Keycloak admin console: http://localhost:8082/admin (`admin` / `admin`)

4. Log in to the app with the user seeded in `keycloak/realm-export.json` (`testuser` / `testpass` unless you've changed it).

## A dependency gap worth checking

Metadata extraction runs inside the Airflow containers and imports `psycopg2` directly (`airflow/dags/utils/get_db.py`). The Airflow services in `docker-compose.yaml` only declare `_PIP_ADDITIONAL_REQUIREMENTS: requests` — not `psycopg2-binary`. This may already work if the base `apache/airflow` image or one of its providers pulls in a Postgres driver transitively; if you see `ModuleNotFoundError: No module named 'psycopg2'` in an Airflow task log, add it explicitly:

```yaml
_PIP_ADDITIONAL_REQUIREMENTS: "requests psycopg2-binary"
```

## Adding a new connector

The class-based path (`/connections/test` and future extensions of the ingestion pipeline that route through it):

1. Create `backend/app/connectors/<name>_connector.py` implementing `BaseConnector`'s five methods.
2. Register it in `backend/app/connectors/registry.py` (stub files for `mysql_connector.py` and `postgres_connector.py` already exist, currently empty).
3. Add the type name to `ALLOWED_CONNECTION_TYPES` in `backend/app/schemas/connection.py`.

The Airflow extraction path (what actually runs today) would additionally need the new database type branched into each `get_db.py`/`get_schema.py`/`get_table.py`/`get_column.py` function — `get_db.py`'s `get_db_connection()` already has a MySQL branch scaffolded as an example.
