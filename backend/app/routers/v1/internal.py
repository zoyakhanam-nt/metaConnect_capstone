import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import verify_internal_api_key
from app.db.session import get_db
from app.services.metadata_service import MetadataNotFoundError, MetadataService

router = APIRouter(tags=["internal"])


def _not_found(exc: MetadataNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.get("/internal/connections/{connection_id}/config", dependencies=[Depends(verify_internal_api_key)])
def get_connection_config(connection_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        return MetadataService(db).connection_config(connection_id)
    except MetadataNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/internal/connections/{connection_id}/start-run", dependencies=[Depends(verify_internal_api_key)])
def start_run(connection_id: uuid.UUID, payload: dict[str, Any] = {}, db: Session = Depends(get_db)):
    try:
        return MetadataService(db).start_run(connection_id, payload)
    except MetadataNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/internal/connections/{connection_id}/metadata", dependencies=[Depends(verify_internal_api_key)])
def receive_metadata(connection_id: uuid.UUID, payload: dict[str, Any], db: Session = Depends(get_db)):
    try:
        return MetadataService(db).receive_metadata(connection_id, payload)
    except MetadataNotFoundError as exc:
        raise _not_found(exc) from exc
