import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionScheduleUpdate,
    ConnectionTestResult,
    ConnectionUpdate,
)
from app.schemas.metadata import IngestionRunOut
from app.schemas.pagination import Page
from app.services.connection_service import ConnectionNotFoundError, ConnectionService

router = APIRouter(tags=["connections"])


def _service(db: Session) -> ConnectionService:
    return ConnectionService(db)


def _not_found(exc: ConnectionNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.post("/connections", response_model=ConnectionResponse, status_code=201)
def create_connection(
    payload: ConnectionCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return _service(db).create(payload, user)


@router.get("/connections", response_model=Page[ConnectionResponse])
def list_connections(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Filter by connection name"),
    status: str | None = Query(None, description="Filter by connection status"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return _service(db).list(skip, limit, search, status)


@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
def get_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    service = _service(db)
    try:
        return service.to_response(service.get(connection_id))
    except ConnectionNotFoundError as exc:
        raise _not_found(exc) from exc


@router.put("/connections/{connection_id}", response_model=ConnectionResponse)
def update_connection(
    connection_id: uuid.UUID,
    payload: ConnectionUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        return _service(db).update(connection_id, payload)
    except ConnectionNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/connections/{connection_id}/runs", response_model=Page[IngestionRunOut])
def list_connection_runs(
    connection_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        return _service(db).list_runs(connection_id, skip, limit)
    except ConnectionNotFoundError as exc:
        raise _not_found(exc) from exc


@router.put("/connections/{connection_id}/schedule", response_model=ConnectionResponse)
def update_schedule(
    connection_id: uuid.UUID,
    payload: ConnectionScheduleUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        return _service(db).update_schedule(connection_id, payload)
    except ConnectionNotFoundError as exc:
        raise _not_found(exc) from exc


@router.delete("/connections/{connection_id}", status_code=204)
def delete_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        _service(db).delete(connection_id)
    except ConnectionNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/connections/test", response_model=ConnectionTestResult)
def test_new_connection(
    payload: ConnectionCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    return _service(db).test_new(payload)


@router.post("/connections/{connection_id}/test", response_model=ConnectionTestResult)
def test_existing_connection(
    connection_id: uuid.UUID,
    payload: ConnectionUpdate | None = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        return _service(db).test_and_update_status(connection_id, payload)
    except ConnectionNotFoundError as exc:
        raise _not_found(exc) from exc
