import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_value
from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.models.connection import Connection
from app.models.metadata import IngestionRun
from app.services.ingestion_service import IngestionService

router = APIRouter(tags=["internal"])


@router.get(
    "/internal/connections/{connection_id}/config",
    dependencies=[Depends(verify_internal_api_key)],
)
def get_connection_config(connection_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Returns decrypted connection configuration so Airflow workers can connect
    and extract metadata directly with full database flexibility.
    """
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    return {
        "connection_id": str(connection.id),
        "connection_name": connection.connection_name,
        "connection_type": connection.connection_type,
        "host": decrypt_value(connection.host),
        "port": int(decrypt_value(connection.port)),
        "database": connection.database,
        "username": connection.username,
        "password": decrypt_value(connection.password),
    }


@router.post(
    "/internal/connections/{connection_id}/start-run",
    dependencies=[Depends(verify_internal_api_key)],
)
def start_run(
    connection_id: uuid.UUID,
    payload: dict[str, Any] = {},
    db: Session = Depends(get_db),
):
    """
    Called by Airflow when a scheduled or manual run starts without an existing run row,
    or to register dag_id and dag_run_id.
    """
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    service = IngestionService(db)
    run = service.start_run(
        connection_id=connection_id,
        dag_id=payload.get("dag_id"),
        dag_run_id=payload.get("dag_run_id"),
    )
    return {"status": run.status, "run_id": str(run.id)}


@router.post(
    "/internal/connections/{connection_id}/metadata",
    dependencies=[Depends(verify_internal_api_key)],
)
def receive_metadata(
    connection_id: uuid.UUID,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
):
    """
    Called by Airflow upon finishing metadata extraction to persist all databases,
    schemas, tables, and columns into PostgreSQL and update run status.
    """
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    service = IngestionService(db)
    result = service.handle_metadata_payload(connection_id, payload)
    return result




