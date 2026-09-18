--liquibase formatted sql
--changeset zoya.khanam:1-create-connection-table
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE connection (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_name VARCHAR(255) NOT NULL,
    host_port VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    description TEXT,
    database VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

--rollback DROP TABLE connection;
--changeset zoya.khanam:2-create-test-table
CREATE TABLE test (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid()
);

--changeset zoya.khanam:3-drop-test-table
DROP TABLE IF EXISTS test;

--changeset zoya.khanam:4-add-connection-type-and-split-host-port
ALTER TABLE connection ADD COLUMN connection_type VARCHAR(50) NOT NULL DEFAULT 'cockroachdb';
ALTER TABLE connection ADD COLUMN host VARCHAR(255);
ALTER TABLE connection ADD COLUMN port INTEGER;
ALTER TABLE connection ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'untested';
UPDATE connection SET host = split_part(host_port, ':', 1), port = split_part(host_port, ':', 2)::int WHERE host_port IS NOT NULL;
ALTER TABLE connection ALTER COLUMN host SET NOT NULL;
ALTER TABLE connection ALTER COLUMN port SET NOT NULL;
ALTER TABLE connection DROP COLUMN host_port;

--rollback ALTER TABLE connection ADD COLUMN host_port VARCHAR(255); ALTER TABLE connection DROP COLUMN connection_type; ALTER TABLE connection DROP COLUMN host; ALTER TABLE connection DROP COLUMN port; ALTER TABLE connection DROP COLUMN status;

--changeset zoya.khanam:5-create-metadata-tables
CREATE TABLE metadata_databases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES connection(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (connection_id, name)
);

CREATE TABLE metadata_schemas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    database_id UUID NOT NULL REFERENCES metadata_databases(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (database_id, name)
);

CREATE TABLE metadata_tables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schema_id UUID NOT NULL REFERENCES metadata_schemas(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (schema_id, name)
);

CREATE TABLE metadata_columns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_id UUID NOT NULL REFERENCES metadata_tables(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    data_type VARCHAR(100),
    is_primary_key BOOLEAN NOT NULL DEFAULT false,
    is_nullable BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (table_id, name)
);

--rollback DROP TABLE metadata_columns; DROP TABLE metadata_tables; DROP TABLE metadata_schemas; DROP TABLE metadata_databases;

--changeset zoya.khanam:6-create-ingestion-runs
CREATE TABLE ingestion_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES connection(id) ON DELETE CASCADE,
    dag_id VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

--rollback DROP TABLE ingestion_runs;

--changeset zoya.khanam:7-add-schedule-cron
ALTER TABLE connection ADD COLUMN schedule_cron VARCHAR(100);

--changeset zoya.khanam:8-add-owner-details
ALTER TABLE connection ADD COLUMN owner_name VARCHAR(255);
ALTER TABLE connection ADD COLUMN owner_email VARCHAR(255);

--rollback ALTER TABLE connection DROP COLUMN owner_name; ALTER TABLE connection DROP COLUMN owner_email;


--changeset zoya.khanam:9-encrypt-host-port
ALTER TABLE connection ALTER COLUMN host TYPE VARCHAR(500);
ALTER TABLE connection ALTER COLUMN port TYPE VARCHAR(500) USING port::text;

--rollback ALTER TABLE connection ALTER COLUMN port TYPE INTEGER USING port::integer; ALTER TABLE connection ALTER COLUMN host TYPE VARCHAR(255);

--changeset zoya.khanam:10-add-dag-run-id
ALTER TABLE ingestion_runs ADD COLUMN dag_run_id VARCHAR(255);

--rollback ALTER TABLE ingestion_runs DROP COLUMN dag_run_id;