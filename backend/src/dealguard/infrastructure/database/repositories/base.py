"""Base repository with tenant isolation."""

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dealguard.shared.context import get_tenant_context


class BaseRepository[T]:
    """Base repository with automatic tenant filtering.

    IMPORTANT: This base class ensures all queries are filtered by
    organization_id, preventing cross-tenant data access.

    All tenant-scoped repositories MUST inherit from this class.
    """

    model_class: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _get_organization_id(self) -> UUID:
        """Get the current tenant's organization ID."""
        return get_tenant_context().organization_id

    def _base_query(self, include_deleted: bool = False) -> Any:
        """Create a base query filtered by tenant and soft-delete status.

        All queries should start from this method to ensure tenant isolation.

        Args:
            include_deleted: If True, includes soft-deleted records (default: False)
        """
        model = cast(Any, self.model_class)
        query = select(model).where(model.organization_id == self._get_organization_id())
        if not include_deleted and hasattr(model, "deleted_at"):
            query = query.where(model.deleted_at.is_(None))
        return query

    @asynccontextmanager
    async def begin_nested(self) -> AsyncIterator[None]:
        """Begin a nested transaction scope for multi-step updates."""
        async with self.session.begin_nested():
            yield

    async def get_by_id(self, id: UUID) -> T | None:
        """Get entity by ID, filtered by tenant."""
        model = cast(Any, self.model_class)
        query = self._base_query().where(model.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[T]:
        """Get all entities for the current tenant."""
        model = cast(Any, self.model_class)
        query = (
            self._base_query()
            .order_by(model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(self) -> int:
        """Count entities for the current tenant."""
        query = select(func.count()).select_from(self._base_query().subquery())
        result = await self.session.execute(query)
        return result.scalar_one()

    async def create(self, entity: T) -> T:
        """Create a new entity.

        Automatically sets organization_id from context.
        """
        # Ensure organization_id is set
        entity_any = cast(Any, entity)
        if not hasattr(entity_any, "organization_id"):
            raise ValueError(f"{type(entity).__name__} is missing organization_id")
        entity_any.organization_id = self._get_organization_id()
        self.session.add(entity_any)
        await self.session.flush()
        await self.session.refresh(entity_any)
        return cast(T, entity_any)

    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: T) -> None:
        """Hard delete an entity.

        Consider using soft delete (setting deleted_at) instead.
        """
        await self.session.delete(entity)
        await self.session.flush()

    async def soft_delete(self, entity: T) -> T:
        """Soft delete an entity by setting deleted_at."""
        entity_any = cast(Any, entity)
        if not hasattr(entity_any, "deleted_at"):
            raise ValueError(f"{type(entity).__name__} does not support soft delete")
        entity_any.deleted_at = datetime.now(UTC)
        return await self.update(cast(T, entity_any))
