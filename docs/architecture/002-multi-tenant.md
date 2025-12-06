# ADR-002: Multi-Tenant Architektur von Tag 1

## Status
**Accepted** (2024-12-04)

## Kontext

DealGuard ist B2B SaaS für KMU. Jede Firma (Organization) hat:
- Eigene Verträge
- Eigene User
- Eigene Quota/Limits

Optionen:
1. **Single-Tenant**: Separate DB pro Kunde
2. **Multi-Tenant Shared DB**: Eine DB, Daten via `organization_id` getrennt
3. **Hybrid**: Shared für kleine, dedicated für Enterprise

## Entscheidung

**Multi-Tenant Shared DB mit Row-Level Isolation**

Jede Tabelle hat `organization_id`:
```sql
CREATE TABLE contracts (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    -- ...
);
CREATE INDEX ix_contracts_organization_id ON contracts(organization_id);
```

**Automatische Filterung im Repository:**

```python
# backend/src/dealguard/infrastructure/database/repositories/base.py

class BaseRepository:
    async def get(self, id: UUID) -> T | None:
        ctx = get_tenant_context()
        return await self.session.execute(
            select(self.model)
            .where(self.model.id == id)
            .where(self.model.organization_id == ctx.organization_id)  # IMMER!
        )
```

**Tenant Context aus JWT:**

```python
# Middleware setzt Context pro Request
set_tenant_context(TenantContext(
    organization_id=user.organization_id,
    user_id=user.id,
    ...
))
```

## Konsequenzen

### Positiv
- Einfaches Setup (eine DB)
- Kostengünstig (keine separate Infrastruktur pro Kunde)
- Einfache Aggregationen über alle Kunden
- Tenant-Isolation ist automatisch (vergessen = unmöglich)

### Negativ
- Noisy Neighbor möglich (ein Kunde belastet alle)
- Keine physische Datentrennung (Compliance-Frage)
- Migration zu Single-Tenant später aufwändig

### Mitigations
- Rate Limiting pro Organization (Phase 4)
- Indexes auf `organization_id` für Performance
- Row-Level Security in PostgreSQL als Backup

## Referenzen

- `backend/src/dealguard/infrastructure/database/repositories/base.py`
- `backend/src/dealguard/shared/context.py`
- `backend/alembic/versions/001_initial.py` (alle Tabellen haben organization_id)
