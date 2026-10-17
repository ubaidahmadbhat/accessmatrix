"""AccessMatrix database models."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from accessmatrix.persistence.database import Base


def utc_now() -> datetime:
    """Return the current UTC time."""

    return datetime.now(UTC)


class Project(Base):
    """An API authorization testing project."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    base_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    openapi_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    openapi_title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    spec_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    spec_path: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    operation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    identities: Mapped[list[IdentityProfile]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class IdentityProfile(Base):
    """An authenticated or unauthenticated API identity."""

    __tablename__ = "identity_profiles"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "name",
            name="uq_identity_profiles_project_name",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    role: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        index=True,
    )

    tenant: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        index=True,
    )

    department: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
        index=True,
    )

    auth_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="none",
    )

    secret_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="environment",
    )

    secret_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    username_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    password_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    auth_location: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    auth_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    auth_prefix: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    project: Mapped[Project] = relationship(
        back_populates="identities",
    )
