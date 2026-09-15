from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class Connection(BaseModel):
    __tablename__ = "connection"

    connection_name: Mapped[str] = mapped_column(String(255), nullable=False)
    connection_type: Mapped[str] = mapped_column(String(50), nullable=False, default="cockroachdb")
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    database: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="untested")