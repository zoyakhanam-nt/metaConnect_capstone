from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.connection import Connection
from app.models.metadata import ColumnMetadata, DatabaseMetadata, IngestionRun, TableMetadata
from app.schemas.dashboard import DashboardStats, IngestionRunSummary


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def stats(self) -> DashboardStats:
        recent_runs = self.db.execute(
            select(IngestionRun, Connection.connection_name)
            .join(Connection, Connection.id == IngestionRun.connection_id)
            .order_by(IngestionRun.started_at.desc())
            .limit(10)
        ).all()
        return DashboardStats(
            total_connections=self._count(Connection),
            total_databases=self._count(DatabaseMetadata),
            total_tables=self._count(TableMetadata),
            total_columns=self._count(ColumnMetadata),
            recent_runs=[IngestionRunSummary(
                id=run.id,
                connection_name=name,
                status=run.status,
                started_at=run.started_at,
                finished_at=run.finished_at,
            ) for run, name in recent_runs],
        )

    def _count(self, model) -> int:
        return self.db.scalar(select(func.count()).select_from(model)) or 0
