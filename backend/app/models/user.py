from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    full_name: Mapped[str] = mapped_column(String)
    organization: Mapped[str] = mapped_column(String, default="")
    role: Mapped[str] = mapped_column(String, default="responder")  # ngo, responder, researcher, admin
    phone: Mapped[str] = mapped_column(String, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow
    )


class IncidentAction(Base):
    """Audit log of human-in-the-loop verification, assignments, and resolution notes."""

    __tablename__ = "incident_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    detection_id: Mapped[str] = mapped_column(String, ForeignKey("detections.id"), index=True)
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)

    user_name: Mapped[str] = mapped_column(String, default="System")
    organization: Mapped[str] = mapped_column(String, default="")
    action: Mapped[str] = mapped_column(String)  # verified, rejected, assigned, being_handled, resolved, note_added
    previous_status: Mapped[str] = mapped_column(String, default="")
    new_status: Mapped[str] = mapped_column(String, default="")
    assigned_team: Mapped[str] = mapped_column(String, default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
