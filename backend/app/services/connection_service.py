import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.registry import get_connector
from app.core.crypto import decrypt_value, encrypt_value
from app.core.scheduling import compute_next_run
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


class ConnectionNotFoundError(ValueError):
    pass


class ConnectionService:
    def __init__(self, db: Session, airflow_service: AirflowService | None = None):
        self.db = db
        self.airflow_service = airflow_service or AirflowService()

    @staticmethod
    def to_response(connection: Connection) -> ConnectionResponse:
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

    def get(self, connection_id: uuid.UUID) -> Connection:
        connection = self.db.get(Connection, connection_id)
        if connection is None:
            raise ConnectionNotFoundError("Connection not found")
        return connection

    def create(self, payload: ConnectionCreate, user: dict) -> ConnectionResponse:
        data = payload.model_dump()
        data["password"] = encrypt_value(data["password"])
        data["host"] = encrypt_value(data["host"])
        data["port"] = encrypt_value(str(data["port"]))
        data["owner_name"] = user.get("preferred_username") or user.get("name")
        data["owner_email"] = user.get("email")

        connection = Connection(**data)
        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)
        self._register_schedule(connection)
        return self.to_response(connection)

    def list(
        self, skip: int, limit: int, search: str | None, status: str | None
    ) -> Page[ConnectionResponse]:
        query = select(Connection)
        if search:
            query = query.where(Connection.connection_name.ilike(f"%{search}%"))
        if status:
            query = query.where(Connection.status == status)
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.execute(query.offset(skip).limit(limit)).scalars().all()
        return Page(items=[self.to_response(item) for item in items], total=total, skip=skip, limit=limit)

    def update(self, connection_id: uuid.UUID, payload: ConnectionUpdate) -> ConnectionResponse:
        connection = self.get(connection_id)
        data = payload.model_dump(exclude_unset=True)
        if "host" in data:
            connection.host = encrypt_value(data.pop("host"))
        if "port" in data:
            connection.port = encrypt_value(str(data.pop("port")))
        if data.get("password"):
            connection.password = encrypt_value(data.pop("password"))
        else:
            data.pop("password", None)
        for field, value in data.items():
            setattr(connection, field, value)
        self.db.commit()
        self.db.refresh(connection)
        self._register_schedule(connection)
        return self.to_response(connection)

    def delete(self, connection_id: uuid.UUID) -> None:
        connection = self.get(connection_id)
        self.db.delete(connection)
        self.db.commit()

    def update_schedule(
        self, connection_id: uuid.UUID, payload: ConnectionScheduleUpdate
    ) -> ConnectionResponse:
        connection = self.get(connection_id)
        connection.schedule_cron = payload.schedule_cron
        self.db.commit()
        self.db.refresh(connection)
        self._register_schedule(connection)
        return self.to_response(connection)

    def list_runs(
        self, connection_id: uuid.UUID, skip: int, limit: int
    ) -> Page[IngestionRunOut]:
        self.get(connection_id)
        query = select(IngestionRun).where(
            IngestionRun.connection_id == connection_id
        ).order_by(IngestionRun.started_at.desc())
        total = self.db.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = self.db.execute(query.offset(skip).limit(limit)).scalars().all()
        return Page(items=items, total=total, skip=skip, limit=limit)

    def test_new(self, payload: ConnectionCreate) -> ConnectionTestResult:
        return self._test(
            payload.connection_type,
            payload.host,
            payload.port,
            payload.database,
            payload.username,
            payload.password,
        )

    def test_existing(
        self, connection_id: uuid.UUID, payload: ConnectionUpdate | None = None
    ) -> ConnectionTestResult:
        connection = self.get(connection_id)
        values = payload.model_dump(exclude_unset=True) if payload else {}
        password = values.get("password") or decrypt_value(connection.password)
        return self._test(
            connection.connection_type,
            values.get("host", decrypt_value(connection.host)),
            values.get("port", int(decrypt_value(connection.port))),
            values.get("database", connection.database),
            values.get("username", connection.username),
            password,
        )

    def test_and_update_status(
        self, connection_id: uuid.UUID, payload: ConnectionUpdate | None = None
    ) -> ConnectionTestResult:
        result = self.test_existing(connection_id, payload)
        connection = self.get(connection_id)
        connection.status = "connected" if result.success else "failed"
        self.db.commit()
        return result

    @staticmethod
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
        except Exception as exc:
            return ConnectionTestResult(success=False, message=str(exc))

    def _register_schedule(self, connection: Connection) -> None:
        if connection.schedule_cron:
            self.airflow_service.register_schedule(
                str(connection.id), connection.connection_name, connection.schedule_cron
            )
