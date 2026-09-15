import uuid
from datetime import datetime

from pydantic import BaseModel


class IngestionRunSummary(BaseModel):
    id: uuid.UUID
    connection_name: str
    status: str
    started_at: datetime
    finished_at: datetime | None


class DashboardStats(BaseModel):
    total_connections: int
    total_databases: int
    total_tables: int
    total_columns: int
    recent_runs: list[IngestionRunSummary]