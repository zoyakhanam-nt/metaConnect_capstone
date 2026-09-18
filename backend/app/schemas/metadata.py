import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

ALLOWED_CONNECTION_TYPES = {"cockroachdb"}
CRON_REGEX = re.compile(r"^(\S+\s+){4}\S+$")


class ConnectionCreate(BaseModel):
    connection_name: str = Field(..., min_length=1, max_length=255)
    connection_type: str = Field(default="cockroachdb")
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = ""
    description: str | None = Field(default=None, max_length=1000)
    database: str = Field(..., min_length=1, max_length=255)
    schedule_cron: str | None = Field(default=None, max_length=100)
    # NOTE: no owner fields here on purpose — owner is derived from the
    # authenticated user at creation time, not supplied by the client.

    @field_validator("connection_type")
    @classmethod
    def validate_connection_type(cls, v: str) -> str:
        if v not in ALLOWED_CONNECTION_TYPES:
            raise ValueError(f"connection_type must be one of {sorted(ALLOWED_CONNECTION_TYPES)}")
        return v

    @field_validator("connection_name", "host", "username", "database")
    @classmethod
    def strip_and_require_non_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("schedule_cron")
    @classmethod
    def validate_cron(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        v = v.strip()
        if not CRON_REGEX.match(v):
            raise ValueError("schedule_cron must be a 5-field cron expression, e.g. '0 */6 * * *'")
        return v


class ConnectionUpdate(BaseModel):
    connection_name: str | None = Field(default=None, min_length=1, max_length=255)
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = None  # omit or send "" to leave unchanged; non-empty replaces it
    description: str | None = Field(default=None, max_length=1000)
    database: str | None = Field(default=None, min_length=1, max_length=255)
    schedule_cron: str | None = Field(default=None, max_length=100)
    owner_name: str | None = Field(default=None, max_length=255)
    owner_email: EmailStr | None = None

    @field_validator("schedule_cron")
    @classmethod
    def validate_cron(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        v = v.strip()
        if not CRON_REGEX.match(v):
            raise ValueError("schedule_cron must be a 5-field cron expression, e.g. '0 */6 * * *'")
        return v


class ConnectionScheduleUpdate(BaseModel):
    schedule_cron: str | None = Field(default=None, max_length=100)

    @field_validator("schedule_cron")
    @classmethod
    def validate_cron(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        v = v.strip()
        if not CRON_REGEX.match(v):
            raise ValueError("schedule_cron must be a 5-field cron expression, e.g. '0 */6 * * *'")
        return v


class ConnectionResponse(BaseModel):
    id: uuid.UUID
    connection_name: str
    connection_type: str
    host: str
    port: int
    username: str
    description: str | None
    database: str
    status: str
    schedule_cron: str | None
    next_run_at: datetime | None = None
    owner_name: str | None
    owner_email: str | None
    created_at: datetime
    updated_at: datetime


class ConnectionTestResult(BaseModel):
    success: bool
    message: str


class DatabaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    connection_id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime


class SchemaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    database_id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime


class TableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    schema_id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime


class ColumnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    table_id: uuid.UUID
    name: str
    data_type: str | None
    is_primary_key: bool
    is_nullable: bool
    created_at: datetime
    updated_at: datetime


class IngestionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    connection_id: uuid.UUID
    dag_id: str | None
    dag_run_id: str | None
    status: str
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None

class IngestionRunWithConnection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    connection_id: uuid.UUID
    connection_name: str
    dag_id: str | None
    dag_run_id: str | None
    status: str
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None