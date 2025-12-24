# DealGuard

**Austrian Legal Infrastructure as a Service** - KI-gestützte Vertragsanalyse, Partner-Intelligence und Zugang zu echten österreichischen Rechtsdaten für KMU im DACH-Raum.

## Was macht DealGuard besonders?

DealGuard ist nicht nur ein Vertragsanalyse-Tool - es ist eine **vollständige Legal-Tech-Plattform** mit Zugang zu echten österreichischen Datenquellen:

### 🏛️ Austrian Legal Data APIs
- **RIS OGD**: Alle Bundesgesetze, OGH-Urteile - tagesaktuell und GRATIS
- **Ediktsdatei**: Insolvenzen, Versteigerungen, Pfändungen - GRATIS
- **OpenFirmenbuch**: Firmendaten, Geschäftsführer, Kapital - GRATIS
- **OpenSanctions**: EU/UN/US Sanktionslisten, PEP-Daten - GRATIS

### 📋 Features

| Feature | Beschreibung |
|---------|--------------|
| **Vertragsanalyse** | PDF/DOCX Upload → KI-Analyse → Risiko-Score + Empfehlungen |
| **Partner-Intelligence** | Bonitätsprüfung, Sanktions-Screening, Insolvenz-Check |
| **AI Legal Chat** | Fragen zu eigenen Verträgen mit echten Gesetzeszitaten |
| **Proaktives Monitoring** | Fristen-Wächter, Risk Radar, automatische Alerts |
| **MCP Server** | 13 Tools für Claude/LLMs mit echten Rechtsdaten |

### 🔍 Warum das Game-Changing ist

- **ABGB-Zitate sind ECHT** (aus RIS API, nicht halluziniert)
- **Insolvenz-Info ist ECHT** (aus Ediktsdatei)
- **Firmendaten sind ECHT** (aus OpenFirmenbuch)
- **Sanktionsprüfung ist ECHT** (aus OpenSanctions)
- **ChatGPT kann das NICHT** (kein Zugang zu diesen Datenquellen)

## Tech Stack

| Bereich | Technologie |
|---------|-------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Database | PostgreSQL 16 |
| Queue | Redis + ARQ |
| AI | Anthropic Claude / DeepSeek (wählbar) |
| Auth | Supabase Auth (Dev-Mode ohne Supabase möglich) |
| Storage | S3-kompatibel (MinIO lokal) |
| Edge/TLS | Caddy |
| Observability | Prometheus, Grafana, Loki, Alertmanager |
| Security | Gitleaks, Trivy, Bandit, ZAP (DAST) |

## Schnellstart

### Voraussetzungen

- Docker & Docker Compose
- Node.js 20+ (für lokale Frontend-Entwicklung)
- Python 3.12+ (für lokale Backend-Entwicklung)

### 1. Repository klonen

```bash
git clone https://github.com/aliuyar1234/DealGuard.git
cd DealGuard
```

### 2. Umgebungsvariablen konfigurieren

```bash
cp .env.example .env
# Bearbeiten und konfigurieren:
# - APP_SECRET_KEY (REQUIRED - generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
# - AI_PROVIDER=deepseek (günstiger) oder AI_PROVIDER=anthropic
# - DEEPSEEK_API_KEY oder ANTHROPIC_API_KEY
# - AUTH_PROVIDER=dev (kein Supabase nötig für lokale Entwicklung)
```

### 3. Services starten

```bash
# Alle Services starten (PostgreSQL, Redis, MinIO, Backend, Frontend)
make dev

# Oder nur Infrastruktur (für lokale Entwicklung)
make dev-infra
```

### 4. Datenbank migrieren

```bash
make migrate
```

### 5. Öffnen

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001 (MINIO_ROOT_USER / MINIO_ROOT_PASSWORD)

## Production (docker-compose.prod.yml)

### Secrets
- Secrets are provided via files in `secrets/` (Docker secrets).
- `docker compose` requires these files to exist.
- Core: `secrets/app_secret_key.txt`, `secrets/database_url.txt`, `secrets/database_sync_url.txt`, `secrets/postgres_password.txt`, `secrets/redis_url.txt`, `secrets/redis_password.txt`, `secrets/s3_access_key.txt`, `secrets/s3_secret_key.txt`
- Auth (Supabase, required in production): `secrets/supabase_jwt_secret.txt`, `secrets/supabase_service_role_key.txt`
- AI (provide at least one; the unused provider can be a dummy): `secrets/anthropic_api_key.txt`, `secrets/deepseek_api_key.txt`
- Optional (features): `secrets/minio_root_password.txt`, `secrets/grafana_admin_password.txt`, `secrets/alert_webhook_url.txt`

### Start
```bash
# Core services only
docker compose -f docker-compose.prod.yml up -d

# Full stack (observability + MinIO)
docker compose -f docker-compose.prod.yml --profile observability --profile minio up -d
```

### Observability
- Prometheus: http://localhost:9090 (localhost-only, `--profile observability`)
- Grafana: http://localhost:3001 (localhost-only, `--profile observability`)
- Alertmanager: http://localhost:9093 (localhost-only, `--profile observability`)
- `/metrics` is internal-only (not exposed by Caddy)

### Backups & Restore
- Postgres/MinIO backups run in `pg-backup` / `minio-backup`.
- Restore runbook: `deploy/backup-restore-runbook.md`

### CI Security (DAST)
- GitHub Actions runs OWASP ZAP when `STAGING_BASE_URL` secret is set.

### WAF/CDN (optional)
- Guide: `deploy/cdn-waf.md`


## MCP Server - Austrian Legal Tools

DealGuard stellt 13 MCP-Tools für LLMs bereit:

| Tool | Beschreibung | Datenquelle |
|------|-------------|-------------|
| `dealguard_search_ris` | Suche nach österreichischen Gesetzen | RIS OGD API |
| `dealguard_get_law_text` | Vollständiger Gesetzestext | RIS OGD API |
| `dealguard_search_insolvency` | Insolvenz-Suche | Ediktsdatei |
| `dealguard_search_companies` | Firmensuche Österreich | OpenFirmenbuch |
| `dealguard_get_company_details` | Firmenbuch-Auszug | OpenFirmenbuch |
| `dealguard_check_sanctions` | Sanktionslisten-Check | OpenSanctions |
| `dealguard_check_pep` | PEP-Prüfung | OpenSanctions |
| `dealguard_comprehensive_compliance` | Compliance-Gesamtprüfung | OpenSanctions |
| `dealguard_search_contracts` | Vertragssuche | DealGuard DB |
| `dealguard_get_contract` | Vertragsdetails | DealGuard DB |
| `dealguard_get_partners` | Partnerliste | DealGuard DB |
| `dealguard_get_deadlines` | Fristen-Übersicht | DealGuard DB |

## API Endpunkte

### Contracts
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| POST | `/api/v1/contracts/` | Vertrag hochladen |
| GET | `/api/v1/contracts/` | Alle Verträge listen |
| GET | `/api/v1/contracts/{id}` | Vertrag mit Analyse |
| POST | `/api/v1/contracts/{id}/analyze` | Analyse starten |

### Partners
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/v1/partners/` | Partner listen |
| POST | `/api/v1/partners/` | Partner anlegen |
| POST | `/api/v1/partners/{id}/checks` | Prüfungen starten |

### Chat (AI Legal Assistant)
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| POST | `/api/v2/chat` | Chat mit echten Rechtsdaten |
| GET | `/api/v2/chat/tools` | Verfügbare Tools |

### Settings
| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/v1/settings` | Einstellungen laden |
| PUT | `/api/v1/settings/api-keys` | API Keys speichern |

## Entwicklung

### Backend Tests

```bash
cd backend
python -m pytest tests/ -v
```

If Postgres is not on the default port, point the integration tests to your
container:

```bash
# Example (Postgres on localhost:5433)
TEST_DATABASE_URL=postgresql+asyncpg://dealguard:dealguard@localhost:5433/dealguard_test \
TEST_DATABASE_SYNC_URL=postgresql://dealguard:dealguard@localhost:5433/dealguard_test \
python -m pytest tests/ -v
```

To make Postgres-backed integration tests fail (instead of skipping) when the DB is unavailable:

```bash
REQUIRE_TEST_DB=1 python -m pytest -v
```

### Frontend Tests

```bash
cd frontend
npm test
```

## Projektstruktur

```
DealGuard/
├── backend/
│   ├── src/dealguard/
│   │   ├── api/              # HTTP Routes + Rate Limiting
│   │   ├── domain/           # Business Logic
│   │   │   ├── chat/         # AI Chat Service
│   │   │   ├── contracts/    # Vertragsanalyse
│   │   │   ├── legal/        # Legal Chat
│   │   │   ├── partners/     # Partner Intelligence
│   │   │   └── proactive/    # Alerts & Deadlines
│   │   ├── infrastructure/   # External Services
│   │   │   ├── ai/           # Anthropic/DeepSeek Clients
│   │   │   ├── auth/         # Supabase/Dev Auth
│   │   │   ├── database/     # SQLAlchemy Models
│   │   │   └── external/     # OpenFirmenbuch, OpenSanctions
│   │   ├── mcp/              # MCP Server + Tools
│   │   └── shared/           # Crypto, Logging
│   ├── alembic/              # DB Migrations
│   └── tests/                # Tests
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js Pages
│   │   ├── components/       # React Components
│   │   └── hooks/            # Custom Hooks
│   └── e2e/                  # Playwright Tests
├── docs/                     # Architecture Docs
├── deploy/                  # Production configs
├── docker-compose.yml
└── docker-compose.prod.yml
```

## Architektur

### Security
- **Encryption at Rest**: Vertragstext und API Keys mit Fernet verschlüsselt
- **Rate Limiting**: slowapi mit Redis Backend
- **Tenant Isolation**: Alle Queries per `organization_id` gefiltert

### Multi-Provider AI
- **Anthropic Claude**: Production (Claude Sonnet)
- **DeepSeek**: Development (~20x günstiger)
- Konfigurierbar per User-Settings

## Kosten

| Operation | DeepSeek | Anthropic |
|-----------|----------|-----------|
| Vertragsanalyse | ~€0.05 | ~€1.00 |
| Chat-Nachricht | ~€0.001 | ~€0.02 |
| Compliance-Check | GRATIS | GRATIS |

Die österreichischen Datenquellen (RIS, Ediktsdatei, OpenFirmenbuch, OpenSanctions) sind **kostenlos**.

## Lizenz

MIT License - Open Source

