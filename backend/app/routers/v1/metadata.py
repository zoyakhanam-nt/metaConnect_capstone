import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.metadata import DatabaseOut, IngestionRunOut, IngestionRunWithConnection, SchemaOut, TableOut, ColumnOut
from app.schemas.pagination import Page
from app.services.metadata_service import AirflowLogsError, MetadataNotFoundError, MetadataService

router = APIRouter(tags=["metadata"])


def _not_found(exc: MetadataNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


def _service(db: Session) -> MetadataService:
    return MetadataService(db)


@router.post("/connections/{connection_id}/ingest", response_model=IngestionRunOut, status_code=201)
def trigger_ingestion(connection_id: uuid.UUID, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        return _service(db).trigger_ingestion(connection_id)
    except MetadataNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/ingestion/{run_id}", response_model=IngestionRunOut)
def get_ingestion_status(run_id: uuid.UUID, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        return _service(db).get_run(run_id)
    except MetadataNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/metadata/databases", response_model=Page[DatabaseOut])
def list_databases(connection_id: uuid.UUID, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), search: str | None = Query(None), db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return _service(db).databases(connection_id, skip, limit, search)


@router.get("/metadata/schemas", response_model=Page[SchemaOut])
def list_schemas(database_id: uuid.UUID, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), search: str | None = Query(None), db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return _service(db).schemas(database_id, skip, limit, search)


@router.get("/metadata/tables", response_model=Page[TableOut])
def list_tables(schema_id: uuid.UUID, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), search: str | None = Query(None), db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return _service(db).tables(schema_id, skip, limit, search)


@router.get("/metadata/columns", response_model=Page[ColumnOut])
def list_columns(table_id: uuid.UUID, skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), search: str | None = Query(None), db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return _service(db).columns(table_id, skip, limit, search)


@router.get("/ingestion/{run_id}/logs")
def get_ingestion_logs(run_id: uuid.UUID, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    try:
        return _service(db).logs(run_id)
    except MetadataNotFoundError as exc:
        raise _not_found(exc) from exc
    except AirflowLogsError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/runs", response_model=Page[IngestionRunWithConnection])
def list_all_runs(connection_id: uuid.UUID | None = Query(None), status: str | None = Query(None), skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    return _service(db).all_runs(connection_id, status, skip, limit)
