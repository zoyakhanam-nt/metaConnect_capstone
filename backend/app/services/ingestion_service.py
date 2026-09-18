import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.connection import Connection
from app.models.metadata import (
    ColumnMetadata,
    DatabaseMetadata,
    IngestionRun,
    SchemaMetadata,
    TableMetadata,
)

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Object-Oriented Service handling metadata persistence and ingestion run lifecycles.
    All extraction logic is decoupled and executed in Airflow workers.
    """

    def __init__(self, db: Session):
        self.db = db

    def start_run(
        self,
        connection_id: uuid.UUID,
        dag_id: str | None = None,
        dag_run_id: str | None = None,
    ) -> IngestionRun:
        """Create or advance an IngestionRun to 'running' status."""
        run = IngestionRun(
            connection_id=connection_id,
            dag_id=dag_id,
            dag_run_id=dag_run_id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        logger.info("Started ingestion run %s for connection %s", run.id, connection_id)
        return run

    def complete_run(
        self,
        run_id: uuid.UUID,
        status: str = "success",
        error_message: str | None = None,
    ) -> IngestionRun:
        """Mark an IngestionRun as completed (success or failed)."""
        run = self.db.get(IngestionRun, run_id)
        if not run:
            raise ValueError(f"IngestionRun '{run_id}' not found")

        run.status = status
        run.error_message = error_message
        run.finished_at = datetime.now(timezone.utc)

        # Update connection status accordingly
        connection = self.db.get(Connection, run.connection_id)
        if connection:
            connection.status = "connected" if status == "success" else "failed"

        self.db.commit()
        self.db.refresh(run)
        logger.info(
            "Completed ingestion run %s for connection %s with status '%s'",
            run.id,
            run.connection_id,
            status,
        )
        return run

    def save_metadata(self, connection_id: uuid.UUID, metadata: list[dict[str, Any]]) -> None:
        """
        Persist the extracted hierarchical metadata payload into the PostgreSQL database.
        Deletes prior metadata associated with the connection and replaces it atomically.
        """
        logger.info(
            "Persisting metadata for connection %s (%d database(s) in payload)...",
            connection_id,
            len(metadata),
        )

        try:
            # Clear existing metadata for this connection (cascades to schemas, tables, columns)
            self.db.query(DatabaseMetadata).filter(
                DatabaseMetadata.connection_id == connection_id
            ).delete()
            self.db.commit()

            for db_item in metadata:
                db_row = DatabaseMetadata(connection_id=connection_id, name=db_item["name"])
                self.db.add(db_row)
                self.db.flush()

                for schema_item in db_item.get("schemas", []):
                    schema_row = SchemaMetadata(
                        database_id=db_row.id, name=schema_item["name"]
                    )
                    self.db.add(schema_row)
                    self.db.flush()

                    for table_item in schema_item.get("tables", []):
                        table_row = TableMetadata(
                            schema_id=schema_row.id, name=table_item["name"]
                        )
                        self.db.add(table_row)
                        self.db.flush()

                        for col in table_item.get("columns", []):
                            self.db.add(
                                ColumnMetadata(
                                    table_id=table_row.id,
                                    name=col["name"],
                                    data_type=col.get("data_type"),
                                    is_primary_key=col.get("is_primary_key", False),
                                    is_nullable=col.get("is_nullable", True),
                                )
                            )

            self.db.commit()
            logger.info("Successfully persisted metadata for connection %s", connection_id)

        except Exception as e:
            self.db.rollback()
            logger.exception("Failed to persist metadata for connection %s: %s", connection_id, str(e))
            raise

    def handle_metadata_payload(self, connection_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Handle incoming metadata payload from Airflow worker.
        """
        run_id_str = payload.get("run_id")
        run_id = uuid.UUID(run_id_str) if run_id_str else None
        status = payload.get("status", "success")
        error_message = payload.get("error_message")
        metadata = payload.get("metadata", [])

        if status == "success":
            self.save_metadata(connection_id, metadata)
            if run_id:
                self.complete_run(run_id, status="success")
            else:
                conn = self.db.get(Connection, connection_id)
                if conn:
                    conn.status = "connected"
                    self.db.commit()
        else:
            if run_id:
                self.complete_run(run_id, status="failed", error_message=error_message)
            else:
                conn = self.db.get(Connection, connection_id)
                if conn:
                    conn.status = "failed"
                    self.db.commit()

        return {
            "status": status,
            "connection_id": str(connection_id),
            "run_id": str(run_id) if run_id else None,
        }
