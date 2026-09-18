from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class Connection(BaseModel):
    __tablename__ = "connection"

    connection_name: Mapped[str] = mapped_column(String(255), nullable=False)
    connection_type: Mapped[str] = mapped_column(String(50), nullable=False, default="cockroachdb")
    host: Mapped[str] = mapped_column(String(500), nullable=False)      # stored ENCRYPTED
    port: Mapped[str] = mapped_column(String(500), nullable=False)      # stored ENCRYPTED (parse to int after decrypt)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)  # stored ENCRYPTED
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    database: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="untested")
    schedule_cron: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
