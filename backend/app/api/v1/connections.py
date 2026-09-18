import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.registry import get_connector
from app.core.crypto import decrypt_value, encrypt_value
from app.core.scheduling import compute_next_run
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.connection import Connection
from app.models.metadata import IngestionRun
from app.schemas.connection import (
    ConnectionCreate,
    ConnectionResponse,
    ConnectionScheduleUpdate,
    ConnectionTestResult,
    ConnectionUpdate,
)
from app.schemas.metadata import IngestionRunOut
from app.schemas.pagination import Page
from app.services.airflow_service import AirflowService

router = APIRouter(tags=["connections"])
airflow_service = AirflowService()


def _to_response(connection: Connection) -> ConnectionResponse:
    return ConnectionResponse(
        id=connection.id,
        connection_name=connection.connection_name,
        connection_type=connection.connection_type,
        host=decrypt_value(connection.host),
        port=int(decrypt_value(connection.port)),
        username=connection.username,
        description=connection.description,
        database=connection.database,
        status=connection.status,
        schedule_cron=connection.schedule_cron,
        next_run_at=compute_next_run(connection.schedule_cron),
        owner_name=connection.owner_name,
        owner_email=connection.owner_email,
        created_at=connection.created_at,
        updated_at=connection.updated_at,
    )


@router.post("/connections", response_model=ConnectionResponse, status_code=201)
def create_connection(
    payload: ConnectionCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    data = payload.model_dump()
    data["password"] = encrypt_value(data["password"])
    data["host"] = encrypt_value(data["host"])
    data["port"] = encrypt_value(str(data["port"]))

    # owner is derived from the logged-in user's token, never from the client
    data["owner_name"] = user.get("preferred_username") or user.get("name")
    data["owner_email"] = user.get("email")

    connection = Connection(**data)
    db.add(connection)
    db.commit()
    db.refresh(connection)

    if connection.schedule_cron:
        airflow_service.register_schedule(
            str(connection.id), connection.connection_name, connection.schedule_cron
        )

    return _to_response(connection)


@router.get("/connections", response_model=Page[ConnectionResponse])
def list_connections(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Filter by connection name"),
    status: str | None = Query(None, description="Filter by status: untested/connected/failed"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = select(Connection)
    if search:
        query = query.where(Connection.connection_name.ilike(f"%{search}%"))
    if status:
        query = query.where(Connection.status == status)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.execute(query.offset(skip).limit(limit)).scalars().all()
    return Page(items=[_to_response(c) for c in items], total=total, skip=skip, limit=limit)


@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
def get_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    return _to_response(connection)


@router.put("/connections/{connection_id}", response_model=ConnectionResponse)
def update_connection(
    connection_id: uuid.UUID,
    payload: ConnectionUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    data = payload.model_dump(exclude_unset=True)

    if "host" in data:
        connection.host = encrypt_value(data.pop("host"))
    if "port" in data:
        connection.port = encrypt_value(str(data.pop("port")))
    if "password" in data:
        pw = data.pop("password")
        if pw:  # empty/omitted password means "leave unchanged"
            connection.password = encrypt_value(pw)

    for field, value in data.items():
        setattr(connection, field, value)

    db.commit()
    db.refresh(connection)

    airflow_service.register_schedule(
        str(connection.id), connection.connection_name, connection.schedule_cron
    )

    return _to_response(connection)


@router.get("/connections/{connection_id}/runs", response_model=Page[IngestionRunOut])
def list_connection_runs(
    connection_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    query = select(IngestionRun).where(IngestionRun.connection_id == connection_id).order_by(
        IngestionRun.started_at.desc()
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.execute(query.offset(skip).limit(limit)).scalars().all()
    return Page(items=items, total=total, skip=skip, limit=limit)


@router.put("/connections/{connection_id}/schedule", response_model=ConnectionResponse)
def update_schedule(
    connection_id: uuid.UUID,
    payload: ConnectionScheduleUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    connection.schedule_cron = payload.schedule_cron
    db.commit()
    db.refresh(connection)

    airflow_service.register_schedule(
        str(connection.id), connection.connection_name, connection.schedule_cron
    )

    return _to_response(connection)


@router.delete("/connections/{connection_id}", status_code=204)
def delete_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    db.delete(connection)
    db.commit()


def _test(
    connection_type: str,
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
) -> ConnectionTestResult:
    try:
        connector = get_connector(
            connection_type or "cockroachdb",
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
        )
        connector.test_connection()
        return ConnectionTestResult(success=True, message="Connection successful")
    except Exception as e:
        return ConnectionTestResult(success=False, message=str(e))


@router.post("/connections/test", response_model=ConnectionTestResult)
def test_new_connection(payload: ConnectionCreate, user: dict = Depends(get_current_user)):
    """Used both by the standalone 'test before save' call and by the Add/Edit form's
    inline Test button — takes raw (unencrypted, not-yet-saved) values."""
    return _test(
        payload.connection_type,
        payload.host,
        payload.port,
        payload.database,
        payload.username,
        payload.password,
    )


@router.post("/connections/{connection_id}/test", response_model=ConnectionTestResult)
def test_existing_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")

    result = _test(
        connection.connection_type,
        decrypt_value(connection.host),
        int(decrypt_value(connection.port)),
        connection.database,
        connection.username,
        decrypt_value(connection.password),
    )
    connection.status = "connected" if result.success else "failed"
    db.commit()
    return result