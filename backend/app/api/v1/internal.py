import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.models.connection import Connection
from app.models.metadata import IngestionRun
from app.services.ingestion_service import run_ingestion

router = APIRouter(tags=["internal"])


def _run_and_record(db: Session, run: IngestionRun, connection: Connection) -> None:
    run.status = "running"
    db.commit()

    try:
        run_ingestion(db, connection)
        run.status = "success"
        connection.status = "connected"
    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        connection.status = "failed"
    finally:
        run.finished_at = datetime.now(timezone.utc)
        db.commit()


@router.post("/internal/ingestion-runs/{run_id}/execute", dependencies=[Depends(verify_internal_api_key)])
def execute_ingestion(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.get(IngestionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Ingestion run not found")

    connection = db.get(Connection, run.connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    _run_and_record(db, run, connection)
    return {"status": run.status}


@router.post("/internal/connections/{connection_id}/scheduled-ingest", dependencies=[Depends(verify_internal_api_key)])
def scheduled_ingest(connection_id: uuid.UUID, db: Session = Depends(get_db)):
    """Called by Airflow when a DAG fires on its own cron schedule (no pre-existing run row)."""
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    run = IngestionRun(connection_id=connection_id, status="pending")
    db.add(run)
    db.commit()
    db.refresh(run)

    _run_and_record(db, run, connection)
    return {"status": run.status, "run_id": str(run.id)}