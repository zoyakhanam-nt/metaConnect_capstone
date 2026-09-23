import uuid
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.connection import Connection
from app.models.metadata import ColumnMetadata, DatabaseMetadata, IngestionRun, SchemaMetadata, TableMetadata
from app.schemas.metadata import ColumnOut, DatabaseOut, IngestionRunOut, IngestionRunWithConnection, SchemaOut, TableOut
from app.schemas.pagination import Page
from app.services.airflow_service import AirflowService
from app.services.ingestion_service import IngestionService


class MetadataNotFoundError(ValueError):
    pass


class AirflowLogsError(ValueError):
    pass


class MetadataService:
    def __init__(self, db: Session, airflow_service: AirflowService | None = None):
        self.db = db
        self.airflow_service = airflow_service or AirflowService()

    def trigger_ingestion(self, connection_id: uuid.UUID) -> IngestionRun:
        connection = self.db.get(Connection, connection_id)
        if connection is None:
            raise MetadataNotFoundError("Connection not found")
        run = IngestionRun(connection_id=connection_id, status="pending")
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        try:
            dag_id, dag_run_id = self.airflow_service.deploy_and_trigger(
                str(connection_id), connection.connection_name, str(run.id), connection.schedule_cron
            )
            run.dag_id, run.dag_run_id, run.status = dag_id, dag_run_id, "running"
        except Exception as exc:
            run.status, run.error_message = "failed", str(exc)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: uuid.UUID) -> IngestionRun:
        run = self.db.get(IngestionRun, run_id)
        if run is None:
            raise MetadataNotFoundError("Ingestion run not found")
        return run

    def _page(self, model, parent_field, parent_id, name_field, skip, limit, search):
        query = select(model).where(parent_field == parent_id)
        if search:
            query = query.where(name_field.ilike(f"%{search}%"))
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.execute(query.offset(skip).limit(limit)).scalars().all()
        return Page(items=items, total=total, skip=skip, limit=limit)

    def databases(self, connection_id, skip, limit, search) -> Page[DatabaseOut]:
        return self._page(DatabaseMetadata, DatabaseMetadata.connection_id, connection_id, DatabaseMetadata.name, skip, limit, search)

    def schemas(self, database_id, skip, limit, search) -> Page[SchemaOut]:
        return self._page(SchemaMetadata, SchemaMetadata.database_id, database_id, SchemaMetadata.name, skip, limit, search)

    def tables(self, schema_id, skip, limit, search) -> Page[TableOut]:
        return self._page(TableMetadata, TableMetadata.schema_id, schema_id, TableMetadata.name, skip, limit, search)

    def columns(self, table_id, skip, limit, search) -> Page[ColumnOut]:
        return self._page(ColumnMetadata, ColumnMetadata.table_id, table_id, ColumnMetadata.name, skip, limit, search)

    def logs(self, run_id: uuid.UUID) -> dict[str, str]:
        run = self.get_run(run_id)
        if not run.dag_id or not run.dag_run_id:
            raise AirflowLogsError("No Airflow logs available for this run")
        try:
            return {"logs": self.airflow_service.fetch_task_logs(run.dag_id, run.dag_run_id)}
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 502
            body = exc.response.text[:300] if exc.response is not None else str(exc)
            raise AirflowLogsError(f"Airflow returned {status_code}: {body}") from exc
        except Exception as exc:
            raise AirflowLogsError(f"Could not reach Airflow: {exc}") from exc

    def all_runs(self, connection_id, status, skip, limit) -> Page[IngestionRunWithConnection]:
        query = select(IngestionRun, Connection.connection_name).join(Connection, Connection.id == IngestionRun.connection_id)
        if connection_id:
            query = query.where(IngestionRun.connection_id == connection_id)
        if status:
            query = query.where(IngestionRun.status == status)
        query = query.order_by(IngestionRun.started_at.desc())
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self.db.execute(query.offset(skip).limit(limit)).all()
        items = [IngestionRunWithConnection(
            id=run.id, connection_id=run.connection_id, connection_name=name,
            dag_id=run.dag_id, dag_run_id=run.dag_run_id, status=run.status,
            error_message=run.error_message, started_at=run.started_at, finished_at=run.finished_at,
        ) for run, name in rows]
        return Page(items=items, total=total, skip=skip, limit=limit)

    def receive_metadata(self, connection_id: uuid.UUID, payload: dict) -> dict:
        if self.db.get(Connection, connection_id) is None:
            raise MetadataNotFoundError("Connection not found")
        return IngestionService(self.db).handle_metadata_payload(connection_id, payload)

    def start_run(self, connection_id: uuid.UUID, payload: dict) -> dict:
        if self.db.get(Connection, connection_id) is None:
            raise MetadataNotFoundError("Connection not found")
        run = IngestionService(self.db).start_run(connection_id, payload.get("dag_id"), payload.get("dag_run_id"))
        return {"status": run.status, "run_id": str(run.id)}

    def connection_config(self, connection_id: uuid.UUID) -> dict:
        connection = self.db.get(Connection, connection_id)
        if connection is None:
            raise MetadataNotFoundError("Connection not found")
        from app.core.crypto import decrypt_value
        return {
            "connection_id": str(connection.id), "connection_name": connection.connection_name,
            "connection_type": connection.connection_type, "host": decrypt_value(connection.host),
            "port": int(decrypt_value(connection.port)), "database": connection.database,
            "username": connection.username, "password": decrypt_value(connection.password),
        }


class ChartDataService:
    def __init__(self, db: Session):
        self.db = db

    def connection_status(self) -> dict[str, int]:
        rows = self.db.execute(select(Connection.status, func.count()).group_by(Connection.status)).all()
        return {status: count for status, count in rows} or {"untested": 0}

    def ingestion_runs(self) -> list[dict[str, str]]:
        since = datetime.now(timezone.utc) - timedelta(days=14)
        runs = self.db.execute(select(IngestionRun.started_at, IngestionRun.status).where(IngestionRun.started_at >= since)).all()
        return [{"date": started_at.strftime("%Y-%m-%d"), "status": status} for started_at, status in runs]

    def metadata_counts(self) -> dict[str, int]:
        return {
            "Databases": self.db.scalar(select(func.count()).select_from(DatabaseMetadata)) or 0,
            "Tables": self.db.scalar(select(func.count()).select_from(TableMetadata)) or 0,
            "Columns": self.db.scalar(select(func.count()).select_from(ColumnMetadata)) or 0,
        }
