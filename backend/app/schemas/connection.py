import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_CONNECTION_TYPES = {"cockroachdb"}


class ConnectionCreate(BaseModel):
    connection_name: str = Field(..., min_length=1, max_length=255)
    connection_type: str = Field(default="cockroachdb")
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = ""
    description: str | None = Field(default=None, max_length=1000)
    database: str = Field(..., min_length=1, max_length=255)

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
    created_at: datetime
    updated_at: datetime


class ConnectionTestResult(BaseModel):
    success: bool
    message: str