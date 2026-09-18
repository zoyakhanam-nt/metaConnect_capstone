import uuid

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.connection import Connection
from app.models.metadata import ColumnMetadata, DatabaseMetadata, IngestionRun, SchemaMetadata, TableMetadata
from app.schemas.metadata import ColumnOut, DatabaseOut, IngestionRunOut, IngestionRunWithConnection, SchemaOut, TableOut
from app.schemas.pagination import Page
from app.services.airflow_service import AirflowService

router = APIRouter(tags=["metadata"])
airflow_service = AirflowService()


@router.post("/connections/{connection_id}/ingest", response_model=IngestionRunOut, status_code=201)
def trigger_ingestion(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    run = IngestionRun(connection_id=connection_id, status="pending")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        dag_id, dag_run_id = airflow_service.deploy_and_trigger(str(connection_id), str(run.id), connection.schedule_cron)
        run.dag_id = dag_id
        run.dag_run_id = dag_run_id
        run.status = "running"
    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)

    db.commit()
    db.refresh(run)
    return run


@router.get("/ingestion/{run_id}", response_model=IngestionRunOut)
def get_ingestion_status(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    run = db.get(IngestionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Ingestion run not found")
    return run


@router.get("/metadata/databases", response_model=Page[DatabaseOut])
def list_databases(
    connection_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = select(DatabaseMetadata).where(DatabaseMetadata.connection_id == connection_id)
    if search:
        query = query.where(DatabaseMetadata.name.ilike(f"%{search}%"))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.execute(query.offset(skip).limit(limit)).scalars().all()
    return Page(items=items, total=total, skip=skip, limit=limit)


@router.get("/metadata/schemas", response_model=Page[SchemaOut])
def list_schemas(
    database_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = select(SchemaMetadata).where(SchemaMetadata.database_id == database_id)
    if search:
        query = query.where(SchemaMetadata.name.ilike(f"%{search}%"))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.execute(query.offset(skip).limit(limit)).scalars().all()
    return Page(items=items, total=total, skip=skip, limit=limit)


@router.get("/metadata/tables", response_model=Page[TableOut])
def list_tables(
    schema_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = select(TableMetadata).where(TableMetadata.schema_id == schema_id)
    if search:
        query = query.where(TableMetadata.name.ilike(f"%{search}%"))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.execute(query.offset(skip).limit(limit)).scalars().all()
    return Page(items=items, total=total, skip=skip, limit=limit)


@router.get("/metadata/columns", response_model=Page[ColumnOut])
def list_columns(
    table_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    ):
    query = select(ColumnMetadata).where(ColumnMetadata.table_id == table_id)
    if search:
        query = query.where(ColumnMetadata.name.ilike(f"%{search}%"))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.execute(query.offset(skip).limit(limit)).scalars().all()
    return Page(items=items, total=total, skip=skip, limit=limit)

@router.get("/ingestion/{run_id}/logs")
def get_ingestion_logs(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    run = db.get(IngestionRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Ingestion run not found")
    if not run.dag_id or not run.dag_run_id:
        raise HTTPException(status_code=404, detail="No Airflow logs available for this run")

    try:
        logs = airflow_service.fetch_task_logs(run.dag_id, run.dag_run_id)
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else 502
        body = e.response.text[:300] if e.response is not None else str(e)
        raise HTTPException(status_code=502, detail=f"Airflow returned {status_code}: {body}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Airflow: {e}")

    return {"logs": logs}

@router.get("/runs", response_model=Page[IngestionRunWithConnection])
def list_all_runs(
    connection_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = select(IngestionRun, Connection.connection_name).join(
        Connection, Connection.id == IngestionRun.connection_id
    )
    if connection_id:
        query = query.where(IngestionRun.connection_id == connection_id)
    if status:
        query = query.where(IngestionRun.status == status)
    query = query.order_by(IngestionRun.started_at.desc())

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(query.offset(skip).limit(limit)).all()

    items = [
        IngestionRunWithConnection(
            id=run.id,
            connection_id=run.connection_id,
            connection_name=name,
            dag_id=run.dag_id,
            dag_run_id=run.dag_run_id,
            status=run.status,
            error_message=run.error_message,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )
        for run, name in rows
    ]
    return Page(items=items, total=total, skip=skip, limit=limit)