# Database

Single application database (`app-db`, PostgreSQL), managed entirely through Liquibase changesets in `liquibase/changelog/changelog-master.sql`. Airflow has its own separate internal Postgres database that this app never queries directly.

## Tables

### `connection`

One row per configured data source connection.

| Column                       | Type         | Notes                                                                                     |
| ---------------------------- | ------------ | ----------------------------------------------------------------------------------------- |
| `id`                         | UUID         | primary key                                                                               |
| `connection_name`            | varchar(255) |                                                                                           |
| `connection_type`            | varchar(50)  | e.g. `cockroachdb`; drives which connector class is used                                  |
| `host`                       | varchar(500) | **encrypted** (Fernet)                                                                    |
| `port`                       | varchar(500) | **encrypted** — stored as text since it's ciphertext, parsed back to int after decryption |
| `username`                   | varchar(255) |                                                                                           |
| `password`                   | varchar(255) | **encrypted**                                                                             |
| `description`                | text         | optional                                                                                  |
| `database`                   | varchar(255) | target database name on the source                                                        |
| `status`                     | varchar(20)  | `untested` / `connected` / `failed`                                                       |
| `schedule_cron`              | varchar(100) | nullable; 5-field cron expression, null = manual only                                     |
| `owner_name` / `owner_email` | varchar(255) | set once from the creating user's Keycloak token, not user-editable afterward             |
| `created_at` / `updated_at`  | timestamptz  |                                                                                           |

### `metadata_databases` / `metadata_schemas` / `metadata_tables` / `metadata_columns`

Mirror the extraction hierarchy exactly: `connection → database → schema → table → column`. Each level has a foreign key to its parent with `ON DELETE CASCADE`, and a `UNIQUE(parent_id, name)` constraint.

Cascading deletes mean: deleting a `connection` row deletes every database/schema/table/column that was ever ingested for it, automatically — no manual cleanup code needed.

The unique constraints mean: a re-ingestion must delete existing metadata for a connection before re-inserting, or it will hit constraint violations on duplicate names (`ingestion_service.py` does this at the start of every run).

`metadata_columns` additionally carries `data_type`, `is_primary_key`, and `is_nullable` — derived from `information_schema` joins against `key_column_usage`/`table_constraints` at extraction time (there's no direct "is primary key" flag in the standard information_schema views).

### `ingestion_runs`

One row per ingestion attempt (manual or scheduled).

| Column                       | Type         | Notes                                                                    |
| ---------------------------- | ------------ | ------------------------------------------------------------------------ |
| `id`                         | UUID         | primary key                                                              |
| `connection_id`              | UUID         | FK → `connection`, cascade delete                                        |
| `dag_id`                     | varchar(255) | which Airflow DAG ran this                                               |
| `dag_run_id`                 | varchar(255) | Airflow's specific run identifier — needed to fetch that run's task logs |
| `status`                     | varchar(20)  | `pending` / `running` / `success` / `failed`                             |
| `error_message`              | text         | populated on failure                                                     |
| `started_at` / `finished_at` | timestamptz  | `finished_at` is null while running                                      |

This table exists independently of Airflow's own run history so the app can show ingestion status to end users without exposing (or depending on) Airflow's internal schema.

## Migration history (changesets, in order)

1. Create `connection` (original schema, combined `host_port` field)
2. / 3. Scratch table added and dropped (early scaffolding, harmless no-op today)
3. Split `host_port` into `host` + `port`, add `connection_type` and `status`
4. Create the four metadata tables
5. Create `ingestion_runs`
6. Add `schedule_cron` to `connection`
7. Add `owner_name` / `owner_email` to `connection`
8. Widen `host`/`port` to `varchar(500)` to hold encrypted ciphertext instead of plaintext values
9. Add `dag_run_id` to `ingestion_runs`

Each changeset is tracked by Liquibase's own bookkeeping table inside the database, so `docker compose up` is always safe to re-run — already-applied changesets are skipped automatically.
