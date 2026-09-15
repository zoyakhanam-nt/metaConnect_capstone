import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.cockroachdb import get_connector
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.connection import Connection
from app.schemas.connection import ConnectionCreate, ConnectionResponse, ConnectionTestResult
from app.schemas.pagination import Page

router = APIRouter(tags=["connections"])


@router.post("/connections", response_model=ConnectionResponse, status_code=201)
def create_connection(
    payload: ConnectionCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    connection = Connection(**payload.model_dump())
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


@router.get("/connections", response_model=Page[ConnectionResponse])
def list_connections(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="Filter by connection name"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    query = select(Connection)
    if search:
        query = query.where(Connection.connection_name.ilike(f"%{search}%"))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.execute(query.offset(skip).limit(limit)).scalars().all()

    return Page(items=items, total=total, skip=skip, limit=limit)


@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
def get_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    return connection


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


def _test(connection: Connection) -> ConnectionTestResult:
    connector = get_connector(
        connection.connection_type,
        host=connection.host,
        port=connection.port,
        database=connection.database,
        username=connection.username,
        password=connection.password,
    )
    try:
        connector.test_connection()
        return ConnectionTestResult(success=True, message="Connection successful")
    except Exception as e:
        return ConnectionTestResult(success=False, message=str(e))


@router.post("/connections/test", response_model=ConnectionTestResult)
def test_new_connection(
    payload: ConnectionCreate,
    user: dict = Depends(get_current_user),
):
    connection = Connection(**payload.model_dump())
    return _test(connection)


@router.post("/connections/{connection_id}/test", response_model=ConnectionTestResult)
def test_existing_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    result = _test(connection)
    connection.status = "connected" if result.success else "failed"
    db.commit()
    return result