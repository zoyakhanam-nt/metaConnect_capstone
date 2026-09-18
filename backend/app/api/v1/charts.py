from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.connection import Connection
from app.models.metadata import ColumnMetadata, DatabaseMetadata, IngestionRun, TableMetadata
from app.services.chart_service import (
    render_connection_status_chart,
    render_metadata_counts_chart,
    render_runs_over_time_chart,
)

router = APIRouter(tags=["charts"])


@router.get("/dashboard/charts/connection-status.png")
def connection_status_chart(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    rows = db.execute(select(Connection.status, func.count()).group_by(Connection.status)).all()
    status_counts = {status: count for status, count in rows} or {"untested": 0}
    png = render_connection_status_chart(status_counts)
    return Response(content=png, media_type="image/png")


@router.get("/dashboard/charts/ingestion-runs.png")
def ingestion_runs_chart(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    since = datetime.now(timezone.utc) - timedelta(days=14)
    runs = db.execute(
        select(IngestionRun.started_at, IngestionRun.status).where(IngestionRun.started_at >= since)
    ).all()
    rows = [{"date": started_at.strftime("%Y-%m-%d"), "status": status} for started_at, status in runs]
    png = render_runs_over_time_chart(rows)
    return Response(content=png, media_type="image/png")


@router.get("/dashboard/charts/metadata-counts.png")
def metadata_counts_chart(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    counts = {
        "Databases": db.scalar(select(func.count()).select_from(DatabaseMetadata)) or 0,
        "Tables": db.scalar(select(func.count()).select_from(TableMetadata)) or 0,
        "Columns": db.scalar(select(func.count()).select_from(ColumnMetadata)) or 0,
    }
    png = render_metadata_counts_chart(counts)
    return Response(content=png, media_type="image/png")