"""Search index models for encrypted contract text."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from dealguard.infrastructure.database.models.base import Base


class ContractSearchToken(Base):
    """HMAC-hashed token index for contracts.

    Primary access pattern:
    - organization_id + token_hash -> contract_ids
    """

    __tablename__ = "contract_search_tokens"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    token_hash: Mapped[bytes] = mapped_column(
        LargeBinary(length=32),
        primary_key=True,
    )
    contract_id: Mapped[UUID] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
