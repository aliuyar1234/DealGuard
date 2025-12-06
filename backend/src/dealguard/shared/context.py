"""Request context for multi-tenant isolation."""

from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class TenantContext:
    """Context for the current request's tenant (organization)."""

    organization_id: UUID
    user_id: UUID
    user_email: str
    user_role: str

    def is_admin(self) -> bool:
        return self.user_role in ("owner", "admin")

    def is_owner(self) -> bool:
        return self.user_role == "owner"


# Context variable to hold tenant info for current request
_tenant_context: ContextVar[TenantContext | None] = ContextVar(
    "tenant_context", default=None
)


def set_tenant_context(ctx: TenantContext) -> None:
    """Set the tenant context for the current request."""
    _tenant_context.set(ctx)


def get_tenant_context() -> TenantContext:
    """Get the tenant context for the current request.

    Raises:
        RuntimeError: If no tenant context is set (e.g., unauthenticated request).
    """
    ctx = _tenant_context.get()
    if ctx is None:
        raise RuntimeError("Kein Tenant-Kontext verfügbar. Bitte einloggen.")
    return ctx


def get_optional_tenant_context() -> TenantContext | None:
    """Get the tenant context if available, None otherwise."""
    return _tenant_context.get()


def clear_tenant_context() -> None:
    """Clear the tenant context."""
    _tenant_context.set(None)
