from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.connection import Connection
from app.models.metadata import ColumnMetadata, DatabaseMetadata, IngestionRun, TableMetadata
from app.schemas.dashboard import DashboardStats, IngestionRunSummary

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    total_connections = db.scalar(select(func.count()).select_from(Connection)) or 0
    total_databases = db.scalar(select(func.count()).select_from(DatabaseMetadata)) or 0
    total_tables = db.scalar(select(func.count()).select_from(TableMetadata)) or 0
    total_columns = db.scalar(select(func.count()).select_from(ColumnMetadata)) or 0

    recent_runs = db.execute(
        select(IngestionRun, Connection.connection_name)
        .join(Connection, Connection.id == IngestionRun.connection_id)
        .order_by(IngestionRun.started_at.desc())
        .limit(10)
    ).all()

    return DashboardStats(
        total_connections=total_connections,
        total_databases=total_databases,
        total_tables=total_tables,
        total_columns=total_columns,
        recent_runs=[
            IngestionRunSummary(
                id=run.id,
                connection_name=conn_name,
                status=run.status,
                started_at=run.started_at,
                finished_at=run.finished_at,
            )
            for run, conn_name in recent_runs
        ],
    )