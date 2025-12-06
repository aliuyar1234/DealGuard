# DealGuard

KI-gestützte Vertragsanalyse und Partner-Intelligence für KMU im DACH-Raum.

## Features (MVP)

- **Vertragsanalyse**: Upload von PDF/DOCX → KI-Analyse → Risiko-Score und Empfehlungen
- **Deutsches Recht**: Analyse nach BGB/HGB mit Fokus auf typische Vertragsrisiken
- **Risikokategorien**: Haftung, Zahlung, Kündigung, Gerichtsstand, IP, DSGVO, Gewährleistung

## Tech Stack

| Bereich | Technologie |
|---------|-------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2 |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Database | PostgreSQL 16 |
| Queue | Redis + ARQ |
| AI | Anthropic Claude API |
| Auth | Supabase Auth |
| Storage | S3-kompatibel (MinIO lokal) |

## Schnellstart

### Voraussetzungen

- Docker & Docker Compose
- Node.js 20+ (für lokale Frontend-Entwicklung)
- Python 3.12+ (für lokale Backend-Entwicklung)

### 1. Repository klonen

```bash
git clone <repo-url>
cd dealguard
```

### 2. Umgebungsvariablen konfigurieren

```bash
cp .env.example .env
# Bearbeiten und API-Keys eintragen:
# - ANTHROPIC_API_KEY
# - SUPABASE_* Variablen
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
- MinIO Console: http://localhost:9001 (minio/minio123)

## Entwicklung

### Backend (lokal ohne Docker)

```bash
cd backend

# Virtual Environment erstellen
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Dependencies installieren
pip install -e ".[dev]"

# Server starten
uvicorn dealguard.main:app --reload
```

### Frontend (lokal ohne Docker)

```bash
cd frontend

# Dependencies installieren
npm install

# Dev Server starten
npm run dev
```

### Nützliche Befehle

```bash
make help         # Alle Befehle anzeigen
make logs         # Logs aller Services
make test         # Tests ausführen
make lint         # Linter ausführen
make migrate      # Datenbank-Migrationen
make db-shell     # PostgreSQL Shell
```

## Projektstruktur

```
dealguard/
├── backend/
│   ├── src/dealguard/
│   │   ├── api/              # HTTP Routes
│   │   ├── domain/           # Business Logic
│   │   ├── infrastructure/   # External Services
│   │   └── shared/           # Cross-cutting
│   ├── alembic/              # DB Migrations
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js Pages
│   │   ├── components/       # React Components
│   │   └── lib/              # Utilities
│   └── public/
└── infrastructure/
    └── docker/
```

## API Endpunkte

### Contracts

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| POST | `/api/v1/contracts/` | Vertrag hochladen |
| GET | `/api/v1/contracts/` | Alle Verträge listen |
| GET | `/api/v1/contracts/{id}` | Vertrag mit Analyse |
| POST | `/api/v1/contracts/{id}/analyze` | Analyse starten |
| DELETE | `/api/v1/contracts/{id}` | Vertrag löschen |

### Health

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/v1/health` | Health Check |
| GET | `/api/v1/ready` | Readiness Check |

## Architektur

### Backend Layers

```
API Layer (FastAPI)
    ↓
Domain Layer (Pure Python - Business Logic)
    ↓
Infrastructure Layer (DB, AI, Storage)
```

### Multi-Tenant

Alle Daten sind per `organization_id` isoliert. Das Repository-Pattern stellt sicher, dass Queries automatisch gefiltert werden.

### Auth Abstraktion

Der `AuthProvider` ist abstrakt implementiert, sodass ein späterer Wechsel von Supabase zu Clerk nur eine neue Provider-Implementierung erfordert.

## Lizenz

Proprietary - All rights reserved
