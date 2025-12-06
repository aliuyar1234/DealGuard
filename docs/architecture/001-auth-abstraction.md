# ADR-001: Auth-Abstraktion für Provider-Wechsel

## Status
**Accepted** (2024-12-04)

## Kontext

Wir starten mit Supabase Auth wegen:
- Kostenloser Tier für MVP
- Schnelles Setup
- Gute Next.js Integration

Später wollen wir zu Clerk wechseln wegen:
- Enterprise SSO (SAML, OIDC)
- Bessere Multi-Tenant Features
- Organizations out-of-the-box

Problem: Wie wechseln wir Auth-Provider ohne großes Refactoring?

## Entscheidung

**Abstraktion via Interface-Pattern:**

```python
# backend/src/dealguard/infrastructure/auth/provider.py

class AuthProvider(ABC):
    @abstractmethod
    async def verify_token(self, token: str) -> AuthUser:
        pass

    @abstractmethod
    async def get_user(self, user_id: str) -> AuthUser | None:
        pass

# Implementierungen:
# - SupabaseAuthProvider (jetzt)
# - ClerkAuthProvider (später)
```

**Dependency Injection in Middleware:**

```python
# backend/src/dealguard/api/middleware/auth.py

def get_auth_provider() -> AuthProvider:
    # Hier einfach Provider wechseln:
    return SupabaseAuthProvider()
    # return ClerkAuthProvider()
```

## Konsequenzen

### Positiv
- Provider-Wechsel = 1 Zeile ändern + neue Klasse
- Tests können MockAuthProvider nutzen
- Frontend bleibt unberührt (JWT ist JWT)

### Negativ
- Minimal mehr Code als direkte Supabase-Nutzung
- AuthUser muss alle Provider-Felder abdecken

### Neutral
- JWT-Validierung bleibt ähnlich (beide nutzen JWTs)
- User-Sync zwischen Providern muss manuell erfolgen

## Referenzen

- `backend/src/dealguard/infrastructure/auth/provider.py` - Interface
- `backend/src/dealguard/infrastructure/auth/supabase.py` - Implementierung
- `backend/src/dealguard/api/middleware/auth.py` - Usage
