from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.services.chart_service import ChartService
from app.services.metadata_service import ChartDataService

router = APIRouter(tags=["charts"])


@router.get("/dashboard/charts/connection-status.png")
def connection_status_chart(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    png = ChartService().render_connection_status_chart(ChartDataService(db).connection_status())
    return Response(content=png, media_type="image/png")


@router.get("/dashboard/charts/ingestion-runs.png")
def ingestion_runs_chart(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    png = ChartService().render_runs_over_time_chart(ChartDataService(db).ingestion_runs())
    return Response(content=png, media_type="image/png")


@router.get("/dashboard/charts/metadata-counts.png")
def metadata_counts_chart(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    png = ChartService().render_metadata_counts_chart(ChartDataService(db).metadata_counts())
    return Response(content=png, media_type="image/png")
