"""User model."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dealguard.infrastructure.database.models.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
)

if TYPE_CHECKING:
    from dealguard.infrastructure.database.models.contract import Contract
    from dealguard.infrastructure.database.models.organization import Organization
    from dealguard.infrastructure.database.models.partner import Partner


class UserRole(str, Enum):
    """User roles within an organization."""

    OWNER = "owner"  # Full access including billing
    ADMIN = "admin"  # Full access except billing
    MEMBER = "member"  # Can perform analyses, view own
    VIEWER = "viewer"  # Read-only access


class User(Base, TimestampMixin, SoftDeleteMixin):
    """User model.

    Users belong to an organization and have a role within it.
    Authentication is handled by Supabase; we store the reference.
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Organization relationship
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Supabase auth reference
    supabase_user_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # User info
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        String(50),
        default=UserRole.MEMBER,
        nullable=False,
    )

    # Status
    email_verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # User settings
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="users",
    )
    contracts: Mapped[list["Contract"]] = relationship(
        "Contract",
        back_populates="created_by_user",
        foreign_keys="Contract.created_by",
    )
    partners: Mapped[list["Partner"]] = relationship(
        "Partner",
        back_populates="created_by_user",
        foreign_keys="Partner.created_by",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def is_admin(self) -> bool:
        return self.role in (UserRole.OWNER, UserRole.ADMIN)

    @property
    def is_owner(self) -> bool:
        return self.role == UserRole.OWNER

    @property
    def can_write(self) -> bool:
        return self.role in (UserRole.OWNER, UserRole.ADMIN, UserRole.MEMBER)
