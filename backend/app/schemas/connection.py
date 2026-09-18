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
    owner_name: str | None = Field(default=None, max_length=255)
    owner_email: EmailStr | None = None

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
    password: str | None = None
    description: str | None = Field(default=None, max_length=1000)
    database: str | None = Field(default=None, min_length=1, max_length=255)
    schedule_cron: str | None = Field(default=None, max_length=100)

    @field_validator("schedule_cron")
    @classmethod
    def validate_update_cron(cls, v: str | None) -> str | None:
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
    model_config = ConfigDict(from_attributes=True)

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