import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DatabaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class SchemaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class TableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class ColumnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    data_type: str | None
    is_primary_key: bool
    is_nullable: bool


class IngestionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    connection_id: uuid.UUID
    dag_id: str | None
    status: str
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None